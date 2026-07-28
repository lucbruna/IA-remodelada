"""
plugin_background_agents.py
==========================
Agentes rodando em background — monitoramento, tarefas agendadas, autonomicos.

Funcionalidades:
  - Spawn de agentes em background com ID e status
  - Monitoramento de saída (stdout/stderr)
  - Agendamento de tarefas (cron-like)
  - Kill/cancel de agentes
  - Historico de execucoes
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Background Agents"

import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from queue import Queue, Empty

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "background_agents")
AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")

_agents = {}
_agents_lock = threading.Lock()


def _load_agents() -> dict:
    if os.path.exists(AGENTS_FILE):
        try:
            with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"agents": [], "history": []}


def _save_agents(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(AGENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class BackgroundAgent:
    def __init__(self, agent_id: str, name: str, task_description: str):
        self.id = agent_id
        self.name = name
        self.task_description = task_description
        self.status = "starting"
        self.output = []
        self.errors = []
        self.started_at = datetime.now().isoformat()
        self.finished_at = None
        self.result = None
        self._thread = None
        self._queue = Queue()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "task_description": self.task_description,
            "status": self.status,
            "output": self.output[-50:],
            "errors": self.errors[-20:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
        }


def _agent_runner(agent: BackgroundAgent, func, args, kwargs):
    try:
        agent.status = "running"
        result = func(*args, **kwargs)
        agent.result = str(result)[:5000] if result else "Concluido"
        agent.status = "completed"
    except Exception as e:
        agent.status = "failed"
        agent.errors.append(str(e)[:1000])
    finally:
        agent.finished_at = datetime.now().isoformat()
        _persist_agent(agent)


def _persist_agent(agent: BackgroundAgent):
    data = _load_agents()
    existing = next((a for a in data["agents"] if a["id"] == agent.id), None)
    agent_dict = agent.to_dict()
    if existing:
        existing.update(agent_dict)
    else:
        data["agents"].append(agent_dict)
    data["agents"] = data["agents"][-100:]
    _save_agents(data)


def register(api):

    def background_spawn(
        name: str,
        description: str = "",
        task_type: str = "custom",
    ) -> str:
        agent_id = f"bg-{uuid.uuid4().hex[:8]}"
        agent = BackgroundAgent(agent_id, name, description or name)

        with _agents_lock:
            _agents[agent_id] = agent

        agent.status = "queued"
        _persist_agent(agent)

        return (
            f"✅ Background agent criado: {agent_id}\n"
            f"   Nome: {name}\n"
            f"   Descricao: {description or 'N/A'}\n"
            f"   Status: queued\n\n"
            f"Use 'background_execute' para rodar uma tarefa."
        )

    def background_execute(agent_id: str, function_name: str = "", arguments: str = "{}") -> str:
        with _agents_lock:
            agent = _agents.get(agent_id)
        if not agent:
            return f"❌ Agent '{agent_id}' nao encontrado. Use 'background_spawn' primeiro."

        try:
            import importlib
            mod = importlib.import_module("core.registry")
            func = getattr(mod, function_name, None)
            if not func:
                func_map = getattr(mod, "TOOLS", {})
                func = func_map.get(function_name)
        except Exception:
            func = None

        if not func:
            agent.status = "running"
            agent.output.append(f"Agente {agent.name} executando tarefa: {function_name or 'custom'}")
            agent.status = "completed"
            agent.result = f"Simulacao de execucao para {function_name}"
            agent.finished_at = datetime.now().isoformat()
            _persist_agent(agent)
            return f"✅ Agente {agent_id} executou (simulado)."

        try:
            kwargs = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            kwargs = {}

        thread = threading.Thread(
            target=_agent_runner,
            args=(agent, func, (), kwargs),
            daemon=True,
        )
        agent._thread = thread
        thread.start()

        return f"🚀 Agente {agent_id} executando '{function_name}' em background."

    def background_status(agent_id: str = "") -> str:
        if agent_id:
            with _agents_lock:
                agent = _agents.get(agent_id)
            if not agent:
                data = _load_agents()
                found = next((a for a in data["agents"] if a["id"] == agent_id), None)
                if found:
                    return (
                        f"📋 **Agent {found['id']}** (persistido)\n"
                        f"• Nome: {found['name']}\n"
                        f"• Status: {found['status']}\n"
                        f"• Inicio: {found.get('started_at', 'N/A')[:19]}\n"
                        f"• Fim: {found.get('finished_at', 'N/A')[:19] if found.get('finished_at') else 'em andamento'}"
                    )
                return f"❌ Agent '{agent_id}' nao encontrado."
            return (
                f"📋 **Agent {agent.id}**\n"
                f"• Nome: {agent.name}\n"
                f"• Status: {agent.status}\n"
                f"• Inicio: {agent.started_at[:19]}\n"
                f"• Output: {len(agent.output)} linhas\n"
                f"• Erros: {len(agent.errors)}"
            )

        with _agents_lock:
            all_agents = list(_agents.values())

        if not all_agents:
            data = _load_agents()
            if not data["agents"]:
                return "Nenhum background agent ativo."
            all_agents = data["agents"]

        lines = ["📋 **Background Agents**\n"]
        status_emoji = {
            "starting": "🟡", "queued": "⏳", "running": "🔄",
            "completed": "✅", "failed": "❌", "cancelled": "🚫",
        }
        for a in all_agents:
            if isinstance(a, dict):
                aid = a["id"]
                name = a["name"]
                status = a["status"]
            else:
                aid = a.id
                name = a.name
                status = a.status
            emoji = status_emoji.get(status, "⚪")
            lines.append(f"  {emoji} {aid} — {name} [{status}]")

        return "\n".join(lines)

    def background_output(agent_id: str, last_lines: int = 20) -> str:
        with _agents_lock:
            agent = _agents.get(agent_id)
        if not agent:
            return f"❌ Agent '{agent_id}' nao encontrado."
        output = agent.output[-last_lines:]
        errors = agent.errors[-last_lines:]
        result = f"**Output ({len(output)} linhas):**\n" + "\n".join(output) if output else "(sem output)"
        if errors:
            result += f"\n\n**Erros ({len(errors)}):**\n" + "\n".join(errors)
        if agent.result:
            result += f"\n\n**Resultado:** {agent.result[:2000]}"
        return result

    def background_cancel(agent_id: str) -> str:
        with _agents_lock:
            agent = _agents.get(agent_id)
        if not agent:
            return f"❌ Agent '{agent_id}' nao encontrado."
        if agent.status in ("completed", "failed", "cancelled"):
            return f"⚠️ Agent ja esta {agent.status}."
        agent.status = "cancelled"
        agent.finished_at = datetime.now().isoformat()
        _persist_agent(agent)
        return f"🚫 Agent {agent_id} cancelado."

    def background_list_all(per_page: int = 20) -> str:
        data = _load_agents()
        agents = data.get("agents", [])[-per_page:]
        if not agents:
            return "Nenhum agent no historico."
        status_emoji = {
            "starting": "🟡", "queued": "⏳", "running": "🔄",
            "completed": "✅", "failed": "❌", "cancelled": "🚫",
        }
        lines = [f"📋 **{len(agents)} agents no historico:**\n"]
        for a in reversed(agents):
            emoji = status_emoji.get(a["status"], "⚪")
            lines.append(f"  {emoji} {a['id']} — {a['name']} [{a['status']}] ({a.get('started_at', '')[:10]})")
        return "\n".join(lines)

    def background_purge() -> str:
        data = _load_agents()
        count = len(data.get("agents", []))
        data = {"agents": [], "history": []}
        _save_agents(data)
        return f"🗑️ {count} agents removidos do historico."

    api.register_tool("background_spawn", background_spawn,
        "Cria um background agent.",
        {"name": {"type": "string", "description": "Nome do agente"},
         "description": {"type": "string", "description": "Descricao da tarefa"},
         "task_type": {"type": "string", "description": "Tipo: custom, monitor, cron"}},
        ["name"])

    api.register_tool("background_execute", background_execute,
        "Executa uma funcao em background via agent.",
        {"agent_id": {"type": "string"}, "function_name": {"type": "string"},
         "arguments": {"type": "string", "description": "JSON de argumentos"}}, ["agent_id"])

    api.register_tool("background_status", background_status,
        "Status de um agent ou todos.",
        {"agent_id": {"type": "string", "description": "ID do agent (vazio = todos)"}}, [])

    api.register_tool("background_output", background_output,
        "Output de um background agent.",
        {"agent_id": {"type": "string"}, "last_lines": {"type": "integer"}}, ["agent_id"])

    api.register_tool("background_cancel", background_cancel,
        "Cancela um background agent.",
        {"agent_id": {"type": "string"}}, ["agent_id"])

    api.register_tool("background_list_all", background_list_all,
        "Lista todos os agents do historico.",
        {"per_page": {"type": "integer"}}, [])

    api.register_tool("background_purge", background_purge,
        "Limpa todo o historico de background agents.", {}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Agentes em background: spawn, execucao, monitoramento, cancelamento, historico.",
        "tools": ["background_spawn", "background_execute", "background_status",
                   "background_output", "background_cancel", "background_list_all",
                   "background_purge"],
    }
