"""
core
====
Pacote principal do Agente Local.

Expoe a API publica do agente para compatibilidade com imports anteriores.
Usage:
    from core import MODEL, run_agent_turn, AVAILABLE_FUNCTIONS
"""

from ._common import (
    MODEL, VISION_MODEL, NUM_CTX, TEMPERATURE,
    OLLAMA_TIMEOUT_SECONDS, OLLAMA_KEEP_ALIVE,
    MAX_TOOL_ROUNDS, MAX_HISTORY_MESSAGES, OLLAMA_MAX_RETRIES,
    AUTO_CONTEXT_MAX_CHARS, DATA_DIR, reload_config,
    TURBO_AVAILABLE, MEMORY_FILE, HISTORY_FILE, AUTONOMY_FILE,
    LOG_FILE, _load_json, _save_json,
    EMBEDDING_MODEL, WHISPER_MODEL, MAX_TOKENS,
    AUTO_EVOLVE_INTERVAL, HINDSIGHT_DEDUP_THRESHOLD,
    CHARS_PER_TOKEN, PROMPT_GUARD_MAX_INPUT,
)

from .memory_pipeline import SYSTEM_PROMPT, run_memory_pipeline
from .memory import load_conversation_history, save_conversation_history, list_memories, trim_and_summarize_history, remember, recall, forget
from .registry import TOOLS_LIST, AVAILABLE_FUNCTIONS
from .agent_loop import run_agent_turn, run_agent_turn_async, run_agent_turn_stream_async, _execute_tool_call
from .plugins_api import list_plugins, reload_plugins, PluginAPI, PluginManager, PLUGINS_DIR
from .search_tools import search_conversation, search_and_replace
from .downloads_git import session_save, session_load, session_list
from .export import export_conversation_markdown, export_conversation_html, _format_mensagem_para_export
from .hindsight import hindsight_auto_learn, hindsight_context_for_turn
from .llm import _clean_messages, _call_ollama_with_timeout, ensure_ollama, _chat_with_retries
from .turbo_api import turbo_diagnostico, turbo_cache_clear, task_decompose, structured_reasoning, code_review
from .code_exec import get_system_info, calculate, _safe_eval, get_datetime, run_command, run_python_code, fetch_url
from .filesystem import create_folder, write_file, append_file, read_file, list_files, search_files, get_file_info, move_file, copy_file, delete_path
from .media import read_pdf, read_image_text, describe_image
from .autonomy import autonomia_planejar, autonomia_status, _autonomous_context_for_turn

__all__ = [
    "MODEL", "VISION_MODEL", "NUM_CTX", "TEMPERATURE",
    "OLLAMA_TIMEOUT_SECONDS", "OLLAMA_KEEP_ALIVE",
    "MAX_TOOL_ROUNDS", "MAX_HISTORY_MESSAGES", "OLLAMA_MAX_RETRIES",
    "AUTO_CONTEXT_MAX_CHARS", "DATA_DIR", "reload_config",
    "TURBO_AVAILABLE", "MEMORY_FILE", "HISTORY_FILE", "AUTONOMY_FILE",
    "LOG_FILE", "_load_json", "_save_json",
    "EMBEDDING_MODEL", "WHISPER_MODEL", "MAX_TOKENS",
    "AUTO_EVOLVE_INTERVAL", "HINDSIGHT_DEDUP_THRESHOLD",
    "CHARS_PER_TOKEN", "PROMPT_GUARD_MAX_INPUT",
    "SYSTEM_PROMPT", "run_memory_pipeline",
    "TOOLS_LIST", "AVAILABLE_FUNCTIONS",
    "run_agent_turn", "run_agent_turn_async", "run_agent_turn_stream_async",
    "load_conversation_history", "save_conversation_history", "list_memories", "trim_and_summarize_history",
    "list_plugins", "reload_plugins",
    "search_conversation", "search_and_replace",
    "session_save", "session_load", "session_list",
    "export_conversation_markdown", "export_conversation_html",
    "hindsight_auto_learn", "hindsight_context_for_turn",
    "remember", "recall", "forget",
    "_clean_messages", "_call_ollama_with_timeout", "ensure_ollama",
    "turbo_diagnostico", "turbo_cache_clear", "task_decompose",
    "structured_reasoning", "code_review", "get_system_info",
    "calculate", "_safe_eval", "get_datetime", "run_command", "run_python_code", "fetch_url",
    "create_folder", "write_file", "append_file", "read_file", "list_files", "search_files",
    "get_file_info", "move_file", "copy_file", "delete_path",
    "read_pdf", "read_image_text", "describe_image",
    "autonomia_planejar", "autonomia_status", "_autonomous_context_for_turn",
    "PluginAPI", "PluginManager", "PLUGINS_DIR",
    "_execute_tool_call", "_chat_with_retries",
    "_format_mensagem_para_export",
]
