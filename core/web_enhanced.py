"""
core/web_enhanced.py
====================
Web browsing avancado com extracao estruturada e sumarizacao.

Inspirado por:
  - ChatGPT Web Browsing: busca + leitura + sumarizacao automatica
  - Claude Computer Use: navegacao interativa com Playwright
  - OpenAI Cookbook: web scraping patterns

Funcionalidades:
  - Busca web com multiplos provedores (DuckDuckGo, Brave, SerpAPI)
  - Extracao estruturada de conteudo (artigos, tabelas, listas)
  - Sumarizacao automatica via LLM
  - Navegacao interativa com Playwright
  - Cache de paginas visitadas
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from ._common import (
    os, re, json, hashlib, logging, datetime,
    _load_json, _save_json, DATA_DIR, urllib,
)

# --- Config ---
WEB_CACHE_DIR = os.path.join(DATA_DIR, "web_cache")
os.makedirs(WEB_CACHE_DIR, exist_ok=True)

MAX_CACHE_AGE_HOURS = int(os.environ.get("AGENTE_WEB_CACHE_HOURS", "24"))
MAX_CONTENT_LENGTH = int(os.environ.get("AGENTE_WEB_MAX_CONTENT", "50000"))


# --- Cache ---

def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _get_cached(url: str) -> Optional[dict]:
    """Recupera pagina do cache se ainda valida."""
    key = _cache_key(url)
    cache_file = os.path.join(WEB_CACHE_DIR, f"{key}.json")
    if not os.path.exists(cache_file):
        return None
    try:
        data = _load_json(cache_file, {})
        cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours > MAX_CACHE_AGE_HOURS:
            return None
        return data
    except Exception:
        return None


def _set_cached(url: str, content: dict):
    """Salva pagina no cache."""
    key = _cache_key(url)
    cache_file = os.path.join(WEB_CACHE_DIR, f"{key}.json")
    content["cached_at"] = datetime.now().isoformat()
    content["url"] = url
    _save_json(cache_file, content)


# --- Busca Web ---

def web_search_enhanced(
    query: str,
    provider: str = "auto",
    max_results: int = 5,
    language: str = "pt-br",
) -> List[Dict[str, str]]:
    """Busca web com multiplos provedores.

    Args:
        query: Termo de busca
        provider: "auto", "duckduckgo", "brave", "serpapi"
        max_results: Numero maximo de resultados
        language: Idioma da busca

    Returns:
        Lista de dicts com title, url, snippet
    """
    if provider == "auto":
        # Auto-detecta melhor provedor disponivel
        if os.environ.get("BRAVE_API_KEY"):
            provider = "brave"
        elif os.environ.get("SERPAPI_KEY"):
            provider = "serpapi"
        else:
            provider = "duckduckgo"

    try:
        if provider == "duckduckgo":
            return _search_duckduckgo(query, max_results)
        elif provider == "brave":
            return _search_brave(query, max_results, language)
        elif provider == "serpapi":
            return _search_serpapi(query, max_results, language)
    except Exception as e:
        logging.warning("Busca web falhou (%s): %s", provider, e)

    # Fallback: tenta DuckDuckGo
    try:
        return _search_duckduckgo(query, max_results)
    except Exception:
        return []


def _search_duckduckgo(query: str, max_results: int) -> list:
    """Busca via DuckDuckGo (sem API key)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in results
            ]
    except ImportError:
        # Fallback: HTML scraping
        return _search_html_fallback(query, max_results)


def _search_brave(query: str, max_results: int, language: str) -> list:
    """Busca via Brave Search API."""
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return _search_duckduckgo(query, max_results)

    url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count={max_results}&search_lang={language}"
    req = urllib.request.Request(url, headers={"X-Subscription-Token": api_key, "Accept": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    results = data.get("web", {}).get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in results[:max_results]
    ]


def _search_serpapi(query: str, max_results: int, language: str) -> list:
    """Busca via SerpAPI."""
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        return _search_duckduckgo(query, max_results)

    url = f"https://serpapi.com/search.json?q={query}&num={max_results}&hl={language}&api_key={api_key}"
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read())
    results = data.get("organic_results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
        for r in results[:max_results]
    ]


