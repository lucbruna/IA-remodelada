"""
core/semantic_cache.py
======================
Cache semantico de respostas usando ChromaDB.

Inspirado no ChatGPT que reutiliza respostas similares.
Cacheia perguntas e respostas com embeddings para busca por similaridade.

Funcionalidades:
  - Cache por similaridade cosine (nao exata)
  - TTL configuravel para invalidacao
  - Estatisticas de hit/miss
  - Export/import do cache
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ._common import (
    os, json, logging, datetime, timedelta, time,
    DATA_DIR, EMBEDDING_MODEL,
)

# --- Config ---
CACHE_DIR = os.path.join(DATA_DIR, "semantic_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL_HOURS = int(os.environ.get("AGENTE_CACHE_TTL_HOURS", "24"))
CACHE_MAX_ENTRIES = int(os.environ.get("AGENTE_CACHE_MAX_ENTRIES", "10000"))
CACHE_SIMILARITY_THRESHOLD = float(os.environ.get("AGENTE_CACHE_THRESHOLD", "0.85"))


class SemanticCache:
    """Cache semantico de respostas usando ChromaDB."""

    def __init__(self, collection_name: str = "response_cache"):
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._stats = {"hits": 0, "misses": 0, "stores": 0}

    def _init_chroma(self):
        """Inicializa ChromaDB."""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=CACHE_DIR,
                settings=Settings(anonymized_telemetry=False),
            )

            def ollama_embedding(texts):
                try:
                    import ollama
                    embeddings = []
                    for text in texts:
                        resp = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
                        embeddings.append(resp.get("embedding", [0] * 384))
                    return embeddings
                except Exception:
                    return [[0] * 384 for _ in texts]

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=ollama_embedding,
                metadata={"hnsw:space": "cosine"},
            )

        except ImportError:
            logging.warning("ChromaDB nao instalado. Cache semantico indisponivel.")
            self._client = None
        except Exception as e:
            logging.error("Erro ao inicializar ChromaDB: %s", e)
            self._client = None

    def get(self, query: str, threshold: float = None) -> Optional[Dict[str, Any]]:
        """Busca cache por similaridade semantica."""
        self._init_chroma()
        if not self._collection:
            return None

        threshold = threshold or CACHE_SIMILARITY_THRESHOLD

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=1,
            )

            if not results.get("ids") or not results["ids"][0]:
                self._stats["misses"] += 1
                return None

            doc_id = results["ids"][0][0]
            distance = results["distances"][0][0] if results.get("distances") else 1.0
            similarity = 1 - distance

            if similarity < threshold:
                self._stats["misses"] += 1
                return None

            doc = self._collection.get(ids=[doc_id])
            if not doc.get("metadatas"):
                self._stats["misses"] += 1
                return None

            metadata = doc["metadatas"][0]
            cached_at = metadata.get("cached_at", "")

            if cached_at:
                try:
                    cached_time = datetime.fromisoformat(cached_at)
                    age_hours = (datetime.now() - cached_time).total_seconds() / 3600
                    if age_hours > CACHE_TTL_HOURS:
                        self._stats["misses"] += 1
                        return None
                except Exception:
                    pass

            self._stats["hits"] += 1
            return {
                "response": metadata.get("response", ""),
                "query": metadata.get("query", ""),
                "similarity": round(similarity, 3),
                "cached_at": cached_at,
                "hits": metadata.get("hits", 0) + 1,
            }

        except Exception as e:
            logging.warning("Erro ao buscar cache: %s", e)
            self._stats["misses"] += 1
            return None

    def set(self, query: str, response: str, metadata: dict = None) -> bool:
        """Armazena par pergunta-resposta no cache."""
        self._init_chroma()
        if not self._collection:
            return False

        try:
            doc_id = hashlib.md5(("%s:%s" % (query, response[:100])).encode()).hexdigest()

            meta = {
                "query": query[:500],
                "response": response[:2000],
                "cached_at": datetime.now().isoformat(),
                "hits": 0,
            }
            if metadata:
                meta.update(metadata)

            self._collection.upsert(
                ids=[doc_id],
                documents=[query],
                metadatas=[meta],
            )

            self._stats["stores"] += 1
            self._cleanup_if_needed()
            return True

        except Exception as e:
            logging.warning("Erro ao armazenar no cache: %s", e)
            return False

    def _cleanup_if_needed(self):
        """Remove entradas antigas se exceder o limite."""
        try:
            count = self._collection.count()
            if count <= CACHE_MAX_ENTRIES:
                return

            remove_count = count - int(CACHE_MAX_ENTRIES * 0.9)
            docs = self._collection.get(limit=remove_count)
            if docs.get("ids"):
                self._collection.delete(ids=docs["ids"][:remove_count])
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Retorna estatisticas do cache."""
        self._init_chroma()
        count = 0
        if self._collection:
            try:
                count = self._collection.count()
            except Exception:
                pass

        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "total_entries": count,
            "max_entries": CACHE_MAX_ENTRIES,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "stores": self._stats["stores"],
            "hit_rate": round(hit_rate * 100, 1),
            "ttl_hours": CACHE_TTL_HOURS,
            "threshold": CACHE_SIMILARITY_THRESHOLD,
        }

    def clear(self) -> str:
        """Limpa todo o cache."""
        self._init_chroma()
        if self._collection:
            try:
                self._client.delete_collection(self.collection_name)
                self._collection = None
                self._stats = {"hits": 0, "misses": 0, "stores": 0}
                return "Cache limpo com sucesso."
            except Exception as e:
                return "Erro ao limpar cache: %s" % e
        return "Cache nao inicializado."


# --- Instancia global ---
_cache = None


def get_cache() -> SemanticCache:
    """Retorna a instancia global do cache semantico."""
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache


# --- Ferramentas para o agente ---

def semantic_cache_get(query: str) -> str:
    """Ferramenta: busca cache semantico por pergunta similar."""
    cache = get_cache()
    result = cache.get(query)
    if result:
        return "(Cache hit %.0f%%): %s" % (result["similarity"] * 100, result["response"][:500])
    return "Nenhum cache encontrado."


def semantic_cache_set(query: str, response: str) -> str:
    """Ferramenta: armazena par pergunta-resposta no cache."""
    cache = get_cache()
    ok = cache.set(query, response)
    return "Cache atualizado." if ok else "Erro ao atualizar cache."


def semantic_cache_stats() -> str:
    """Ferramenta: retorna estatisticas do cache."""
    cache = get_cache()
    stats = cache.get_stats()
    return json.dumps(stats, indent=2)


def semantic_cache_clear() -> str:
    """Ferramenta: limpa o cache semantico."""
    cache = get_cache()
    return cache.clear()
