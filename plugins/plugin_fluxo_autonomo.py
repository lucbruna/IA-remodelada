"""Maquina de estados persistente para tarefas autonomas verificaveis.

Separa planejamento de execucao: este modulo registra a tarefa, seu estado e
evidencias. Ferramentas de execucao continuam sendo escolhidas pelo agente,
mas a entrega so pode ser marcada como aprovada apos validacao observavel.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "1.0.0"
PLUGIN_NAME = "Fluxo Autonomo Persistente"

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT_DIR / "agente_data" / "fluxo_autonomo" / "tarefas.json"
STATES = ("planejado", "executando", "validando", "corrigindo", "aguardando_aprovacao", "aprovado", "bloqueado")
TRANSITIONS = {
    "planejado": {"executando", "bloqueado"},
    "executando": {"validando", "corrigindo", "aguardando_aprovacao", "bloqueado"},
    "validando": {"corrigindo", "aprovado", "bloqueado"},
    "corrigindo": {"executando", "validando", "aguardando_aprovacao", "bloqueado"},
    "aguardando_aprovacao": {"executando", "bloqueado"},
    "aprovado": set(),
    "bloqueado": {"executando"},
}


def _load() -> list[dict[str, Any]]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save(tasks: list[dict[str, Any]]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(tasks[-300:], ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_FILE)


def _get_task(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise ValueError(f"Tarefa nao encontrada: {task_id}")


def iniciar_fluxo(objetivo: str, pasta: str = "", plano: str = "") -> str:
    """Cria uma tarefa rastreavel. Nao executa comandos nem altera arquivos."""
    if not objetivo or not objetivo.strip():
        return "Informe um objetivo para iniciar o fluxo."
    now = datetime.now(timezone.utc).isoformat()
    task_id = f"task-{int(time.time() * 1000)}"
    task = {
        "id": task_id,
        "objetivo": objetivo.strip(),
        "pasta": pasta.strip(),
        "plano": plano.strip(),
        "estado": "planejado",
        "criada_em": now,
        "atualizada_em": now,
        "historico": [{"em": now, "de": None, "para": "planejado", "nota": "Tarefa registrada."}],
        "evidencias": [],
    }
    tasks = _load()
    tasks.append(task)
    _save(tasks)
    return f"Fluxo iniciado: {task_id}\nEstado: planejado\nProximo passo: registrar plano e mover para executando."


def atualizar_fluxo(task_id: str, estado: str, nota: str = "") -> str:
    """Move uma tarefa somente por transicoes validas e preserva o historico."""
    estado = estado.strip().lower()
    if estado not in STATES:
        return f"Estado invalido. Use: {', '.join(STATES)}"
    tasks = _load()
    task = _get_task(tasks, task_id)
    current = task["estado"]
    if estado == current:
        return f"A tarefa {task_id} ja esta em {estado}."
    if estado not in TRANSITIONS[current]:
        return f"Transicao nao permitida: {current} -> {estado}."
    now = datetime.now(timezone.utc).isoformat()
    task["estado"] = estado
    task["atualizada_em"] = now
    task.setdefault("historico", []).append({"em": now, "de": current, "para": estado, "nota": nota.strip()})
    _save(tasks)
    return f"Tarefa {task_id}: {current} -> {estado}."


def registrar_evidencia(task_id: str, tipo: str, resultado: str, aprovado: bool = False) -> str:
    """Anexa evidencia factual, como teste, health-check, diff ou revisao."""
    tasks = _load()
    task = _get_task(tasks, task_id)
    now = datetime.now(timezone.utc).isoformat()
    evidence = {"em": now, "tipo": (tipo or "observacao").strip(), "resultado": (resultado or "").strip()[:8000], "aprovado": bool(aprovado)}
    task.setdefault("evidencias", []).append(evidence)
    task["atualizada_em"] = now
    _save(tasks)
    return f"Evidencia registrada para {task_id}: {evidence['tipo']}."


def aprovar_por_validacao(task_id: str, alvo: str = "") -> str:
    """Executa o validador universal e aprova somente se ele retornar veredito aprovado."""
    tasks = _load()
    task = _get_task(tasks, task_id)
    if task["estado"] != "validando":
        return "A tarefa precisa estar em 'validando' antes da aprovacao."
    try:
        from agente_core import AVAILABLE_FUNCTIONS
        validator = AVAILABLE_FUNCTIONS.get("validar_entrega")
        if validator is None:
            return "Validador Universal nao esta carregado. Recarregue plugins."
        report = validator(alvo or task.get("pasta", ""))
    except Exception as exc:
        return f"Falha ao validar: {exc}"
    task.setdefault("evidencias", []).append({
        "em": datetime.now(timezone.utc).isoformat(), "tipo": "validacao_universal", "resultado": report[:8000], "aprovado": "Veredito: APROVADO" in report,
    })
    if "Veredito: APROVADO" in report:
        current = task["estado"]
        task["estado"] = "aprovado"
        task["historico"].append({"em": datetime.now(timezone.utc).isoformat(), "de": current, "para": "aprovado", "nota": "Validacao universal aprovada."})
    else:
        task["estado"] = "corrigindo"
        task["historico"].append({"em": datetime.now(timezone.utc).isoformat(), "de": "validando", "para": "corrigindo", "nota": "Validacao falhou; retorno para correcao."})
    task["atualizada_em"] = datetime.now(timezone.utc).isoformat()
    _save(tasks)
    return f"Validacao concluida. Estado atual: {task['estado']}.\n{report}"


def status_fluxo(task_id: str = "", limite: int = 20) -> str:
    """Exibe uma tarefa ou uma fila resumida de tarefas persistidas."""
    tasks = _load()
    if task_id:
        task = _get_task(tasks, task_id)
        lines = [f"--- {task['id']} ---", f"Objetivo: {task['objetivo']}", f"Estado: {task['estado']}", f"Evidencias: {len(task.get('evidencias', []))}", "Historico:"]
        lines.extend(f"- {item['de']} -> {item['para']}: {item.get('nota', '')}" for item in task.get("historico", []))
        return "\n".join(lines)
    selected = list(reversed(tasks[-max(1, min(int(limite), 100)):]))
    if not selected:
        return "Nenhuma tarefa persistida."
    return "\n".join(["--- Fila Autonoma ---", *[f"- {task['id']} | {task['estado']} | {task['objetivo'][:120]}" for task in selected]])


def listar_tarefas(task_id: str = "", limite: int = 20) -> list[dict[str, Any]]:
    """Retorna tarefas estruturadas para API/dashboard, incluindo evidencias."""
    tasks = _load()
    if task_id:
        return [_get_task(tasks, task_id)]
    return list(reversed(tasks[-max(1, min(int(limite), 100)):]))


def register(api):
    api.register_tool("iniciar_fluxo", iniciar_fluxo, "Cria uma tarefa autonoma persistente com estado planejado.", {"objetivo": {"type": "string", "description": "Resultado desejado"}, "pasta": {"type": "string", "description": "Pasta de trabalho"}, "plano": {"type": "string", "description": "Plano inicial"}}, ["objetivo"])
    api.register_tool("atualizar_fluxo", atualizar_fluxo, "Atualiza uma tarefa por transicoes seguras de estado.", {"task_id": {"type": "string", "description": "Identificador da tarefa"}, "estado": {"type": "string", "description": "Novo estado"}, "nota": {"type": "string", "description": "Justificativa/evidencia"}}, ["task_id", "estado"])
    api.register_tool("registrar_evidencia", registrar_evidencia, "Registra teste, revisao, health-check ou outra evidencia factual.", {"task_id": {"type": "string", "description": "Identificador da tarefa"}, "tipo": {"type": "string", "description": "Tipo da evidencia"}, "resultado": {"type": "string", "description": "Resultado observado"}, "aprovado": {"type": "boolean", "description": "Se a evidencia foi aprovada"}}, ["task_id", "tipo", "resultado"])
    api.register_tool("aprovar_por_validacao", aprovar_por_validacao, "Valida a entrega e move a tarefa para aprovado ou corrigindo.", {"task_id": {"type": "string", "description": "Identificador da tarefa"}, "alvo": {"type": "string", "description": "Arquivo/pasta para validar"}}, ["task_id"])
    api.register_tool("status_fluxo", status_fluxo, "Mostra estado, historico e fila de tarefas autonomas.", {"task_id": {"type": "string", "description": "Identificador opcional"}, "limite": {"type": "integer", "description": "Itens da fila"}}, [])
    api.register_tool("listar_tarefas_estruturadas", listar_tarefas, "Retorna tarefas estruturadas, estados, historico e evidencias para dashboard/API.", {"task_id": {"type": "string"}, "limite": {"type": "integer"}}, [])
    return {"name": PLUGIN_NAME, "version": __version__, "description": "Ciclo persistente: planejar, executar, validar, corrigir e aprovar com evidencias.", "tools": ["iniciar_fluxo", "atualizar_fluxo", "registrar_evidencia", "aprovar_por_validacao", "status_fluxo", "listar_tarefas_estruturadas"]}
