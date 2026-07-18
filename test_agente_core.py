"""
test_agente_core.py
===================
Testes unitarios para as funcoes do modulo agente_core.

Uso:
    pytest test_agente_core.py -v          # verbose
    pytest test_agente_core.py -v -k calc  # filtra por nome
    pytest test_agente_core.py --coverage  # cobertura (se pytest-cov instalado)
"""

import os
import sys
import json
import tempfile
import shutil
import math
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

import pytest

# Adiciona o diretorio raiz ao path para importar agente_core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_core import (
    # Core
    DATA_DIR,
    MEMORY_FILE,
    HISTORY_FILE,
    MODEL,
    MAX_HISTORY_MESSAGES,
    # Memoria
    remember,
    recall,
    forget,
    list_memories,
    load_conversation_history,
    save_conversation_history,
    trim_and_summarize_history,
    # Arquivos
    create_folder,
    write_file,
    append_file,
    read_file,
    list_files,
    search_files,
    get_file_info,
    move_file,
    copy_file,
    delete_path,
    search_and_replace,
    # Calculos
    calculate,
    _safe_eval,
    # Documentos
    read_pdf,
    read_image_text,
    # Sistema
    get_datetime,
    get_system_info,
    run_command,
    run_python_code,
    fetch_url,
    describe_image,
    # Export
    export_conversation_markdown,
    export_conversation_html,
    _format_mensagem_para_export,
    # Plugins
    PluginAPI,
    PluginManager,
    list_plugins,
    reload_plugins,
    PLUGINS_DIR,
    # Internas
    _load_json,
    _save_json,
    _execute_tool_call,
    # Loop do agente
    run_agent_turn,
    _chat_with_retries,
    OLLAMA_MAX_RETRIES,
    MAX_TOOL_ROUNDS,
)

# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture(autouse=True)
def limpar_memoria():
    """Limpa memoria e historico antes de cada teste."""
    _save_json(MEMORY_FILE, {})
    _save_json(HISTORY_FILE, [])
    yield
    _save_json(MEMORY_FILE, {})
    _save_json(HISTORY_FILE, [])


