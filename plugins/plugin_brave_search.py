"""
plugin_brave_search.py
======================
Busca web via Brave Search API.

Requer: BRAVE_API_KEY no .env (https://brave.com/search/api/)
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Brave Search"

import os
import json
import logging

logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_API = "https://api.search.brave.com/res/v1"


def _headers():
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }


def register(api):

    def brave_search_status() -> str:
        if not BRAVE_API_KEY:
            return "❌ BRAVE_API_KEY nao configurado. Obtenha em https://brave.com/search/api/"
        return f"✅ Brave Search API configurada (chave: ...{BRAVE_API_KEY[-6:]})"

    def brave_search_web(query: str, count: int = 10) -> str:
        import requests
        if not BRAVE_API_KEY:
            return "❌ BRAVE_API_KEY nao configurado."
        try:
            params = {"q": query, "count": min(count, 20)}
            resp = requests.get(f"{BRAVE_API}/web/search", headers=_headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("web", {}).get("results", [])
            if not results:
                return f"Nenhum resultado para: {query}"
            items = []
            for r in results[:count]:
                items.append(
                    f"**{r.get('title', 'N/A')}**\n"
                    f"  URL: {r.get('url', '')}\n"
                    f"  {r.get('description', '')[:120]}"
                )
            return f"**{len(results)} resultados para '{query}':**\n\n" + "\n\n".join(items)
        except Exception as e:
            return f"❌ Erro na busca: {e}"

    def brave_search_news(query: str, count: int = 5) -> str:
        import requests
        if not BRAVE_API_KEY:
            return "❌ BRAVE_API_KEY nao configurado."
        try:
            params = {"q": query, "count": min(count, 20)}
            resp = requests.get(f"{BRAVE_API}/news/search", headers=_headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return f"Nenhuma noticia para: {query}"
            items = []
            for r in results[:count]:
                items.append(
                    f"**{r.get('title', 'N/A')}**\n"
                    f"  Fonte: {r.get('meta_url', {}).get('hostname', '')}\n"
                    f"  URL: {r.get('url', '')}\n"
                    f"  {r.get('description', '')[:120]}"
                )
            return f"**{len(results)} noticias para '{query}':**\n\n" + "\n\n".join(items)
        except Exception as e:
            return f"❌ Erro ao buscar noticias: {e}"

    def brave_search_images(query: str, count: int = 5) -> str:
        import requests
        if not BRAVE_API_KEY:
            return "❌ BRAVE_API_KEY nao configurado."
        try:
            params = {"q": query, "count": min(count, 20)}
            resp = requests.get(f"{BRAVE_API}/images/search", headers=_headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return f"Nenhuma imagem para: {query}"
            items = []
            for r in results[:count]:
                items.append(
                    f"• {r.get('title', 'N/A')[:50]}\n"
                    f"  URL: {r.get('url', '')}\n"
                    f"  Thumbnail: {r.get('properties', {}).get('url', '')[:80]}"
                )
            return f"**{len(results)} imagens para '{query}':**\n\n" + "\n".join(items)
        except Exception as e:
            return f"❌ Erro ao buscar imagens: {e}"

    def brave_search_suggest(query: str) -> str:
        import requests
        if not BRAVE_API_KEY:
            return "❌ BRAVE_API_KEY nao configurado."
        try:
            params = {"q": query}
            resp = requests.get(f"{BRAVE_API}/suggestions/search", headers=_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            suggestions = data.get("results", [])
            if not suggestions:
                return "Nenhuma sugestao."
            items = [f"• {s.get('query', '')}" for s in suggestions[:10]]
            return "**Sugestoes:**\n" + "\n".join(items)
        except Exception as e:
            return f"❌ Erro ao buscar sugestoes: {e}"

    api.register_tool("brave_search_status", brave_search_status,
        "Verifica configuracao da Brave Search API.", {}, [])

    api.register_tool("brave_search_web", brave_search_web,
        "Busca na web via Brave Search.",
        {"query": {"type": "string", "description": "Termo de busca"},
         "count": {"type": "integer", "description": "Numero de resultados (opcional, max 20)"}}, ["query"])

    api.register_tool("brave_search_news", brave_search_news,
        "Busca noticias via Brave Search.",
        {"query": {"type": "string"}, "count": {"type": "integer"}}, ["query"])

    api.register_tool("brave_search_images", brave_search_images,
        "Busca imagens via Brave Search.",
        {"query": {"type": "string"}, "count": {"type": "integer"}}, ["query"])

    api.register_tool("brave_search_suggest", brave_search_suggest,
        "Retorna sugestoes de busca.",
        {"query": {"type": "string"}}, ["query"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Busca web, noticias e imagens via Brave Search API.",
        "tools": ["brave_search_status", "brave_search_web", "brave_search_news",
                   "brave_search_images", "brave_search_suggest"],
    }
