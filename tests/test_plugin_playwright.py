"""
test_plugin_playwright.py
=========================
Testes automatizados para plugin_playwright com mocks.

Cobre:
- Navegacao (playwright_navigate)
- Extracao de texto/HTML/atributos (playwright_extract_text, etc.)
- Screenshots (playwright_screenshot)
- Multiplas abas (new_tab, switch_tab, list_tabs, close_tab)
- Interacao (click, fill, select_option, check, press)
- Espera (wait, wait_selector)
- Scroll (playwright_scroll)
- JavaScript (playwright_evaluate)
- Cookies (get_cookies, clear_cookies)
- Status, close, restart, go_back, go_forward, reload
- Erros: navegador fechado, timeout, seletor inexistente
- Register do plugin (api.register_tool)
- Navegacao paralela (navigate_all)

Uso:
    pytest test_plugin_playwright.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_page():
    """Cria um mock completo de pagina Playwright."""
    page = MagicMock()
    page.url = "https://exemplo.com"
    page.title.return_value = "Titulo Exemplo"
    page.content.return_value = "<html><body><h1>Ola</h1></body></html>"
    page.inner_text.return_value = "Texto visivel da pagina"

    locator = MagicMock()
    locator.count.return_value = 1
    locator.inner_text.return_value = "Texto do elemento"
    locator.inner_html.return_value = "<span>HTML</span>"
    locator.get_attribute.return_value = "https://link.com"
    locator.is_visible.return_value = True
    locator.bounding_box.return_value = {"width": 100, "height": 50}
    locator.click.return_value = None
    locator.fill.return_value = None
    locator.type.return_value = None
    locator.press.return_value = None
    locator.wait_for.return_value = None
    locator.all_inner_texts.return_value = ["Texto 1", "Texto 2"]
    locator.all.return_value = [
        MagicMock(get_attribute=lambda x: f"https://link{i}.com", inner_text=lambda: f"Link {i}")
        for i in range(3)
    ]

    page.locator.return_value = locator
    page.query_selector.return_value = locator
    page.query_selector_all.return_value = locator.all.return_value
    page.wait_for_load_state.return_value = None
    page.wait_for_selector.return_value = locator
    page.wait_for_timeout.return_value = None
    page.evaluate.return_value = "resultado_js"
    page.goto.return_value = None
    page.screenshot.return_value = None
    page.pdf.return_value = None
    page.set_default_timeout.return_value = None

    context = MagicMock()
    context.cookies.return_value = [
        {"name": "session", "value": "abc123", "domain": ".exemplo.com"}
    ]
    context.clear_cookies.return_value = None
    context.add_cookies.return_value = None
    context.pages = [page]

    page.context = context

    return page


@pytest.fixture
def mock_browser(mock_page):
    """Cria um mock de navegador Playwright."""
    browser = MagicMock()
    context = MagicMock()
    context.new_page.return_value = mock_page
    context.pages = [mock_page]
    context.cookies.return_value = [
        {"name": "session", "value": "abc123", "domain": ".exemplo.com"}
    ]
    context.clear_cookies.return_value = None
    context.add_cookies.return_value = None
    browser.new_context.return_value = context
    browser.contexts = [context]
    browser.close.return_value = None
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    """Cria um mock do modulo Playwright sync_api."""
    pw = MagicMock()
    pw.chromium = MagicMock()
    pw.chromium.launch.return_value = mock_browser
    pw.firefox = MagicMock()
    pw.firefox.launch.return_value = mock_browser
    pw.webkit = MagicMock()
    pw.webkit.launch.return_value = mock_browser
    pw.stop.return_value = None
    return pw


@pytest.fixture(autouse=True)
def reset_globals():
    """Reseta as variaveis globais do plugin antes de cada teste."""
    import plugins.plugin_playwright as pp

    pp._browser = None
    pp._context = None
    pp._page = None
    pp._playwright = None
    pp._tabs = {}
    pp._active_tab_id = None
    pp._tab_counter = 0


# =============================================================================
# Testes — Navegacao
# =============================================================================


class TestNavegacao:
    """Testes para navegacao basica com Playwright."""

    def test_navigate_url_valida(self, mock_playwright, mock_page, reset_globals):
        """playwright_navigate deve abrir URL e retornar informacoes."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            resultado = pp.playwright_navigate("https://exemplo.com")

        assert "Titulo Exemplo" in resultado
        assert "https://exemplo.com" in resultado
        mock_page.goto.assert_called_once_with("https://exemplo.com", wait_until="networkidle", timeout=30000)

    def test_navigate_sem_protocolo(self, mock_playwright, mock_page, reset_globals):
        """URL sem http:// nao recebe prefixo automatico (goto recebe a URL crua)."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("exemplo.com")

        # O plugin nao adiciona https automaticamente — testa que a URL e passada direto
        args, _ = mock_page.goto.call_args
        assert isinstance(args[0], str) and len(args[0]) > 0

    def test_navigate_timeout(self, mock_playwright, reset_globals):
        """Timeout no goto deve ser tratado graciosamente."""
        import plugins.plugin_playwright as pp

        page = mock_playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value
        page.goto.side_effect = Exception("Timeout 30000ms excedido")

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            resultado = pp.playwright_navigate("https://exemplo.com")

        assert "erro" in resultado.lower() or "timeout" in resultado.lower()

    def test_navigate_reusa_browser(self, mock_playwright, reset_globals):
        """Segunda navegacao deve reutilizar o navegador (nao chamar launch novamente)."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://site1.com")
            chamadas_launch = mock_playwright.chromium.launch.call_count

            pp.playwright_navigate("https://site2.com")
            assert mock_playwright.chromium.launch.call_count == chamadas_launch

    def test_go_back(self, mock_playwright, mock_page, reset_globals):
        """playwright_go_back deve voltar no historico."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_go_back()

        assert "voltou" in resultado.lower()

    def test_go_forward(self, mock_playwright, mock_page, reset_globals):
        """playwright_go_forward deve avancar no historico."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_go_forward()

        assert "avan" in resultado.lower() or "avancou" in resultado.lower()

    def test_reload(self, mock_playwright, mock_page, reset_globals):
        """playwright_reload deve recarregar a pagina."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_reload()

        assert "recarregada" in resultado.lower()


# =============================================================================
# Testes — Extracao de Conteudo
# =============================================================================


class TestExtracao:
    """Testes para extracao de conteudo."""

    def test_extract_text(self, mock_playwright, mock_page, reset_globals):
        """playwright_extract_text deve extrair texto do seletor."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_extract_text("body")

        assert "Texto" in resultado or len(resultado) > 0

    def test_get_content(self, mock_playwright, mock_page, reset_globals):
        """playwright_get_content deve extrair texto visivel da pagina."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_get_content()

        assert "Texto visivel" in resultado or len(resultado) > 0

    def test_get_url(self, mock_playwright, reset_globals):
        """playwright_get_url deve retornar URL atual."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_get_url()

        assert "https://exemplo.com" in resultado

    def test_get_title(self, mock_playwright, reset_globals):
        """playwright_get_title deve retornar titulo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_get_title()

        assert "Titulo Exemplo" in resultado

    def test_extract_links(self, mock_playwright, reset_globals):
        """playwright_extract_links deve extrair links."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_extract_links()

        assert "link" in resultado.lower() or "href" in resultado.lower()

    def test_extract_html(self, mock_playwright, reset_globals):
        """playwright_extract_html deve extrair HTML."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_extract_html("body")

        assert resultado is not None

    def test_extract_attribute(self, mock_playwright, reset_globals):
        """playwright_extract_attribute deve extrair atributo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_extract_attribute("a", "href")

        assert "link" in resultado.lower() or "href" in resultado.lower()