@pytest.fixture
def temp_dir():
    """Cria diretorio temporario para testes de arquivo."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def mensagens_exemplo():
    """Mensagens padrao para testes de export."""
    return [
        {"role": "system", "content": "Prompt do sistema"},
        {"role": "user", "content": "Ola, tudo bem?"},
        {"role": "assistant", "content": "Tudo bem! Como posso ajudar?"},
        {"role": "user", "content": "Qual a capital do Brasil?"},
        {"role": "assistant", "content": "Brasilia"},
    ]


# =====================================================================
# Tests: _load_json / _save_json (utilitarios internos)
# =====================================================================


class TestJsonUtils:
    def test_save_e_load_json(self, tmp_path):
        """Salva e carrega JSON corretamente."""
        arquivo = tmp_path / "test.json"
        _save_json(str(arquivo), {"chave": "valor"})
        assert arquivo.exists()
        resultado = _load_json(str(arquivo), {})
        assert resultado == {"chave": "valor"}

    def test_load_json_arquivo_inexistente(self):
        """Retorna default quando arquivo nao existe."""
        resultado = _load_json("/caminho/inexistente.json", [])
        assert resultado == []

    def test_load_json_arquivo_corrompido(self, tmp_path):
        """Retorna default quando JSON e invalido."""
        arquivo = tmp_path / "corrompido.json"
        arquivo.write_text("isto nao e json", encoding="utf-8")
        resultado = _load_json(str(arquivo), {"fallback": True})
        assert resultado == {"fallback": True}


# =====================================================================
# Tests: Memoria Persistente
# =====================================================================


class TestMemoria:
    def test_remember_e_recall(self):
        """Guarda e recupera um fato."""
        resultado = remember("nome", "Joao")
        assert "Guardado" in resultado
        assert "Joao" in resultado

        resultado = recall("nome")
        assert resultado == "Joao"

    def test_recall_chave_inexistente(self):
        """Retorna mensagem para chave que nao existe."""
        resultado = recall("chave_inexistente")
        assert "Nao encontrei" in resultado

    def test_forget(self):
        """Remove um fato guardado."""
        remember("cor", "azul")
        resultado = forget("cor")
        assert "Removido" in resultado
        assert recall("cor") != "azul"

    def test_forget_chave_inexistente(self):
        """Retorna mensagem ao tentar remover chave inexistente."""
        resultado = forget("nao_existe")
        assert "Nao havia" in resultado

    def test_list_memories_vazia(self):
        """Lista vazia retorna mensagem especifica."""
        resultado = list_memories()
        assert "vazia" in resultado

    def test_list_memories_com_itens(self):
        """Lista retorna todos os fatos."""
        remember("a", "1")
        remember("b", "2")
        resultado = list_memories()
        assert "a: 1" in resultado
        assert "b: 2" in resultado


class TestHistorico:
    def test_save_e_load(self):
        """Salva e carrega historico corretamente."""
        msgs = [
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "ola"},
        ]
        save_conversation_history(msgs)
        carregado = load_conversation_history()
        assert len(carregado) == 2
        assert carregado[0]["role"] == "user"

    def test_save_filtra_tool_calls(self):
        """Salva apenas campos serializaveis (role, content)."""
        msgs = [
            {"role": "user", "content": "teste", "tool_calls": ["x"]},
        ]
        save_conversation_history(msgs)
        carregado = load_conversation_history()
        assert "tool_calls" not in carregado[0]

    def test_load_vazia(self):
        """Historico vazio retorna lista vazia."""
        _save_json(HISTORY_FILE, [])
        carregado = load_conversation_history()
        assert carregado == []


# =====================================================================
# Tests: Operacoes com Arquivos e Pastas
# =====================================================================


class TestArquivos:
    def test_create_folder(self, temp_dir):
        """Cria uma pasta."""
        path = os.path.join(temp_dir, "nova_pasta")
        resultado = create_folder(path)
        assert os.path.isdir(path)
        assert "criada" in resultado

    def test_create_folder_subpastas(self, temp_dir):
        """Cria pastas aninhadas."""
        path = os.path.join(temp_dir, "a", "b", "c")
        resultado = create_folder(path)
        assert os.path.isdir(path)
        assert "criada" in resultado

    def test_write_e_read_file(self, temp_dir):
        """Escreve e le um arquivo."""
        path = os.path.join(temp_dir, "teste.txt")
        resultado = write_file(path, "conteudo")
        assert "salvo" in resultado
        assert os.path.exists(path)

        conteudo = read_file(path)
        assert conteudo == "conteudo"

    def test_append_file(self, temp_dir):
        """Adiciona conteudo ao final de um arquivo."""
        path = os.path.join(temp_dir, "append.txt")
        write_file(path, "linha1")
        append_file(path, "\nlinha2")
        conteudo = read_file(path)
        assert "linha1" in conteudo
        assert "linha2" in conteudo

    def test_read_file_inexistente(self):
        """Retorna erro ao ler arquivo que nao existe."""
        resultado = read_file("/tmp/nao_existe_12345.txt")
        assert "Erro" in resultado

    def test_list_files(self, temp_dir):
        """Lista arquivos de uma pasta."""
        write_file(os.path.join(temp_dir, "a.txt"), "a")
        write_file(os.path.join(temp_dir, "b.txt"), "b")
        resultado = list_files(temp_dir)
        assert "a.txt" in resultado
        assert "b.txt" in resultado

    def test_list_files_vazia(self, temp_dir):
        """Pasta vazia retorna mensagem."""
        resultado = list_files(temp_dir)
        assert "vazia" in resultado

    def test_search_files(self, temp_dir):
        """Busca arquivos por padrao no nome."""
        write_file(os.path.join(temp_dir, "relatorio_2024.pdf"), "")
        write_file(os.path.join(temp_dir, "foto.jpg"), "")
        resultado = search_files(temp_dir, "relatorio")
        assert "relatorio_2024" in resultado
        assert "foto" not in resultado

    def test_get_file_info(self, temp_dir):
        """Retorna informacoes do arquivo."""
        path = os.path.join(temp_dir, "info.txt")
        write_file(path, "dados")
        resultado = get_file_info(path)
        assert "arquivo" in resultado
        assert "bytes" in resultado
        assert "modificacao" in resultado.lower()

    def test_get_file_info_inexistente(self):
        """Caminho inexistente retorna mensagem."""
        resultado = get_file_info("/tmp/nao_existe_123.txt")
        assert "nao existe" in resultado

    def test_move_file(self, temp_dir):
        """Move um arquivo."""
        origem = os.path.join(temp_dir, "origem.txt")
        destino = os.path.join(temp_dir, "destino.txt")
        write_file(origem, "movido")
        resultado = move_file(origem, destino)
        assert "Movido" in resultado
        assert os.path.exists(destino)
        assert not os.path.exists(origem)

    def test_copy_file(self, temp_dir):
        """Copia um arquivo."""
        origem = os.path.join(temp_dir, "origem.txt")
        destino = os.path.join(temp_dir, "copia.txt")
        write_file(origem, "copia")
        resultado = copy_file(origem, destino)
        assert "Copiado" in resultado
        assert os.path.exists(origem)
        assert os.path.exists(destino)

    def test_delete_path(self, temp_dir):
        """Apaga um arquivo (com confirmacao)."""
        path = os.path.join(temp_dir, "deletar.txt")
        write_file(path, "x")
        resultado = delete_path(path, confirm=True)
        assert "apagado" in resultado
        assert not os.path.exists(path)

    def test_delete_sem_confirmacao(self, temp_dir):
        """Sem confirm=true, retorna aviso de seguranca."""
        path = os.path.join(temp_dir, "seguro.txt")
        write_file(path, "x")
        resultado = delete_path(path)
        assert "cancelada" in resultado or "seguranca" in resultado
        assert os.path.exists(path)  # arquivo nao foi apagado

    def test_search_and_replace(self, temp_dir):
        """Substitui texto em um arquivo."""
        path = os.path.join(temp_dir, "substituir.txt")
        write_file(path, "Ola mundo, mundo lindo")
        resultado = search_and_replace(path, "mundo", "terra")
        assert "Substituido" in resultado
        conteudo = read_file(path)
        assert "terra" in conteudo
        assert "mundo" not in conteudo

    def test_search_and_replace_nao_encontrado(self, temp_dir):
        """Texto nao encontrado retorna mensagem."""
        path = os.path.join(temp_dir, "sem_match.txt")
        write_file(path, "conteudo original")
        resultado = search_and_replace(path, "inexistente", "x")
        assert "nao encontrado" in resultado


# =====================================================================
# Tests: Calculadora (_safe_eval / calculate)
# =====================================================================


class TestCalculadora:
    @pytest.mark.parametrize("expr,esperado", [
        ("2 + 3", "5"),
        ("10 - 4", "6"),
        ("3 * 7", "21"),
        ("20 / 4", "5"),
        ("(3 + 4) * 2", "14"),
        ("2 ** 8", "256"),
        ("10 % 3", "1"),
        ("-5 + 3", "-2"),
        ("0.5 * 10", "5"),
        ("7", "7"),
    ])
    def test_calculate_basico(self, expr, esperado):
        """Operacoes matematicas basicas."""
        resultado = calculate(expr)
        assert resultado == esperado, f"{expr} -> {resultado}, esperado {esperado}"

    def test_calculate_decimais(self):
        """Resultados com casas decimais."""
        resultado = calculate("1 / 3")
        assert "0.3333" in resultado

    def test_calculate_divisao_zero(self):
        """Divisao por zero retorna erro."""
        resultado = calculate("1 / 0")
        assert "divisao por zero" in resultado.lower()

    def test_calculate_expressao_invalida(self):
        """Expressao invalida retorna erro."""
        resultado = calculate("ola + mundo")
        assert "invalida" in resultado.lower() or "Erro" in resultado

    def test_calculate_seguranca(self):
        """Tentativa de injecao via eval e bloqueada."""
        resultado = calculate("__import__('os').system('dir')")
        assert "invalida" in resultado.lower() or "Erro" in resultado

    @pytest.mark.parametrize("expr", [
        "__import__('os')",
        "print('teste')",
        "globals()",
        "open('/etc/passwd')",
    ])
    def test_calculate_bloqueia_funcoes(self, expr):
        """Expressoes com chamadas de funcao sao bloqueadas."""
        resultado = calculate(expr)
        assert "invalida" in resultado.lower() or "Erro" in resultado

    def test_safe_eval_potencia_grande(self):
        """Numeros muito grandes funcionam."""
        resultado = _safe_eval("2 ** 20")
        assert resultado == 1048576.0

    def test_calculate_numero_muito_pequeno(self):
        """Numeros muito pequenos nao geram string vazia."""
        resultado = calculate("1e-7")
        # Nao deve ser string vazia
        assert resultado != ""
        assert resultado is not None


# =====================================================================
# Tests: Sistema e Utilitarios
# =====================================================================


class TestSistema:
    def test_get_datetime_formato(self):
        """Data/hora no formato brasileiro."""
        resultado = get_datetime()
        # Deve ter barras (dd/mm/aaaa)
        assert "/" in resultado
        assert ":" in resultado
        # Deve ser a data atual
        hoje = datetime.now().strftime("%d/%m/%Y")
        assert hoje in resultado

    @patch("agente_core.subprocess.run")
    def test_run_command(self, mock_run):
        """Executa comando e retorna saida."""
        mock_run.return_value.stdout = "saida do comando\n"
        mock_run.return_value.stderr = ""
        resultado = run_command("echo teste")
        assert "saida do comando" in resultado

    @patch("agente_core.subprocess.run")
    def test_run_command_com_erro(self, mock_run):
        """Comando com stderr e incluido na saida."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "erro: nao encontrado"
        resultado = run_command("comando_falso")
        assert "stderr" in resultado
        assert "erro" in resultado

    def test_run_python_code_simples(self):
        """Executa codigo Python e retorna print."""
        resultado = run_python_code("print('hello from python')")
        assert "hello from python" in resultado

    def test_run_python_code_sem_saida(self):
        """Codigo sem print retorna mensagem padrao."""
        resultado = run_python_code("x = 42")
        assert "sem saida" in resultado

    def test_run_python_code_erro(self):
        """Erro no codigo e capturado."""
        resultado = run_python_code("1/0")
        assert "Erro" in resultado

    @patch("requests.get")
    def test_fetch_url(self, mock_get):
        """Busca URL com sucesso."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "conteudo da pagina"
        mock_get.return_value.raise_for_status = MagicMock()
        resultado = fetch_url("https://exemplo.com")
        assert "conteudo da pagina" in resultado

    @patch("requests.get")
    def test_fetch_url_truncada(self, mock_get):
        """Conteudo maior que max_chars e truncado."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "a" * 10000
        mock_get.return_value.raise_for_status = MagicMock()
        resultado = fetch_url("https://exemplo.com", max_chars=100)
        assert len(resultado) <= 200  # 100 + mensagem de truncamento
        assert "truncado" in resultado

    @patch("requests.get", side_effect=ImportError("no module"))
    def test_fetch_url_sem_requests(self, mock_get):
        """Sem requests instalado, retorna mensagem de instalacao."""
        resultado = fetch_url("https://exemplo.com")
        assert "Instale" in resultado or "requests" in resultado


