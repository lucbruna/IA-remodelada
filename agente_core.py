"""
agente_core.py
==============
Facade de compatibilidade.

Todo o código que antes vivia neste arquivo (4.2k linhas) foi dividido em
módulos do pacote ``core/`` (llm, memory, filesystem, media, code_exec,
web, export, plugins_api, search_tools, downloads_git, vcs_db_proc,
media_gen, docker_tasks, security, converters, autonomy, turbo_api,
dashboard, registry, memory_pipeline, agent_loop).

Este arquivo apenas reexporta a interface pública para que qualquer módulo
que faça ``from agente_core import MODEL, run_agent_turn, ...`` continue
funcionando sem alteração.

A fonte de verdade para modelo/visão/limites é ``config.py``.
"""

from core import *  # noqa: F401,F403

# `import *` ignora nomes com underline. Reexporta TUDO (inclusive underline)
# para manter 100% de compatibilidade com quem fazia
# `from agente_core import _safe_eval, _clean_messages, ...`.
import core as _core
for _n in dir(_core):
    if _n.startswith("__"):
        continue
    try:
        globals()[_n] = getattr(_core, _n)
    except Exception:
        pass

from core import (  # re-export explícito dos nomes mais usados
    MODEL,
    VISION_MODEL,
    NUM_CTX,
    TEMPERATURE,
    DATA_DIR,
    SYSTEM_PROMPT,
    TOOLS_LIST,
    AVAILABLE_FUNCTIONS,
    run_agent_turn,
    load_conversation_history,
    save_conversation_history,
    list_memories,
    list_plugins,
    reload_plugins,
    search_conversation,
    session_save,
    session_load,
    session_list,
    export_conversation_markdown,
    export_conversation_html,
    run_memory_pipeline,
    trim_and_summarize_history,
    hindsight_auto_learn,
    hindsight_context_for_turn,
    _clean_messages,
    _call_ollama_with_timeout,
    turbo_diagnostico,
    turbo_cache_clear,
    task_decompose,
    structured_reasoning,
    code_review,
    ensure_ollama,
    get_system_info,
)

__all__ = [
    "MODEL", "VISION_MODEL", "NUM_CTX", "TEMPERATURE", "DATA_DIR",
    "SYSTEM_PROMPT", "TOOLS_LIST", "AVAILABLE_FUNCTIONS", "run_agent_turn",
    "load_conversation_history", "save_conversation_history", "list_memories",
    "list_plugins", "reload_plugins", "search_conversation", "session_save",
    "session_load", "session_list", "export_conversation_markdown",
    "export_conversation_html",     "run_memory_pipeline", "trim_and_summarize_history",
    "_clean_messages", "_call_ollama_with_timeout", "turbo_diagnostico",
    "hindsight_auto_learn", "hindsight_context_for_turn",
    "turbo_cache_clear", "task_decompose", "structured_reasoning", "code_review",
    "ensure_ollama", "get_system_info",
]
