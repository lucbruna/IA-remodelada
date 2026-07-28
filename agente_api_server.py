"""
agente_api_server.py
=====================
Servidor Web API (FastAPI) para o Agente Local — Versão ChatGPT-like.
Expõe todas as ferramentas via REST com streaming, upload de documentos,
múltiplas conversas e listagem de modelos.

COMO RODAR:
  python agente_api_server.py
  # Acessar: http://localhost:8000 (ChatGPT Web UI)
  # Acessar: http://localhost:8000/docs (Swagger UI)

DEPENDÊNCIAS:
  pip install fastapi uvicorn python-multipart
"""

import os
import sys
import json
import time
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import sys
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding and sys.stdout.encoding.upper() not in ('UTF-8', 'UTF8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# --- FastAPI --------------------------------------------------------
from fastapi import FastAPI, HTTPException, Body, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel, Field

# --- Agente Core ----------------------------------------------------
from agente_core import (
    SYSTEM_PROMPT, MODEL, run_agent_turn, run_agent_turn_async, run_agent_turn_stream_async,
    AVAILABLE_FUNCTIONS, TOOLS_LIST,
    list_memories, list_plugins, reload_plugins, get_system_info,
    export_conversation_markdown, export_conversation_html,
    session_save, session_load, session_list,
    DATA_DIR as CORE_DATA_DIR, ensure_ollama,
)

# --- Config ---------------------------------------------------------
from config import TEMPERATURE, NUM_CTX, MAX_TOKENS, TOP_P, TOP_K, REPEAT_PENALTY


HOST = os.environ.get("AGENTE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AGENTE_PORT", "8000"))
MODEL_NAME = os.environ.get("AGENTE_MODEL", MODEL)

# --- Diretórios -----------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERSATIONS_DIR = os.path.join(CORE_DATA_DIR, "conversations")
UPLOADS_DIR = os.path.join(CORE_DATA_DIR, "uploads")
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

CONVERSATIONS_INDEX = os.path.join(CONVERSATIONS_DIR, "index.json")


# --- Estado global para stop de geração ----------------------------
_stop_events: dict = {}  # conversation_id -> asyncio.Event
_active_streams: dict = {}  # conversation_id -> bool


def _get_stop_event(conv_id: str) -> asyncio.Event:
    if conv_id not in _stop_events:
        _stop_events[conv_id] = asyncio.Event()
    return _stop_events[conv_id]

def _reset_stop_event(conv_id: str):
    _stop_events[conv_id] = asyncio.Event()


# --- Schemas Pydantic ----------------------------------------------

class ChatParams(BaseModel):
    temperature: float = Field(default=TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=64, le=32768)
    num_ctx: int = Field(default=NUM_CTX, ge=2048, le=131072)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"
    model: str = MODEL_NAME
    params: Optional[ChatParams] = None

class ChatResponse(BaseModel):
    reply: str
    tool_calls: int = 0
    messages_count: int = 0

class RegenerateRequest(BaseModel):
    conversation_id: str = "default"
    model: str = MODEL_NAME
    message_index: Optional[int] = None
    params: Optional[ChatParams] = None

class EditMessageRequest(BaseModel):
    content: str

class ToolCallRequest(BaseModel):
    arguments: dict = {}

class MemoryItem(BaseModel):
    key: str
    value: str

class PluginInstallRequest(BaseModel):
    url: str

class ExportRequest(BaseModel):
    format: str = "md"
    conversation_id: str = "default"
    start_date: str = ""
    end_date: str = ""
    role_filter: str = ""

class ConversationCreate(BaseModel):
    title: str = "Nova Conversa"
    model: str = MODEL_NAME
    params: Optional[ChatParams] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    params: Optional[ChatParams] = None

class AutonomyUpdate(BaseModel):
    state: str
    note: str = ""

class EvidenceCreate(BaseModel):
    type: str
    result: str
    approved: bool = False

class EvaluationRequest(BaseModel):
    name: str
    command: str
    project: str = "."
    timeout_seconds: int = Field(default=300, ge=1, le=900)


# --- Sandbox Models ------------------------------------------------

class SandboxCreateProjectRequest(BaseModel):
    nome: str
    descricao: str = ""
    python_version: str = "3.11"
    requirements: str = ""
    cpu: float = 1.0
    memory_mb: int = 512
    timeout: int = 30

class SandboxExecuteRequest(BaseModel):
    codigo: str
    timeout: Optional[int] = None
    cpu: Optional[float] = None
    memory_mb: Optional[int] = None
    rede: bool = False

class SandboxCommandRequest(BaseModel):
    comando: str
    timeout: Optional[int] = None
    cpu: Optional[float] = None
    memory_mb: Optional[int] = None
    rede: bool = False

class SandboxInstallRequest(BaseModel):
    pacotes: str




# --- Gerenciamento de Conversas ------------------------------------

def _load_conv_index() -> dict:
    if os.path.exists(CONVERSATIONS_INDEX):
        try:
            with open(CONVERSATIONS_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"conversations": {}, "order": []}