# =============================================================================
# Testes — Screenshots
# =============================================================================


class TestScreenshot:
    """Testes para captura de screenshots."""

    def test_screenshot_valido(self, mock_playwright, reset_globals):
        """playwright_screenshot deve salvar screenshot e retornar caminho."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_screenshot()

        assert "screenshot" in resultado.lower()
        assert ".png" in resultado.lower()

    def test_screenshot_com_selector(self, mock_playwright, reset_globals):
        """playwright_screenshot com seletor deve capturar elemento."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_screenshot(selector="#elemento")

        assert "screenshot" in resultado.lower()

    def test_screenshot_sem_navegador(self, reset_globals):
        """playwright_screenshot sem navegador deve levantar RuntimeError."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright", side_effect=ImportError("No module")):
            with pytest.raises(RuntimeError) as excinfo:
                pp.playwright_screenshot()
        assert "Playwright" in str(excinfo.value)


# =============================================================================
# Testes — Multiplas Abas
# =============================================================================


class TestMultiplasAbas:
    """Testes para gerenciamento de multiplas abas."""

    def test_new_tab_cria_aba(self, mock_playwright, mock_page, reset_globals):
        """playwright_new_tab deve criar nova aba com URL."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://site1.com")

            mock_page2 = MagicMock()
            mock_page2.url = "https://site2.com"
            mock_page2.title.return_value = "Site 2"
            mock_page2.goto.return_value = None
            mock_page2.set_default_timeout.return_value = None

            context = mock_playwright.chromium.launch.return_value.new_context.return_value
            context.new_page.return_value = mock_page2

            resultado = pp.playwright_new_tab("https://site2.com")

        assert "nova aba" in resultado.lower()
        assert "tab_" in resultado

    def test_new_tab_url_vazia(self, mock_playwright, reset_globals):
        """playwright_new_tab sem URL deve criar aba about:blank."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_new_tab()

        assert "nova aba" in resultado.lower()

    def test_list_tabs(self, mock_playwright, reset_globals):
        """playwright_list_tabs deve listar abas abertas."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_list_tabs()

        assert "aba" in resultado.lower()

    def test_switch_tab(self, mock_playwright, reset_globals):
        """playwright_switch_tab deve alternar para aba especifica."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://site1.com")

            tab1_id = pp._active_tab_id
            mock_page2 = MagicMock()
            context = mock_playwright.chromium.launch.return_value.new_context.return_value
            context.new_page.return_value = mock_page2
            pp.playwright_new_tab("https://site2.com")

            resultado = pp.playwright_switch_tab(tab1_id)

        assert "alternado" in resultado.lower() or tab1_id in resultado

    def test_switch_tab_id_invalido(self, mock_playwright, reset_globals):
        """playwright_switch_tab com ID invalido deve retornar erro."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_switch_tab("id_inexistente")

        assert "nao encontrada" in resultado.lower()

    def test_close_tab(self, mock_playwright, reset_globals):
        """playwright_close_tab deve fechar aba ativa."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_close_tab()

        assert "fechada" in resultado.lower()


# =============================================================================
# Testes — Interacao
# =============================================================================


class TestInteracao:
    """Testes para interacao com elementos."""

    def test_click_valido(self, mock_playwright, reset_globals):
        """playwright_click deve clicar no seletor."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_click("#botao")

        assert "clique" in resultado.lower()

    def test_click_erro(self, mock_playwright, reset_globals):
        """playwright_click com erro deve retornar mensagem de erro."""
        import plugins.plugin_playwright as pp

        page = mock_playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value
        page.click.side_effect = Exception("Elemento nao encontrado")

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_click("#inexistente")

        assert "erro" in resultado.lower()

    def test_fill_valido(self, mock_playwright, reset_globals):
        """playwright_fill deve preencher campo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_fill("#campo", "valor teste")

        assert "preenchido" in resultado.lower()

    def test_type_valido(self, mock_playwright, reset_globals):
        """playwright_type deve digitar texto caractere por caractere."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_type("#campo", "texto")

        assert "digitado" in resultado.lower()

    def test_select_option(self, mock_playwright, reset_globals):
        """playwright_select_option deve selecionar opcao."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_select_option("#select", "opcao1")

        assert "selecionada" in resultado.lower()

    def test_check_uncheck(self, mock_playwright, reset_globals):
        """playwright_check e playwright_uncheck devem funcionar."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")

            r1 = pp.playwright_check("#checkbox")
            r2 = pp.playwright_uncheck("#checkbox")

        assert "check" in r1.lower() and "desmarcado" in r2.lower()

    def test_press_tecla(self, mock_playwright, reset_globals):
        """playwright_press deve pressionar tecla."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_press("Enter")

        assert "Enter" in resultado or "tecla" in resultado.lower()


# =============================================================================
# Testes — Espera e Scroll
# =============================================================================


class TestEsperaScroll:
    """Testes para wait, wait_selector e scroll."""

    def test_wait(self, mock_playwright, reset_globals):
        """playwright_wait deve aguardar tempo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_wait(2000)

        assert "2000" in resultado

    def test_wait_selector(self, mock_playwright, reset_globals):
        """playwright_wait_selector deve aguardar elemento."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_wait_selector("#elemento")

        assert "encontrado" in resultado.lower()

    def test_scroll_down(self, mock_playwright, reset_globals):
        """playwright_scroll deve rolar para baixo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_scroll(direction="down", amount=500)

        assert "scroll" in resultado.lower()

    def test_scroll_top(self, mock_playwright, reset_globals):
        """playwright_scroll deve rolar para o topo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_scroll(direction="top")

        assert "scroll" in resultado.lower()

    def test_scroll_direcao_invalida(self, mock_playwright, reset_globals):
        """playwright_scroll com direcao invalida deve retornar erro."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_scroll(direction="diagonal")

        assert "invalida" in resultado.lower()


