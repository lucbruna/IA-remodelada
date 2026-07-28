"""
core/structured_logging.py
=========================
Logging estruturado para producao.

Funcionalidades:
  - Logs em formato JSON para ELK/Grafana
  - Request ID tracking (UUID por request)
  - Performance timing automatico
  - Contexto por request (user, session, model)
  - Rotacao de arquivos
"""

import os
import sys
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar

from ._common import DATA_DIR

# --- Config ---
LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_LEVEL = os.environ.get("AGENTE_LOG_LEVEL", "INFO")
LOG_FORMAT = os.environ.get("AGENTE_LOG_FORMAT", "json")  # "json" ou "text"
LOG_MAX_SIZE_MB = int(os.environ.get("AGENTE_LOG_MAX_SIZE", "50"))
LOG_BACKUP_COUNT = int(os.environ.get("AGENTE_LOG_BACKUPS", "5"))

# --- Context Variables (request-scoped) ---
_request_id: ContextVar = ContextVar("request_id", default="")
_user_id: ContextVar = ContextVar("user_id", default="anonymous")
_session_id: ContextVar = ContextVar("session_id", default="")
_model: ContextVar = ContextVar("model", default="")

_request_start: ContextVar = ContextVar("request_start", default=0.0)


class StructuredFormatter(logging.Formatter):
    """Formatter que gera logs em JSON estruturado."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Adiciona contexto do request
        req_id = _request_id.get("")
        if req_id:
            log_entry["request_id"] = req_id

        user_id = _user_id.get("")
        if user_id:
            log_entry["user_id"] = user_id

        session_id = _session_id.get("")
        if session_id:
            log_entry["session_id"] = session_id

        model = _model.get("")
        if model:
            log_entry["model"] = model

        # Adiciona duration se disponivel
        start = _request_start.get(0.0)
        if start > 0:
            log_entry["duration_ms"] = round((time.time() - start) * 1000, 1)

        # Adiciona extras
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        # Adiciona exception se houver
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Formatter para logs legiveis em terminal."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        req_id = _request_id.get("")[:8]
        req_tag = f" [{req_id}]" if req_id else ""

        timestamp = datetime.now().strftime("%H:%M:%S")

        return "%s%s %-5s%s %s%s%s %s" % (
            timestamp, color, record.levelname, reset,
            record.name, req_tag, "",
            record.getMessage(),
        )


class PerformanceFilter(logging.Filter):
    """Filter que adiciona timing automatico."""

    def filter(self, record):
        if not hasattr(record, "start_time"):
            record.start_time = time.time()
        return True


# --- Request Context Management ---

def generate_request_id() -> str:
    """Gera um novo request ID unico."""
    return str(uuid.uuid4())[:12]


def set_request_context(
    request_id: str = None,
    user_id: str = None,
    session_id: str = None,
    model: str = None,
):
    """Define o contexto do request atual."""
    if request_id:
        _request_id.set(request_id)
    if user_id:
        _user_id.set(user_id)
    if session_id:
        _session_id.set(session_id)
    if model:
        _model.set(model)
    _request_start.set(time.time())


def get_request_id() -> str:
    """Retorna o request ID atual."""
    return _request_id.get("")


def get_request_context() -> Dict[str, Any]:
    """Retorna todo o contexto do request atual."""
    return {
        "request_id": _request_id.get(""),
        "user_id": _user_id.get(""),
        "session_id": _session_id.get(""),
        "model": _model.get(""),
        "duration_ms": round((time.time() - _request_start.get(time.time())) * 1000, 1),
    }


# --- Logger Setup ---

_loggers: Dict[str, logging.Logger] = {}
_configured = False


def setup_logging():
    """Configura o sistema de logging estruturado."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Remove handlers existentes
    root.handlers.clear()

    # Handler para arquivo JSON
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "agente_structured.log"),
        maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(StructuredFormatter())
    file_handler.addFilter(PerformanceFilter())
    root.addHandler(file_handler)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(TextFormatter())
    console_handler.addFilter(PerformanceFilter())
    root.addHandler(console_handler)

    # Handler para erros
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "agente_errors.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root.addHandler(error_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado."""
    if name not in _loggers:
        setup_logging()
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


# --- Convenience Functions ---

def log_request(method: str, path: str, status: int = 200, **extra):
    """Log de request HTTP."""
    logger = get_logger("http")
    logger.info(
        "%s %s -> %d",
        method, path, status,
        extra={"extra_data": {"method": method, "path": path, "status": status, **extra}},
    )


def log_tool_call(tool_name: str, args: dict, duration_ms: float = 0, success: bool = True):
    """Log de chamada de ferramenta."""
    logger = get_logger("tool")
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        "Tool %s (%.0fms) %s",
        tool_name, duration_ms, "OK" if success else "FAIL",
        extra={"extra_data": {"tool": tool_name, "duration_ms": duration_ms, "success": success}},
    )


def log_model_call(model: str, tokens_in: int = 0, tokens_out: int = 0, duration_ms: float = 0):
    """Log de chamada ao modelo."""
    logger = get_logger("model")
    logger.info(
        "Model %s in=%d out=%d (%.0fms)",
        model, tokens_in, tokens_out, duration_ms,
        extra={"extra_data": {"model": model, "tokens_in": tokens_in, "tokens_out": tokens_out, "duration_ms": duration_ms}},
    )


def log_error(error: Exception, context: str = ""):
    """Log de erro com contexto."""
    logger = get_logger("error")
    logger.error(
        "%s: %s",
        context or "Error", str(error),
        exc_info=True,
        extra={"extra_data": {"context": context, "error_type": type(error).__name__}},
    )


def log_security(event: str, level: str = "INFO", details: dict = None):
    """Log de evento de seguranca."""
    logger = get_logger("security")
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(
        log_level,
        "Security: %s",
        event,
        extra={"extra_data": {"event": event, "details": details or {}}},
    )


# Auto-setup on import
setup_logging()
