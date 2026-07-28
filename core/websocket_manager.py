"""
core/websocket_manager.py
=========================
Gerenciamento de WebSocket para atualizacoes em tempo real.

Inspirado no ChatGPT que mostra tokens sendo gerados ao vivo.

Funcionalidades:
  - Conexoes WebSocket por conversa
  - Broadcast de eventos (tokens, steps, erros)
  - Keepalive automatico
  - Desconexao limpa
"""

import json
import time
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime

from ._common import logging, json, datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexoes WebSocket ativas."""

    def __init__(self):
        # conversation_id -> set of WebSocket connections
        self._connections: Dict[str, Set] = {}
        # connection_id -> metadata
        self._metadata: Dict[str, dict] = {}
        self._heartbeat_task = None

    async def connect(self, websocket, conversation_id: str, client_id: str = ""):
        """Aceita nova conexao WebSocket."""
        await websocket.accept()

        if conversation_id not in self._connections:
            self._connections[conversation_id] = set()

        conn_id = client_id or f"{conversation_id}_{id(websocket)}"
        self._connections[conversation_id].add(websocket)
        self._metadata[conn_id] = {
            "websocket": websocket,
            "conversation_id": conversation_id,
            "connected_at": datetime.now().isoformat(),
            "last_ping": time.time(),
        }

        logger.info("WebSocket connected: %s (total: %d)",
                     conn_id, len(self._connections.get(conversation_id, set())))

        # Envia confirmacao
        await self._send_to(websocket, {
            "type": "connected",
            "conversation_id": conversation_id,
            "client_id": conn_id,
            "timestamp": datetime.now().isoformat(),
        })

    async def disconnect(self, websocket, conversation_id: str):
        """Remove conexao WebSocket."""
        if conversation_id in self._connections:
            self._connections[conversation_id].discard(websocket)

            # Remove metadata
            for conn_id, meta in list(self._metadata.items()):
                if meta["websocket"] is websocket:
                    del self._metadata[conn_id]
                    break

            # Limpa conversa vazia
            if not self._connections[conversation_id]:
                del self._connections[conversation_id]

            logger.info("WebSocket disconnected from %s", conversation_id)

    async def broadcast(self, conversation_id: str, message: dict):
        """Envia mensagem para todas as conexoes de uma conversa."""
        if conversation_id not in self._connections:
            return

        dead = set()
        for ws in self._connections[conversation_id]:
            try:
                await self._send_to(ws, message)
            except Exception:
                dead.add(ws)

        # Remove conexoes mortas
        for ws in dead:
            self._connections[conversation_id].discard(ws)

    async def _send_to(self, websocket, message: dict):
        """Envia mensagem JSON para um WebSocket."""
        try:
            data = json.dumps(message, ensure_ascii=False, default=str)
            await websocket.send_text(data)
        except Exception as e:
            logger.warning("Failed to send WebSocket message: %s", e)
            raise

    async def send_token(self, conversation_id: str, token: str, model: str = ""):
        """Envia token incremental (streaming)."""
        await self.broadcast(conversation_id, {
            "type": "token",
            "content": token,
            "model": model,
            "timestamp": datetime.now().isoformat(),
        })

    async def send_step(self, conversation_id: str, step: str, tool_name: str = ""):
        """Envia notificacao de step (tool call, etc)."""
        await self.broadcast(conversation_id, {
            "type": "step",
            "text": step,
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
        })

    async def send_error(self, conversation_id: str, error: str):
        """Envia notificacao de erro."""
        await self.broadcast(conversation_id, {
            "type": "error",
            "message": error,
            "timestamp": datetime.now().isoformat(),
        })

    async def send_done(self, conversation_id: str, reply: str, stats: dict = None):
        """Envia notificacao de conclusao."""
        await self.broadcast(conversation_id, {
            "type": "done",
            "reply": reply,
            "stats": stats or {},
            "timestamp": datetime.now().isoformat(),
        })

    async def send_typing(self, conversation_id: str, is_typing: bool = True):
        """Envia indicador de digitacao."""
        await self.broadcast(conversation_id, {
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat(),
        })

    def get_connections(self, conversation_id: str = None) -> dict:
        """Retorna informacoes sobre conexoes ativas."""
        if conversation_id:
            conns = self._connections.get(conversation_id, set())
            return {
                "conversation_id": conversation_id,
                "count": len(conns),
            }

        total = sum(len(conns) for conns in self._connections.values())
        return {
            "total_connections": total,
            "active_conversations": len(self._connections),
            "conversations": {
                cid: len(conns)
                for cid, conns in self._connections.items()
            },
        }

    async def heartbeat_loop(self, interval: int = 30):
        """Loop de keepalive para manter conexoes vivas."""
        while True:
            try:
                await asyncio.sleep(interval)
                for conv_id in list(self._connections.keys()):
                    await self.broadcast(conv_id, {
                        "type": "ping",
                        "timestamp": datetime.now().isoformat(),
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Heartbeat error: %s", e)

    def start_heartbeat(self):
        """Inicia o loop de heartbeat."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            try:
                loop = asyncio.get_event_loop()
                self._heartbeat_task = loop.create_task(self.heartbeat_loop())
            except RuntimeError:
                pass

    def stop_heartbeat(self):
        """Para o loop de heartbeat."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()


# --- Instancia global ---
_manager = None


def get_ws_manager() -> ConnectionManager:
    """Retorna o gerenciador de WebSocket global."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


# --- Ferramentas para o agente ---

def websocket_status() -> str:
    """Ferramenta: retorna status das conexoes WebSocket."""
    manager = get_ws_manager()
    status = manager.get_connections()
    return json.dumps(status, indent=2, default=str)


def websocket_broadcast(conversation_id: str, message: str) -> str:
    """Ferramenta: envia mensagem para WebSocket de uma conversa."""
    manager = get_ws_manager()
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(manager.broadcast(conversation_id, {
            "type": "notification",
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }))
        return "Mensagem enviada para conversa %s" % conversation_id
    except Exception as e:
        return "Erro ao enviar: %s" % e
