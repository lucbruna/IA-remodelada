import os
import sys
import json
import time
import logging
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from ._common import DATA_DIR

MODEL_CACHE_FILE = os.path.join(DATA_DIR, "model_recommendation.json")
os.makedirs(DATA_DIR, exist_ok=True)

MODEL_REGISTRY = {
    "small": {
        "ram_gb": 8,
        "description": "Maquinas modestas (8GB RAM, sem GPU)",
        "models": [
            {"name": "qwen2.5:7b", "size_gb": 4.5, "type": "text", "ctx": 32768, "quality": "medio", "recommended": True},
            {"name": "gemma4:E4B", "size_gb": 3.8, "type": "text", "ctx": 8192, "quality": "medio", "recommended": False},
            {"name": "llama3.2:3b", "size_gb": 2.5, "type": "text", "ctx": 8192, "quality": "basico", "recommended": False},
            {"name": "phi3:mini", "size_gb": 2.8, "type": "text", "ctx": 4096, "quality": "basico", "recommended": False},
        ],
    },
    "medium": {
        "ram_gb": 16,
        "description": "Maquinas intermediarias (16-24GB RAM)",
        "models": [
            {"name": "qwen2.5:32b", "size_gb": 19, "type": "text", "ctx": 32768, "quality": "alto", "recommended": True},
            {"name": "gemma4:12B", "size_gb": 10, "type": "text", "ctx": 8192, "quality": "alto", "recommended": False},
            {"name": "llama3.1:8b", "size_gb": 5.5, "type": "text", "ctx": 32768, "quality": "medio-alto", "recommended": False},
            {"name": "mistral:7b", "size_gb": 4.8, "type": "text", "ctx": 32768, "quality": "medio", "recommended": False},
        ],
    },
    "large": {
        "ram_gb": 32,
        "description": "Maquinas potentes (32-64GB RAM)",
        "models": [
            {"name": "qwen2.5:72b", "size_gb": 42, "type": "text", "ctx": 32768, "quality": "excelente", "recommended": True},
            {"name": "llama3.1:70b", "size_gb": 42, "type": "text", "ctx": 32768, "quality": "excelente", "recommended": False},
            {"name": "mixtral:8x7b", "size_gb": 30, "type": "text", "ctx": 32768, "quality": "alto", "recommended": False},
            {"name": "qwen2.5:32b", "size_gb": 19, "type": "text", "ctx": 32768, "quality": "alto", "recommended": False},
        ],
    },
    "vision": [
        {"name": "llava", "size_gb": 4.2, "type": "vision", "ctx": 4096, "quality": "medio"},
        {"name": "llama3.2-vision:11b", "size_gb": 8.0, "type": "vision", "ctx": 8192, "quality": "alto"},
        {"name": "llava:13b", "size_gb": 8.5, "type": "vision", "ctx": 4096, "quality": "alto"},
    ],
    "embedding": [
        {"name": "nomic-embed-text", "size_gb": 0.3, "type": "embedding", "ctx": 8192, "quality": "bom"},
        {"name": "mxbai-embed-large", "size_gb": 0.7, "type": "embedding", "ctx": 512, "quality": "bom"},
        {"name": "snowflake-arctic-embed2", "size_gb": 0.5, "type": "embedding", "ctx": 8192, "quality": "excelente"},
    ],
}

_download_progress = {}
_download_lock = threading.Lock()


def _get_ram_gb() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().total / (1024**3))
    except ImportError:
        return 16


def _get_vram_gb() -> int:
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            nums = [int(x.strip()) for x in result.stdout.strip().split("\n") if x.strip().isdigit()]
            return max(nums) // 1024 if nums else 0
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return 16
    except Exception:
        pass
    return 0


def _get_ollama_models() -> List[Dict[str, Any]]:
    try:
        import ollama
        resp = ollama.list()
        raw = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
        return [
            {
                "name": m.get("name", m.get("model", "?")),
                "size_gb": round(m.get("size", 0) / (1024**3), 1),
                "modified": m.get("modified_at", ""),
            }
            for m in raw
        ]
    except Exception:
        return []