def _save_conv_index(index: dict):
    with open(CONVERSATIONS_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def _conv_path(conv_id: str) -> str:
    return os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json")

def _load_conv_messages(conv_id: str) -> list:
    path = _conv_path(conv_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [{"role": "system", "content": SYSTEM_PROMPT}]

def _save_conv_messages(conv_id: str, messages: list):
    path = _conv_path(conv_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def _get_or_create_conv(conv_id: str, title: str = "Nova Conversa") -> dict:
    index = _load_conv_index()
    if conv_id not in index["conversations"]:
        index["conversations"][conv_id] = {
            "id": conv_id,
            "title": title,
            "model": MODEL_NAME,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
        }
        index["order"].insert(0, conv_id)
        _save_conv_index(index)
        # Ensure messages file exists
        if not os.path.exists(_conv_path(conv_id)):
            _save_conv_messages(conv_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    return index["conversations"][conv_id]

def _update_conv_meta(conv_id: str, **kwargs):
    index = _load_conv_index()
    if conv_id in index["conversations"]:
        index["conversations"][conv_id].update(kwargs)
        index["conversations"][conv_id]["updated_at"] = datetime.now().isoformat()
        _save_conv_index(index)


# --- Estado global --------------------------------------------------
conversation_start = time.time()
tool_call_count = 0


# --- App Setup -----------------------------------------------------

# --- Helpers para parâmetros do modelo ----------------------------

def _get_chat_options(params: Optional[ChatParams] = None) -> dict:
    """Retorna dicionario de opcoes para o Ollama com base nos parametros."""
    if params:
        opts = {
            "num_ctx": params.num_ctx,
            "temperature": params.temperature,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "repeat_penalty": REPEAT_PENALTY,
        }
    else:
        opts = {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "repeat_penalty": REPEAT_PENALTY,
        }
    return opts


# --- RAG: ChromaDB/Qdrant para busca semântica em documentos -------
# Usa o plugin RAG dedicado (plugins/plugin_rag.py)

RAG_AVAILABLE = False
RAG_COLLECTION = None
RAG_CLIENT = None
CHROMA_DIR = os.path.join(CORE_DATA_DIR, "chroma_db")

def _init_rag():
    """Inicializa RAG via plugin dedicado."""
    global RAG_AVAILABLE
    try:
        from plugins.plugin_rag import init_rag as plugin_init
        RAG_AVAILABLE = plugin_init(prefer="chromadb")
        if RAG_AVAILABLE:
            from plugins.plugin_rag import RAG_COLLECTION as COL, RAG_CLIENT as CL, RAG_DOCUMENT_COUNT
            global RAG_COLLECTION, RAG_CLIENT
            RAG_COLLECTION = COL
            RAG_CLIENT = CL
    except ImportError:
        print("  ⚠ RAG: plugin_rag.py não encontrado")
    except Exception as e:
        print(f"  ⚠ RAG: {e}")


def _index_document_in_rag(doc_id: str, text: str, metadata: dict = None):
    """Indexa um documento via plugin RAG."""
    try:
        from plugins.plugin_rag import index_document
        return index_document(doc_id, text, metadata)
    except ImportError:
        return False
    except Exception as e:
        print(f"  ⚠ Erro ao indexar no RAG: {e}")
        return False


def _search_rag(query: str, n_results: int = 3, where: dict = None) -> list:
    """Busca documentos via plugin RAG."""
    try:
        from plugins.plugin_rag import search_rag
        return search_rag(query, n_results, where=where)
    except ImportError:
        return []
    except Exception as e:
        print(f"  ⚠ Erro na busca RAG: {e}")
        return []


async def _ensure_ollama_async():
    """Garante que o Ollama esta rodando (auto-start) sem bloquear o event loop."""
    try:
        await asyncio.to_thread(ensure_ollama)
    except Exception as e:
        logging.warning("Falha ao tentar auto-iniciar o Ollama: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que a conversa default existe
    _get_or_create_conv("default", "Conversa Principal")
    # Inicializa RAG
    _init_rag()
    # Auto-inicia o Ollama (se nao estiver rodando) antes de aceitar requisicoes
    await _ensure_ollama_async()
    yield


app = FastAPI(
    title="🤖 Agente Local API — ChatGPT Edition",
    description="API completa com streaming, upload de documentos e múltiplas conversas.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Middleware (API key + rate limiting) ---
from core.api_security import security_middleware
app.middleware("http")(security_middleware)


# --- Página Inicial ------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redireciona para a interface web."""
    web_path = os.path.join(BASE_DIR, "agente_web.html")
    if os.path.exists(web_path):
        with open(web_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Agente Local</h1><p><a href='/docs'>API Docs</a></p>")


@app.get("/health")
async def health_check():
    """Health check endpoint para load balancers e monitoring."""
    ollama_ok = False
    try:
        await _ensure_ollama_async()
        ollama_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "model": MODEL_NAME,
        "tools": len(AVAILABLE_FUNCTIONS),
        "rag": RAG_AVAILABLE,
        "ollama": ollama_ok,
        "uptime_seconds": int(time.time() - conversation_start),
    }


# ====================================================================
# MÍDIA GERADA (FLUX, ComfyUI, Wan)
# ====================================================================

MEDIA_DIR = os.path.join(CORE_DATA_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

@app.get("/media/{filename}")
async def serve_media(filename: str):
    """Serve arquivos de mídia gerados (imagens, vídeos)."""
    from fastapi.responses import FileResponse
    safe_name = os.path.basename(filename)
    path = os.path.join(MEDIA_DIR, safe_name)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "Arquivo não encontrado")

@app.get("/media")
async def list_media():
    """Lista arquivos de mídia gerados."""
    files = []
    if os.path.exists(MEDIA_DIR):
        for f in sorted(os.listdir(MEDIA_DIR), reverse=True)[:50]:
            path = os.path.join(MEDIA_DIR, f)
            if os.path.isfile(path):
                ext = os.path.splitext(f)[1].lower()
                icon = "🎬" if ext in ('.mp4', '.webm', '.avi') else "🖼️"
                files.append({
                    "name": f,
                    "size": os.path.getsize(path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                    "url": f"/media/{f}",
                    "icon": icon,
                })
    return {"media": files, "total": len(files)}


# ====================================================================
# MODELOS
# ====================================================================

@app.get("/models")
async def list_models():
    """Lista todos os modelos disponíveis no Ollama local."""
    try:
        await _ensure_ollama_async()
        import ollama
        response = ollama.list()
        # Normaliza a resposta do Ollama (dict em versões antigas,
        # pydantic ListResponse em versões novas do cliente `ollama`).
        raw_models = response.get("models", []) if hasattr(response, "get") else getattr(response, "models", [])
        models = []
        for m in raw_models:
            # Em versões novas cada modelo é um objeto pydantic; extrai dict.
            if hasattr(m, "model_dump"):
                d = m.model_dump()
            elif isinstance(m, dict):
                d = m
            else:
                d = {}
            name = d.get("name") or d.get("model") or "?"
            details = d.get("details", {}) or {}
            models.append({
                "name": name,
                "size": d.get("size", 0),
                "modified_at": str(d.get("modified_at", "")),
                "parameter_size": details.get("parameter_size", ""),
                "quantization_level": details.get("quantization_level", ""),
                "family": details.get("family", ""),
            })
        return {"models": models, "active": MODEL_NAME}
    except ImportError:
        raise HTTPException(500, "Biblioteca ollama não instalada")
    except Exception as e:
        raise HTTPException(500, f"Erro ao listar modelos: {e}")

@app.get("/models/default")
async def get_default_model():
    """Retorna o modelo atualmente configurado."""
    return {"model": MODEL_NAME}


# ====================================================================
# CONVERSAS (Múltiplas)
# ====================================================================

@app.get("/conversations")
async def list_conversations():
    """Lista todas as conversas salvas."""
    index = _load_conv_index()
    convs = []
    for cid in index["order"]:
        if cid in index["conversations"]:
            convs.append(index["conversations"][cid])
    return {"conversations": convs}

@app.post("/conversations")
async def create_conversation(req: ConversationCreate):
    """Cria uma nova conversa."""
    conv_id = str(uuid.uuid4())[:8]
    _get_or_create_conv(conv_id, req.title)
    return {"id": conv_id, "title": req.title, "status": "created"}

@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Obtém metadados de uma conversa."""
    index = _load_conv_index()
    if conv_id not in index["conversations"]:
        raise HTTPException(404, "Conversa não encontrada")
    return index["conversations"][conv_id]

@app.patch("/conversations/{conv_id}")
async def update_conversation(conv_id: str, req: ConversationUpdate):
    """Atualiza título/modelo de uma conversa."""
    index = _load_conv_index()
    if conv_id not in index["conversations"]:
        raise HTTPException(404, "Conversa não encontrada")
    updates = {}
    if req.title:
        updates["title"] = req.title
    if req.model:
        updates["model"] = req.model
    _update_conv_meta(conv_id, **updates)
    return {"status": "updated"}

@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Apaga uma conversa e seus arquivos."""
    if conv_id == "default":
        raise HTTPException(400, "Não é possível apagar a conversa padrão")
    index = _load_conv_index()
    if conv_id in index["conversations"]:
        del index["conversations"][conv_id]
        if conv_id in index["order"]:
            index["order"].remove(conv_id)
        _save_conv_index(index)
        # Remove arquivo de mensagens
        msg_path = _conv_path(conv_id)
        if os.path.exists(msg_path):
            os.remove(msg_path)
    return {"status": "deleted"}

@app.get("/conversations/{conv_id}/messages")
async def get_conv_messages(conv_id: str, limit: int = Query(100, ge=1, le=500)):
    """Retorna mensagens de uma conversa específica."""
    messages = _load_conv_messages(conv_id)
    msgs = []
    for m in messages[-limit:]:
        if m.get("role") != "system":
            msgs.append({
                "role": m.get("role"),
                "content": m.get("content", ""),
                "timestamp": m.get("timestamp", ""),
            })
    return {"messages": msgs, "total": len(messages), "conversation_id": conv_id}

@app.post("/conversations/{conv_id}/clear")
async def clear_conv_messages(conv_id: str):
    """Limpa as mensagens de uma conversa."""
    _save_conv_messages(conv_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    _update_conv_meta(conv_id, message_count=0)
    return {"status": "cleared"}


# ====================================================================
# ====================================================================
# CHAT (normal + streaming + regenerar + editar + stop + RAG)
# ====================================================================

def _auto_title_conversation(conv_id: str, user_msg: str):
    """Gera título automático para a conversa baseado na primeira mensagem."""
    index = _load_conv_index()
    conv = index["conversations"].get(conv_id)
    if not conv or conv.get("title", "") not in ("Nova Conversa", ""):
        return
    title = user_msg.strip()[:60]
    if len(title) < 3:
        return
    title = title.rstrip(".!?:;, ")
    if len(title) > 50:
        title = title[:47] + "..."
    conv["title"] = title
    conv["updated_at"] = datetime.now().isoformat()
    _save_conv_index(index)


def _augment_with_rag(messages: list, user_msg: str, conv_id: str = "") -> list:
    """Aumenta as mensagens com contexto RAG se disponível.
    
    Usa o plugin RAG dedicado (plugins/plugin_rag.py) para buscar
    documentos relevantes e aumentar o system prompt.
    """
    if not RAG_AVAILABLE:
        return messages
    try:
        from plugins.plugin_rag import search_rag
        docs = search_rag(user_msg, where={"conversation_id": conv_id} if conv_id else None)
        if docs:
            context_text = "\n\n---\n**Documentos relevantes:**\n"
            for d in docs:
                preview = d['text'][:300].replace('{', '(').replace('}', ')')
                context_text += f"- {preview}\n"
            augmented = []
            for m in messages:
                if m.get("role") == "system":
                    aug_msg = dict(m)
                    aug_msg["content"] = m["content"] + context_text
                    augmented.append(aug_msg)
                else:
                    augmented.append(m)
            return augmented
    except Exception:
        pass
    return messages


def _normalize_model(model: Optional[str]) -> str:
    """Garante um nome de modelo válido.

    O frontend pode enviar modelo vazio, '?' ou None; nesses casos usamos
    o modelo padrão (MODEL_NAME) em vez de quebrar a chamada ao Ollama.
    """
    if not model or not str(model).strip() or str(model).strip() in ("?", "null", "None"):
        return MODEL_NAME
    return str(model).strip()


def _process_chat(conv_id: str, user_msg: str, model: str, stream: bool = False, params: Optional[ChatParams] = None):
    """Processa mensagem do chat — retorna resposta e contagem."""
    global tool_call_count

    # Carrega/garante conversa
    _get_or_create_conv(conv_id)
    messages = _load_conv_messages(conv_id)

    # Adiciona mensagem do usuário
    messages.append({
        "role": "user",
        "content": user_msg,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })

    started = time.perf_counter()
    try:
        steps = []
        def on_step(text):
            steps.append(text)

        # Determina qual modelo usar
        conv_model = _normalize_model(model)

        updated = run_agent_turn(messages, model=conv_model, on_step=on_step)
        messages[:] = updated

        # Extrai resposta
        reply = ""
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                reply = m["content"]
                break

        tool_call_count += len(steps)
        _save_conv_messages(conv_id, messages)
        _update_conv_meta(conv_id, message_count=len(messages))

        observer = AVAILABLE_FUNCTIONS.get("registrar_trace")
        if observer:
            observer("model", conv_model, True, (time.perf_counter() - started) * 1000, f"conversation={conv_id}; tools={len(steps)}")

        return reply, len(steps), len(messages)
    except Exception as e:
        observer = AVAILABLE_FUNCTIONS.get("registrar_trace")
        if observer:
            observer("model", model or MODEL_NAME, False, (time.perf_counter() - started) * 1000, str(e))
        if RAG_AVAILABLE:
            _index_document_in_rag(f"error-{uuid.uuid4().hex[:12]}", str(e), {"conversation_id": conv_id, "project_id": "default", "category": "error", "source": "chat"})
        raise HTTPException(500, f"Erro ao processar: {e}")


async def _process_chat_async(conv_id: str, user_msg: str, model: str, params: Optional[ChatParams] = None):
    """Versao assincrona de _process_chat.

    Roda o pipeline do agente em uma thread (asyncio.to_thread), liberando
    o event loop do FastAPI para atender outras requisicoes enquanto o
    Ollama processa (pode levar minutos).
    """
    global tool_call_count

    _get_or_create_conv(conv_id)
    messages = _load_conv_messages(conv_id)
    messages.append({
        "role": "user",
        "content": user_msg,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })

    started = time.perf_counter()
    try:
        steps = []
        def on_step(text):
            steps.append(text)

        conv_model = _normalize_model(model)
        updated = await run_agent_turn_async(messages, model=conv_model, on_step=on_step)
        messages[:] = updated

        reply = ""
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                reply = m["content"]
                break

        tool_call_count += len(steps)
        _save_conv_messages(conv_id, messages)
        _update_conv_meta(conv_id, message_count=len(messages))

        observer = AVAILABLE_FUNCTIONS.get("registrar_trace")
        if observer:
            observer("model", conv_model, True, (time.perf_counter() - started) * 1000, f"conversation={conv_id}; tools={len(steps)}")

        return reply, len(steps), len(messages)
    except Exception as e:
        observer = AVAILABLE_FUNCTIONS.get("registrar_trace")
        if observer:
            observer("model", model or MODEL_NAME, False, (time.perf_counter() - started) * 1000, str(e))
        if RAG_AVAILABLE:
            _index_document_in_rag(f"error-{uuid.uuid4().hex[:12]}", str(e), {"conversation_id": conv_id, "project_id": "default", "category": "error", "source": "chat"})
        raise HTTPException(500, f"Erro ao processar: {e}")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Envia mensagem e obtém resposta (não-streaming)."""
    await _ensure_ollama_async()
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(400, "Mensagem vazia")

    reply, steps, msg_count = await _process_chat_async(
        req.conversation_id, user_msg, req.model
    )
    return ChatResponse(
        reply=reply or "(sem resposta)",
        tool_calls=steps,
        messages_count=msg_count,
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Envia mensagem e obtém resposta via Server-Sent Events (streaming).

    Usa o pipeline unificado run_agent_turn (com parallel tool calls,
    download override, proteção de loop e streaming de tokens) executado
    em thread, transmitindo tokens e passos em tempo real via SSE.
    """
    await _ensure_ollama_async()
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(400, "Mensagem vazia")

    conv_id = req.conversation_id
    model = _normalize_model(req.model)

    _reset_stop_event(conv_id)
    _active_streams[conv_id] = True

    _get_or_create_conv(conv_id)
    messages = _load_conv_messages(conv_id)
    _auto_title_conversation(conv_id, user_msg)
    messages.append({
        "role": "user",
        "content": user_msg,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })
    _save_conv_messages(conv_id, messages)

    import asyncio
    from asyncio import Queue

    queue: Queue = Queue()

    async def event_generator():
        stop_event = _get_stop_event(conv_id)
        yield "data: {\"type\":\"start\"}\n\n"
        try:
            # Executa o pipeline em thread; tokens/step chegam na queue.
            run_task = asyncio.create_task(
                run_agent_turn_stream_async(messages, model=model, queue=queue)
            )
            updated = None
            while True:
                if stop_event.is_set() or not _active_streams.get(conv_id, True):
                    yield f"data: {json.dumps({'type': 'stopped'})}\n\n"
                    break
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if run_task.done():
                        updated = run_task.result()
                        break
                    continue
                if kind == "token":
                    yield f"data: {json.dumps({'type': 'token', 'content': payload})}\n\n"
                elif kind == "step":
                    yield f"data: {json.dumps({'type': 'step', 'text': payload})}\n\n"

            if updated is None and run_task.done():
                updated = run_task.result()
            elif updated is None:
                updated = await run_task

            full_reply = ""
            for m in reversed(updated):
                if m.get("role") == "assistant" and m.get("content"):
                    full_reply = m["content"]
                    break

            messages[:] = updated
            _save_conv_messages(conv_id, messages)
            _update_conv_meta(conv_id, message_count=len(messages))
            _active_streams[conv_id] = False
            yield f"data: {json.dumps({'type': 'done', 'reply': full_reply, 'messages_count': len(messages)})}\n\n"
        except Exception as e:
            _active_streams[conv_id] = False
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            _active_streams[conv_id] = False
            yield "data: {\"type\":\"close\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Regenerar resposta ---------------------------------------------

@app.post("/chat/regenerate")
async def chat_regenerate(req: RegenerateRequest):
    """Regenera a última resposta do assistente (ou de um índice específico)."""
    await _ensure_ollama_async()
    conv_id = req.conversation_id
    model = _normalize_model(req.model)

    messages = _load_conv_messages(conv_id)
    if not messages:
        raise HTTPException(400, "Conversa vazia")

    # Remove a última resposta do assistente
    if req.message_index is not None:
        # Remove mensagem específica e tudo depois dela
        idx = req.message_index
        if idx < len(messages):
            messages = messages[:idx]
    else:
        # Remove a última resposta do assistente
        removed = False
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "assistant":
                messages = messages[:i]
                removed = True
                break
        if not removed:
            raise HTTPException(400, "Nenhuma resposta do assistente para regenerar")

    _save_conv_messages(conv_id, messages)

    # Pega a última mensagem do usuário para reenviar
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    if not last_user_msg:
        raise HTTPException(400, "Nenhuma mensagem do usuário para responder")

    # Reenvia (em thread p/ nao bloquear o event loop)
    reply, steps, msg_count = await _process_chat_async(
        conv_id, last_user_msg, model
    )
    return ChatResponse(
        reply=reply or "(sem resposta)",
        tool_calls=steps,
        messages_count=msg_count,
    )


# --- Editar mensagem ------------------------------------------------

@app.patch("/conversations/{conv_id}/messages/{msg_idx}")
async def edit_message(conv_id: str, msg_idx: int, req: EditMessageRequest):
    """Edita o conteúdo de uma mensagem específica."""
    if not req.content.strip():
        raise HTTPException(400, "Conteúdo vazio")

    messages = _load_conv_messages(conv_id)
    if msg_idx < 0 or msg_idx >= len(messages):
        raise HTTPException(404, "Mensagem não encontrada")

    messages[msg_idx]["content"] = req.content
    messages[msg_idx]["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    messages[msg_idx]["edited"] = True

    # Remove mensagens após a editada (para manter consistência)
    messages = messages[:msg_idx + 1]

    _save_conv_messages(conv_id, messages)
    _update_conv_meta(conv_id, message_count=len(messages))

    return {"status": "ok", "message_index": msg_idx}


# --- Parar geração --------------------------------------------------

@app.post("/chat/stop")
async def chat_stop(conv_id: str = Body("default", embed=True)):
    """Para a geração em andamento em uma conversa."""
    event = _get_stop_event(conv_id)
    event.set()
    _active_streams[conv_id] = False
    return {"status": "stopped", "conversation_id": conv_id}


@app.post("/chat/export")
async def export_conversation(req: ExportRequest):
    """Exporta conversa em Markdown ou HTML."""
    conv_id = req.conversation_id
    messages = _load_conv_messages(conv_id)

    if req.format == "html":
        result = export_conversation_html(
            messages, start_date=req.start_date,
            end_date=req.end_date, role_filter=req.role_filter,
        )
    else:
        result = export_conversation_markdown(
            messages, start_date=req.start_date,
            end_date=req.end_date, role_filter=req.role_filter,
        )
    if "Erro" in result:
        raise HTTPException(500, result)
    return {"status": "ok", "result": result}


# ====================================================================
# UPLOAD DE DOCUMENTOS
# ====================================================================

UPLOAD_TYPES = {
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.pdf': 'application/pdf',
    '.csv': 'text/csv',
    '.json': 'application/json',
    '.py': 'text/x-python',
    '.js': 'text/javascript',
    '.html': 'text/html',
    '.css': 'text/css',
    '.xml': 'text/xml',
    '.yaml': 'text/yaml',
    '.yml': 'text/yaml',
    '.log': 'text/plain',
    '.toml': 'text/plain',
    '.ini': 'text/plain',
    '.cfg': 'text/plain',
    '.env': 'text/plain',
    '.sql': 'text/plain',
    '.sh': 'text/x-shellscript',
    '.bat': 'text/x-shellscript',
    '.ps1': 'text/x-shellscript',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str = Query("default"),
    project_id: str = Query(""),
):
    """Faz upload de um arquivo para uso na conversa."""
    if not file.filename:
        raise HTTPException(400, "Arquivo sem nome")

    # Sanitiza nome
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ").strip()
    if not safe_name:
        safe_name = f"file_{uuid.uuid4()[:8]}"

    ext = os.path.splitext(safe_name)[1].lower()
    file_id = str(uuid.uuid4())[:8]
    saved_name = f"{file_id}_{safe_name}"
    save_path = os.path.join(UPLOADS_DIR, saved_name)

    # Salva arquivo
    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        file_size = len(content)
        file_type = UPLOAD_TYPES.get(ext, "application/octet-stream")

        # Tenta extrair texto
        extracted_text = ""
        if ext in ('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
                    '.log', '.toml', '.ini', '.cfg', '.env', '.sql', '.sh', '.bat', '.ps1'):
            try:
                extracted_text = content.decode("utf-8", errors="replace")
            except Exception:
                extracted_text = "(não foi possível decodificar o texto)"
        elif ext == '.pdf':
            try:
                import PyPDF2
                import io
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                extracted_text = "(não foi possível extrair texto do PDF)"
        elif ext in ('.png', '.jpg', '.jpeg', '.gif'):
            extracted_text = f"[Imagem: {safe_name} ({file_size} bytes)]"
        elif ext == '.csv':
            try:
                extracted_text = content.decode("utf-8", errors="replace")[:5000]
            except Exception:
                extracted_text = "(não foi possível ler o CSV)"

        # Indexa no RAG se tiver texto extraído
        if extracted_text and extracted_text != "(não foi possível decodificar o texto)" and not extracted_text.startswith("["):
            indexed = _index_document_in_rag(
                file_id,
                extracted_text,
                metadata={"filename": safe_name, "conversation_id": conversation_id, "project_id": project_id or "default", "category": "document"}
            )
            if indexed:
                print(f"  📚 Documento indexado no RAG: {safe_name} ({len(extracted_text)} chars)")

        # Adiciona à conversa se tiver texto extraído
        if extracted_text and conversation_id:
            # Limita o texto
            text_preview = extracted_text[:3000]
            if len(extracted_text) > 3000:
                text_preview += f"\n\n[...arquivo completo salvo em: {save_path}]"

            messages = _load_conv_messages(conversation_id)
            messages.append({
                "role": "user",
                "content": f"📄 **Arquivo enviado: {safe_name}**\n```\n{text_preview}\n```",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "metadata": {"file": safe_name, "path": save_path, "size": file_size},
            })
            _save_conv_messages(conversation_id, messages)
            _update_conv_meta(conversation_id, message_count=len(messages))

        return {
            "status": "ok",
            "file": safe_name,
            "size": file_size,
            "type": file_type,
            "path": save_path,
            "extracted_chars": len(extracted_text),
            "conversation_id": conversation_id,
        }

    except Exception as e:
        raise HTTPException(500, f"Erro ao salvar arquivo: {e}")


# ====================================================================
# ORQUESTRADOR MESTRE (CEO + agentes + Self-Reflection)
# ====================================================================

@app.get("/orchestrate/agents")
async def orchestrate_list_agents():
    """Lista agentes disponíveis para orquestração."""
    from agente_core import AVAILABLE_FUNCTIONS
    subagentes = [
        {"name": name, "description": "Subagente especializado"}
        for name in sorted(AVAILABLE_FUNCTIONS.keys())
        if name.startswith("subagente_")
    ]
    return {"agents": subagentes, "total": len(subagentes)}


@app.post("/orchestrate")
async def orchestrate(
    task: str = Body(..., embed=True),
    context: str = Body("", embed=True),
    model: str = Body("", embed=True),
):
    """Executa o Orquestrador Mestre com streaming SSE de progresso."""
    from orquestrador_mestre import OrquestradorMestre

    await _ensure_ollama_async()
    orb = OrquestradorMestre(model=_normalize_model(model))

    async def event_generator() -> AsyncGenerator[str, None]:
        yield "data: {\"type\":\"orchestrate_start\"}\n\n"

        try:
            for step in orb.executar(task, context):
                data = {
                    "type": "orchestrate_step",
                    "status": step.get("status", ""),
                    "agente": step.get("agente", ""),
                    "mensagem": step.get("mensagem", ""),
                    "progresso": step.get("progresso", 0),
                }

                # Inclui resultado parcial se disponível
                if "resultado" in step:
                    data["resultado"] = step["resultado"]
                if "revisao" in step:
                    data["revisao"] = step["revisao"]
                if "tempo" in step:
                    data["tempo"] = step["tempo"]
                if "ordem" in step:
                    data["ordem"] = step["ordem"]
                if "resultado_final" in step:
                    data["resultado_final"] = step["resultado_final"]

                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            yield "data: {\"type\":\"orchestrate_done\"}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            yield "data: {\"type\":\"close\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ====================================================================
# FERRAMENTAS
# ====================================================================

@app.get("/tools", response_model=dict)
async def list_tools():
    """Lista todas as ferramentas disponíveis com descrições e parâmetros."""
    tools = {}
    for t in TOOLS_LIST:
        fn = t.get("function", {})
        name = fn.get("name", "?")
        tools[name] = {
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {}).get("properties", {}),
            "required": fn.get("parameters", {}).get("required", []),
        }
    return {"total": len(tools), "tools": tools}

@app.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Retorna informações de uma ferramenta específica."""
    func = AVAILABLE_FUNCTIONS.get(tool_name)
    if not func:
        raise HTTPException(404, f"Ferramenta '{tool_name}' não encontrada")
    for t in TOOLS_LIST:
        fn = t.get("function", {})
        if fn.get("name") == tool_name:
            return {
                "name": tool_name,
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}).get("properties", {}),
                "required": fn.get("parameters", {}).get("required", []),
            }
    return {"name": tool_name, "note": "Ferramenta carregada mas sem metadados"}

@app.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, args: ToolCallRequest = Body(default_factory=ToolCallRequest)):
    """Chama uma ferramenta específica com argumentos."""
    func = AVAILABLE_FUNCTIONS.get(tool_name)
    if not func:
        raise HTTPException(404, f"Ferramenta '{tool_name}' não encontrada")
    tool_args = dict(args.arguments)
    approval_id = str(tool_args.pop("_approval_id", ""))
    high_impact = {
        "run_command", "pip_install", "git_clone", "docker_run", "process_kill",
        "send_email", "delete_path", "move_file", "password_save", "mcp_call",
        "download_file", "install_plugin",
    }
    policy = AVAILABLE_FUNCTIONS.get("verificar_aprovacao")
    if tool_name in high_impact and policy:
        decision = policy(approval_id, tool_name)
        if decision != "aprovada":
            raise HTTPException(403, f"Ação requer aprovação válida: {decision}")
    try:
        result = func(**tool_args)
        return {"status": "ok", "tool": tool_name, "result": str(result)}
    except TypeError as e:
        raise HTTPException(400, f"Argumentos inválidos: {e}")
    except Exception as e:
        raise HTTPException(500, f"Erro ao executar: {e}")


# ====================================================================
# FLUXO AUTONOMO PERSISTENTE
# ====================================================================

@app.get("/autonomy/tasks")
async def autonomy_tasks(task_id: str = "", limit: int = 20):
    """Retorna tarefas, estados, historico e evidencias em formato estruturado."""
    func = AVAILABLE_FUNCTIONS.get("listar_tarefas_estruturadas")
    if not func:
        raise HTTPException(503, "Plugin de fluxo autonomo nao carregado")
    return {"tasks": func(task_id=task_id, limite=limit), "updated_at": datetime.now().isoformat()}


@app.post("/autonomy/tasks")
async def autonomy_start(
    objective: str = Body(..., embed=True),
    folder: str = Body("", embed=True),
    plan: str = Body("", embed=True),
):
    """Registra uma nova tarefa autonoma sem executar acao externa."""
    func = AVAILABLE_FUNCTIONS.get("iniciar_fluxo")
    if not func:
        raise HTTPException(503, "Plugin de fluxo autonomo nao carregado")
    return {"result": func(objetivo=objective, pasta=folder, plano=plan)}


@app.patch("/autonomy/tasks/{task_id}")
async def autonomy_update(task_id: str, req: AutonomyUpdate):
    func = AVAILABLE_FUNCTIONS.get("atualizar_fluxo")
    if not func: raise HTTPException(503, "Plugin de fluxo autonomo nao carregado")
    return {"result": func(task_id=task_id, estado=req.state, nota=req.note)}


@app.post("/autonomy/tasks/{task_id}/evidence")
async def autonomy_evidence(task_id: str, req: EvidenceCreate):
    func = AVAILABLE_FUNCTIONS.get("registrar_evidencia")
    if not func: raise HTTPException(503, "Plugin de fluxo autonomo nao carregado")
    return {"result": func(task_id=task_id, tipo=req.type, resultado=req.result, aprovado=req.approved)}


@app.get("/autonomy/events")
async def autonomy_events():
    """SSE: envia snapshot quando tarefas/evidencias forem alteradas."""
    async def stream():
        previous = ""
        while True:
            func = AVAILABLE_FUNCTIONS.get("listar_tarefas_estruturadas")
            tasks = func(limite=100) if func else []
            payload = json.dumps({"tasks": tasks, "timestamp": datetime.now().isoformat()}, ensure_ascii=False)
            if payload != previous:
                yield f"event: tasks\ndata: {payload}\n\n"
                previous = payload
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/evaluations")
async def evaluations_report():
    func = AVAILABLE_FUNCTIONS.get("relatorio_avaliacoes")
    if not func: raise HTTPException(503, "Plugin de avaliacoes nao carregado")
    return func()


@app.post("/evaluations")
async def evaluations_run(req: EvaluationRequest):
    func = AVAILABLE_FUNCTIONS.get("executar_avaliacao")
    if not func: raise HTTPException(503, "Plugin de avaliacoes nao carregado")
    return json.loads(func(req.name, req.command, req.project, req.timeout_seconds))


# ====================================================================
# SANDBOX — Controle do Sandbox Docker via API HTTP
# ====================================================================

@app.get("/sandbox/status")
async def sandbox_status_api():
    """Retorna status detalhado do Sandbox Docker.

    Inclui: disponibilidade do Docker, projetos ativos,
    execucoes realizadas, taxa de sucesso e configuracoes atuais.
    """
    func = AVAILABLE_FUNCTIONS.get("sandbox_status")
    if not func:
        raise HTTPException(503, "Plugin de sandbox nao carregado")
    return {"status": "ok", "result": func()}


@app.post("/sandbox/projects")
async def sandbox_create_project_api(req: SandboxCreateProjectRequest):
    """Cria um novo projeto sandbox com isolamento Docker.

    Define CPU, RAM, versao Python e dependencias iniciais.
    Gera automaticamente uma imagem Docker personalizada para o projeto.

    Args:
        nome: Nome do projeto
        descricao: Descricao opcional
        python_version: Versao Python (ex: 3.11, 3.12)
        requirements: Pacotes pip separados por espaco
        cpu: Limite de CPUs (fracao, ex: 0.5)
        memory_mb: Limite de RAM em MB
        timeout: Timeout padrao em segundos

    Returns:
        Mensagem de confirmacao com detalhes do projeto
    """
    from plugins.plugin_sandbox import sandbox_criar_projeto
    result = sandbox_criar_projeto(
        nome=req.nome,
        descricao=req.descricao,
        python_version=req.python_version,
        requirements=req.requirements,
        cpu=req.cpu,
        memory_mb=req.memory_mb,
        timeout=req.timeout,
    )
    return {"status": "ok", "result": result}


@app.get("/sandbox/projects")
async def sandbox_list_projects_api():
    """Lista todos os projetos sandbox criados.

    Retorna informacoes detalhadas de cada projeto:
    nome, CPU, RAM, numero de execucoes, ultima atividade.
    """
    from plugins.plugin_sandbox import sandbox_listar_projetos
    result = sandbox_listar_projetos()
    return {"status": "ok", "result": result}


@app.get("/sandbox/projects/{project_name}")
async def sandbox_get_project_api(project_name: str):
    """Retorna informacoes detalhadas de um projeto sandbox especifico.

    Args:
        project_name: Nome do projeto

    Returns:
        Metadados do projeto ou erro 404 se nao encontrado
    """
    from plugins.plugin_sandbox import sandbox_info_projeto
    result = sandbox_info_projeto(project_name)
    if not result.get("existe"):
        raise HTTPException(404, result.get("mensagem", "Projeto nao encontrado"))
    return {"status": "ok", "project": project_name, "metadata": result}


@app.delete("/sandbox/projects/{project_name}")
async def sandbox_delete_project_api(project_name: str):
    """Exclui um projeto sandbox e sua imagem Docker.

    Args:
        project_name: Nome do projeto

    Returns:
        Mensagem de confirmacao
    """
    from plugins.plugin_sandbox import sandbox_excluir_projeto
    result = sandbox_excluir_projeto(nome=project_name)
    return {"status": "ok", "result": result}


@app.post("/sandbox/projects/{project_name}/execute")
async def sandbox_execute_api(project_name: str, req: SandboxExecuteRequest):
    """Executa codigo Python no sandbox Docker com isolamento completo.

    O codigo e executado em container efemero com:
    - Sistema de arquivos read-only (exceto /tmp)
    - Rede bloqueada (padrao)
    - CPU e RAM limitados
    - Fallback para subprocess se Docker indisponivel

    Args:
        project_name: Nome do projeto
        codigo: Codigo Python a executar
        timeout: Timeout em segundos (usa config do projeto se None)
        cpu: Limite de CPUs (usa config do projeto se None)
        memory_mb: Limite de RAM (usa config do projeto se None)
        rede: Se True, ativa rede (padrao: False)

    Returns:
        Resultado da execucao com saida, tempo e recursos
    """
    from plugins.plugin_sandbox import sandbox_executar
    result = sandbox_executar(
        projeto=project_name,
        codigo=req.codigo,
        timeout=req.timeout,
        cpu=req.cpu,
        memory_mb=req.memory_mb,
        rede=req.rede,
    )
    return {"status": "ok", "result": result}


@app.post("/sandbox/projects/{project_name}/command")
async def sandbox_command_api(project_name: str, req: SandboxCommandRequest):
    """Executa um comando shell arbitrário no sandbox Docker.

    Args:
        project_name: Nome do projeto
        comando: Comando shell a executar
        timeout: Timeout em segundos
        cpu: Limite de CPUs
        memory_mb: Limite de RAM
        rede: Se True, ativa rede

    Returns:
        JSON com saida, exit_code, duracao
    """
    from plugins.plugin_sandbox import sandbox_executar_comando
    result = sandbox_executar_comando(
        projeto=project_name,
        comando=req.comando,
        timeout=req.timeout,
        cpu=req.cpu,
        memory_mb=req.memory_mb,
        rede=req.rede,
    )
    return {"status": "ok", "result": result}


@app.post("/sandbox/projects/{project_name}/install")
async def sandbox_install_api(project_name: str, req: SandboxInstallRequest):
    """Instala pacotes pip no projeto e reconstroi a imagem Docker.

    Args:
        project_name: Nome do projeto
        pacotes: Pacotes pip separados por espaco (ex: 'numpy pandas')

    Returns:
        Resultado da instalacao
    """
    from plugins.plugin_sandbox import sandbox_instalar_pacotes
    result = sandbox_instalar_pacotes(
        projeto=project_name,
        pacotes=req.pacotes,
    )
    return {"status": "ok", "result": result}


@app.get("/sandbox/history")
async def sandbox_history_api(projeto: str = Query(""), limite: int = Query(10, ge=1, le=100)):
    """Retorna historico de execucoes no sandbox.

    Args:
        projeto: Filtrar por projeto (opcional, vazio = todos)
        limite: Maximo de registros (padrao: 10, max: 100)

    Returns:
        Lista de execucoes com timestamp, duracao, erro
    """
    from plugins.plugin_sandbox import sandbox_historico
    result = sandbox_historico(projeto=projeto, limite=limite)
    return {"status": "ok", "result": result}


@app.get("/sandbox/images")
async def sandbox_images_api():
    """Lista imagens Docker dos projetos sandbox.

    Retorna todas as imagens Docker que comecam com 'sandbox_'.
    """
    from plugins.plugin_sandbox import sandbox_imagens
    result = sandbox_imagens()
    return {"status": "ok", "result": result}


@app.post("/sandbox/cache/clear")
async def sandbox_clear_cache_api():
    """Limpa imagens Docker nao utilizadas dos projetos sandbox.

    Remove imagens com prefixo 'sandbox_' que nao estao em uso.
    Libera espaco em disco.
    """
    from plugins.plugin_sandbox import sandbox_limpar_cache
    result = sandbox_limpar_cache()
    return {"status": "ok", "result": result}


@app.get("/observability")
async def observability_report():
    func = AVAILABLE_FUNCTIONS.get("resumo_observabilidade")
    if not func: raise HTTPException(503, "Plugin de observabilidade nao carregado")
    return func()


# ====================================================================
# MEMÓRIA
# ====================================================================

@app.get("/memory")
async def get_memory():
    """Lista todos os fatos na memória de longo prazo."""
    return {"memories": list_memories()}

@app.post("/memory")
async def add_memory(item: MemoryItem):
    """Adiciona um fato à memória de longo prazo."""
    from agente_core import remember
    result = remember(item.key, item.value)
    return {"status": "ok", "result": result}

@app.delete("/memory/{key}")
async def delete_memory(key: str):
    """Remove um fato da memória."""
    from agente_core import forget
    result = forget(key)
    return {"status": "ok", "result": result}


# ====================================================================
# PLUGINS
# ====================================================================

@app.get("/plugins")
async def get_plugins():
    """Lista todos os plugins carregados."""
    return {"plugins": list_plugins()}

@app.post("/plugins/reload")
async def reload_plugins_endpoint():
    """Recarrega todos os plugins do disco."""
    result = reload_plugins()
    return {"status": "ok", "result": result}

@app.post("/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    """Instala um plugin a partir de uma URL."""
    try:
        import urllib.request
        filename = req.url.split("/")[-1]
        if not filename.endswith(".py"):
            filename += ".py"
        plugins_dir = os.path.join(BASE_DIR, "plugins")
        dest = os.path.join(plugins_dir, filename)
        urllib.request.urlretrieve(req.url, dest)
        result = reload_plugins()
        return {"status": "ok", "file": filename, "reload": result}
    except Exception as e:
        raise HTTPException(500, f"Erro ao instalar plugin: {e}")


# ====================================================================
# PLAYWRIGHT — Navegacao Web via API HTTP
# ====================================================================

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "agente_data", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


@app.get("/playwright/status")
async def playwright_status_api():
    """Retorna o status atual do navegador Playwright (abas, URLs, ativa)."""
    from plugins.plugin_playwright import playwright_status
    raw = playwright_status()
    # Parse para JSON
    lines = raw.split("\n")
    result = {"raw": raw, "browser": "Fechado", "tabs": 0, "active_tab": None, "screenshots": 0}
    for line in lines:
        line = line.strip()
        if "Browser:" in line:
            result["browser"] = line.split(":", 1)[-1].strip()
        elif "Abas abertas:" in line:
            result["tabs"] = int(line.split(":")[-1].strip())
        elif "Aba ativa:" in line:
            val = line.split(":", 1)[-1].strip()
            if val != "nenhuma":
                result["active_tab"] = val
        elif "Screenshots salvos:" in line:
            try:
                result["screenshots"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
    # Lista as abas em detalhe
    tabs_list = []
    for line in lines:
        line = line.strip()
        if line.startswith("[") and "]" in line:
            tab_id = line.split("]")[0].strip("[")
            resto = line.split("]", 1)[-1].strip()
            is_active = "<- ATIVA" in resto
            url_line_idx = lines.index(line) + 1
            url = ""
            if url_line_idx < len(lines):
                url_candidate = lines[url_line_idx].strip()
                if url_candidate and not url_candidate.startswith("["):
                    url = url_candidate.replace("<- ATIVA", "").strip()
            tabs_list.append({
                "id": tab_id,
                "title": resto.replace("<- ATIVA", "").strip(),
                "url": url,
                "active": is_active,
            })
    result["tabs_detail"] = tabs_list
    result["available"] = result["browser"] != "Fechado"
    return result


class PlaywrightNavigateRequest(BaseModel):
    url: str
    wait_until: str = "networkidle"
    timeout: int = 30000
    headless: bool = True

@app.post("/playwright/navigate")
async def playwright_navigate_api(req: PlaywrightNavigateRequest):
    """Navega para uma URL no navegador Playwright."""
    from plugins.plugin_playwright import playwright_navigate, playwright_get_url, playwright_get_title
    result = playwright_navigate(url=req.url, wait_until=req.wait_until,
                                 timeout=req.timeout, headless=req.headless)
    url_atual = playwright_get_url()
    titulo = playwright_get_title()
    return {
        "status": "ok",
        "result": result,
        "url": url_atual.replace("URL atual: ", "").strip(),
        "title": titulo.replace("Titulo: ", "").strip(),
    }


class PlaywrightClickRequest(BaseModel):
    selector: str
    timeout: int = 10000

@app.post("/playwright/click")
async def playwright_click_api(req: PlaywrightClickRequest):
    from plugins.plugin_playwright import playwright_click
    result = playwright_click(selector=req.selector, timeout=req.timeout)
    return {"status": "ok", "result": result}


class PlaywrightFillRequest(BaseModel):
    selector: str
    text: str
    timeout: int = 10000

@app.post("/playwright/fill")
async def playwright_fill_api(req: PlaywrightFillRequest):
    from plugins.plugin_playwright import playwright_fill
    result = playwright_fill(selector=req.selector, text=req.text, timeout=req.timeout)
    return {"status": "ok", "result": result}


class PlaywrightExtractRequest(BaseModel):
    selector: str = "body"

@app.post("/playwright/extract")
async def playwright_extract_api(req: PlaywrightExtractRequest):
    """Extrai texto de elementos da pagina."""
    from plugins.plugin_playwright import playwright_extract_text
    result = playwright_extract_text(selector=req.selector)
    return {"status": "ok", "text": result, "chars": len(result)}


@app.get("/playwright/content")
async def playwright_content_api(max_length: int = Query(5000, ge=100, le=50000)):
    """Extrai todo o texto visivel da pagina atual."""
    from plugins.plugin_playwright import playwright_get_content
    result = playwright_get_content(max_length=max_length)
    return {"status": "ok", "text": result, "chars": min(len(result), max_length)}


@app.get("/playwright/url")
async def playwright_url_api():
    """Retorna a URL atual da pagina."""
    from plugins.plugin_playwright import playwright_get_url
    return {"status": "ok", "url": playwright_get_url()}


@app.get("/playwright/title")
async def playwright_title_api():
    """Retorna o titulo da pagina atual."""
    from plugins.plugin_playwright import playwright_get_title
    return {"status": "ok", "title": playwright_get_title()}


@app.get("/playwright/links")
async def playwright_links_api(selector: str = Query("a")):
    """Extrai links da pagina."""
    from plugins.plugin_playwright import playwright_extract_links
    raw = playwright_extract_links(selector=selector)
    links = [l.strip() for l in raw.split("\n") if l.strip() and not l.startswith("Nenhum") and not l.startswith("Erro")]
    return {"status": "ok", "links": links, "total": len(links)}


class PlaywrightEvaluateRequest(BaseModel):
    js_code: str

@app.post("/playwright/evaluate")
async def playwright_evaluate_api(req: PlaywrightEvaluateRequest):
    """Executa JavaScript na pagina."""
    from plugins.plugin_playwright import playwright_evaluate
    result = playwright_evaluate(js_code=req.js_code)
    return {"status": "ok", "result": result}


class PlaywrightScreenshotRequest(BaseModel):
    selector: str = ""
    full_page: bool = True
    filename: str = ""

@app.post("/playwright/screenshot")
async def playwright_screenshot_api(req: PlaywrightScreenshotRequest):
    """Tira screenshot da pagina ou de um elemento especifico."""
    from plugins.plugin_playwright import playwright_screenshot
    result = playwright_screenshot(selector=req.selector, full_page=req.full_page, filename=req.filename)
    # Extrai caminho do arquivo do resultado
    filepath = ""
    for line in result.split("\n"):
        if "Screenshot salvo:" in line:
            filepath = line.split(":", 1)[-1].strip()
            break
    filename = os.path.basename(filepath) if filepath else ""
    return {
        "status": "ok",
        "result": result,
        "file": filename,
        "url": f"/playwright/screenshots/{filename}" if filename else "",
    }


@app.get("/playwright/screenshots")
async def playwright_list_screenshots():
    """Lista todos os screenshots salvos."""
    files = []
    if os.path.exists(SCREENSHOTS_DIR):
        for f in sorted(os.listdir(SCREENSHOTS_DIR), reverse=True)[:50]:
            path = os.path.join(SCREENSHOTS_DIR, f)
            if os.path.isfile(path) and f.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                files.append({
                    "name": f,
                    "size": os.path.getsize(path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                    "url": f"/playwright/screenshots/{f}",
                })
    return {"screenshots": files, "total": len(files)}


@app.get("/playwright/screenshots/{filename}")
async def playwright_serve_screenshot(filename: str):
    """Serve um screenshot salvo."""
    from fastapi.responses import FileResponse
    safe_name = os.path.basename(filename)
    path = os.path.join(SCREENSHOTS_DIR, safe_name)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    raise HTTPException(404, "Screenshot nao encontrado")


class PlaywrightTabRequest(BaseModel):
    tab_id: str = ""
    url: str = "about:blank"

@app.get("/playwright/tabs")
async def playwright_tabs_api():
    """Lista todas as abas abertas."""
    from plugins.plugin_playwright import playwright_list_tabs
    raw = playwright_list_tabs()
    tabs = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("[") and "]" in line:
            tab_id = line.split("]")[0].strip("[")
            resto = line.split("]", 1)[-1].strip()
            is_active = "<- ATIVA" in resto
            tabs.append({"id": tab_id, "title": resto.replace("<- ATIVA", "").strip(), "active": is_active})
    return {"status": "ok", "tabs": tabs, "total": len(tabs), "raw": raw}


@app.post("/playwright/tabs/new")
async def playwright_new_tab_api(req: PlaywrightTabRequest):
    """Abre uma nova aba, opcionalmente navega para URL."""
    from plugins.plugin_playwright import playwright_new_tab
    result = playwright_new_tab(url=req.url, tab_id=req.tab_id)
    return {"status": "ok", "result": result}


class PlaywrightSwitchTabRequest(BaseModel):
    tab_id: str

@app.post("/playwright/tabs/switch")
async def playwright_switch_tab_api(req: PlaywrightSwitchTabRequest):
    """Alterna para uma aba especifica."""
    from plugins.plugin_playwright import playwright_switch_tab
    result = playwright_switch_tab(tab_id=req.tab_id)
    return {"status": "ok", "result": result}


class PlaywrightCloseTabRequest(BaseModel):
    tab_id: str = ""

@app.post("/playwright/tabs/close")
async def playwright_close_tab_api(req: PlaywrightCloseTabRequest):
    """Fecha uma aba especifica ou a aba ativa."""
    from plugins.plugin_playwright import playwright_close_tab
    result = playwright_close_tab(tab_id=req.tab_id)
    return {"status": "ok", "result": result}


class PlaywrightNavigateAllRequest(BaseModel):
    urls: str
    wait: bool = True

@app.post("/playwright/navigate-all")
async def playwright_navigate_all_api(req: PlaywrightNavigateAllRequest):
    """Navega multiplas URLs em paralelo, cada uma em uma nova aba."""
    from plugins.plugin_playwright import playwright_navigate_all
    result = playwright_navigate_all(urls=req.urls, wait=req.wait)
    return {"status": "ok", "result": result}


@app.post("/playwright/wait")
async def playwright_wait_api(ms: int = Body(1000, embed=True)):
    """Aguarda um tempo em milissegundos."""
    from plugins.plugin_playwright import playwright_wait
    result = playwright_wait(ms=ms)
    return {"status": "ok", "result": result}


@app.post("/playwright/scroll")
async def playwright_scroll_api(
    direction: str = Body("down", embed=True),
    amount: int = Body(500, embed=True),
):
    from plugins.plugin_playwright import playwright_scroll
    result = playwright_scroll(direction=direction, amount=amount)
    return {"status": "ok", "result": result}


@app.post("/playwright/close")
async def playwright_close_api():
    """Fecha o navegador Playwright e libera recursos."""
    from plugins.plugin_playwright import playwright_close
    result = playwright_close()
    return {"status": "ok", "result": result}


@app.post("/playwright/restart")
async def playwright_restart_api():
    """Reinicia o navegador Playwright."""
    from plugins.plugin_playwright import playwright_restart
    result = playwright_restart()
    return {"status": "ok", "result": result}


# ====================================================================
# MCP — Model Context Protocol (API HTTP)
# ====================================================================

# Nota: imports lazy (dentro de cada funcao) para evitar circular imports


@app.get("/mcp/status")
async def mcp_status_api():
    """Retorna status do servidor MCP."""
    try:
        from plugins.plugin_mcp import mcp_server_status, MCP_SERVER_RUNNING
        raw = mcp_server_status()
        running = MCP_SERVER_RUNNING.is_set()
        return {"available": True, "running": running, "raw": raw, "status": "ativo" if running else "inativo"}
    except ImportError:
        return {"available": False, "message": "Plugin MCP nao carregado"}


class MCPStartRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9090

@app.post("/mcp/start")
async def mcp_start_api(req: MCPStartRequest):
    """Inicia o servidor MCP."""
    try:
        from plugins.plugin_mcp import mcp_server_iniciar
        result = mcp_server_iniciar(host=req.host, port=req.port)
        return {"status": "ok", "result": result, "host": req.host, "port": req.port}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


@app.post("/mcp/stop")
async def mcp_stop_api():
    """Para o servidor MCP."""
    try:
        from plugins.plugin_mcp import mcp_server_parar
        result = mcp_server_parar()
        return {"status": "ok", "result": result}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


class MCPConnectRequest(BaseModel):
    server_url: str

@app.post("/mcp/connect")
async def mcp_connect_api(req: MCPConnectRequest):
    """Conecta a um servidor MCP externo e descobre ferramentas."""
    try:
        from plugins.plugin_mcp import mcp_conectar
        result = mcp_conectar(server_url=req.server_url)
        tools = []
        for line in result.split("\n"):
            if "🔧" in line and ":" in line:
                name = line.split(":", 1)[0].replace("🔧", "").strip()
                tools.append(name)
        return {"status": "ok", "result": result, "server_url": req.server_url, "discovered_tools": tools}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


class MCPCallRequest(BaseModel):
    server_url: str
    tool_name: str
    arguments: str = "{}"

@app.post("/mcp/call")
async def mcp_call_api(req: MCPCallRequest):
    """Chama uma ferramenta em um servidor MCP externo."""
    try:
        from plugins.plugin_mcp import mcp_chamar
        result = mcp_chamar(server_url=req.server_url, tool_name=req.tool_name, arguments=req.arguments)
        return {"status": "ok", "result": result, "tool": req.tool_name}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


class MCPListToolsRequest(BaseModel):
    server_url: str

@app.post("/mcp/list-tools")
async def mcp_list_tools_api(req: MCPListToolsRequest):
    """Lista ferramentas de um servidor MCP externo."""
    try:
        from plugins.plugin_mcp import mcp_listar_ferramentas
        result = mcp_listar_ferramentas(server_url=req.server_url)
        return {"status": "ok", "result": result}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


class MCPHealthRequest(BaseModel):
    server_url: str

@app.post("/mcp/health")
async def mcp_health_api(req: MCPHealthRequest):
    """Health check de um servidor MCP."""
    try:
        from plugins.plugin_mcp import mcp_health_check
        result = mcp_health_check(server_url=req.server_url)
        return {"status": "ok", "result": result}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


class MCPDiscoverRequest(BaseModel):
    host: str = "127.0.0.1"
    port_start: int = 9090
    port_end: int = 9190

@app.post("/mcp/discover")
async def mcp_discover_api(req: MCPDiscoverRequest):
    """Descobre servidores MCP em uma faixa de portas."""
    try:
        from plugins.plugin_mcp import mcp_descobrir
        result = mcp_descobrir(host=req.host, port_start=req.port_start, port_end=req.port_end)
        return {"status": "ok", "result": result}
    except ImportError:
        return {"status": "error", "message": "Plugin MCP nao carregado"}


@app.get("/mcp/tools")
async def mcp_tools_list_api():
    """Lista ferramentas expostas pelo servidor MCP local."""
    try:
        from plugins.plugin_mcp import _get_tools_list
        tools = _get_tools_list()
        return {"available": True, "tools": tools, "total": len(tools)}
    except ImportError:
        return {"available": False, "message": "Plugin MCP nao carregado"}


@app.post("/mcp/sse")
async def mcp_sse_api():
    """Streaming SSE de eventos do servidor MCP."""
    async def event_generator():
        yield "data: {\"type\":\"mcp_sse_start\"}\n\n"
        try:
            mcp_available = True
            try:
                from plugins.plugin_mcp import MCP_SERVER_RUNNING
            except ImportError:
                mcp_available = False
            while True:
                if mcp_available and MCP_SERVER_RUNNING.is_set():
                    yield f"data: {json.dumps({'type': 'heartbeat', 'running': True})}\n\n"
                else:
                    yield "data: {\"type\":\"mcp_inactive\"}\n\n"
                    break
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        finally:
            yield "data: {\"type\":\"close\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ====================================================================
# DASHBOARD EM TEMPO REAL (SSE + Métricas)
# ====================================================================

@app.get("/dashboard/stream")
async def dashboard_stream():
    """Streaming SSE de métricas do dashboard em tempo real.
    
    Envia a cada 5s: estado dos plugins, tarefas ativas, erros,
    memória vetorial, benchmarks e muito mais.
    """
    async def event_generator():
        yield "data: {\"type\":\"dashboard_start\"}\n\n"
        try:
            while True:
                metrics = _coletar_metricas_dashboard()
                yield f"data: {json.dumps(metrics, ensure_ascii=False)}\n\n"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        finally:
            yield "data: {\"type\":\"close\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _coletar_metricas_dashboard() -> dict:
    """Coleta métricas para o dashboard em tempo real."""
    m = {
        "type": "dashboard_metrics",
        "timestamp": datetime.now().isoformat(),
        "plugins": {},
        "memoria": {},
        "benchmark": {},
        "sandbox": {},
        "rag": {},
        "mcp": {},
        "playwright": {},
        "sistema": {},
    }

    # Sistema
    m["sistema"] = {
        "model": MODEL_NAME,
        "tools_count": len(AVAILABLE_FUNCTIONS),
        "runtime_hours": round((time.time() - conversation_start) / 3600, 1),
        "tool_calls_total": tool_call_count,
    }

    # RAG
    m["rag"] = {
        "available": RAG_AVAILABLE,
        "chroma_dir": CHROMA_DIR if RAG_AVAILABLE else "",
    }

    # MCP
    try:
        from plugins.plugin_mcp import MCP_SERVER_RUNNING
        m["mcp"]["running"] = MCP_SERVER_RUNNING.is_set()
    except Exception:
        m["mcp"]["running"] = False

    # Benchmark
    try:
        bm_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "agente_data", "benchmark", "metricas.json")
        if os.path.exists(bm_file):
            with open(bm_file, "r") as f:
                m["benchmark"] = json.load(f)
    except Exception:
        pass

    # Memória evolutiva
    try:
        mem_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "agente_data", "memoria_evolutiva")
        fatos = []
        fatos_path = os.path.join(mem_dir, "fatos_semanticos.json")
        if os.path.exists(fatos_path):
            with open(fatos_path, "r") as f:
                fatos = json.load(f)
        grafo_path = os.path.join(mem_dir, "grafo_conhecimento.json")
        grafo = {}
        if os.path.exists(grafo_path):
            with open(grafo_path, "r") as f:
                grafo = json.load(f)
        m["memoria"] = {
            "fatos": len(fatos),
            "grafo_nos": len(grafo.get("nos", {})),
            "grafo_arestas": len(grafo.get("arestas", [])),
        }
    except Exception:
        pass

    # Sandbox
    try:
        sb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "agente_data", "sandbox", "projetos")
        if os.path.isdir(sb_dir):
            projetos = [d for d in os.listdir(sb_dir)
                       if os.path.isdir(os.path.join(sb_dir, d))]
            hist_path = os.path.join(os.path.dirname(sb_dir), "historico.json")
            hist = []
            if os.path.exists(hist_path):
                with open(hist_path, "r") as f:
                    hist = json.load(f)
            m["sandbox"] = {
                "projetos": len(projetos),
                "execucoes": len(hist),
            }
    except Exception:
        pass

    return m


@app.get("/dashboard/metrics")
async def dashboard_metrics_api():
    """Retorna métricas completas do dashboard em JSON."""
    return _coletar_metricas_dashboard()


@app.get("/dashboard/plugins")
async def dashboard_plugins_api():
    """Lista todos os plugins com status e ferramentas."""
    plugins = list_plugins()
    # Parse para JSON
    linhas = plugins.split("\n") if isinstance(plugins, str) else []
    parsed = []
    for linha in linhas:
        linha = linha.strip()
        if linha.startswith("✅") or linha.startswith("❌"):
            nome = linha.split("v")[0] if "v" in linha else linha
            parsed.append({
                "nome": nome,
                "status": "loaded" if linha.startswith("✅") else "error",
            })
    return {"plugins": parsed, "total": len(parsed)}


@app.get("/dashboard/errors")
async def dashboard_errors():
    """Retorna erros recentes do sistema."""
    try:
        # Tenta coletar erros do fluxo autonomo e logs
        errors = []
        # Log de erros do agente_core
        log_path = os.path.join(CORE_DATA_DIR, "agent_errors.json")
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                errors = json.load(f)[-50:]
        return {"errors": errors, "total": len(errors)}
    except Exception as e:
        return {"errors": [], "total": 0, "message": str(e)}


@app.get("/dashboard/evidence")
async def dashboard_evidence():
    """Retorna evidencias de execucao consolidadas (benchmarks + sandbox)."""
    evidence = []

    # Benchmark results
    try:
        bm_dir = os.path.join(CORE_DATA_DIR, "benchmark")
        results_path = os.path.join(bm_dir, "resultados.json")
        if os.path.exists(results_path):
            with open(results_path, "r", encoding="utf-8") as f:
                evidence = json.load(f)[-50:]
    except Exception:
        pass

    # Benchmarks recentes (diretorio de resultados)
    try:
        bm_results_dir = os.path.join(CORE_DATA_DIR, "benchmark", "resultados")
        if os.path.isdir(bm_results_dir):
            for f in sorted(os.listdir(bm_results_dir), reverse=True)[:5]:
                path = os.path.join(bm_results_dir, f)
                with open(path, "r") as fh:
                    r = json.load(fh)
                evidence.append({
                    "type": "benchmark",
                    "id": r.get("id", ""),
                    "name": r.get("task_set_nome", ""),
                    "date": r.get("executado_em", ""),
                    "taxa": r.get("taxa_aprovacao", 0),
                    "total": r.get("total", 0),
                    "aprovados": r.get("aprovados", 0),
                })
    except Exception:
        pass

    return {"evidence": evidence, "total": len(evidence)}


@app.get("/dashboard/tasks")
async def dashboard_tasks():
    """Retorna tarefas ativas consolidadas (sandbox + fluxo autonomo)."""
    tasks = []

    # Tarefas do fluxo autonomo
    try:
        func = AVAILABLE_FUNCTIONS.get("status_fluxo")
        if func:
            tasks.append({"source": "fluxo_autonomo", "data": func(task_id="", limite=5)})
    except Exception:
        pass

    # Tarefas do sandbox
    try:
        sb_dir = os.path.join(CORE_DATA_DIR, "sandbox", "projetos")
        if os.path.isdir(sb_dir):
            for p in sorted(os.listdir(sb_dir)):
                meta_path = os.path.join(sb_dir, p, "meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    tasks.append({
                        "type": "sandbox",
                        "name": meta.get("nome", p),
                        "status": "active",
                        "execucoes": meta.get("execucoes", 0),
                    })
    except Exception:
        pass

    return {"tasks": tasks, "total": len(tasks), "timestamp": datetime.now().isoformat()}


@app.get("/dashboard/errors")
async def dashboard_errors(limite: int = Query(20, ge=1, le=100)):
    """Retorna erros recentes consolidados (JSON logs + agent log)."""
    errors = []

    # Log de erros do agente_core
    try:
        log_path = os.path.join(CORE_DATA_DIR, "agent_errors.json")
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                errors = json.load(f)[-50:]
    except Exception:
        pass

    # Logs de erro do agent.log
    try:
        agent_log = os.path.join(CORE_DATA_DIR, "agente.log")
        if os.path.exists(agent_log):
            with open(agent_log, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for line in lines[-limite:]:
                if "ERROR" in line or "CRITICAL" in line or "ERRO" in line:
                    errors.append({
                        "source": "log",
                        "message": line.strip()[:200],
                        "timestamp": line[:19] if len(line) > 19 else "",
                    })
    except Exception:
        pass

    return {"errors": errors[-limite:], "total": len(errors)}


# ====================================================================
# OBSERVABILIDADE — Métricas e Tracing
# ====================================================================

@app.get("/metrics")
async def metrics_prometheus():
    """Endpoint de métricas no formato Prometheus."""
    metrics_lines = [
        "# HELP agent_tool_calls_total Total de chamadas de ferramentas",
        "# TYPE agent_tool_calls_total counter",
        f"agent_tool_calls_total {tool_call_count}",
        "",
        "# HELP agent_tools_count Número de ferramentas disponíveis",
        "# TYPE agent_tools_count gauge",
        f"agent_tools_count {len(AVAILABLE_FUNCTIONS)}",
        "",
        "# HELP agent_up 1 se o agente está rodando",
        "# TYPE agent_up gauge",
        f"agent_up 1",
        "",
        "# HELP agent_runtime_seconds Tempo de execução do servidor",
        "# TYPE agent_runtime_seconds counter",
        f"agent_runtime_seconds {int(time.time() - conversation_start)}",
        "",
        "# HELP agent_rag_available RAG disponível",
        "# TYPE agent_rag_available gauge",
        f"agent_rag_available {'1' if RAG_AVAILABLE else '0'}",
        "",
        "# HELP agent_conversations_count Total de conversas",
        "# TYPE agent_conversations_count gauge",
        f"agent_conversations_count {len(_load_conv_index().get('conversations', {}))}",
    ]

    # Benchmark metrics
    try:
        bm_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "agente_data", "benchmark", "metricas.json")
        if os.path.exists(bm_file):
            with open(bm_file, "r") as f:
                bm = json.load(f)
            metrics_lines.extend([
                "",
                "# HELP agent_benchmark_approval_rate Taxa média de aprovação",
                "# TYPE agent_benchmark_approval_rate gauge",
                f"agent_benchmark_approval_rate {bm.get('media_taxa_aprovacao', 0)}",
                "",
                "# HELP agent_benchmark_total Total de benchmarks",
                "# TYPE agent_benchmark_total counter",
                f"agent_benchmark_total {bm.get('total_benchmarks', 0)}",
            ])
    except Exception:
        pass

    # MCP metrics
    try:
        from plugins.plugin_mcp import MCP_SERVER_RUNNING
        metrics_lines.extend([
            "",
            "# HELP agent_mcp_server_running MCP server ativo",
            "# TYPE agent_mcp_server_running gauge",
            f"agent_mcp_server_running {'1' if MCP_SERVER_RUNNING.is_set() else '0'}",
        ])
    except Exception:
        pass

    return Response(
        content="\n".join(metrics_lines),
        media_type="text/plain; charset=utf-8",
    )


# ====================================================================
# SISTEMA
# ====================================================================

@app.get("/system/info")
async def system_info():
    """Retorna informações do sistema."""
    return {"info": get_system_info()}

@app.get("/system/status")
async def system_status():
    """Retorna status detalhado do servidor."""
    runtime = int(time.time() - conversation_start)
    index = _load_conv_index()
    total_convs = len(index["conversations"])
    return {
        "model": MODEL_NAME,
        "tools_count": len(AVAILABLE_FUNCTIONS),
        "runtime_seconds": runtime,
        "tool_calls_total": tool_call_count,
        "conversations_count": total_convs,
    }


# ====================================================================
# SESSÕES
# ====================================================================

@app.get("/sessions")
async def list_sessions():
    """Lista sessões salvas."""
    return {"sessions": session_list()}

@app.post("/sessions/{name}")
async def save_session(name: str):
    """Salva a conversa atual como uma sessão nomeada."""
    result = session_save(name)
    return {"status": "ok", "result": result}

@app.get("/sessions/{name}/load")
async def load_session(name: str):
    """Carrega uma sessão salva."""
    result = session_load(name)
    return {"status": "ok", "result": result}


# ====================================================================
# BUSCA (textual + RAG semântica)
# ====================================================================

@app.get("/search")
async def search(query: str = Query(..., min_length=1)):
    """Busca texto em todas as conversas."""
    results = []
    index = _load_conv_index()
    q = query.lower()
    for conv_id in index["order"]:
        messages = _load_conv_messages(conv_id)
        for m in messages:
            if m.get("content") and q in m["content"].lower():
                results.append({
                    "conversation_id": conv_id,
                    "role": m.get("role"),
                    "content": m["content"][:300],
                    "timestamp": m.get("timestamp", ""),
                })
    return {"query": query, "results": results[:50], "total": len(results)}


@app.get("/rag/search")
async def rag_search(query: str = Query(..., min_length=1), n_results: int = Query(3, ge=1, le=10), project_id: str = "", conversation_id: str = "", category: str = ""):
    """Busca semântica nos documentos indexados via RAG (ChromaDB)."""
    if not RAG_AVAILABLE:
        return {"available": False, "message": "RAG não disponível. Instale chromadb: pip install chromadb", "results": []}
    filters = {key: value for key, value in {"project_id": project_id, "conversation_id": conversation_id, "category": category}.items() if value}
    docs = _search_rag(query, n_results, filters or None)
    return {
        "available": True,
        "query": query,
        "results": docs,
        "total": len(docs),
    }

@app.get("/rag/status")
async def rag_status():
    """Retorna status do RAG."""
    if not RAG_AVAILABLE:
        return {"available": False, "message": "RAG não inicializado"}
    try:
        count = RAG_COLLECTION.count() if RAG_COLLECTION else 0
        return {
            "available": True,
            "document_count": count,
            "chroma_dir": CHROMA_DIR,
        }
    except Exception as e:
        return {"available": False, "message": str(e)}


# ====================================================================
# BACKUP — Gerenciamento de backups via API
# ====================================================================

@app.post("/backup/create")
async def backup_create(name: str = Body("", embed=True)):
    """Cria um backup comprimido dos dados do agente."""
    from core.backup_util import create_backup
    return create_backup(name)


@app.get("/backup/list")
async def backup_list():
    """Lista todos os backups disponiveis."""
    from core.backup_util import list_backups, get_backup_stats
    return {
        "backups": list_backups(),
        "stats": get_backup_stats(),
    }


@app.post("/backup/restore/{name}")
async def backup_restore(name: str):
    """Restaura um backup pelo nome. ATENCAO: sobrescreve dados atuais."""
    from core.backup_util import restore_backup
    return restore_backup(name)


@app.delete("/backup/{name}")
async def backup_delete(name: str):
    """Deleta um backup pelo nome."""
    from core.backup_util import delete_backup
    return delete_backup(name)


@app.get("/backup/stats")
async def backup_stats():
    """Retorna estatisticas dos backups."""
    from core.backup_util import get_backup_stats
    return get_backup_stats()


# ====================================================================
# FEEDBACK — Avaliacoes do usuario
# ====================================================================

class FeedbackRequest(BaseModel):
    quality: int = Field(default=0, ge=-1, le=1, description="-1=ruim, 0=neutro, 1=bom")
    comment: str = ""
    conversation_id: str = ""
    message_index: int = -1
    tags: list = []


@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Envia feedback do usuario sobre uma resposta."""
    from core.feedback import submit_feedback as fb_submit
    return {"status": "ok", "result": fb_submit(
        quality=req.quality,
        comment=req.comment,
        conversation_id=req.conversation_id,
        message_index=req.message_index,
        tags=req.tags,
    )}


@app.get("/feedback/stats")
async def feedback_stats():
    """Retorna estatisticas do feedback."""
    from core.feedback import get_feedback_stats
    return get_feedback_stats()


@app.get("/feedback/list")
async def feedback_list(limit: int = Query(50, ge=1, le=200)):
    """Lista os ultimos feedbacks recebidos."""
    from core.feedback import list_feedback
    return {"feedback": list_feedback(limit), "total": limit}


@app.delete("/feedback")
async def feedback_clear():
    """Limpa todo o feedback registrado."""
    from core.feedback import clear_feedback
    return {"status": "ok", "result": clear_feedback()}


# ====================================================================
# OBSERVABILIDADE — Traces consolidados por agente/MCP/modelo
# ====================================================================

@app.get("/traces")
async def observability_traces():
    """Retorna traces consolidados de agentes, MCP e modelos.
    
    Analisa ferramentas chamadas, sessões MCP ativas e modelos
    disponíveis para consolidar rastreabilidade.
    """
    traces = {
        "timestamp": datetime.now().isoformat(),
        "modelo_ativo": MODEL_NAME,
        "total_ferramentas": len(AVAILABLE_FUNCTIONS),
        "chamadas_tool": tool_call_count,
        "conexoes_mcp": [],
        "modelos_disponiveis": [],
        "agentes_executados": [],
        "conversas_ativas": 0,
    }

    # Modelos disponiveis
    try:
        import ollama
        response = ollama.list()
        raw_models = response.get("models", []) if hasattr(response, "get") else getattr(response, "models", [])
        for m in raw_models:
            if hasattr(m, "model_dump"):
                d = m.model_dump()
            elif isinstance(m, dict):
                d = m
            else:
                d = {}
            traces["modelos_disponiveis"].append(d.get("name") or d.get("model") or "?")
    except Exception:
        pass

    # Lista conversas ativas
    try:
        index = _load_conv_index()
        traces["conversas_ativas"] = len(index.get("conversations", {}))
    except Exception:
        pass

    # Agentes do orquestrador (da chave de subagentes)
    agentes = [name for name in sorted(AVAILABLE_FUNCTIONS.keys()) if name.startswith("subagente_")]
    traces["agentes_executados"] = [
        {"nome": a, "tipo": "subagente"} for a in agentes
    ]

    # MCP
    try:
        from plugins.plugin_mcp import MCP_SERVER_RUNNING
        traces["mcp_ativo"] = MCP_SERVER_RUNNING.is_set()
    except Exception:
        traces["mcp_ativo"] = False

    # RAG status
    traces["rag"] = {
        "disponivel": RAG_AVAILABLE,
        "backend": "chromadb" if RAG_AVAILABLE else "inativo",
    }

    return traces


# ====================================================================
# MAIN
# ====================================================================

if __name__ == "__main__":
    import uvicorn
    _init_rag()
    print(f"+------------------------------------------------------+")
    print(f"+  🤖  Agente Local — ChatGPT Edition                +")
    print(f"+                                                    +")
    print(f"+  🌐 Web UI:     http://localhost:{PORT}               +")
    print(f"+  📖 Swagger:    http://localhost:{PORT}/docs          +")
    print(f"+  📕 ReDoc:      http://localhost:{PORT}/redoc         +")
    print(f"+                                                    +")
    print(f"+  🤖 Modelo:     {MODEL_NAME}                          +")
    print(f"+  🔧 Ferramentas: {len(AVAILABLE_FUNCTIONS)}                         +")
    print(f"+  📚 RAG:        {'✅ Ativo' if RAG_AVAILABLE else '❌ Inativo'}                    +")
    print(f"+------------------------------------------------------+")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
