"""
plugin_playwright.py
====================
Browser automation via Playwright — scraping, screenshots, navegacao.

Requer: playwright (pip install playwright && playwright install)
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Playwright Browser"

import os
import logging

logger = logging.getLogger(__name__)


def register(api):

    def playwright_status() -> str:
        try:
            import playwright
            return f"✅ Playwright {playwright.__version__} disponivel"
        except ImportError:
            return "❌ Playwright nao instalado. Rode: pip install playwright && playwright install"

    def playwright_screenshot(url: str, full_page: bool = False) -> str:
        from playwright.sync_api import sync_playwright
        import time
        ts = int(time.time() * 1000)
        path = os.path.join(os.environ.get("TEMP", "."), f"playwright_{ts}.png")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.screenshot(path=path, full_page=full_page)
                browser.close()
            return f"✅ Screenshot salvo em: {path}"
        except Exception as e:
            return f"❌ Erro ao capturar screenshot: {e}"

    def playwright_get_text(url: str) -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                text = page.inner_text("body")
                browser.close()
            if len(text) > 10000:
                text = text[:10000] + "\n[...truncado...]"
            return text
        except Exception as e:
            return f"❌ Erro ao extrair texto: {e}"

    def playwright_get_html(url: str, selector: str = "body") -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.inner_html(selector)
                browser.close()
            if len(html) > 10000:
                html = html[:10000] + "\n[...truncado...]"
            return html
        except Exception as e:
            return f"❌ Erro ao extrair HTML: {e}"

    def playwright_click(url: str, selector: str) -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.click(selector)
                page.wait_for_load_state("networkidle", timeout=15000)
                result = f"✅ Clique realizado em '{selector}'. URL: {page.url}"
                browser.close()
            return result
        except Exception as e:
            return f"❌ Erro ao clicar: {e}"

    def playwright_fill(url: str, selector: str, value: str) -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.fill(selector, value)
                result = f"✅ Preenchido '{selector}' com valor."
                browser.close()
            return result
        except Exception as e:
            return f"❌ Erro ao preencher: {e}"

    def playwright_evaluate(url: str, expression: str) -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                result = page.evaluate(expression)
                browser.close()
            return str(result)[:8000]
        except Exception as e:
            return f"❌ Erro ao executar JS: {e}"

    def playwright_list_links(url: str, limit: int = 20) -> str:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                links = page.eval_on_selector_all("a[href]", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))")
                browser.close()
            links = [l for l in links if l["text"]][:limit]
            if not links:
                return "Nenhum link encontrado."
            result = "\n".join(f"• [{l['text'][:50]}]({l['href']})" for l in links)
            return f"**{len(links)} links:**\n{result}"
        except Exception as e:
            return f"❌ Erro ao listar links: {e}"

    api.register_tool("playwright_status", playwright_status,
        "Verifica se Playwright esta instalado.", {}, [])

    api.register_tool("playwright_screenshot", playwright_screenshot,
        "Captura screenshot de uma pagina.",
        {"url": {"type": "string", "description": "URL da pagina"},
         "full_page": {"type": "boolean", "description": "Captura pagina inteira (opcional)"}}, ["url"])

    api.register_tool("playwright_get_text", playwright_get_text,
        "Extrai todo o texto visivel de uma pagina.",
        {"url": {"type": "string"}}, ["url"])

    api.register_tool("playwright_get_html", playwright_get_html,
        "Extrai HTML de um seletor da pagina.",
        {"url": {"type": "string"}, "selector": {"type": "string", "description": "CSS selector (opcional, padrao body)"}}, ["url"])

    api.register_tool("playwright_click", playwright_click,
        "Clica em um elemento da pagina.",
        {"url": {"type": "string"}, "selector": {"type": "string"}}, ["url", "selector"])

    api.register_tool("playwright_fill", playwright_fill,
        "Preenche um campo de formulario.",
        {"url": {"type": "string"}, "selector": {"type": "string"}, "value": {"type": "string"}},
        ["url", "selector", "value"])

    api.register_tool("playwright_evaluate", playwright_evaluate,
        "Executa JavaScript na pagina e retorna resultado.",
        {"url": {"type": "string"}, "expression": {"type": "string"}}, ["url", "expression"])

    api.register_tool("playwright_list_links", playwright_list_links,
        "Lista todos os links de uma pagina.",
        {"url": {"type": "string"}, "limit": {"type": "integer"}}, ["url"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Browser automation via Playwright: screenshots, extracao de texto, cliques, formularios.",
        "tools": ["playwright_status", "playwright_screenshot", "playwright_get_text",
                   "playwright_get_html", "playwright_click", "playwright_fill",
                   "playwright_evaluate", "playwright_list_links"],
    }