def _check_ollama_health() -> Tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=3)
        return True, "Ollama rodando"
    except Exception as e:
        return False, f"Ollama nao acessivel: {e}"


def detect_system() -> Dict[str, Any]:
    ram = _get_ram_gb()
    vram = _get_vram_gb()
    ollama_ok, ollama_msg = _check_ollama_health()

    if vram >= 48:
        tier = "large"
    elif vram >= 16 or ram >= 24:
        tier = "medium"
    else:
        tier = "small"

    return {
        "ram_gb": ram,
        "vram_gb": vram,
        "has_gpu": vram > 0,
        "tier": tier,
        "ollama_health": ollama_ok,
        "ollama_message": ollama_msg,
        "platform": sys.platform,
    }


def recommend_model(task_type: str = "text") -> Dict[str, Any]:
    system = detect_system()
    ollama_models = _get_ollama_models()
    installed_names = {m["name"].split(":")[0] + ":" + (m["name"].split(":")[1] if ":" in m["name"] else "") for m in ollama_models}

    if task_type == "vision":
        candidates = MODEL_REGISTRY["vision"]
    elif task_type == "embedding":
        candidates = MODEL_REGISTRY["embedding"]
    else:
        tier_info = MODEL_REGISTRY.get(system["tier"], MODEL_REGISTRY["small"])
        candidates = tier_info["models"]

    best = None
    already_installed = None
    for m in candidates:
        if m["name"] in installed_names or any(m["name"] in name for name in installed_names):
            already_installed = m
        if best is None or (m.get("recommended") and not best.get("recommended")):
            best = m

    recommended = already_installed or best or candidates[0]

    return {
        "system": system,
        "task_type": task_type,
        "recommended": recommended,
        "tier_models": candidates,
        "installed": ollama_models[:20],
        "already_have": already_installed is not None,
        "message": f"Recomendado: {recommended['name']} ({recommended['quality']}) - {recommended.get('size_gb', '?')}GB"
        if not already_installed else f"Ja instalado: {recommended['name']}",
    }


def list_available_models() -> List[Dict[str, Any]]:
    result = []
    for tier_name, tier_data in MODEL_REGISTRY.items():
        if isinstance(tier_data, dict):
            for m in tier_data.get("models", []):
                m["tier"] = tier_name
                m["tier_desc"] = tier_data.get("description", "")
                result.append(m)
        elif isinstance(tier_data, list):
            for m in tier_data:
                m["tier"] = tier_name
                result.append(m)
    return result


def get_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    all_models = list_available_models()
    for m in all_models:
        if m["name"] == model_name:
            return m
    return None