def _search_html_fallback(query: str, max_results: int) -> list:
    """Fallback: busca HTML simples via DuckDuckGo HTML."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")
        # Extrai resultados simples
        results = []
        for match in re.finditer(r'class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html):
            if len(results) >= max_results:
                break
            href, title = match.groups()
            # DuckDuckGo usa redirect URLs
            if "uddg=" in href:
                actual_url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            else:
                actual_url = href
            results.append({"title": title.strip(), "url": actual_url, "snippet": ""})
        return results
    except Exception:
        return []


# --- Extracao de Conteudo ---

def fetch_and_extract(
    url: str,
    extract_mode: str = "auto",
    max_length: int = MAX_CONTENT_LENGTH,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Busca URL e extrai conteudo estruturado.

    Args:
        url: URL para buscar
        extract_mode: "auto", "text", "article", "markdown", "structured"
        max_length: Tamanho maximo do conteudo
        use_cache: Se True, usa cache

    Returns:
        Dict com title, content, links, metadata
    """
    # Cache check
    if use_cache:
        cached = _get_cached(url)
        if cached:
            return cached

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; IA-Remodelada/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        content_type = resp.headers.get("Content-Type", "")
        raw_html = resp.read().decode("utf-8", errors="replace")[:max_length * 2]
    except Exception as e:
        return {"url": url, "error": str(e), "content": ""}

    # Extrai dados
    result = {
        "url": url,
        "title": _extract_title(raw_html),
        "content": "",
        "links": [],
        "metadata": {},
        "extracted_at": datetime.now().isoformat(),
    }

    if extract_mode in ("auto", "article"):
        result["content"] = _extract_article(raw_html)
        result["links"] = _extract_links(raw_html, url)[:20]
        result["metadata"] = _extract_metadata(raw_html)
    elif extract_mode == "markdown":
        result["content"] = _html_to_markdown(raw_html)
    elif extract_mode == "structured":
        result["content"] = _extract_structured(raw_html)
        result["links"] = _extract_links(raw_html, url)[:20]
    else:
        # Texto simples
        result["content"] = _extract_text(raw_html)

    # Trunca se necessario
    if len(result["content"]) > max_length:
        result["content"] = result["content"][:max_length] + "\n[...truncado]"

    # Salva no cache
    if use_cache:
        _set_cached(url, result)

    return result


def _extract_title(html: str) -> str:
    """Extrai titulo da pagina."""
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_article(html: str) -> str:
    """Extrai conteudo de artigo (remove nav, footer, etc)."""
    # Remove scripts e styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Tenta encontrar article ou main
    article = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL | re.IGNORECASE)
    if article:
        html = article.group(1)
    else:
        main = re.search(r"<main[^>]*>(.*?)</main>", html, re.DOTALL | re.IGNORECASE)
        if main:
            html = main.group(1)

    return _html_to_text(html)


def _extract_text(html: str) -> str:
    """Extrai texto puro do HTML."""
    return _html_to_text(html)


def _html_to_text(html: str) -> str:
    """Converte HTML para texto limpo."""
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decodifica entidades
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Limpa espacos
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _html_to_markdown(html: str) -> str:
    """Converte HTML para Markdown simplificado."""
    try:
        import markdown
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts e styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        # Converte para markdown
        text = soup.get_text(separator="\n")
        return markdown.markdown(text)
    except ImportError:
        return _html_to_text(html)


def _extract_structured(html: str) -> str:
    """Extrai dados estruturados (tabelas, listas, titulos)."""
    parts = []

    # Titulos
    for i in range(1, 4):
        for match in re.finditer(rf"<h{i}[^>]*>(.*?)</h{i}>", html, re.IGNORECASE | re.DOTALL):
            text = _html_to_text(match.group(1)).strip()
            if text:
                parts.append(f"{'#' * i} {text}")

    # Tabelas
    for match in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.DOTALL | re.IGNORECASE):
        table_html = match.group(1)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
        if rows:
            parts.append("\n**Tabela:**")
            for row in rows[:10]:
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                cells_text = [_html_to_text(c).strip() for c in cells]
                parts.append(" | ".join(cells_text))

    # Listas
    for match in re.finditer(r"<[ou]l[^>]*>(.*?)</[ou]l>", html, re.DOTALL | re.IGNORECASE):
        list_html = match.group(1)
        items = re.findall(r"<li[^>]*>(.*?)</li>", list_html, re.DOTALL | re.IGNORECASE)
        for item in items[:10]:
            text = _html_to_text(item).strip()
            if text:
                parts.append(f"- {text}")

    if not parts:
        return _html_to_text(html)

    return "\n".join(parts)


