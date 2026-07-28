import os
import sys
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_playwright():
    with patch("core.browser_tool.PLAYWRIGHT_AVAILABLE", True):
        with patch("core.browser_tool.sync_playwright") as mock_sync:
            mock_playwright = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_sync.return_value.start.return_value = mock_playwright
            mock_playwright.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example Domain"
            yield mock_page


class TestBrowserTool:
    def test_import(self):
        from core.browser_tool import BrowserTool, get_browser
        assert callable(get_browser)

    def test_navigate(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        result = browser.navigate("https://example.com")
        mock_playwright.goto.assert_called_once()
        assert "Navegado" in result

    def test_read_page_interactive(self, mock_playwright):
        mock_playwright.eval_on_selector_all.return_value = [
            {"ref": "A_abc123", "tag": "A", "text": "Click me", "x": 10, "y": 20}
        ]
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.read_page("interactive")
        assert result["count"] == 1

    def test_get_page_text(self, mock_playwright):
        mock_playwright.eval_on_selector.return_value = "Hello World"
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.get_page_text()
        assert result == "Hello World"

    def test_find_text(self, mock_playwright):
        mock_playwright.eval_on_selector_all.return_value = [
            {"tag": "P", "text": "Hello World", "x": 0, "y": 0}
        ]
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.find("World")
        assert len(result) == 1

    def test_left_click_ref(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.left_click(ref="#button")
        mock_playwright.click.assert_called_once_with("#button", timeout=10000)
        assert "Clicado" in result

    def test_left_click_coordinate(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.left_click(coordinate=[100, 200])
        mock_playwright.mouse.click.assert_called_once()
        assert "Clicado" in result

    def test_form_input(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.form_input("input[name='q']", "test value")
        mock_playwright.fill.assert_called_once_with("input[name='q']", "test value", timeout=10000)
        assert "Preenchido" in result

    def test_screenshot(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.screenshot(filename="test.png")
        assert "Screenshot" in result

    def test_execute_js(self, mock_playwright):
        mock_playwright.evaluate.return_value = "result"
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.execute_js("1 + 1")
        assert result == "result"

    def test_get_links(self, mock_playwright):
        mock_playwright.eval_on_selector_all.return_value = [
            {"href": "https://example.com", "text": "Example", "target": ""}
        ]
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.get_links()
        assert len(result) == 1

    def test_scroll(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.scroll("down", 1)
        assert "Scroll" in result

    def test_back_forward(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._page = mock_playwright
        result = browser.back()
        assert "Voltou" in result
        result = browser.forward()
        assert "Avancou" in result

    def test_close(self, mock_playwright):
        from core.browser_tool import BrowserTool
        browser = BrowserTool()
        browser._context = mock_playwright
        browser._browser = MagicMock()
        browser._playwright = MagicMock()
        result = browser.close()
        assert "fechado" in result.lower()

    def test_context_manager(self, mock_playwright):
        from core.browser_tool import BrowserTool
        with patch.object(BrowserTool, "close", return_value="Browser fechado."):
            with BrowserTool() as browser:
                assert browser is not None

    def test_no_playwright(self):
        with patch("core.browser_tool.PLAYWRIGHT_AVAILABLE", False):
            from core.browser_tool import BrowserTool
            browser = BrowserTool()
            result = browser.navigate("https://example.com")
            assert "Playwright nao disponivel" in result

    def test_singleton_get_browser(self):
        from core.browser_tool import get_browser, _browser_instance
        _browser_instance = None
        b1 = get_browser()
        b2 = get_browser()
        assert b1 is b2

    def test_browser_functions(self, mock_playwright):
        from core.browser_tool import (
            browser_navigate, browser_read_page, browser_get_text,
            browser_screenshot, browser_close,
        )
        with patch("core.browser_tool.get_browser") as mock_get:
            mock_b = MagicMock()
            mock_get.return_value = mock_b
            mock_b.navigate.return_value = "Navegado"
            mock_b.read_page.return_value = {"url": "", "elements": []}
            mock_b.get_page_text.return_value = "text"
            mock_b.screenshot.return_value = "Screenshot"
            mock_b.close.return_value = "Browser fechado."

            assert "Navegado" in browser_navigate("https://example.com")
            assert isinstance(browser_read_page(), dict)
            assert browser_get_text() == "text"
            assert "Screenshot" in browser_screenshot()
            assert "fechado" in browser_close().lower()