# =====================================================================
# Tests: Exportacao
# =====================================================================


class TestExport:
    def test_format_mensagem_user(self):
        assert _format_mensagem_para_export({"role": "user"}) == "Você"

    def test_format_mensagem_assistant(self):
        assert _format_mensagem_para_export({"role": "assistant"}) == "Agente"

    def test_format_mensagem_tool(self):
        assert "Ferramenta" in _format_mensagem_para_export({"role": "tool"})

    def test_format_mensagem_system(self):
        assert _format_mensagem_para_export({"role": "system"}) == "Sistema"

    def test_export_markdown_cria_arquivo(self, mensagens_exemplo, tmp_path):
        """Exporta Markdown e arquivo e criado."""
        path = str(tmp_path / "conversa.md")
        resultado = export_conversation_markdown(mensagens_exemplo, path)
        assert "exportada" in resultado.lower()
        assert os.path.exists(path)

    def test_export_markdown_conteudo(self, mensagens_exemplo, tmp_path):
        """Conteudo do Markdown inclui mensagens."""
        path = str(tmp_path / "conversa.md")
        export_conversation_markdown(mensagens_exemplo, path)
        conteudo = read_file(path)
        assert "Você" in conteudo
        assert "Agente" in conteudo
        assert "Brasil" in conteudo or "Brasilia" in conteudo
        assert MODEL in conteudo

    def test_export_markdown_sem_mensagens(self, tmp_path):
        """Lista vazia retorna mensagem de erro."""
        path = str(tmp_path / "vazia.md")
        resultado = export_conversation_markdown([], path)
        assert "Nao ha mensagens" in resultado

    def test_export_html_cria_arquivo(self, mensagens_exemplo, tmp_path):
        """Exporta HTML e arquivo e criado."""
        path = str(tmp_path / "conversa.html")
        resultado = export_conversation_html(mensagens_exemplo, path)
        assert "exportada" in resultado.lower()
        assert os.path.exists(path)

    def test_export_html_conteudo(self, mensagens_exemplo, tmp_path):
        """Conteudo do HTML inclui CSS e mensagens."""
        path = str(tmp_path / "conversa.html")
        export_conversation_html(mensagens_exemplo, path)
        conteudo = read_file(path)
        assert "<!DOCTYPE html>" in conteudo
        assert "Você" in conteudo
        assert "Agente" in conteudo
        assert "Brasilia" in conteudo
        # CSS embutido
        assert "background: #1e1e2e" in conteudo

    def test_export_html_escapamento(self, mensagens_exemplo, tmp_path):
        """HTML escapa caracteres especiais."""
        msgs = [
            {"role": "user", "content": "<script>alert('xss')</script>"},
            {"role": "assistant", "content": 'Texto com "aspas" & &amp;'},
        ]
        path = str(tmp_path / "seguro.html")
        export_conversation_html(msgs, path)
        conteudo = read_file(path)
        assert "&lt;script&gt;" in conteudo
        assert "&quot;aspas&quot;" in conteudo
        assert "&amp;" in conteudo

    def test_export_html_sem_mensagens(self, tmp_path):
        """Lista vazia retorna erro."""
        path = str(tmp_path / "vazio.html")
        resultado = export_conversation_html([], path)
        assert "Nao ha mensagens" in resultado

    def test_export_markdown_auto_nome(self, mensagens_exemplo):
        """Sem caminho, gera nome automatico em DATA_DIR."""
        resultado = export_conversation_markdown(mensagens_exemplo)
        assert "exportada" in resultado.lower()
        assert "agente_data" in resultado or ".md" in resultado