def _extract_links(html: str, base_url: str) -> list:
    """Extrai links relevantes da pagina."""
    links = []
    for match in re.finditer(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
        href, text = match.groups()
        text = _html_to_text(text).strip()
        if not text or len(text) < 3:
            continue
        # Resolve URL relativa
        if href.startswith("/"):
            href = urljoin(base_url, href)
        elif not href.startswith("http"):
            continue
        # Filtra links internos/irrelevantes
        if any(skip in href.lower() for skip in ["javascript:", "mailto:", "#", ".png", ".jpg", ".gif"]):
            continue
        links.append({"text": text[:100], "url": href})
    return links


def _extract_metadata(html: str) -> dict:
    """Extrai metadata (description, keywords, author, date)."""
    meta = {}
    # Description
    match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html, re.IGNORECASE)
    if match:
        meta["description"] = match.group(1)[:300]
    # Keywords
    match = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]*)"', html, re.IGNORECASE)
    if match:
        meta["keywords"] = match.group(1)[:200]
    # Author
    match = re.search(r'<meta[^>]+name="author"[^>]+content="([^"]*)"', html, re.IGNORECASE)
    if match:
        meta["author"] = match.group(1)
    # Date
    match = re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]*)"', html, re.IGNORECASE)
    if match:
        meta["date"] = match.group(1)
    return meta


# --- Sumarizacao via LLM ---

def summarize_url(url: str, max_length: int = 1000, language: str = "pt") -> str:
    """Busca uma URL e retorna sumario automatico via LLM."""
    data = fetch_and_extract(url)
    if data.get("error"):
        return f"Erro ao buscar URL: {data['error']}"

    content = data.get("content", "")
    if not content:
        return "Nenhum conteudo extraido da URL."

    # Trunca para caber no contexto
    if len(content) > 8000:
        content = content[:8000] + "\n[...truncado]"

    try:
        from .llm_backend import get_backend, ChatMessage
        backend = get_backend()
        lang_instruction = "Portugues do Brasil" if language == "pt" else "English"
        resp = backend.chat([
            ChatMessage(role="system", content=(
                f"Voce e um assistente de sumarizacao. Responda em {lang_instruction}. "
                "Resuma o conteudo abaixo em um paragrafo conciso, destacando os pontos principais."
            )),
            ChatMessage(role="user", content=f"URL: {url}\n\nConteudo:\n{content}"),
        ], temperature=0.3, max_tokens=500)
        return resp.content
    except Exception as e:
        # Fallback: sumario basico
        sentences = re.split(r'[.!?]+', content)
        return ". ".join(sentences[:5]) + "."


def multi_search_and_summarize(
    query: str,
    num_sources: int = 3,
    language: str = "pt",
) -> str:
    """Busca multiplicas fontes, extrai e sumariza em um relatorio unificado."""
    results = web_search_enhanced(query, max_results=num_sources * 2)
    if not results:
        return "Nenhum resultado encontrado para a busca."

    # Pega as top N fontes
    sources = results[:num_sources]
    summaries = []

    for r in sources:
        url = r.get("url", "")
        if not url:
            continue
        try:
            summary = summarize_url(url, max_length=500, language=language)
            summaries.append({
                "title": r.get("title", ""),
                "url": url,
                "summary": summary,
            })
        except Exception as e:
            logging.warning("Falha ao resumir %s: %s", url, e)

    if not summaries:
        return "Nao foi possivel resumer nenhuma fonte."

    # Monta relatorio
    parts = [f"**Busca:** {query}\n"]
    for i, s in enumerate(summaries, 1):
        parts.append(f"### Fonte {i}: {s['title']}")
        parts.append(f"URL: {s['url']}")
        parts.append(f"{s['summary']}\n")

    return "\n".join(parts)


# --- Ferramentas para o agente ---

def web_search_tool(query: str, max_results: int = 5) -> str:
    """Ferramenta: busca web e retorna resultados formatados."""
    results = web_search_enhanced(query, max_results=max_results)
    if not results:
        return "Nenhum resultado encontrado."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   URL: {r['url']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


def web_read_tool(url: str, extract_mode: str = "auto") -> str:
    """Ferramenta: le e extrai conteudo de uma URL."""
    data = fetch_and_extract(url, extract_mode=extract_mode)
    if data.get("error"):
        return f"Erro: {data['error']}"
    parts = [f"**Titulo:** {data.get('title', 'N/A')}"]
    parts.append(f"**URL:** {url}")
    if data.get("metadata"):
        for k, v in data["metadata"].items():
            parts.append(f"**{k.title()}:** {v}")
    parts.append(f"\n**Conteudo:**\n{data.get('content', '')[:3000]}")
    if data.get("links"):
        parts.append(f"\n**Links ({len(data['links'])}):**")
        for link in data["links"][:10]:
            parts.append(f"- [{link['text']}]({link['url']})")
    return "\n".join(parts)


def web_summarize_tool(url: str) -> str:
    """Ferramenta: busca URL e retorna sumario automatico."""
    return summarize_url(url)