def download_model(model_name: str, timeout: int = 600) -> Dict[str, Any]:
    global _download_progress

    ollama_ok, msg = _check_ollama_health()
    if not ollama_ok:
        return {"success": False, "error": msg}

    with _download_lock:
        _download_progress[model_name] = {"status": "downloading", "progress": 0, "started": time.time()}

    try:
        import ollama
        def progress_callback(current, total):
            with _download_lock:
                _download_progress[model_name] = {
                    "status": "downloading",
                    "progress": round(current / total * 100, 1) if total else 0,
                    "current": current,
                    "total": total,
                }

        thread = threading.Thread(target=_do_pull, args=(model_name,), daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        with _download_lock:
            _download_progress[model_name]["status"] = "completed"
            _download_progress[model_name]["progress"] = 100.0

        return {"success": True, "model": model_name, "message": f"Modelo {model_name} baixado com sucesso"}
    except Exception as e:
        with _download_lock:
            _download_progress[model_name] = {"status": "failed", "error": str(e)}
        return {"success": False, "error": str(e)}


def _do_pull(model_name: str) -> None:
    try:
        import ollama
        ollama.pull(model_name)
    except Exception:
        pass


def get_download_progress(model_name: str = None) -> Dict[str, Any]:
    with _download_lock:
        if model_name:
            return _download_progress.get(model_name, {"status": "unknown"})
        return dict(_download_progress)


def benchmark_model(model_name: str = None, quick: bool = True) -> Dict[str, Any]:
    if model_name is None:
        from config import MODEL
        model_name = MODEL

    try:
        import ollama
        from core.llm import _call_ollama_with_timeout

        tests = [
            ("generate short poem", "Crie um poema de 4 versos sobre programacao."),
            ("math reasoning", "Qual e a raiz quadrada de 144? Explique passo a passo."),
        ] if quick else [
            ("generate short poem", "Crie um poema de 4 versos sobre programacao."),
            ("math reasoning", "Qual e a raiz quadrada de 144? Explique passo a passo."),
            ("code generation", "Escreva uma funcao Python que ordena uma lista usando quicksort."),
            ("summarization", "Sumarize em 3 frases: A inteligencia artificial esta transformando todos os setores da economia."),
        ]

        results = []
        total_latency = 0
        total_tokens = 0

        for name, prompt in tests:
            start = time.time()
            try:
                response = _call_ollama_with_timeout(
                    ollama.chat,
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={"num_ctx": 4096, "temperature": 0.1},
                )
                elapsed = time.time() - start
                content = response.get("message", {}).get("content", "")
                tokens = len(content.split())
                total_latency += elapsed
                total_tokens += tokens
                results.append({
                    "test": name,
                    "latency_ms": round(elapsed * 1000),
                    "tokens": tokens,
                    "tokens_per_sec": round(tokens / elapsed, 1) if elapsed > 0 else 0,
                    "content_preview": content[:100],
                })
            except Exception as e:
                results.append({"test": name, "error": str(e)})

        avg_latency = (total_latency / len(tests)) if tests else 0
        avg_tokens_per_sec = (total_tokens / total_latency) if total_latency > 0 else 0

        return {
            "model": model_name,
            "quick": quick,
            "results": results,
            "summary": {
                "avg_latency_ms": round(avg_latency * 1000),
                "avg_tokens_per_sec": round(avg_tokens_per_sec, 1),
                "total_tasks": len(tests),
                "successful": sum(1 for r in results if "error" not in r),
                "failed": sum(1 for r in results if "error" in r),
            },
            "finished_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"model": model_name, "error": str(e)}


def set_default_model(model_name: str) -> Dict[str, Any]:
    info = get_model_info(model_name)
    if info is None:
        ollama_models = _get_ollama_models()
        if not any(model_name in m["name"] for m in ollama_models):
            return {"success": False, "error": f"Modelo {model_name} nao encontrado no registry nem no Ollama"}

    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                lines = f.readlines()
            with open(config_path, "w") as f:
                found = False
                for line in lines:
                    if line.startswith("AGENTE_MODEL="):
                        f.write(f"AGENTE_MODEL={model_name}\n")
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f"\nAGENTE_MODEL={model_name}\n")
        else:
            with open(config_path, "w") as f:
                f.write(f"AGENTE_MODEL={model_name}\n")

        os.environ["AGENTE_MODEL"] = model_name

        import config
        config.reload_config()

        return {"success": True, "model": model_name, "message": f"Modelo padrao alterado para {model_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_recommendation() -> Dict[str, Any]:
    system = detect_system()
    rec = recommend_model("text")

    vision_rec = recommend_model("vision")
    embedding_rec = recommend_model("embedding")

    return {
        "system": system,
        "recommended_model": rec["recommended"],
        "recommended_vision": vision_rec["recommended"],
        "recommended_embedding": embedding_rec["recommended"],
        "already_installed": rec["already_have"],
        "message": (
            f"Sistema: {system['ram_gb']}GB RAM, {system['vram_gb']}GB VRAM\n"
            f"Modelo recomendado: {rec['recommended']['name']} ({rec['recommended']['quality']})\n"
            f"Status: {'Ja instalado' if rec['already_have'] else 'Precisa baixar'}"
        ),
    }