# =====================================================================
# Tests: Plugin System
# =====================================================================


class TestPluginAPI:
    def test_register_tool(self):
        """Registra uma ferramenta via PluginAPI."""
        functions = {}
        tools = []
        api = PluginAPI(functions, tools)

        def minha_func(texto: str) -> str:
            return f"processado: {texto}"

        api.register_tool(
            name="minha_tool",
            func=minha_func,
            description="Processa um texto",
            parameters={
                "texto": {"type": "string", "description": "Texto a processar"}
            },
            required=["texto"],
        )

        assert "minha_tool" in functions
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "minha_tool"
        assert tools[0]["function"]["description"] == "Processa um texto"
        assert "texto" in tools[0]["function"]["parameters"]["properties"]
        assert tools[0]["function"]["parameters"]["required"] == ["texto"]

    def test_register_tool_duplicada(self):
        """Registro duplicado e ignorado com warning."""
        functions = {"existente": lambda: None}
        tools = []
        api = PluginAPI(functions, tools)

        def outra():
            pass

        api.register_tool(
            name="existente",
            func=outra,
            description="dup",
        )

        # Nao deve substituir
        assert len(tools) == 0

    def test_register_tool_sem_parametros(self):
        """Ferramenta sem parametros funciona."""
        functions = {}
        tools = []
        api = PluginAPI(functions, tools)

        def ping() -> str:
            return "pong"

        api.register_tool(name="ping", func=ping, description="ping pong")

        assert "ping" in functions
        assert tools[0]["function"]["parameters"]["properties"] == {}
        assert tools[0]["function"]["parameters"]["required"] == []

    def test_api_properties(self):
        """Propriedades model e data_dir funcionam."""
        api = PluginAPI({}, [])
        assert api.model == MODEL
        assert api.data_dir == DATA_DIR


class TestPluginManager:
    def test_init_vazio(self):
        """PluginManager comeca vazio."""
        pm = PluginManager()
        assert pm.plugin_count == 0
        assert pm.loaded_count == 0
        assert "Nenhum plugin" in pm.list_plugins_text()

    def test_clear(self):
        """Limpa todos os plugins."""
        pm = PluginManager()
        pm._plugins["teste"] = {"name": "teste", "loaded": True}
        assert pm.plugin_count == 1
        pm.clear()
        assert pm.plugin_count == 0

    def test_loaded_plugins_property(self):
        """Propriedade retorna copia do dict."""
        pm = PluginManager()
        pm._plugins["p1"] = {"name": "p1", "loaded": True}
        copia = pm.loaded_plugins
        assert "p1" in copia
        # Modificar a copia nao afeta o original
        copia["p2"] = {"name": "p2"}
        assert pm.plugin_count == 1

    def test_load_all_sem_pasta(self):
        """Sem diretorio plugins/, nao quebra."""
        with patch("agente_core.PLUGINS_DIR", "/tmp/pasta_inexistente_xyz"):
            pm = PluginManager()
            pm.load_all({}, [])
            assert pm.plugin_count == 0

    @patch("agente_core.os.listdir")
    def test_load_all_com_plugin_valido(self, mock_listdir):
        """Carrega plugin que implementa register()."""
        # Mock do diretorio com um plugin
        mock_listdir.return_value = ["meu_plugin.py"]

        # Cria um modulo fake com funcao register
        def fake_register(api):
            def minha_tool():
                return "ok"
            api.register_tool(
                name="tool1", func=minha_tool,
                description="Ferramenta de teste",
            )
            return {
                "name": "meu_plugin",
                "version": "1.0",
                "description": "Plugin de teste",
                "tools": ["tool1"],
            }

        fake_module = MagicMock()
        fake_module.register = fake_register

        # Simula o import dinamico
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_spec_inst = MagicMock()
            mock_spec.return_value = mock_spec_inst
            
            with patch("importlib.util.module_from_spec", return_value=fake_module):
                pm = PluginManager()
                pm.load_all({}, [])
                assert pm.plugin_count == 1
                assert pm.loaded_count == 1
                info = pm.loaded_plugins["meu_plugin"]
                assert info["version"] == "1.0"

    def test_list_plugins_sem_plugins(self):
        """Nenhum plugin carregado."""
        pm = PluginManager()
        with patch("agente_core._plugin_manager", pm):
            resultado = list_plugins()
            assert "Nenhum plugin" in resultado

    def test_list_plugins_com_plugins(self):
        """Plugin carregado aparece na listagem."""
        pm = PluginManager()
        pm._plugins["clima"] = {
            "name": "clima",
            "version": "1.0.0",
            "description": "Consulta clima",
            "loaded": True,
            "tools": ["consultar_clima"],
        }

        with patch("agente_core._plugin_manager", pm):
            resultado = list_plugins()
            assert "clima" in resultado
            assert "1.0.0" in resultado
            assert "consulta" in resultado.lower()


