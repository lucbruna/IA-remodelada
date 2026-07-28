"""
core/api_security.py
====================
Middleware de seguranca para a API: autenticacao por API key,
rate limiting por IP, e validacao de input.

Ativado por variavel de ambiente:
  AGENTE_API_KEY=chave_secreta    (se definido, exige header Authorization)
  AGENTE_RATE_LIMIT=60            (max requests/min por IP, padrao 60)
  AGENTE_RATE_LIMIT_WINDOW=60     (janela em segundos, padrao 60)
"""

import os
import time
import hashlib
import secrets
from collections import defaultdict
from functools import wraps
from typing import Optional

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader

# --- Config ---
API_KEY = os.environ.get("AGENTE_API_KEY", "")
RATE_LIMIT = int(os.environ.get("AGENTE_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW = int(os.environ.get("AGENTE_RATE_LIMIT_WINDOW", "60"))

# Endpoints que NAO precisam de autenticacao
PUBLIC_ENDPOINTS = {
    "/", "/docs", "/redoc", "/openapi.json",
    "/system/status", "/health",
}

# Endpoints que NAO contam no rate limit (SSE streams longos)
RATE_LIMIT_EXEMPT = {
    "/chat/stream", "/autonomy/events", "/dashboard/stream",
    "/mcp/sse", "/metrics",
}


def _get_client_ip(request: Request) -> str:
    """Extrai o IP real do cliente, considerando proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


# --- Rate Limiter ---

class RateLimiter:
    """Rate limiter sliding window por IP."""

    def __init__(self, max_requests: int = RATE_LIMIT, window: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window = window
        self._requests: dict = defaultdict(list)
        self._lock = __import__("threading").Lock()

    def is_allowed(self, ip: str) -> bool:
        """Retorna True se o request e permitido, False se excedeu o limite."""
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            # Limpa requests antigos
            self._requests[ip] = [
                t for t in self._requests[ip] if t > cutoff
            ]

            if len(self._requests[ip]) >= self.max_requests:
                return False

            self._requests[ip].append(now)
            return True

    def get_retry_after(self, ip: str) -> int:
        """Retorna quantos segundos ate poder fazer novo request."""
        with self._lock:
            if not self._requests[ip]:
                return 0
            oldest = min(self._requests[ip])
            return max(1, int(self.window - (time.time() - oldest)))

    def get_usage(self, ip: str) -> dict:
        """Retorna uso atual do rate limit."""
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            recent = [t for t in self._requests.get(ip, []) if t > cutoff]
        return {
            "used": len(recent),
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - len(recent)),
            "window_seconds": self.window,
        }


# Instancia global
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Retorna a instancia do rate limiter."""
    return _rate_limiter


# --- Auth ---

def verify_api_key(api_key: str) -> bool:
    """Verifica se a API key e valida (comparacao constante-time)."""
    if not API_KEY:
        return True
    if not api_key:
        return False
    return secrets.compare_digest(api_key, API_KEY)


def _hash_key(key: str) -> str:
    """Hash da API key para logging seguro (nao expoe a chave)."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# --- Middleware ---

async def security_middleware(request: Request, call_next):
    """Middleware de seguranca: autenticacao + rate limiting.

    1. Verifica API key (se configurada)
    2. Aplica rate limiting por IP
    3. Registra metricas de uso
    """
    path = request.url.path
    client_ip = _get_client_ip(request)

    # Endpoints publicos pulam autenticacao
    if path in PUBLIC_ENDPOINTS or path.startswith("/docs") or path.startswith("/redoc"):
        response = await call_next(request)
        return response

    # Auth check (se API_KEY configurada)
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")

        # Suporta: Authorization: Bearer <key> ou X-API-Key: <key>
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        elif not api_key:
            api_key = ""

        if not verify_api_key(api_key):
            raise HTTPException(
                status_code=401,
                detail="API key invalida ou ausente. Use Authorization: Bearer <key> ou header X-API-Key.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Rate limiting (exceto endpoints exempt)
    if path not in RATE_LIMIT_EXEMPT:
        if not _rate_limiter.is_allowed(client_ip):
            retry_after = _rate_limiter.get_retry_after(client_ip)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit excedido. Tente novamente em {retry_after}s.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                },
            )

    # Processa request
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    # Adiciona headers de seguranca na resposta
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Rate limit headers
    if path not in RATE_LIMIT_EXEMPT:
        usage = _rate_limiter.get_usage(client_ip)
        response.headers["X-RateLimit-Limit"] = str(usage["limit"])
        response.headers["X-RateLimit-Remaining"] = str(usage["remaining"])
        response.headers["X-RateLimit-Reset"] = str(usage["window_seconds"])

    # Timing header
    response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

    return response


# --- Helpers para endpoints ---

def require_admin(request: Request) -> None:
    """Verifica se o request tem permissao de admin (para acoes destrutivas)."""
    if not API_KEY:
        return  # Sem API key configurada, permite tudo (modo desenvolvimento)
    api_key = request.headers.get("X-API-Key", "")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        api_key = auth[7:]
    # Para operacoes admin, exige que a key seja a mesma do .env
    if not verify_api_key(api_key):
        raise HTTPException(403, "Operacao requer permissao de administrador.")
