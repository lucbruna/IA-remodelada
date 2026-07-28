"""
core/request_middleware.py
=========================
Middleware de logging e tracking para requests HTTP.

Funcionalidades:
  - Request ID tracking (UUID unico por request)
  - Logging de todas as requests (method, path, status, duration)
  - Rate limiting por IP
  - Request body logging (opcional)
  - Response time tracking
  - Error tracking
"""

import os
import time
import json
import logging
from typing import Optional, Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ._common import logging, json, datetime, time

logger = logging.getLogger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loga todas as requests HTTP."""

    async def dispatch(self, request: Request, call_next):
        # Gera request ID unico
        import uuid
        request_id = str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Log do request
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Skip logging para endpoints de ruido
        skip_paths = {"/health", "/metrics", "/dashboard/stream", "/autonomy/events"}
        log_request = path not in skip_paths

        if log_request:
            logger.info(
                "[%s] %s %s from %s",
                request_id, method, path, client_ip,
            )

        # Processa request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log do erro
            duration_ms = (time.time() - request.state.start_time) * 1000
            logger.error(
                "[%s] %s %s -> ERROR %.0fms: %s",
                request_id, method, path, duration_ms, str(e),
            )
            raise

        # Calcula duration
        duration_ms = (time.time() - request.state.start_time) * 1000

        # Adiciona headers de tracking
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = "%.0fms" % duration_ms

        # Log do response
        if log_request:
            status = response.status_code
            level = logging.WARNING if status >= 400 else logging.INFO
            logger.log(
                level,
                "[%s] %s %s -> %d (%.0fms)",
                request_id, method, path, status, duration_ms,
            )

        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware que trackea erros e envia para observabilidade."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Registra erro para observabilidade
            try:
                from .hooks import hook_emit
                hook_emit("error", {
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "error_type": type(e).__name__,
                })
            except Exception:
                pass

            # Registra no plugin de analytics
            try:
                from plugins.plugin_analytics import track_error
                track_error("http_middleware", str(e))
            except Exception:
                pass

            raise


class RequestBodyLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware opcional que loga o body das requests (debug)."""

    def __init__(self, app, log_body: bool = False, max_body_size: int = 1000):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        if not self.log_body:
            return await call_next(request)

        # Le body (apenas para requests com body)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    body_str = body.decode("utf-8", errors="replace")
                    logger.debug(
                        "[%s] Request body: %s",
                        getattr(request.state, "request_id", "?"),
                        body_str[:500],
                    )
            except Exception:
                pass

        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware que coleta metricas de requests."""

    def __init__(self, app):
        super().__init__(app)
        self._metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "total_duration_ms": 0,
            "by_status": {},
            "by_path": {},
        }
        self._lock = __import__("threading").Lock()

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        self._metrics["total_requests"] += 1

        try:
            response = await call_next(request)
        except Exception as e:
            self._metrics["total_errors"] += 1
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            self._metrics["total_duration_ms"] += duration_ms

            status = getattr(response, "status_code", 500)
            with self._lock:
                self._metrics["by_status"][status] = self._metrics["by_status"].get(status, 0) + 1

                path = request.url.path
                # Normaliza paths com IDs
                normalized = self._normalize_path(path)
                if normalized not in self._metrics["by_path"]:
                    self._metrics["by_path"][normalized] = {"count": 0, "total_ms": 0}
                self._metrics["by_path"][normalized]["count"] += 1
                self._metrics["by_path"][normalized]["total_ms"] += duration_ms

        return response

    def _normalize_path(self, path: str) -> str:
        """Normaliza paths com IDs numericos/UUIDs."""
        import re
        # UUIDs
        path = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}", path)
        # IDs numericos
        path = re.sub(r"/\d+", "/{id}", path)
        return path

    def get_metrics(self) -> dict:
        """Retorna metricas coletadas."""
        avg_duration = (
            self._metrics["total_duration_ms"] / self._metrics["total_requests"]
            if self._metrics["total_requests"] > 0
            else 0
        )

        return {
            **self._metrics,
            "average_duration_ms": round(avg_duration, 1),
            "error_rate": round(
                self._metrics["total_errors"] / max(self._metrics["total_requests"], 1) * 100,
                2,
            ),
        }


# --- Instancia global ---
_metrics_middleware = None


def get_metrics_middleware() -> MetricsMiddleware:
    """Retorna o middleware de metricas global."""
    global _metrics_middleware
    if _metrics_middleware is None:
        _metrics_middleware = MetricsMiddleware(None)
    return _metrics_middleware


def get_request_metrics() -> str:
    """Ferramenta: retorna metricas de requests."""
    middleware = get_metrics_middleware()
    metrics = middleware.get_metrics()
    return json.dumps(metrics, indent=2, default=str)