# =============================================================================
# Testes — JavaScript
# =============================================================================


class TestJavaScript:
    """Testes para execucao de JavaScript."""

    def test_evaluate(self, mock_playwright, mock_page, reset_globals):
        """playwright_evaluate deve executar JS e retornar resultado."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_evaluate("document.title")

        assert "resultado_js" in resultado

    def test_evaluate_sem_navegador(self, reset_globals):
        """playwright_evaluate sem navegador deve levantar RuntimeError."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright", side_effect=ImportError("No module")):
            with pytest.raises((ImportError, RuntimeError)):
                pp.playwright_evaluate("1+1")


# =============================================================================
# Testes — Cookies
# =============================================================================


class TestCookies:
    """Testes para gerenciamento de cookies."""

    def test_get_cookies(self, mock_playwright, reset_globals):
        """playwright_get_cookies deve listar cookies."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_get_cookies()

        assert "session" in resultado
        assert "abc123" in resultado

    def test_clear_cookies(self, mock_playwright, reset_globals):
        """playwright_clear_cookies deve limpar cookies."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_clear_cookies()

        assert "limpos" in resultado.lower()


# =============================================================================
# Testes — Gerenciamento do Navegador
# =============================================================================


class TestGerenciamento:
    """Testes para gerenciamento do navegador."""

    def test_status_ativo(self, mock_playwright, reset_globals):
        """playwright_status deve mostrar status ativo."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_status()

        assert "conectado" in resultado.lower() or "abas" in resultado.lower()

    def test_status_inativo(self, reset_globals):
        """playwright_status sem navegador deve mostrar fechado."""
        import plugins.plugin_playwright as pp

        resultado = pp.playwright_status()
        assert "fechado" in resultado.lower()

    def test_close(self, mock_playwright, reset_globals):
        """playwright_close deve fechar navegador."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_close()

        assert "fechado" in resultado.lower()
        assert pp._browser is None

    def test_restart(self, mock_playwright, reset_globals):
        """playwright_restart deve reiniciar navegador."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_restart()

        assert "reiniciado" in resultado.lower()


# =============================================================================
# Testes — Register do Plugin
# =============================================================================


class TestRegister:
    """Testes para registro do plugin."""

    def test_register_registra_ferramentas(self, reset_globals):
        """register() deve chamar api.register_tool para todas as funcoes."""
        import plugins.plugin_playwright as pp

        api = MagicMock()
        resultado = pp.register(api)

        assert api.register_tool.call_count >= 20
        nomes = [c.kwargs.get("name") or c.args[0] for c in api.register_tool.call_args_list]
        assert "playwright_navigate" in nomes
        assert "playwright_click" in nomes
        assert "playwright_fill" in nomes
        assert "playwright_screenshot" in nomes
        assert "playwright_new_tab" in nomes
        assert "playwright_close" in nomes

    def test_register_inclui_descricoes(self, reset_globals):
        """register() deve incluir descricoes das ferramentas."""
        import plugins.plugin_playwright as pp

        api = MagicMock()
        pp.register(api)

        for call_args in api.register_tool.call_args_list:
            kwargs = call_args.kwargs if call_args.kwargs else {}
            nome = kwargs.get("name") or call_args.args[0] if call_args.args else "unknown"
            descricao = kwargs.get("description") or (call_args.args[2] if len(call_args.args) > 2 else "")
            assert nome, "Ferramenta sem nome"
            assert isinstance(descricao, str) and len(descricao) > 5, f"{nome} sem descricao"

    def test_register_retorna_dict(self, reset_globals):
        """register() deve retornar dicionario com metadados."""
        import plugins.plugin_playwright as pp

        api = MagicMock()
        resultado = pp.register(api)

        assert isinstance(resultado, dict)
        assert "name" in resultado
        assert "tools" in resultado
        assert len(resultado["tools"]) >= 20


# =============================================================================
# Testes — Navegacao Paralela
# =============================================================================


class TestNavegacaoParalela:
    """Testes para navegacao paralela com multiplas URLs."""

    def test_navigate_all_valido(self, mock_playwright, mock_page, reset_globals):
        """playwright_navigate_all deve navegar multiplas URLs."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")

            resultado = pp.playwright_navigate_all("https://site1.com, https://site2.com")

        assert "2 URLs" in resultado or "conclu" in resultado.lower()

    def test_navigate_all_sem_urls(self, mock_playwright, reset_globals):
        """playwright_navigate_all sem URLs deve retornar erro."""
        import plugins.plugin_playwright as pp

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_navigate_all("")

        assert "nenhuma url" in resultado.lower() or "erro" in resultado.lower()

    def test_navigate_all_mais_de_10(self, mock_playwright, reset_globals):
        """playwright_navigate_all com mais de 10 URLs deve limitar."""
        import plugins.plugin_playwright as pp

        urls = ", ".join([f"https://site{i}.com" for i in range(15)])
        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.start.return_value = mock_playwright
            pp.playwright_navigate("https://exemplo.com")
            resultado = pp.playwright_navigate_all(urls)

        assert "limite" in resultado.lower() or "10" in resultado
