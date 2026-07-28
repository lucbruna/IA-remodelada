"""
core/health_check.py
====================
Health check detalhado com verificacao de dependencias.

Funcionalidades:
  - Verificacao de Ollama (rodando + modelo disponivel)
  - Verificacao de Docker (sandbox)
  - Verificacao de ChromaDB (RAG)
  - Verificacao de disk space
  - Verificacao de memoria
  - Graceful shutdown com cleanup
"""

import os
import sys
import signal
import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Any

from ._common import (
    os, sys, logging, datetime, threading,
    DATA_DIR, MODEL, EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)


class HealthChecker:
    """Verifica saude de todos os componentes do sistema."""

    def __init__(self):
        self._results = {}
        self._last_check = None

    def check_all(self) -> Dict[str, Any]:
        """Executa todos os health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        checks = [
            ("ollama", self._check_ollama),
            ("disk", self._check_disk),
            ("memory", self._check_memory),
            ("docker", self._check_docker),
            ("chromadb", self._check_chromadb),
            ("models", self._check_models),
        ]

        failed = 0
        for name, check_fn in checks:
            try:
                result = check_fn()
                results["checks"][name] = result
                if not result.get("healthy", True):
                    failed += 1
            except Exception as e:
                results["checks"][name] = {"healthy": False, "error": str(e)}
                failed += 1

        if failed > 0:
            results["status"] = "degraded" if failed < len(checks) else "unhealthy"

        self._results = results
        self._last_check = datetime.now()
        return results

    def _check_ollama(self) -> Dict[str, Any]:
        """Verifica se o Ollama esta rodando."""
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            data = __import__("json").loads(resp.read())
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"healthy": True, "status": "running", "models_available": len(models)}
        except Exception as e:
            return {"healthy": False, "status": "offline", "error": str(e)}

    def _check_disk(self) -> Dict[str, Any]:
        """Verifica espaco em disco."""
        try:
            import shutil
            usage = shutil.disk_usage(DATA_DIR)
            free_gb = usage.free / (1024 ** 3)
            return {
                "healthy": free_gb > 1.0,
                "free_gb": round(free_gb, 2),
                "used_percent": round((usage.used / usage.total) * 100, 1),
            }
        except Exception as e:
            return {"healthy": True, "error": str(e)}

    def _check_memory(self) -> Dict[str, Any]:
        """Verifica uso de memoria."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {"healthy": mem.percent < 90, "used_percent": mem.percent}
        except ImportError:
            return {"healthy": True, "note": "psutil not installed"}
        except Exception as e:
            return {"healthy": True, "error": str(e)}

    def _check_docker(self) -> Dict[str, Any]:
        """Verifica se o Docker esta disponivel."""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return {"healthy": True, "version": result.stdout.strip()}
            return {"healthy": False, "error": "Docker not responding"}
        except FileNotFoundError:
            return {"healthy": True, "note": "Docker not installed"}
        except Exception as e:
            return {"healthy": True, "error": str(e)}

    def _check_chromadb(self) -> Dict[str, Any]:
        """Verifica se o ChromaDB esta funcional."""
        try:
            import chromadb
            client = chromadb.PersistentClient(path=os.path.join(DATA_DIR, "semantic_cache"))
            collections = client.list_collections()
            return {"healthy": True, "collections": len(collections)}
        except ImportError:
            return {"healthy": True, "note": "ChromaDB not installed"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def _check_models(self) -> Dict[str, Any]:
        """Verifica se os modelos necessarios estao disponiveis."""
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            data = __import__("json").loads(resp.read())
            models = [m.get("name", "") for m in data.get("models", [])]
            required = [MODEL, EMBEDDING_MODEL]
            missing = [m for m in required if not any(m in available for available in models)]
            return {"healthy": len(missing) == 0, "missing": missing}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def get_summary(self) -> str:
        """Retorna resumo textual do health check."""
        results = self._results or self.check_all()
        lines = ["Health Check Summary", "=" * 40]
        lines.append("Status: %s" % results["status"].upper())
        lines.append("Timestamp: %s" % results["timestamp"])
        lines.append("")
        for name, check in results.get("checks", {}).items():
            status = "OK" if check.get("healthy", True) else "FAIL"
            lines.append("[%s] %s" % (status, name))
            for k, v in check.items():
                if k != "healthy":
                    lines.append("    %s: %s" % (k, v))
        return "\n".join(lines)


class GracefulShutdown:
    """Gerencia shutdown limpo do servidor."""

    def __init__(self):
        self._cleanup_handlers = []
        self._is_shutting_down = False

    def register_cleanup(self, handler):
        """Registra funcao de cleanup para o shutdown."""
        self._cleanup_handlers.append(handler)

    def signal_handler(self, signum, frame):
        """Handler para sinais de shutdown."""
        logger.info("Shutdown signal received (signal=%d)", signum)
        self._is_shutting_down = True
        for handler in reversed(self._cleanup_handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(handler())
                else:
                    handler()
            except Exception as e:
                logger.error("Cleanup handler error: %s", e)
        logger.info("Shutdown complete")

    def setup_signals(self):
        """Configura handlers de sinal para shutdown limpo."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    @property
    def is_shutting_down(self) -> bool:
        return self._is_shutting_down


# --- Instancias globais ---
_health_checker = None
_graceful_shutdown = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def get_graceful_shutdown() -> GracefulShutdown:
    global _graceful_shutdown
    if _graceful_shutdown is None:
        _graceful_shutdown = GracefulShutdown()
    return _graceful_shutdown


def health_check_detailed() -> str:
    """Ferramenta: retorna health check detalhado."""
    checker = get_health_checker()
    checker.check_all()
    return checker.get_summary()


def system_resources() -> str:
    """Ferramenta: retorna recursos do sistema."""
    import json
    checker = get_health_checker()
    results = checker.check_all()
    return json.dumps(results.get("checks", {}), indent=2, default=str)
