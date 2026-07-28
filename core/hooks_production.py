"""
core/hooks_production.py
========================
Hooks de produção inspirados no Fable 5 Methodology.

O Fable 5 define hooks como scripts determinísticos que bloqueiam ações
perigosas. Este módulo implementa hooks similares para o agente local:

- pre_tool_guard: Bloqueia comandos destrutivos (rm -rf, etc.)
- close_guard: Verifica critérios de sucesso antes de "done"
- spawn_guard: Gate em spawns de sub-agentes
- session_end: Cleanup de recursos

Hooks são fail-safe: em caso de erro interno, permitem a ação (fail-open)
para não travar o sistema.

Uso:
    from core.hooks_production import pre_tool_guard, close_guard

    # Verifica se um comando é seguro
    if not pre_tool_guard("rm -rf /"):
        print("Comando bloqueado!")

    # Verifica critérios de sucesso
    result = close_guard(task_result="codigo gerado", criteria=["testes passaram"])
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Set

from ._common import (
    os, re, logging, datetime,
    _load_json, _save_json, DATA_DIR,
)

HOOKS_DIR = os.path.join(DATA_DIR, "hooks")
os.makedirs(HOOKS_DIR, exist_ok=True)

_LOG_FILE = os.path.join(HOOKS_DIR, "hook_events.json")

_DESTRUCTIVE_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"rm\s+-rf\s+\$\(",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
    r":\(\)\s*\{\s*:\|:\&\s*\}\s*;:",
    r">\s*/dev/sda",
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+.*\s+/",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"subprocess\.call\s*\(\s*[\"'].*shell",
    r"os\.system\s*\(",
]

_DESTRUCTIVE_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in _DESTRUCTIVE_PATTERNS]

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./\.\./", re.IGNORECASE),
    re.compile(r"/etc/passwd", re.IGNORECASE),
    re.compile(r"/etc/shadow", re.IGNORECASE),
    re.compile(r"~/.ssh/", re.IGNORECASE),
]

_ALLOWED_PATHS: Set[str] = set()
_BLOCKED_PATHS: Set[str] = set()

_HOOK_EVENTS: List[Dict[str, Any]] = []


def _log_hook_event(hook_name: str, action: str, allowed: bool, details: str = "") -> None:
    """Registra um evento de hook."""
    event = {
        "hook": hook_name,
        "action": action[:200],
        "allowed": allowed,
        "details": details,
        "timestamp": datetime.now().isoformat(),
    }
    _HOOK_EVENTS.append(event)
    if len(_HOOK_EVENTS) > 1000:
        _HOOK_EVENTS.pop(0)

    try:
        history = _load_json(_LOG_FILE, [])
        history.append(event)
        history = history[-1000:]
        _save_json(_LOG_FILE, history)
    except Exception:
        pass


def pre_tool_guard(command: str, tool_name: str = "") -> bool:
    """Hook: Verifica se uma ação/tool é segura antes de executar.

    Bloqueia:
    - Comandos destrutivos (rm -rf /, mkfs, etc.)
    - Path traversal (../../etc/passwd)
    - Execução de código perigoso (eval, exec, __import__)

    Fail-safe: em caso de erro, permite a ação (fail-open).

    Args:
        command: Comando ou código a verificar
        tool_name: Nome da ferramenta (opcional)

    Returns:
        True se permitido, False se bloqueado
    """
    try:
        if not command or not isinstance(command, str):
            return True

        command_lower = command.lower()

        # Verifica padrões destrutivos
        for pattern in _DESTRUCTIVE_PATTERNS_COMPILED:
            if pattern.search(command):
                _log_hook_event("pre_tool_guard", command, False,
                                f"Padrão destrutivo detectado: {pattern.pattern}")
                return False

        # Verifica path traversal
        for pattern in _PATH_TRAVERSAL_PATTERNS:
            if pattern.search(command):
                _log_hook_event("pre_tool_guard", command, False,
                                f"Path traversal detectado: {pattern.pattern}")
                return False

        # Verifica se o caminho esta bloqueado
        for blocked in _BLOCKED_PATHS:
            if blocked in command:
                _log_hook_event("pre_tool_guard", command, False,
                                f"Caminho bloqueado: {blocked}")
                return False

        _log_hook_event("pre_tool_guard", command, True)
        return True

    except Exception as e:
        logging.warning("Hook pre_tool_guard falhou (fail-open): %s", e)
        return True


def close_guard(task_result: str, criteria: List[str], task_id: str = "") -> Dict[str, Any]:
    """Hook: Verifica critérios de sucesso antes de considerar uma tarefa concluída.

    Inspirado no Fable 5 close-guard: verifica se o trabalho atende aos
    critérios antes de aceitar como "done".

    Args:
        task_result: Resultado da tarefa
        criteria: Lista de critérios de sucesso (ex: ["testes passaram", "arquivo criado"])
        task_id: ID da tarefa (opcional)

    Returns:
        Dict com passed, missing_criteria, details
    """
    try:
        result_lower = task_result.lower()
        missing = []

        for criterion in criteria:
            criterion_lower = criterion.lower()
            # Verifica se o critério e mencionado no resultado
            if criterion_lower not in result_lower:
                # Tenta variações
                keywords = criterion_lower.split()
                found = any(kw in result_lower for kw in keywords if len(kw) > 3)
                if not found:
                    missing.append(criterion)

        passed = len(missing) == 0
        _log_hook_event("close_guard", task_id or task_result[:50], passed,
                        f"Missing: {missing}" if missing else "All criteria met")

        return {
            "passed": passed,
            "missing_criteria": missing,
            "details": f"Verificados {len(criteria)} criterios, {len(missing)} faltando",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.warning("Hook close_guard falhou (fail-open): %s", e)
        return {"passed": True, "missing_criteria": [], "details": f"Erro: {e}"}


def spawn_guard(prompt: str, subagent_type: str = "") -> Dict[str, Any]:
    """Hook: Gate em spawns de sub-agentes.

    Verifica se o prompt de um sub-agente:
    - Nao e muito longo (gate de 1500 chars)
    - Nao contem comandos destrutivos
    - Tem critérios de aceitação

    Args:
        prompt: Prompt do sub-agente
        subagent_type: Tipo do sub-agente (ex: "builder", "qa-verifier")

    Returns:
        Dict com allowed, reason, suggestions
    """
    try:
        MAX_PROMPT_LENGTH = 1500

        if not prompt or len(prompt) > MAX_PROMPT_LENGTH:
            return {
                "allowed": False,
                "reason": f"Prompt muito longo ({len(prompt or '')} chars, max {MAX_PROMPT_LENGTH})",
                "suggestions": ["Divida a tarefa em subtarefas menores"],
            }

        # Verifica comandos destrutivos
        if not pre_tool_guard(prompt, subagent_type):
            return {
                "allowed": False,
                "reason": "Prompt contem comandos destrutivos",
                "suggestions": ["Remova comandos perigosos do prompt"],
            }

        # Verifica se tem critérios de aceitação
        has_acceptance = any(kw in prompt.lower() for kw in [
            "critério", "aceitação", "aceitar", "done when", "verificar",
            "teste", "validar", "success", "passar",
        ])

        if not has_acceptance:
            return {
                "allowed": True,
                "reason": "Prompt permitido (sem critérios de aceitação explícitos)",
                "suggestions": ["Adicione critérios de aceitação para melhor verificação"],
            }

        return {
            "allowed": True,
            "reason": "Prompt passou no gate",
            "suggestions": [],
        }

    except Exception as e:
        logging.warning("Hook spawn_guard falhou (fail-open): %s", e)
        return {"allowed": True, "reason": f"Erro: {e}", "suggestions": []}


def session_end(session_id: str = "") -> Dict[str, Any]:
    """Hook: Cleanup de recursos ao final de uma sessão.

    - Remove arquivos temporários
    - Limpa cache expirado
    - Salva estado da sessão

    Args:
        session_id: ID da sessão

    Returns:
        Dict com cleanup realizado
    """
    try:
        cleaned = []
        errors = []

        # Limpa arquivos temporários
        temp_dirs = [
            os.path.join(DATA_DIR, "browser_cache", "screenshots"),
            os.path.join(DATA_DIR, "turbo_cache"),
            os.path.join(DATA_DIR, "web_cache"),
        ]

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    for fname in os.listdir(temp_dir):
                        fpath = os.path.join(temp_dir, fname)
                        if os.path.isfile(fpath):
                            age = datetime.now().timestamp() - os.path.getmtime(fpath)
                            if age > 86400:  # 24 horas
                                os.remove(fpath)
                                cleaned.append(fpath)
                except Exception as e:
                    errors.append(f"{temp_dir}: {e}")

        # Salva estado da sessão
        session_state = {
            "session_id": session_id,
            "ended_at": datetime.now().isoformat(),
            "cleaned_files": len(cleaned),
        }

        _log_hook_event("session_end", session_id, True,
                        f"Cleaned {len(cleaned)} files")

        return {
            "success": True,
            "cleaned_files": len(cleaned),
            "cleaned_paths": cleaned[:20],
            "errors": errors,
            "session_state": session_state,
        }

    except Exception as e:
        logging.warning("Hook session_end falhou: %s", e)
        return {"success": False, "error": str(e)}


def pre_tool_guard_command(command: str) -> bool:
    """Hook específico para comandos shell (PreToolUse Bash).

    Variante do pre_tool_guard focada em comandos shell.
    """
    return pre_tool_guard(command, "bash")


def pre_tool_guard_python(code: str) -> bool:
    """Hook específico para código Python (PreToolUse Python).

    Variante do pre_tool_guard focada em código Python.
    """
    return pre_tool_guard(code, "python")


def add_allowed_path(path: str) -> None:
    """Adiciona um caminho à lista de permitidos."""
    _ALLOWED_PATHS.add(os.path.abspath(path))


def add_blocked_path(path: str) -> None:
    """Adiciona um caminho à lista de bloqueados."""
    _BLOCKED_PATHS.add(path)


def get_hook_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Retorna eventos de hook recentes."""
    return _HOOK_EVENTS[-limit:]


def get_hook_stats() -> Dict[str, Any]:
    """Retorna estatísticas dos hooks."""
    total = len(_HOOK_EVENTS)
    allowed = sum(1 for e in _HOOK_EVENTS if e["allowed"])
    blocked = total - allowed

    by_hook = {}
    for e in _HOOK_EVENTS:
        hook = e["hook"]
        by_hook.setdefault(hook, {"total": 0, "allowed": 0, "blocked": 0})
        by_hook[hook]["total"] += 1
        if e["allowed"]:
            by_hook[hook]["allowed"] += 1
        else:
            by_hook[hook]["blocked"] += 1

    return {
        "total_events": total,
        "allowed": allowed,
        "blocked": blocked,
        "by_hook": by_hook,
    }


def reset_hooks() -> str:
    """Limpa todos os eventos de hook (para testes)."""
    global _HOOK_EVENTS
    _HOOK_EVENTS = []
    try:
        if os.path.exists(_LOG_FILE):
            os.remove(_LOG_FILE)
    except Exception:
        pass
    return "Hooks resetados."