# =====================================================================
# Tests: _execute_tool_call
# =====================================================================


class TestExecuteToolCall:
    def test_chamada_valida(self):
        """Chamada de ferramenta valida executa e retorna resultado."""
        funcoes = {"soma": lambda a, b: str(a + b)}
        tool_call = {
            "function": {
                "name": "soma",
                "arguments": '{"a": 3, "b": 4}',
            }
        }
        with patch("agente_core.AVAILABLE_FUNCTIONS", funcoes):
            nome, args, resultado = _execute_tool_call(tool_call)
            assert nome == "soma"
            assert args == {"a": 3, "b": 4}
            assert resultado == "7"

    def test_ferramenta_inexistente(self):
        """Ferramenta que nao existe retorna erro."""
        tool_call = {
            "function": {
                "name": "nao_existe",
                "arguments": "{}",
            }
        }
        with patch("agente_core.AVAILABLE_FUNCTIONS", {}):
            nome, args, resultado = _execute_tool_call(tool_call)
            assert "nao existe" in resultado

    def test_argumentos_invalidos_json(self):
        """JSON invalido nos argumentos retorna erro."""
        tool_call = {
            "function": {
                "name": "read_file",
                "arguments": "json invalido {{{",
            }
        }
        nome, args, resultado = _execute_tool_call(tool_call)
        assert "argumentos invalidos" in resultado

    def test_argumentos_incorretos(self):
        """Argumentos incorretos para a funcao."""
        funcoes = {"soma": lambda a, b: a + b}
        tool_call = {
            "function": {
                "name": "soma",
                "arguments": '{"x": 1}',  # espera 'a' e 'b', recebe 'x'
            }
        }
        with patch("agente_core.AVAILABLE_FUNCTIONS", funcoes):
            nome, args, resultado = _execute_tool_call(tool_call)
            assert "argumentos incorretos" in resultado.lower() or "Erro" in resultado


# =====================================================================
# Tests: Edge Cases e Seguranca
# =====================================================================


class TestEdgeCases:
    def test_search_files_padrao_vazio(self, temp_dir):
        """Busca com padrao vazio retorna todos os arquivos."""
        write_file(os.path.join(temp_dir, "qualquer.txt"), "x")
        resultado = search_files(temp_dir, "")
        assert "qualquer.txt" in resultado

    def test_move_file_destino_ja_existe(self, temp_dir):
        """Mover para destino existente sobrescreve (shutil.move)."""
        origem = os.path.join(temp_dir, "origem.txt")
        destino = os.path.join(temp_dir, "destino.txt")
        write_file(origem, "conteudo novo")
        write_file(destino, "conteudo antigo")
        resultado = move_file(origem, destino)
        assert "Movido" in resultado
        assert not os.path.exists(origem)

    def test_delete_path_pasta_com_itens(self, temp_dir):
        """Apaga pasta com arquivos dentro."""
        subpasta = os.path.join(temp_dir, "subpasta")
        os.makedirs(subpasta)
        write_file(os.path.join(subpasta, "arquivo.txt"), "x")
        resultado = delete_path(subpasta, confirm=True)
        assert "apagado" in resultado
        assert not os.path.exists(subpasta)

    def test_write_file_cria_subpastas(self, temp_dir):
        """write_file cria subpastas intermediarias."""
        path = os.path.join(temp_dir, "a", "b", "c", "arquivo.txt")
        resultado = write_file(path, "teste")
        assert os.path.exists(path)
        assert "salvo" in resultado

    def test_append_file_cria_se_nao_existe(self, temp_dir):
        """append_file cria o arquivo se ele nao existir (modo 'a')."""
        path = os.path.join(temp_dir, "novo_append.txt")
        resultado = append_file(path, "primeira linha")
        # 'a' mode cria se nao existir
        assert os.path.exists(path)
        conteudo = read_file(path)
        assert "primeira linha" in conteudo

    def test_copy_file_pasta(self, temp_dir):
        """Copia pasta com todo conteudo."""
        origem = os.path.join(temp_dir, "pasta_origem")
        destino = os.path.join(temp_dir, "pasta_destino")
        os.makedirs(origem)
        write_file(os.path.join(origem, "doc.txt"), "conteudo")
        resultado = copy_file(origem, destino)
        assert "Copiado" in resultado
        assert os.path.isdir(destino)
        assert os.path.exists(os.path.join(destino, "doc.txt"))

    def test_get_file_info_pasta(self, temp_dir):
        """get_file_info funciona em pastas."""
        info = get_file_info(temp_dir)
        assert "pasta" in info


# =====================================================================
# Tests: trim_and_summarize_history
# =====================================================================


class TestTrimSummarize:
    def test_abaixo_do_limite_inalterado(self):
        """Menos mensagens que o limite, retorna inalterado."""
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        resultado = trim_and_summarize_history(msgs, MODEL)
        assert len(resultado) == len(msgs)
        assert resultado == msgs

    def test_summary_fallback_quando_modelo_falha(self):
        """Quando o Ollama falha, usa texto de fallback."""
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(MAX_HISTORY_MESSAGES + 10)]
        with patch("agente_core._call_ollama_with_timeout", side_effect=Exception("Ollama offline")):
            resultado = trim_and_summarize_history(msgs, MODEL)
            # Deve ter menos mensagens que o original (resumiu)
            assert len(resultado) < len(msgs)
            # Deve ter um resumo
            resumos = [m for m in resultado if m.get("content", "").startswith("[Resumo")]
            assert len(resumos) > 0
            assert "indisponivel" in resumos[0]["content"]


# =====================================================================
# Tests: get_system_info
# =====================================================================


