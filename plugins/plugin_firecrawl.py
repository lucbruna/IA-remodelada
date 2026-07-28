"""
plugin_firecrawl.py
====================
Web scraping avancado via Firecrawl — busca, scrape e interacao com web
em escala. Suporta JS rendering, interacao com paginas e saida LLM-ready.

Requer: FIRECRAWL_API_KEY no .env (ou variavel de ambiente)
Ou mode local: firecrawl self-hosted
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Firecrawl (Web Scraping Avancado)"

import os
import json
import logging

# ─── Config ─────────────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "https://api.firecrawl.dev")

logger = logging.getLogger(__name__)


def _get_client():
    """Retorna cliente Firecrawl configurado."""
    try:
        from firecrawl import FirecrawlApp
    except ImportError:
        return None, "Instale: pip install firecrawl-py"

    if FIRECRAWL_URL and FIRECRAWL_URL != "https://api.firecrawl.dev":
        return FirecrawlApp(api_key=FIRECRAWL_API_KEY or "local", api_url=FIRECRAWL_URL), None

    if not FIRECRAWL_API_KEY:
        return None, "FIRECRAWL_API_KEY nao configurada. Adicione no .env ou use FIRECRAWL_URL para self-hosted."

    return FirecrawlApp(api_key=FIRECRAWL_API_KEY), None


def register(api):
    """Registra ferramentas Firecrawl no agente."""

    def firecrawl_status() -> str:
        """Verifica se o Firecrawl esta configurado e disponivel."""
        client, err = _get_client()
        if err:
            return f"❌ Firecrawl indisponivel: {err}"
        return (
            f"✅ Firecrawl ativo\n"
            f"   Modo: {'Self-hosted' if FIRECRAWL_URL != 'https://api.firecrawl.dev' else 'Cloud'}\n"
            f"   URL: {FIRECRAWL_URL}\n"
            f"   API Key: {'Configurada' if FIRECRAWL_API_KEY else 'Nao configurada (self-hosted)'}"
        )

    def firecrawl_scrape(url: str, formats: str = "markdown", only_clean: bool = True) -> str:
        """Faz scrape de uma pagina web e retorna conteudo limpo para LLMs.
        
        Args:
            url: URL da pagina para fazer scrape
            formats: Formatos de saida (markdown, html, rawHtml, screenshot, json)
            only_clean: Se True, remove nav, footer, ads e conteudo nao semantico
        """
        client, err = _get_client()
        if err:
            return err

        try:
            params = {
                "url": url,
                "formats": formats.split(",") if isinstance(formats, str) else [formats],
            }
            if only_clean:
                params["onlyCleanContent"] = True

            result = client.scrape_url(url, params=params)

            if not result:
                return "Nenhum conteudo retornado."

            output_parts = []

            if "markdown" in result and result["markdown"]:
                md = result["markdown"]
                if len(md) > 8000:
                    md = md[:8000] + "\n\n[...truncado...]"
                output_parts.append(f"**Markdown:**\n{md}")

            if "html" in result and result["html"] and "html" in formats:
                html = result["html"]
                if len(html) > 5000:
                    html = html[:5000] + "\n[...truncado...]"
                output_parts.append(f"**HTML:**\n{html}")

            if "screenshot" in result and result["screenshot"]:
                output_parts.append(f"**Screenshot:** {result['screenshot'][:200]}...")

            if "metadata" in result and result["metadata"]:
                meta = result["metadata"]
                title = meta.get("title", "")
                desc = meta.get("description", "")
                if title or desc:
                    output_parts.insert(0, f"**Titulo:** {title}\n**Descricao:** {desc}")

            return "\n\n".join(output_parts) if output_parts else "Nenhum conteudo extraido."

        except Exception as e:
            return f"Erro no scrape Firecrawl: {e}"

    def firecrawl_search(query: str, limit: int = 5, scrape_options: bool = True) -> str:
        """Busca na web e retorna conteudo completo das paginas encontradas.
        
        Args:
            query: Termo de busca
            limit: Numero maximo de resultados (1-20)
            scrape_options: Se True, faz scrape do conteudo completo de cada resultado
        """
        client, err = _get_client()
        if err:
            return err

        try:
            params = {
                "query": query,
                "limit": min(limit, 20),
            }
            if scrape_options:
                params["scrapeOptions"] = {
                    "formats": ["markdown"],
                    "onlyCleanContent": True,
                }

            result = client.search(query, params=params)

            if not result or "data" not in result:
                return "Nenhum resultado encontrado."

            output = []
            for i, item in enumerate(result["data"][:limit], 1):
                title = item.get("title", "Sem titulo")
                url = item.get("url", "")
                markdown = item.get("markdown", "")

                output.append(f"### {i}. {title}")
                output.append(f"URL: {url}")
                if markdown:
                    preview = markdown[:1500]
                    if len(markdown) > 1500:
                        preview += "\n[...truncado...]"
                    output.append(f"\n{preview}")
                output.append("\n---\n")

            return "\n".join(output) if output else "Nenhum resultado encontrado."

        except Exception as e:
            return f"Erro na busca Firecrawl: {e}"

    def firecrawl_crawl(url: str, max_pages: int = 10, exclude_paths: str = "") -> str:
        """Faz crawl de um site inteiro, retornando conteudo de multiplas paginas.
        
        Args:
            url: URL inicial para crawl
            max_pages: Numero maximo de paginas para crawl (1-100)
            exclude_paths: Caminhos para excluir (separados por virgula, ex: /blog,/about)
        """
        client, err = _get_client()
        if err:
            return err

        try:
            params = {
                "limit": min(max_pages, 100),
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyCleanContent": True,
                },
            }

            if exclude_paths:
                exclude_list = [p.strip() for p in exclude_paths.split(",") if p.strip()]
                if exclude_list:
                    params["scrapeOptions"]["excludePaths"] = exclude_list

            crawl_result = client.crawl_url(url, params=params, poll_interval=5)

            if not crawl_result or "data" not in crawl_result:
                return "Nenhum conteudo retornado do crawl."

            pages = crawl_result["data"]
            output = [f"**Crawl concluido:** {len(pages)} paginas coletadas\n"]

            for i, page in enumerate(pages[:max_pages], 1):
                page_url = page.get("metadata", {}).get("sourceURL", "")
                title = page.get("metadata", {}).get("title", "")
                markdown = page.get("markdown", "")

                output.append(f"### Pagina {i}: {title or page_url}")
                output.append(f"URL: {page_url}")
                if markdown:
                    preview = markdown[:800]
                    if len(markdown) > 800:
                        preview += "\n[...truncado...]"
                    output.append(f"{preview}")
                output.append("\n---\n")

            return "\n".join(output)

        except Exception as e:
            return f"Erro no crawl Firecrawl: {e}"

    def firecrawl_extract(url: str, prompt: str) -> str:
        """Extrai dados estruturados de uma pagina usando IA.
        
        Args:
            url: URL da pagina
            prompt: Instrucao em linguagem natural do que extrair (ex: "extraia nome, preco e descricao dos produtos")
        """
        client, err = _get_client()
        if err:
            return err

        try:
            result = client.scrape_url(url, params={
                "formats": ["json"],
                "json": {
                    "prompt": prompt,
                },
            })

            if not result:
                return "Nenhum dado extraido."

            if "json" in result and result["json"]:
                json_data = result["json"]
                if isinstance(json_data, dict) or isinstance(json_data, list):
                    return json.dumps(json_data, ensure_ascii=False, indent=2)
                return str(json_data)

            return "Nenhum dado estruturado extraido."

        except Exception as e:
            return f"Erro na extracao Firecrawl: {e}"

    def firecrawl_interact(url: str, actions: str) -> str:
        """Interage com uma pagina web (clique, preencher formulario, etc).
        
        Args:
            url: URL da pagina
            actions: Acoes em JSON array. Ex: [{"type":"click","selector":"button#submit"},{"type":"type","selector":"input[name='q']","text":"hello"}]
                     Tipos: click, type, scroll, wait, press
        """
        client, err = _get_client()
        if err:
            return err

        try:
            if isinstance(actions, str):
                actions_list = json.loads(actions)
            else:
                actions_list = actions

            result = client.scrape_url(url, params={
                "formats": ["markdown"],
                "actions": actions_list,
            })

            if not result:
                return "Nenhum conteudo retornado apos interacao."

            markdown = result.get("markdown", "")
            if markdown:
                if len(markdown) > 8000:
                    markdown = markdown[:8000] + "\n[...truncado...]"
                return f"**Conteudo apos interacao:**\n{markdown}"

            return "Interacao realizada, mas nenhum conteudo retornado."

        except Exception as e:
            return f"Erro na interacao Firecrawl: {e}"

    # ─── Registro das ferramentas ───────────────────────────────────

    api.register_tool("firecrawl_status", firecrawl_status,
        "Verifica status do Firecrawl (configuracao, modo cloud/self-hosted).",
        {}, [])

    api.register_tool("firecrawl_scrape", firecrawl_scrape,
        "Faz scrape de pagina web via Firecrawl. Suporta JS rendering, saida markdown/HTML limpo para LLMs.",
        {
            "url": {"type": "string", "description": "URL da pagina para scrape"},
            "formats": {"type": "string", "description": "Formatos: markdown, html, rawHtml, screenshot, json (opcional, padrao: markdown)"},
            "only_clean": {"type": "boolean", "description": "Remover nav/footer/ads (opcional, padrao: true)"},
        }, ["url"])

    api.register_tool("firecrawl_search", firecrawl_search,
        "Busca na web via Firecrawl e retorna conteudo completo das paginas encontradas.",
        {
            "query": {"type": "string", "description": "Termo de busca"},
            "limit": {"type": "integer", "description": "Maximo de resultados 1-20 (opcional, padrao: 5)"},
            "scrape_options": {"type": "boolean", "description": "Fazer scrape do conteudo completo (opcional, padrao: true)"},
        }, ["query"])

    api.register_tool("firecrawl_crawl", firecrawl_crawl,
        "Faz crawl de um site inteiro, retornando conteudo de multiplas paginas.",
        {
            "url": {"type": "string", "description": "URL inicial para crawl"},
            "max_pages": {"type": "integer", "description": "Maximo de paginas 1-100 (opcional, padrao: 10)"},
            "exclude_paths": {"type": "string", "description": "Caminhos para excluir, separados por virgula (opcional)"},
        }, ["url"])

    api.register_tool("firecrawl_extract", firecrawl_extract,
        "Extrai dados estruturados de uma pagina usando IA (prompt em linguagem natural).",
        {
            "url": {"type": "string", "description": "URL da pagina"},
            "prompt": {"type": "string", "description": "Instrucao do que extrair (ex: 'extraia nome e preco dos produtos')"},
        }, ["url", "prompt"])

    api.register_tool("firecrawl_interact", firecrawl_interact,
        "Interage com pagina web (clique, formulario, scroll). Actions em JSON.",
        {
            "url": {"type": "string", "description": "URL da pagina"},
            "actions": {"type": "string", "description": "Array JSON de acoes: [{\"type\":\"click\",\"selector\":\"button\"},{\"type\":\"type\",\"selector\":\"input\",\"text\":\"valor\"}]"},
        }, ["url", "actions"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Web scraping avancado via Firecrawl: busca, scrape, crawl, extracao estruturada e interacao com paginas.",
        "tools": ["firecrawl_status", "firecrawl_scrape", "firecrawl_search", "firecrawl_crawl", "firecrawl_extract", "firecrawl_interact"],
    }
