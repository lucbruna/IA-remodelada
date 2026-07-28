"""
core/browser_tool.py
====================
Browser automation DOM-aware inspirado no Playwright MCP do Claude.

Diferente do plugin_playwright.py (que usa Playwright diretamente), este módulo
implementa o conceito de "element refs" do Claude Browser Automation:
- Elementos são identificados por refs (não por pixel coordinates)
- Coordenadas são escaladas automaticamente (1456x819 → viewport real)
- Operações são baseadas em DOM, não em visão/pixels
- Mais rápido e determinístico que computer use

Inspirado por:
  - Anthropic Claude Browser Automation (browser-use-demo)
  - Playwright MCP (accessibility tree)
  - ChatGPT Web Browsing (GET requests, robots.txt)

Funcionalidades:
  - Navegação (navigate, back, forward)
  - Leitura de página (read_page, get_page_text)
  - Interação (left_click, form_input, scroll_to)
  - Busca (find, highlight)
  - Captura (screenshot, zoom)
  - JavaScript (execute_js)
  - Cache de páginas
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ._common import (
    os, logging, datetime,
    DATA_DIR,
)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

BROWSER_CACHE_DIR = os.path.join(DATA_DIR, "browser_cache")
os.makedirs(BROWSER_CACHE_DIR, exist_ok=True)

MAX_CACHE_AGE_HOURS = int(os.environ.get("AGENTE_BROWSER_CACHE_HOURS", "24"))
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1080
CLAUDE_PROCESSED_WIDTH = 1456
CLAUDE_PROCESSED_HEIGHT = 819

_SCALE_X = DEFAULT_VIEWPORT_WIDTH / CLAUDE_PROCESSED_WIDTH
_SCALE_Y = DEFAULT_VIEWPORT_HEIGHT / CLAUDE_PROCESSED_HEIGHT


class BrowserTool:
    """Browser automation DOM-aware com element refs.

    Uso:
        browser = BrowserTool()
        browser.navigate("https://example.com")
        page_text = browser.get_page_text()
        browser.form_input("input[name='q']", "hello world")
        browser.left_click("button[type='submit']")
        browser.screenshot()
    """

    def __init__(self, headless: bool = True, viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
                 viewport_height: int = DEFAULT_VIEWPORT_HEIGHT):
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._playwright = None
        self._browser = None
        self._page = None
        self._context = None
        self._current_url = ""
        self._scale_x = viewport_width / CLAUDE_PROCESSED_WIDTH
        self._scale_y = viewport_height / CLAUDE_PROCESSED_HEIGHT

    def _ensure_browser(self) -> bool:
        """Inicializa o browser se necessário."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is not None:
            return True
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            self._page = self._context.new_page()
            return True
        except Exception as e:
            logging.error("Erro ao inicializar browser: %s", e)
            return False

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> str:
        """Navega para uma URL.

        Args:
            url: URL para navegar
            wait_until: "domcontentloaded", "load", "networkidle", ou "commit"

        Returns:
            Mensagem de status
        """
        if not self._ensure_browser():
            return "Erro: Playwright nao disponivel. Instale: pip install playwright && playwright install chromium"
        try:
            self._page.goto(url, wait_until=wait_until, timeout=30000)
            self._current_url = self._page.url
            title = self._page.title()
            return f"Navegado para: {url}\nTitulo: {title}"
        except PlaywrightTimeoutError:
            return f"Timeout ao navegar para: {url}"
        except Exception as e:
            return f"Erro ao navegar: {e}"

    def back(self) -> str:
        """Navega para a pagina anterior."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.go_back()
            self._current_url = self._page.url
            return f"Voltou para: {self._current_url}"
        except Exception as e:
            return f"Erro ao voltar: {e}"

    def forward(self) -> str:
        """Navega para a pagina seguinte."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.go_forward()
            self._current_url = self._page.url
            return f"Avancou para: {self._current_url}"
        except Exception as e:
            return f"Erro ao avancar: {e}"

    def read_page(self, text: str = "interactive") -> Dict[str, Any]:
        """Lê a estrutura DOM da pagina atual.

        Args:
            text: "interactive" para filtrar elementos interativos,
                  "all" para todos os elementos

        Returns:
            Dict com estrutura da página (refs, tags, textos)
        """
        if not self._page:
            return {"error": "Browser nao inicializado."}
        try:
            if text == "interactive":
                elements = self._page.eval_on_selector_all(
                    "a, button, input, select, textarea, [role='button'], [role='link']",
                    """(elements) => elements.map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            ref: el.tagName + '_' + Math.random().toString(36).substr(2, 9),
                            tag: el.tagName,
                            role: el.getAttribute('role') || '',
                            name: el.getAttribute('name') || '',
                            id: el.id || '',
                            className: el.className || '',
                            text: (el.innerText || el.value || '').trim().substring(0, 100),
                            href: el.getAttribute('href') || '',
                            type: el.getAttribute('type') || '',
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        };
                    })""",
                )
            else:
                elements = self._page.eval_on_selector_all(
                    "*",
                    """(elements) => elements.slice(0, 500).map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            ref: el.tagName + '_' + Math.random().toString(36).substr(2, 9),
                            tag: el.tagName,
                            text: (el.innerText || '').trim().substring(0, 80),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                        };
                    })""",
                )
            return {
                "url": self._page.url,
                "title": self._page.title(),
                "elements": elements,
                "count": len(elements),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_page_text(self) -> str:
        """Extrai todo o texto visível da página."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            return self._page.eval_on_selector("body", "el => el.innerText || ''")
        except Exception as e:
            return f"Erro ao extrair texto: {e}"

    def find(self, text: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Encontra e destaca texto na página.

        Args:
            text: Texto a procurar
            case_sensitive: Se a busca diferencia maiúsculas/minúsculas

        Returns:
            Lista de resultados com posição e contexto
        """
        if not self._page:
            return [{"error": "Browser nao inicializado."}]
        try:
            results = self._page.eval_on_selector_all(
                "*",
                f"""(elements, searchTerm, caseSensitive) => {{
                    const results = [];
                    const flags = caseSensitive ? 'g' : 'gi';
                    const regex = new RegExp(searchTerm.replace(/[.*+?^${{}}|[\\]\\\\/\\)/g, '\\\\$&'), flags);
                    elements.forEach(el => {{
                        const text = el.innerText || '';
                        if (regex.test(text)) {{
                            const rect = el.getBoundingClientRect();
                            results.push({{
                                tag: el.tagName,
                                text: text.trim().substring(0, 100),
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                            }});
                        }}
                    }});
                    return results.slice(0, 20);
                }}""",
                text, case_sensitive,
            )
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def left_click(self, ref: str = None, coordinate: List[int] = None) -> str:
        """Clica em um elemento.

        Args:
            ref: Seletor CSS do elemento (ex: "button[type='submit']")
            coordinate: [x, y] em coordenadas do viewport do Claude (1456x819)

        Returns:
            Mensagem de status
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            if ref:
                self._page.click(ref, timeout=10000)
                return f"Clicado em: {ref}"
            elif coordinate:
                x, y = coordinate
                scaled_x = x * self._scale_x
                scaled_y = y * self._scale_y
                self._page.mouse.click(scaled_x, scaled_y)
                return f"Clicado em coordenada: ({x}, {y}) -> ({scaled_x:.0f}, {scaled_y:.0f})"
            else:
                return "Forneça ref ou coordinate"
        except Exception as e:
            return f"Erro ao clicar: {e}"

    def right_click(self, ref: str = None, coordinate: List[int] = None) -> str:
        """Clique direito em um elemento."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            if ref:
                self._page.click(ref, button="right", timeout=10000)
                return f"Clique direito em: {ref}"
            elif coordinate:
                x, y = coordinate
                self._page.mouse.click(x * self._scale_x, y * self._scale_y, button="right")
                return f"Clique direito em: ({x}, {y})"
            return "Forneça ref ou coordinate"
        except Exception as e:
            return f"Erro ao clicar: {e}"

    def double_click(self, ref: str = None, coordinate: List[int] = None) -> str:
        """Duplo clique em um elemento."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            if ref:
                self._page.dblclick(ref, timeout=10000)
                return f"Duplo clique em: {ref}"
            elif coordinate:
                x, y = coordinate
                self._page.mouse.dblclick(x * self._scale_x, y * self._scale_y)
                return f"Duplo clique em: ({x}, {y})"
            return "Forneça ref ou coordinate"
        except Exception as e:
            return f"Erro ao clicar: {e}"

    def hover(self, ref: str = None, coordinate: List[int] = None) -> str:
        """Move o cursor sobre um elemento (sem clicar)."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            if ref:
                self._page.hover(ref, timeout=10000)
                return f"Hover em: {ref}"
            elif coordinate:
                x, y = coordinate
                self._page.mouse.move(x * self._scale_x, y * self._scale_y)
                return f"Hover em: ({x}, {y})"
            return "Forneça ref ou coordinate"
        except Exception as e:
            return f"Erro ao fazer hover: {e}"

    def form_input(self, ref: str, value: str) -> str:
        """Preenche um campo de formulário diretamente no DOM.

        Args:
            ref: Seletor CSS do campo (ex: "input[name='email']")
            value: Valor a inserir

        Returns:
            Mensagem de status
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.fill(ref, value, timeout=10000)
            return f"Preenchido '{ref}' com: {value[:50]}{'...' if len(value) > 50 else ''}"
        except Exception as e:
            return f"Erro ao preencher formulario: {e}"

    def type(self, text: str, delay: int = 50) -> str:
        """Digita texto no elemento focado."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.keyboard.type(text, delay=delay)
            return f"Digitado: {text[:50]}{'...' if len(text) > 50 else ''}"
        except Exception as e:
            return f"Erro ao digitar: {e}"

    def key(self, key: str) -> str:
        """Pressiona uma tecla ou combinação."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.keyboard.press(key)
            return f"Tecla pressionada: {key}"
        except Exception as e:
            return f"Erro ao pressionar tecla: {e}"

    def scroll(self, direction: str = "down", amount: int = 3,
               coordinate: List[int] = None) -> str:
        """Faz scroll na página.

        Args:
            direction: "up", "down", "left", "right"
            amount: Quantidade de scrolls
            coordinate: [x, y] para scroll em posição específica
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            if coordinate:
                x, y = coordinate
                self._page.mouse.wheel(0, amount * 100 if direction == "down" else -amount * 100)
                return f"Scroll {direction} em ({x}, {y})"
            else:
                delta_y = amount * 100 if direction in ("down", "right") else -amount * 100
                delta_x = 0
                if direction in ("left", "right"):
                    delta_x = delta_y
                    delta_y = 0
                self._page.mouse.wheel(delta_x, delta_y)
                return f"Scroll {direction} x{amount}"
        except Exception as e:
            return f"Erro ao fazer scroll: {e}"

    def scroll_to(self, ref: str) -> str:
        """Faz scroll até um elemento específico."""
        if not self._page:
            return "Browser nao inicializado."
        try:
            self._page.evaluate(f"""document.querySelector('{ref}').scrollIntoView({{behavior: 'smooth', block: 'center'}});""")
            return f"Scroll ate: {ref}"
        except Exception as e:
            return f"Erro ao fazer scroll: {e}"

    def screenshot(self, selector: str = None, full_page: bool = False,
                   filename: str = None) -> str:
        """Tira screenshot da página ou de um elemento.

        Args:
            selector: Seletor CSS para screenshot de elemento específico
            full_page: Se True, captura página inteira
            filename: Nome do arquivo (opcional)

        Returns:
            Caminho do arquivo ou base64
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_dir = os.path.join(BROWSER_CACHE_DIR, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            filepath = os.path.join(screenshot_dir, filename)

            if selector:
                element = self._page.query_selector(selector)
                if element:
                    element.screenshot(path=filepath)
                else:
                    return f"Elemento nao encontrado: {selector}"
            else:
                self._page.screenshot(path=filepath, full_page=full_page)

            return f"Screenshot salvo: {filepath}"
        except Exception as e:
            return f"Erro ao tirar screenshot: {e}"

    def zoom(self, region: List[int]) -> str:
        """Captura uma região específica da tela em alta resolução.

        Args:
            region: [x1, y1, x2, y2] em coordenadas do viewport do Claude

        Returns:
            Caminho do arquivo
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            x1, y1, x2, y2 = region
            scaled_x1 = x1 * self._scale_x
            scaled_y1 = y1 * self._scale_y
            scaled_x2 = x2 * self._scale_x
            scaled_y2 = y2 * self._scale_y

            filename = f"zoom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(BROWSER_CACHE_DIR, "screenshots", filename)

            self._page.screenshot(
                path=filepath,
                clip={"x": scaled_x1, "y": scaled_y1,
                      "width": scaled_x2 - scaled_x1,
                      "height": scaled_y2 - scaled_y1},
            )
            return f"Zoom salvo: {filepath}"
        except Exception as e:
            return f"Erro ao fazer zoom: {e}"

    def execute_js(self, code: str) -> str:
        """Executa código JavaScript na página.

        Args:
            code: Código JavaScript a executar

        Returns:
            Resultado da execução
        """
        if not self._page:
            return "Browser nao inicializado."
        try:
            result = self._page.evaluate(code)
            return str(result) if result is not None else "(sem retorno)"
        except Exception as e:
            return f"Erro ao executar JS: {e}"

    def get_url(self) -> str:
        """Retorna a URL atual."""
        if not self._page:
            return ""
        return self._page.url

    def get_title(self) -> str:
        """Retorna o título da página atual."""
        if not self._page:
            return ""
        try:
            return self._page.title()
        except Exception:
            return ""

    def get_links(self, selector: str = "a") -> List[Dict[str, str]]:
        """Extrai todos os links da página.

        Args:
            selector: Seletor CSS para filtrar links

        Returns:
            Lista de dicts com href e texto
        """
        if not self._page:
            return []
        try:
            links = self._page.eval_on_selector_all(
                selector,
                """(elements) => elements.map(el => ({
                    href: el.href || el.getAttribute('href') || '',
                    text: (el.innerText || '').trim().substring(0, 100),
                    target: el.target || '',
                })).filter(l => l.href)""",
            )
            return links[:50]
        except Exception as e:
            return [{"error": str(e)}]

    def close(self) -> str:
        """Fecha o browser."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None
            self._playwright = None
            return "Browser fechado."
        except Exception as e:
            return f"Erro ao fechar browser: {e}"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


_browser_instance: Optional[BrowserTool] = None


def get_browser() -> BrowserTool:
    """Retorna instância singleton do browser."""
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = BrowserTool()
    return _browser_instance


def browser_navigate(url: str, wait_until: str = "domcontentloaded") -> str:
    """Navega para uma URL usando o browser singleton."""
    return get_browser().navigate(url, wait_until)


def browser_read_page(text: str = "interactive") -> Dict[str, Any]:
    """Lê a estrutura da página atual."""
    return get_browser().read_page(text)


def browser_get_text() -> str:
    """Extrai texto da página atual."""
    return get_browser().get_page_text()


def browser_click(ref: str = None, coordinate: List[int] = None) -> str:
    """Clica em um elemento."""
    return get_browser().left_click(ref, coordinate)


def browser_form_input(ref: str, value: str) -> str:
    """Preenche um campo de formulário."""
    return get_browser().form_input(ref, value)


def browser_screenshot(selector: str = None, full_page: bool = False,
                       filename: str = None) -> str:
    """Tira screenshot."""
    return get_browser().screenshot(selector, full_page, filename)


def browser_execute_js(code: str) -> str:
    """Executa JavaScript."""
    return get_browser().execute_js(code)


def browser_find(text: str) -> List[Dict[str, Any]]:
    """Encontra texto na página."""
    return get_browser().find(text)


def browser_get_links(selector: str = "a") -> List[Dict[str, str]]:
    """Extrai links da página."""
    return get_browser().get_links(selector)


def browser_close() -> str:
    """Fecha o browser."""
    global _browser_instance
    if _browser_instance:
        result = _browser_instance.close()
        _browser_instance = None
        return result
    return "Browser nao estava aberto."
