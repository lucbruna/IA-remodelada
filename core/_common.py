"""
core/_common.py
===============
Imports e constantes compartilhados por todos os submódulos do pacote core.

Os módulos de domínio (llm, memory, filesystem, ...) importam daqui em vez
de repetir imports e de referenciar agente_core (que evitaria importação
circular). Tudo que era global no antigo agente_core.py e é usado por
múltiplos domínios vive aqui.
"""

import os
import re
import sys
import io
import json
import ast
import time
import zipfile
import hashlib
import shutil
import shlex
import logging
import platform
import operator
import subprocess
import contextlib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Any, Callable, Optional, Generator, List, Dict, Tuple

import threading

# Configuração centralizada (modelo, visão, limites, paths).
from config import (
    MODEL,
    VISION_MODEL,
    EMBEDDING_MODEL,
    WHISPER_MODEL,
    MAX_TOKENS,
    NUM_CTX,
    TEMPERATURE,
    OLLAMA_TIMEOUT_SECONDS,
    OLLAMA_KEEP_ALIVE,
    MAX_TOOL_ROUNDS,
    MAX_HISTORY_MESSAGES,
    OLLAMA_MAX_RETRIES,
    AUTO_CONTEXT_MAX_CHARS,
    DATA_DIR,
    reload_config,
    AUTO_EVOLVE_INTERVAL,
    HINDSIGHT_DEDUP_THRESHOLD,
    CHARS_PER_TOKEN,
    PROMPT_GUARD_MAX_INPUT,
)

# Turbo module — inteligencia avancada (carregado silenciosamente se disponivel)
try:
    import agente_turbo
    TURBO_AVAILABLE = True
except ImportError:
    TURBO_AVAILABLE = False

MEMORY_FILE = os.path.join(DATA_DIR, "memoria.json")
HISTORY_FILE = os.path.join(DATA_DIR, "historico.json")
AUTONOMY_FILE = os.path.join(DATA_DIR, "autonomia.json")

LOG_FILE = os.path.join(DATA_DIR, "agente.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def _load_json(path: str, default: Any) -> Any:
    """Carrega JSON com fallback seguro (usado por toda a aplicacao)."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(path: str, data: Any) -> None:
    """Salva dados em JSON (encoding utf-8, indentado)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


__all__ = [
    "os", "re", "sys", "io", "json", "ast", "time", "zipfile", "hashlib",
    "shutil", "shlex", "logging", "platform", "operator", "subprocess",
    "contextlib", "urllib", "datetime", "threading",
    "Any", "Callable", "Optional", "Generator", "List", "Dict", "Tuple",
    "MODEL", "VISION_MODEL", "EMBEDDING_MODEL", "WHISPER_MODEL", "MAX_TOKENS", "NUM_CTX", "TEMPERATURE",
    "OLLAMA_TIMEOUT_SECONDS", "OLLAMA_KEEP_ALIVE", "MAX_TOOL_ROUNDS",
    "MAX_HISTORY_MESSAGES", "OLLAMA_MAX_RETRIES", "AUTO_CONTEXT_MAX_CHARS",
    "DATA_DIR", "reload_config", "TURBO_AVAILABLE", "agente_turbo",
    "MEMORY_FILE", "HISTORY_FILE", "AUTONOMY_FILE", "LOG_FILE",
    "_load_json", "_save_json", "shlex",
    "AUTO_EVOLVE_INTERVAL", "HINDSIGHT_DEDUP_THRESHOLD",
    "CHARS_PER_TOKEN", "PROMPT_GUARD_MAX_INPUT",
]
