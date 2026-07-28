"""
config.py
=========
Fonte única de configuração do Agente Local.

Centraliza modelo, visão, limites e parâmetros para evitar divergências
entre módulos (ex: agente_core usava "llama3.1" enquanto a documentação
e o plugin de ensemble usavam "qwen2.5:1.5b"). Tudo pode ser sobrescrito
por variáveis de ambiente ou pelo arquivo .env.

Carregue sempre daqui:
    from config import MODEL, VISION_MODEL, NUM_CTX, TEMPERATURE
"""

import os
import json
import threading


def _load_dotenv() -> None:
    """
    Carrega variáveis de ambiente de um arquivo .env, se existir.

    Feito manualmente (sem dependência de python-dotenv) para não quebrar
    em ambientes onde a lib não está instalada. Só define a variável se ela
    ainda não estiver definida no ambiente.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(base, ".env"),):
        if not os.path.exists(candidate):
            return
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key, val = key.strip(), val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            return


_load_dotenv()

# ─── Modelos ────────────────────────────────────────────────────────
# Modelo principal de texto/ferramentas.
# Opcoes recomendadas (por qualidade):
#   - qwen2.5:7b (OTIMIZADO - 7B params, roda bem em 16GB RAM)
#   - qwen2.5:32b (ALTA QUALIDADE - 32B params, requer 24GB+ RAM)
#   - llama3.1:70b (MAXIMA QUALIDADE - 70B params, requer 48GB+ RAM)
#   - gemma4:12b (Google - 12B params, bom equilibrio)
#   - bonsai-27b-q4km (PRISM ML - 27B params, 15.4GB GGUF, requer ollama create)
MODEL = os.environ.get("AGENTE_MODEL", "qwen2.5:7b")
# Modelo multimodal para descrever/perguntar sobre imagens.
# Opcoes: llava, bakllava, llava:13b, llama3.2-vision:11b
VISION_MODEL = os.environ.get("AGENTE_VISION_MODEL", "llava")
# Modelo de embeddings para busca semantica
EMBEDDING_MODEL = os.environ.get("AGENTE_EMBEDDING_MODEL", "nomic-embed-text")
# Modelo para transcricao de audio (Whisper via Ollama ou local)
WHISPER_MODEL = os.environ.get("AGENTE_WHISPER_MODEL", "whisper-large-v3")

# ─── Qualidade de raciocínio ────────────────────────────────────────
# Otimizado para qwen2.5:7b em 16GB RAM (oficial Qwen docs)
# num_ctx 8192: suficiente para código/chat, KV cache cabe em ~1.5GB RAM
# temperature 0.6: equilíbrio entre criatividade e precisão
NUM_CTX = int(os.environ.get("AGENTE_NUM_CTX", "8192"))
TEMPERATURE = float(os.environ.get("AGENTE_TEMPERATURE", "0.6"))
# Max tokens na resposta (0 = sem limite, usa padrao do modelo)
MAX_TOKENS = int(os.environ.get("AGENTE_MAX_TOKENS", "4096"))

# ─── Robustez (evita travamentos e loops) ───────────────────────────
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("AGENTE_TIMEOUT", "300"))
OLLAMA_KEEP_ALIVE = os.environ.get("AGENTE_KEEP_ALIVE", "5m")
MAX_TOOL_ROUNDS = int(os.environ.get("AGENTE_MAX_TOOL_ROUNDS", "15"))
MAX_HISTORY_MESSAGES = int(os.environ.get("AGENTE_MAX_HISTORY", "80"))
OLLAMA_MAX_RETRIES = int(os.environ.get("AGENTE_MAX_RETRIES", "3"))
AUTO_CONTEXT_MAX_CHARS = int(os.environ.get("AGENTE_AUTO_CONTEXT", "3500"))

# ─── Servidor ───────────────────────────────────────────────────────
HOST = os.environ.get("AGENTE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AGENTE_PORT", "8000"))

# ─── Diretório de dados ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "agente_data")
os.makedirs(DATA_DIR, exist_ok=True)

PARAM_FILE = os.path.join(DATA_DIR, "parametros_otimizados.json")

# ─── API Fallback (quando modelo local nao da conta) ─────────────────
# Se True, usa modelo API automaticamente quando local falha
LLM_FALLBACK_ENABLED = os.environ.get("AGENTE_FALLBACK_ENABLED", "false").lower() == "true"
# Modelo API padrao para fallback
LLM_FALLBACK_MODEL = os.environ.get("AGENTE_FALLBACK_MODEL", "gpt-4o")
# Threshold de confianca para fallback (0.0 = sempre usa API, 1.0 = nunca)
LLM_FALLBACK_THRESHOLD = float(os.environ.get("AGENTE_FALLBACK_THRESHOLD", "0.7"))
# Cost tracking (para monitorar gastos com API)
LLM_COST_LIMIT_USD = float(os.environ.get("AGENTE_COST_LIMIT", "10.0"))
LLM_COST_TRACK_FILE = os.path.join(DATA_DIR, "cost_tracking.json")
# Prompt caching (reduz tokens repetidos em ate 90%)
PROMPT_CACHE_ENABLED = os.environ.get("AGENTE_CACHE_ENABLED", "true").lower() == "true"
PROMPT_CACHE_TTL_SECONDS = int(os.environ.get("AGENTE_CACHE_TTL", "600"))
PROMPT_CACHE_DIR = os.path.join(DATA_DIR, "prompt_cache")

# ─── Seguranca da API ────────────────────────────────────────────────
# Se definido, a API exige autenticacao por API key.
# Use: AGENTE_API_KEY=sua_chave_aqui no .env
API_KEY = os.environ.get("AGENTE_API_KEY", "")
# Rate limiting: max requests por IP por janela de tempo
RATE_LIMIT = int(os.environ.get("AGENTE_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW = int(os.environ.get("AGENTE_RATE_LIMIT_WINDOW", "60"))

# ─── Constantes nomeadas (evitam magic numbers) ──────────────────────
# Memoria evolutiva: frequencia de auto-evolucao (1 em N chamadas)
AUTO_EVOLVE_INTERVAL = int(os.environ.get("AGENTE_AUTO_EVOLVE_INTERVAL", "20"))
# Hindsight: threshold de cosine similarity para dedup de fatos
HINDSIGHT_DEDUP_THRESHOLD = float(os.environ.get("AGENTE_HINDSIGHT_DEDUP", "0.92"))
# Hindsight: embeddings max por batch
HINDSIGHT_EMBED_BATCH_SIZE = int(os.environ.get("AGENTE_HINDSIGHT_BATCH", "10"))
# Compactacao: caracteres por token (estimativa)
CHARS_PER_TOKEN = int(os.environ.get("AGENTE_CHARS_PER_TOKEN", "4"))
# Prompt guard: tamanho maximo de input
PROMPT_GUARD_MAX_INPUT = int(os.environ.get("AGENTE_PROMPT_GUARD_MAX", "20000"))

_lock = threading.Lock()


def _coerce(name, value, cast):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def load_optimized_parameters() -> None:
    """
    Aplica parâmetros otimizados pela auto-evolução em runtime.

    Substitui a lógica anterior que só carregava no import (obrigando
    reiniciar o processo). Respeita os limites de segurança definidos no
    plugin de auto-evolução.
    """
    if not os.path.exists(PARAM_FILE):
        return
    with _lock:
        try:
            with open(PARAM_FILE, "r", encoding="utf-8") as f:
                params = json.load(f)
        except Exception:
            return

        ranges = {
            "num_ctx": (4096, 131072),
            "temperature": (0.1, 1.0),
            "max_tool_rounds": (5, 30),
            "history_messages": (20, 200),
            "timeout_seconds": (30, 300),
        }
        mapping = {
            "num_ctx": "NUM_CTX",
            "temperature": "TEMPERATURE",
            "max_tool_rounds": "MAX_TOOL_ROUNDS",
            "history_messages": "MAX_HISTORY_MESSAGES",
            "timeout_seconds": "OLLAMA_TIMEOUT_SECONDS",
        }
        for key, var in mapping.items():
            if key not in params:
                continue
            val = _coerce(key, params[key], type(ranges[key][0]))
            if val is None:
                continue
            lo, hi = ranges[key]
            val = max(lo, min(hi, val))
            globals()[var] = val


def reload_config() -> None:
    """Recarrega parâmetros otimizados (chamar após auto-evolução)."""
    load_optimized_parameters()


# Carrega parâmetros otimizados assim que o módulo é importado.
load_optimized_parameters()
