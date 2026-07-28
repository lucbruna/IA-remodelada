"""Politicas e aprovacoes locais para ferramentas de alto impacto."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

__version__ = "1.0.0"
ROOT_DIR = Path(__file__).resolve().parent.parent
APPROVALS_FILE = ROOT_DIR / "agente_data" / "governanca" / "aprovacoes.json"

HIGH_IMPACT_TOOLS = {
    "run_command", "pip_install", "git_clone", "docker_run", "process_kill",
    "send_email", "delete_path", "move_file", "password_save", "mcp_call",
    "download_file", "install_plugin",
}


def _load():
    try:
        return json.loads(APPROVALS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save(data):
    APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPROVALS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(APPROVALS_FILE)


def politica_ferramenta(nome: str) -> str:
    """Informa se a ferramenta exige aprovacao explicita."""
    level = "aprovacao_obrigatoria" if nome in HIGH_IMPACT_TOOLS else "permitida"
    return json.dumps({"ferramenta": nome, "politica": level}, ensure_ascii=False)


def solicitar_aprovacao(ferramenta: str, justificativa: str, validade_minutos: int = 10) -> str:
    """Cria um pedido de aprovacao, sem executar a ferramenta solicitada."""
    if ferramenta not in HIGH_IMPACT_TOOLS:
        return "Esta ferramenta nao exige aprovacao adicional."
    now = datetime.now(timezone.utc)
    approval = {
        "id": f"approval-{secrets.token_urlsafe(8)}", "ferramenta": ferramenta,
        "justificativa": justificativa[:1000], "criada_em": now.isoformat(),
        "expira_em": (now + timedelta(minutes=max(1, min(int(validade_minutos), 60)))).isoformat(),
        "status": "pendente",
    }
    data = _load(); data.append(approval); _save(data)
    return f"Aprovacao criada: {approval['id']}\nStatus: pendente\nFerramenta: {ferramenta}"


def aprovar_acao(approval_id: str) -> str:
    """Registra aprovacao humana local para um pedido pendente."""
    data = _load()
    for item in data:
        if item["id"] == approval_id:
            if item["status"] != "pendente":
                return f"Aprovacao esta em estado: {item['status']}"
            item["status"] = "aprovada"; item["aprovada_em"] = datetime.now(timezone.utc).isoformat(); _save(data)
            return f"Aprovacao registrada: {approval_id}"
    return "Aprovacao nao encontrada."


def verificar_aprovacao(approval_id: str, ferramenta: str) -> str:
    """Verifica aprovacao, ferramenta e validade; nao consome a aprovacao."""
    for item in _load():
        if item["id"] == approval_id:
            if item["ferramenta"] != ferramenta:
                return "negada: aprovacao pertence a outra ferramenta"
            if item["status"] != "aprovada":
                return f"negada: status {item['status']}"
            if datetime.now(timezone.utc) > datetime.fromisoformat(item["expira_em"]):
                return "negada: aprovacao expirada"
            return "aprovada"
    return "negada: aprovacao inexistente"


def register(api):
    api.register_tool("politica_ferramenta", politica_ferramenta, "Consulta a politica de risco de uma ferramenta.", {"nome": {"type": "string", "description": "Nome da ferramenta"}}, ["nome"])
    api.register_tool("solicitar_aprovacao", solicitar_aprovacao, "Cria pedido de aprovacao para ferramenta de alto impacto.", {"ferramenta": {"type": "string", "description": "Ferramenta"}, "justificativa": {"type": "string", "description": "Motivo"}, "validade_minutos": {"type": "integer", "description": "Validade"}}, ["ferramenta", "justificativa"])
    api.register_tool("aprovar_acao", aprovar_acao, "Registra aprovacao humana de uma acao pendente.", {"approval_id": {"type": "string", "description": "ID do pedido"}}, ["approval_id"])
    api.register_tool("verificar_aprovacao", verificar_aprovacao, "Verifica se uma aprovacao e valida para ferramenta.", {"approval_id": {"type": "string", "description": "ID"}, "ferramenta": {"type": "string", "description": "Ferramenta"}}, ["approval_id", "ferramenta"])
    return {"name": "Governanca de Execucao", "version": __version__, "description": "Aprovacoes locais e temporarias para ferramentas de alto impacto.", "tools": ["politica_ferramenta", "solicitar_aprovacao", "aprovar_acao", "verificar_aprovacao"]}