class TestSystemInfo:
    @patch("agente_core.platform.system", return_value="Windows")
    @patch("agente_core.platform.release", return_value="10")
    @patch("agente_core.platform.processor", return_value="Intel64")
    def test_system_info_basico(self, mock_proc, mock_release, mock_system):
        """Retorna informacoes basicas do sistema."""
        resultado = get_system_info()
        assert "Windows" in resultado
        assert "Intel64" in resultado

    @patch("agente_core.platform.system", return_value="Linux")
    @patch("agente_core.platform.release", return_value="6.5.0")
    @patch("agente_core.platform.processor", return_value="x86_64")
    def test_system_info_com_psutil(self, mock_proc, mock_release, mock_system):
        """Com psutil mockado via sys.modules."""
        # Cria um mock completo do modulo psutil
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value.percent = 60
        mock_psutil.virtual_memory.return_value.used = 8 * 1024**3
        mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
        mock_psutil.disk_usage.return_value.percent = 55
        mock_psutil.disk_usage.return_value.used = 200 * 1024**3
        mock_psutil.disk_usage.return_value.total = 500 * 1024**3

        # Usa patch.dict para substituir o psutil em sys.modules
        # Assim, 'import psutil' dentro de get_system_info() pega o mock
        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            resultado = get_system_info()
            assert "Linux" in resultado
            assert "CPU" in resultado
            assert "Memoria" in resultado
            assert "Disco" in resultado


# =====================================================================
# Tests: describe_image (sem dependencia)
# =====================================================================


class TestDescribeImage:
    def test_arquivo_inexistente(self):
        """Caminho invalido retorna mensagem de erro (nao quebra)."""
        resultado = describe_image("/tmp/foto_inexistente_xyz.jpg")
        assert isinstance(resultado, str)
        # Deve ser uma mensagem de erro, nao uma descricao
        assert "Erro" in resultado or "Instale" in resultado or "certifique" in resultado

    @patch("agente_core._call_ollama_with_timeout")
    def test_descricao_sucesso(self, mock_call):
        """Retorna descricao da imagem com sucesso."""
        mock_call.return_value = {"message": {"content": "Uma foto de um gato laranja dormindo no sofa."}}
        with patch.dict("sys.modules", {"ollama": MagicMock()}):
            resultado = describe_image("/tmp/gato.jpg")

        assert "gato" in resultado
        assert "laranja" in resultado
        # Verifica que a pergunta padrao foi enviada ao modelo
        mock_call.assert_called_once()

    @patch("agente_core._call_ollama_with_timeout")
    def test_pergunta_customizada(self, mock_call):
        """Passa pergunta personalizada para o modelo de visao."""
        mock_call.return_value = {"message": {"content": "Sim, ha uma arvore na foto."}}
        pergunta = "Ha alguma arvore na imagem?"
        with patch.dict("sys.modules", {"ollama": MagicMock()}):
            resultado = describe_image("/tmp/paisagem.jpg", pergunta)

        assert "arvore" in resultado
        # Verifica que a pergunta customizada foi passada para a API
        _, kwargs = mock_call.call_args
        messages = kwargs.get("messages", [])
        mensagem_user = messages[0] if messages else {}
        conteudo = mensagem_user.get("content", "")
        assert pergunta in conteudo

    def test_sem_ollama(self):
        """Sem ollama instalado, retorna mensagem de instalacao."""
        with patch.dict("sys.modules", {"ollama": None}):
            resultado = describe_image("/tmp/foto.jpg")

        assert "Instale" in resultado
        assert "ollama" in resultado

    @patch("agente_core._call_ollama_with_timeout")
    def test_timeout(self, mock_call):
        """Timeout do modelo de visao retorna mensagem especifica."""
        mock_call.side_effect = TimeoutError("Modelo nao respondeu a tempo")
        with patch.dict("sys.modules", {"ollama": MagicMock()}):
            resultado = describe_image("/tmp/foto.jpg")

        assert "Timeout" in resultado

    @patch("agente_core._call_ollama_with_timeout")
    def test_erro_generico(self, mock_call):
        """Erro generico retorna mensagem com sugestao de instalacao."""
        mock_call.side_effect = Exception("Falha na GPU: out of memory")
        with patch.dict("sys.modules", {"ollama": MagicMock()}):
            resultado = describe_image("/tmp/foto.jpg")

        assert "Erro" in resultado
        assert "certifique" in resultado
        assert "GPU" in resultado or "memory" in resultado


# =====================================================================
# Tests: read_pdf
# =====================================================================


class TestReadPdf:
    def test_read_pdf_sucesso(self):
        """Extrai texto de PDF com PyPDF2 mockado."""
        mock_pypdf2 = MagicMock()
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Texto da pagina 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Texto da pagina 2"
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pypdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pypdf2}):
            with patch("builtins.open"):
                resultado = read_pdf("/fake/documento.pdf")

        assert "Texto da pagina 1" in resultado
        assert "Texto da pagina 2" in resultado

    def test_read_pdf_sem_texto(self):
        """PDF sem texto extraivel retorna mensagem."""
        mock_pypdf2 = MagicMock()
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader.pages = [mock_page]
        mock_pypdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pypdf2}):
            with patch("builtins.open"):
                resultado = read_pdf("/fake/vazio.pdf")

        assert "Nao foi possivel extrair texto" in resultado

    def test_read_pdf_truncado(self):
        """Texto maior que max_chars e truncado."""
        mock_pypdf2 = MagicMock()
        mock_reader = MagicMock()
        mock_page = MagicMock()
        texto_longo = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
        mock_page.extract_text.return_value = texto_longo
        mock_reader.pages = [mock_page]
        mock_pypdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pypdf2}):
            with patch("builtins.open"):
                resultado = read_pdf("/fake/longo.pdf", max_chars=100)

        assert "[...conteudo truncado...]" in resultado
        assert len(resultado) < len(texto_longo)

    def test_read_pdf_arquivo_inexistente(self):
        """Arquivo inexistente retorna mensagem de erro."""
        mock_pypdf2 = MagicMock()
        mock_pypdf2.PdfReader.side_effect = FileNotFoundError(
            "Arquivo nao encontrado"
        )

        with patch.dict("sys.modules", {"PyPDF2": mock_pypdf2}):
            with patch("builtins.open"):
                resultado = read_pdf("/fake/inexistente.pdf")

        assert "Erro" in resultado

    def test_read_pdf_sem_pypdf2(self):
        """Sem PyPDF2 instalado, retorna mensagem de instalacao."""
        with patch.dict("sys.modules", {"PyPDF2": None}):
            resultado = read_pdf("/fake/qualquer.pdf")

        assert "Instale" in resultado
        assert "PyPDF2" in resultado


# =====================================================================
# Tests: read_image_text (OCR)
# =====================================================================


class TestReadImageText:
    def test_read_image_text_sucesso(self):
        """Extrai texto de imagem com OCR mockado."""
        mock_pil = MagicMock()
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "Texto extraido da imagem"

        with patch.dict("sys.modules", {
            "PIL": mock_pil,
            "pytesseract": mock_pytesseract,
        }):
            resultado = read_image_text("/fake/print.png")

        assert "Texto extraido da imagem" in resultado

    def test_read_image_text_sem_texto(self):
        """Imagem sem texto detectavel retorna mensagem."""
        mock_pil = MagicMock()
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "  "

        with patch.dict("sys.modules", {
            "PIL": mock_pil,
            "pytesseract": mock_pytesseract,
        }):
            resultado = read_image_text("/fake/branca.png")

        assert "Nenhum texto encontrado" in resultado

    def test_read_image_text_arquivo_inexistente(self):
        """Arquivo de imagem inexistente retorna erro."""
        mock_pil = MagicMock()
        # Simula o caminho: from PIL import Image -> mock_pil.Image
        # Image.open(path) -> mock_pil.Image.open(path) -> levanta erro
        mock_pil.Image.open.side_effect = FileNotFoundError(
            "No such file: /fake/inexistente.jpg"
        )
        mock_pytesseract = MagicMock()

        with patch.dict("sys.modules", {
            "PIL": mock_pil,
            "pytesseract": mock_pytesseract,
        }):
            resultado = read_image_text("/fake/inexistente.jpg")

        assert "Erro" in resultado

    def test_read_image_text_sem_libs(self):
        """Sem pytesseract/PIL instalados, retorna mensagem de instalacao."""
        with patch.dict("sys.modules", {
            "PIL": None,
            "pytesseract": None,
        }):
            resultado = read_image_text("/fake/qualquer.png")

        assert "Instale" in resultado
        assert "pillow" in resultado or "pytesseract" in resultado


# =====================================================================
# Tests: run_agent_turn (integracao com Ollama mockado)
# =====================================================================


def _mock_ollama_response(text: str = "", tool_calls: list = None) -> dict:
    """Helper: cria resposta no formato que ollama.chat retorna."""
    msg = {"role": "assistant", "content": text}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"message": msg}


@pytest.fixture
def mock_ollama():
    """Mocka o modulo ollama inteiro via sys.modules.
    
    O ollama e importado DENTRO de _chat_with_retries() e tambem
    dentro de trim_and_summarize_history(). Ao substituir em
    sys.modules, ambos os caminhos pegam o mock.
    """
    mock = MagicMock()
    mock.chat = MagicMock()
    with patch("agente_core.time.sleep"), \
         patch.dict("sys.modules", {"ollama": mock}):
        yield mock


class TestRunAgentTurn:
    """Testes de integracao do loop principal run_agent_turn().

    Fluxo testado:
      1. run_agent_turn() chama _chat_with_retries() que faz
         import ollama -> pega o mock
      2. mock_ollama.chat retorna respostas controladas com
         ou sem tool_calls
      3. O loop processa ferramentas, detecta repeticoes,
         respeita MAX_TOOL_ROUNDS, etc.
    """

    def test_resposta_direta_sem_ferramentas(self, mock_ollama):
        """Modelo responde apenas com texto, sem chamar ferramentas."""
        mock_ollama.chat.return_value = _mock_ollama_response(
            text="Ola! Como posso ajudar?"
        )

        messages = [{"role": "user", "content": "Oi"}]
        resultado = run_agent_turn(messages)

        # A resposta do modelo foi adicionada
        ultima = resultado[-1]
        assert ultima["role"] == "assistant"
        assert "Ola!" in ultima["content"]
        # Timestamp foi adicionado
        assert "timestamp" in ultima
        # A chamada foi feita com os argumentos esperados
        mock_ollama.chat.assert_called_once()
        # Nao ha mensagens de ferramenta
        tools = [m for m in resultado if m["role"] == "tool"]
        assert len(tools) == 0

    def test_chamada_ferramenta_unica(self, mock_ollama):
        """Modelo chama get_datetime, tool executa, modelo responde."""
        tool_call = {
            "function": {
                "name": "get_datetime",
                "arguments": "{}",
            }
        }
        mock_ollama.chat.side_effect = [
            _mock_ollama_response(tool_calls=[tool_call]),
            _mock_ollama_response(text="A data atual e 15/07/2026"),
        ]

        messages = [{"role": "user", "content": "Que dia e hoje?"}]
        resultado = run_agent_turn(messages)

        # Resposta final deve conter a data
        ultima = resultado[-1]
        assert ultima["role"] == "assistant"
        assert "15/07/2026" in ultima["content"]
        # Deve ter uma mensagem tool
        tools = [m for m in resultado if m["role"] == "tool"]
        assert len(tools) == 1
        # O resultado da tool deve ser a data (string com /)
        assert "/" in tools[0]["content"]

    def test_ferramenta_inexistente(self, mock_ollama):
        """Modelo tenta chamar ferramenta que nao existe."""
        tool_call = {
            "function": {
                "name": "nao_existe",
                "arguments": "{}",
            }
        }
        mock_ollama.chat.side_effect = [
            _mock_ollama_response(tool_calls=[tool_call]),
            _mock_ollama_response(text="Desculpe, erro de ferramenta."),
        ]

        messages = [{"role": "user", "content": "teste"}]
        resultado = run_agent_turn(messages)

        # O erro foi registrado na mensagem da ferramenta
        tools = [m for m in resultado if m["role"] == "tool"]
        assert any("nao existe" in m["content"] for m in tools)

    def test_chamada_repetida_detecta_loop(self, mock_ollama):
        """Mesma ferramenta com mesmos args gera aviso de loop."""
        tool_call = {
            "function": {
                "name": "get_datetime",
                "arguments": "{}",
            }
        }
        # Modelo insiste na mesma chamada 2x, depois responde
        mock_ollama.chat.side_effect = [
            _mock_ollama_response(tool_calls=[tool_call]),
            _mock_ollama_response(tool_calls=[tool_call]),
            _mock_ollama_response(text="Pronto, finalizado."),
        ]

        messages = [{"role": "user", "content": "teste"}]
        resultado = run_agent_turn(messages)

        # Deve haver um aviso de repeticao em alguma tool
        tools = [m for m in resultado if m["role"] == "tool"]
        assert any("ja foi feita" in m["content"] for m in tools)

    def test_max_tool_rounds_respeita_limite(self, mock_ollama):
        """Loop para apos MAX_TOOL_ROUNDS mesmo com tool_calls."""
        tool_call = {
            "function": {
                "name": "get_datetime",
                "arguments": "{}",
            }
        }
        # Mais respostas que o limite (10 > 8)
        responses = [
            _mock_ollama_response(tool_calls=[tool_call])
            for _ in range(MAX_TOOL_ROUNDS + 2)
        ]
        mock_ollama.chat.side_effect = responses

        messages = [{"role": "user", "content": "teste"}]
        resultado = run_agent_turn(messages)

        # Nao deve exceder MAX_TOOL_ROUNDS mensagens de tool
        tools = [m for m in resultado if m["role"] == "tool"]
        assert len(tools) <= MAX_TOOL_ROUNDS

    def test_erro_comunicacao_modelo(self, mock_ollama):
        """Falha na comunicacao com o modelo retorna mensagem de erro."""
        mock_ollama.chat.side_effect = Exception("Ollama offline")

        messages = [{"role": "user", "content": "Oi"}]
        resultado = run_agent_turn(messages)

        # Deve ter adicionado mensagem de erro
        ultima = resultado[-1]
        assert ultima["role"] == "assistant"
        assert "Erro" in ultima["content"] or "offline" in ultima["content"]

    def test_tool_call_argumentos_complexos(self, mock_ollama):
        """Ferramenta com argumentos (calculate) funciona."""
        tool_call = {
            "function": {
                "name": "calculate",
                "arguments": '{"expression": "2+2"}',
            }
        }
        mock_ollama.chat.side_effect = [
            _mock_ollama_response(tool_calls=[tool_call]),
            _mock_ollama_response(text="Resultado: 4"),
        ]

        messages = [{"role": "user", "content": "Quanto e 2+2?"}]
        resultado = run_agent_turn(messages)

        tools = [m for m in resultado if m["role"] == "tool"]
        assert len(tools) == 1
        assert tools[0]["content"] == "4"


# =====================================================================
# Tests: _chat_with_retries (retentativas do Ollama)
# =====================================================================


class TestChatWithRetries:
    """Testa a logica de retentativas de _chat_with_retries().

    Diferente do run_agent_turn, aqui testamos diretamente o
    comportamento de retry quando o Ollama falha temporariamente.
    """

    def test_chamada_bem_sucedida(self, mock_ollama):
        """Chamada normal retorna a resposta do modelo."""
        mock_ollama.chat.return_value = _mock_ollama_response(
            text="Resposta ok"
        )

        resultado = _chat_with_retries(
            model=MODEL,
            messages=[{"role": "user", "content": "oi"}],
            tools=[],
        )

        assert resultado["message"]["content"] == "Resposta ok"
        assert resultado["message"]["role"] == "assistant"

    def test_retry_apos_timeout(self, mock_ollama):
        """Timeout na primeira tentativa, retry bem sucedido."""
        mock_ollama.chat.side_effect = [
            TimeoutError("Simulated timeout"),
            _mock_ollama_response(text="Resposta apos timeout"),
        ]

        resultado = _chat_with_retries(
            model=MODEL,
            messages=[{"role": "user", "content": "oi"}],
            tools=[],
        )

        assert resultado["message"]["content"] == "Resposta apos timeout"
        # Deve ter tentado 2 vezes
        assert mock_ollama.chat.call_count == 2

    def test_todas_tentativas_falham(self, mock_ollama):
        """Todas as retentativas falham, levanta RuntimeError."""
        # OLLAMA_MAX_RETRIES = 2, entao tenta 3 vezes (1 + 2)
        mock_ollama.chat.side_effect = [
            TimeoutError("Timeout 1"),
            TimeoutError("Timeout 2"),
            TimeoutError("Timeout 3"),
        ]

        with pytest.raises(RuntimeError) as excinfo:
            _chat_with_retries(
                model=MODEL,
                messages=[{"role": "user", "content": "oi"}],
                tools=[],
            )

        assert "Nao consegui falar" in str(excinfo.value)
        assert mock_ollama.chat.call_count == OLLAMA_MAX_RETRIES + 1

    def test_clean_messages_filtra_campos_extras(self, mock_ollama):
        """Mensagens com campos extras (timestamp) sao limpas."""
        mock_ollama.chat.return_value = _mock_ollama_response(
            text="Resposta"
        )

        # Mensagem com timestamp (que o Ollama nao aceitaria)
        messages = [
            {
                "role": "user",
                "content": "oi",
                "timestamp": "15/07/2026 10:00:00",
            }
        ]
        _chat_with_retries(model=MODEL, messages=messages, tools=[])

        # Verifica que a mensagem enviada ao chat foi limpa
        chamada_kwargs = mock_ollama.chat.call_args.kwargs
        mensagens_enviadas = chamada_kwargs["messages"]
        assert "timestamp" not in mensagens_enviadas[0]
        assert mensagens_enviadas[0]["role"] == "user"
        assert mensagens_enviadas[0]["content"] == "oi"


# =====================================================================
# Execucao direta
# =====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
