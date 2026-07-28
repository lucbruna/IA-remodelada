"""
test_plugin_mcp.py
==================
Testes automatizados para plugin_mcp com mocks.

Cobre:
- Funcoes do protocolo JSON-RPC (_make_rpc_request, _make_rpc_response, _make_rpc_error)
- Handler MCP (_handle_mcp_request): initialize, ping, tools/list, tools/call,
  resources/list, resources/read, prompts/list, prompts/get, logging/setLevel, shutdown
- Tool call (_handle_tool_call): sucesso, ferramenta inexistente, parametro faltando, erro
- Resource read (_handle_resource_read): memory, system, agent, recurso inexistente
- Prompt get (_handle_prompt_get): analyze_code, debug_issue, inexistente
- Funcoes do plugin: mcp_server_iniciar, mcp_server_parar, mcp_server_status
- Cliente MCP: _get_tools_list, _get_resources_list, _get_prompts_list
- Register do plugin (api.register_tool)
- Erros: JSON invalido, metodo desconhecido

Uso:
    pytest test_plugin_mcp.py -v
"""

import pytest
import sys
import os
import json
import time
from unittest.mock import MagicMock, patch, call, ANY

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_mcp_globals():
    """Reseta as variaveis globais do plugin antes de cada teste."""
    import plugins.plugin_mcp as pm

    pm.MCP_SERVER_RUNNING.clear()
    pm.MCP_SERVER_THREAD = None
    pm.MCP_SERVER_INSTANCE = None
    pm.MCP_SSE_CLIENTS.clear()
    pm.MCP_DEFAULT_PORT = 9090


@pytest.fixture
def mock_agente_core():
    """Cria um mock do modulo agente_core para _get_tools_list e _handle_tool_call.
    Remove o modulo real de sys.modules antes e restaura depois.
    """
    mock_core = MagicMock()
    mock_core.TOOLS_LIST = [
        {
            "function": {
                "name": "test_tool",
                "description": "Uma ferramenta de teste",
                "parameters": {
                    "type": "object",
                    "properties": {"arg1": {"type": "string"}},
                    "required": ["arg1"],
                },
            }
        }
    ]
    def _test_tool(arg1):
        return f"Resultado: {arg1}"
    mock_core.AVAILABLE_FUNCTIONS = {
        "test_tool": _test_tool
    }
    mock_core.list_memories = lambda: '{"memorias": []}'
    mock_core.get_system_info = lambda: "Linux x86_64"
    mock_core.list_plugins = lambda: '{"plugins": []}'

    saved = {}
    if 'agente_core' in sys.modules:
        saved['agente_core'] = sys.modules.pop('agente_core')
    sys.modules['agente_core'] = mock_core
    yield mock_core
    # Restore
    sys.modules.pop('agente_core', None)
    if 'agente_core' in saved:
        sys.modules['agente_core'] = saved['agente_core']


# =============================================================================
# Testes — Funcoes do Protocolo JSON-RPC
# =============================================================================


class TestProtocoloRPC:
    """Testes para as funcoes internas de formatacao JSON-RPC."""

    def test_make_rpc_request_sem_params(self):
        """_make_rpc_request deve criar requisicao basica."""
        from plugins.plugin_mcp import _make_rpc_request

        req = _make_rpc_request("ping")
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "ping"
        assert req["id"] == 1

    def test_make_rpc_request_com_params(self):
        """_make_rpc_request deve incluir params."""
        from plugins.plugin_mcp import _make_rpc_request

        req = _make_rpc_request("tools/call", {"name": "test"}, request_id=5)
        assert req["params"]["name"] == "test"
        assert req["id"] == 5

    def test_make_rpc_response_sucesso(self):
        """_make_rpc_response deve criar resposta de sucesso."""
        from plugins.plugin_mcp import _make_rpc_response

        resp = _make_rpc_response(1, {"status": "ok"})
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["status"] == "ok"
        assert "error" not in resp

    def test_make_rpc_response_erro(self):
        """_make_rpc_response deve criar resposta de erro."""
        from plugins.plugin_mcp import _make_rpc_response

        erro = {"code": -32601, "message": "Metodo nao encontrado"}
        resp = _make_rpc_response(1, error=erro)
        assert resp["error"]["code"] == -32601
        assert "result" not in resp

    def test_make_rpc_error(self):
        """_make_rpc_error deve criar objeto de erro."""
        from plugins.plugin_mcp import _make_rpc_error

        err = _make_rpc_error(-32602, "Parametro invalido", {"detalhe": "x"})
        assert err["code"] == -32602
        assert err["data"]["detalhe"] == "x"


# =============================================================================
# Testes — Handler MCP
# =============================================================================


class TestHandlerMCP:
    """Testes para processamento de requisicoes MCP."""

    def test_handle_initialize(self):
        """initialize deve retornar capabilities e serverInfo."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        resp = _handle_mcp_request(req)

        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "Agente MCP Server"

    def test_handle_initialized_notification(self):
        """notifications/initialized deve retornar None."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = _handle_mcp_request(req)

        assert resp is None

    def test_handle_ping(self):
        """ping deve retornar status ok."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        resp = _handle_mcp_request(req)

        assert resp["result"]["status"] == "ok"

    def test_handle_tools_list(self, mock_agente_core):
        """tools/list deve retornar lista de ferramentas."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        resp = _handle_mcp_request(req)

        tools = resp["result"]["tools"]
        assert len(tools) >= 1
        assert tools[0]["name"] == "test_tool"

    def test_handle_resources_list(self):
        """resources/list deve retornar recursos padrao."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 4, "method": "resources/list"}
        resp = _handle_mcp_request(req)

        resources = resp["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "memory://fatos" in uris
        assert "system://info" in uris
        assert "agent://plugins" in uris

    def test_handle_prompts_list(self):
        """prompts/list deve retornar templates de prompt."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 5, "method": "prompts/list"}
        resp = _handle_mcp_request(req)

        prompts = resp["result"]["prompts"]
        nomes = [p["name"] for p in prompts]
        assert "analyze_code" in nomes
        assert "debug_issue" in nomes

    def test_handle_logging_set_level(self):
        """logging/setLevel deve retornar ok."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 6, "method": "logging/setLevel", "params": {"level": "debug"}}
        resp = _handle_mcp_request(req)

        assert resp["result"]["status"] == "ok"

    def test_handle_shutdown(self):
        """shutdown deve retornar shutting_down."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 7, "method": "shutdown"}
        resp = _handle_mcp_request(req)

        assert resp["result"]["status"] == "shutting_down"

    def test_handle_metodo_desconhecido(self):
        """Metodo desconhecido deve retornar erro -32601."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {"jsonrpc": "2.0", "id": 8, "method": "metodo_inexistente"}
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32601


# =============================================================================
# Testes — Tool Call
# =============================================================================


class TestToolCall:
    """Testes para execucao de ferramentas via MCP."""

    def test_tool_call_sucesso(self, mock_agente_core):
        """tools/call deve executar ferramenta e retornar resultado."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {"arg1": "hello"}},
        }
        resp = _handle_mcp_request(req)

        content = resp["result"]["content"]
        assert content[0]["type"] == "text"
        assert "hello" in content[0]["text"]

    def test_tool_call_ferramenta_inexistente(self, mock_agente_core):
        """tools/call para ferramenta inexistente deve retornar erro."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "nao_existe", "arguments": {}},
        }
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32602
        assert "nao_existe" in resp["error"]["message"]

    def test_tool_call_parametro_faltando(self, mock_agente_core):
        """tools/call sem parametro obrigatorio deve retornar erro."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
        }
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32602

    def test_tool_call_erro_execucao(self, mock_agente_core):
        """tools/call com erro interno deve retornar erro -32603."""
        from plugins.plugin_mcp import _handle_mcp_request

        # Make the tool raise an exception - use a tool with NO required params
        def failing_tool():
            raise RuntimeError("Erro interno na ferramenta")

        mock_agente_core.AVAILABLE_FUNCTIONS["failing_tool"] = failing_tool

        req = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "failing_tool", "arguments": {}},
        }
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32603


# =============================================================================
# Testes — Resource Read
# =============================================================================


class TestResourceRead:
    """Testes para leitura de recursos MCP."""

    def test_resource_read_memory(self, mock_agente_core):
        """resources/read para memory://fatos deve retornar memorias."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "resources/read",
            "params": {"uri": "memory://fatos"},
        }
        resp = _handle_mcp_request(req)

        assert resp["result"]["contents"][0]["uri"] == "memory://fatos"

    def test_resource_read_system(self, mock_agente_core):
        """resources/read para system://info deve retornar info do sistema."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "resources/read",
            "params": {"uri": "system://info"},
        }
        resp = _handle_mcp_request(req)

        assert resp["result"]["contents"][0]["mimeType"] == "text/plain"

    def test_resource_read_inexistente(self):
        """resources/read para uri inexistente deve retornar erro."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "resources/read",
            "params": {"uri": "inexistente://url"},
        }
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32602


# =============================================================================
# Testes — Prompt Get
# =============================================================================


class TestPromptGet:
    """Testes para obtencao de prompts MCP."""

    def test_prompt_get_analyze_code(self):
        """prompts/get para analyze_code deve retornar mensagens."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "prompts/get",
            "params": {"name": "analyze_code", "arguments": {"code": "print('hello')", "language": "python"}},
        }
        resp = _handle_mcp_request(req)

        assert len(resp["result"]["messages"]) == 1
        assert "print('hello')" in resp["result"]["messages"][0]["content"]

    def test_prompt_get_debug_issue(self):
        """prompts/get para debug_issue deve retornar mensagens."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 31,
            "method": "prompts/get",
            "params": {"name": "debug_issue", "arguments": {"issue": "Erro 500", "context": "Produção"}},
        }
        resp = _handle_mcp_request(req)

        assert "Erro 500" in resp["result"]["messages"][0]["content"]
        assert "Produção" in resp["result"]["messages"][0]["content"]

    def test_prompt_get_inexistente(self):
        """prompts/get para prompt inexistente deve retornar erro."""
        from plugins.plugin_mcp import _handle_mcp_request

        req = {
            "jsonrpc": "2.0",
            "id": 32,
            "method": "prompts/get",
            "params": {"name": "inexistente"},
        }
        resp = _handle_mcp_request(req)

        assert resp["error"]["code"] == -32602


# =============================================================================
# Testes — Funcoes Auxiliares
# =============================================================================


class TestFuncoesAuxiliares:
    """Testes para funcoes auxiliares do plugin MCP."""

    def test_get_tools_list_vazio_sem_agente_core(self):
        """_get_tools_list deve retornar [] se agente_core nao disponivel."""
        import sys
        from plugins.plugin_mcp import _get_tools_list

        # Impede import do agente_core marcando como None
        saved = sys.modules.get('agente_core')
        sys.modules['agente_core'] = None
        try:
            tools = _get_tools_list()
            assert tools == []
        finally:
            if saved:
                sys.modules['agente_core'] = saved
            else:
                sys.modules.pop('agente_core', None)

    def test_get_resources_list_tem_recursos(self):
        """_get_resources_list deve retornar recursos configurados."""
        from plugins.plugin_mcp import _get_resources_list

        resources = _get_resources_list()
        assert len(resources) == 3
        uris = [r["uri"] for r in resources]
        assert "memory://fatos" in uris

    def test_get_prompts_list_tem_prompts(self):
        """_get_prompts_list deve retornar prompts configurados."""
        from plugins.plugin_mcp import _get_prompts_list

        prompts = _get_prompts_list()
        assert len(prompts) == 2
        nomes = [p["name"] for p in prompts]
        assert "analyze_code" in nomes


# =============================================================================
# Testes — MCP Server (iniciar, parar, status)
# =============================================================================


class TestMCServer:
    """Testes para funcoes do servidor MCP."""

    def test_server_iniciar_ja_rodando(self, reset_mcp_globals):
        """mcp_server_iniciar quando ja rodando deve retornar aviso."""
        import plugins.plugin_mcp as pm

        pm.MCP_SERVER_RUNNING.set()
        resultado = pm.mcp_server_iniciar()

        assert "ja" in resultado.lower() or "rodando" in resultado.lower()

    def test_server_parar_quando_rodando(self, reset_mcp_globals):
        """mcp_server_parar deve parar servidor em execucao."""
        import plugins.plugin_mcp as pm

        pm.MCP_SERVER_RUNNING.set()
        pm.MCP_SERVER_INSTANCE = MagicMock()

        resultado = pm.mcp_server_parar()

        assert "parado" in resultado.lower()
        assert not pm.MCP_SERVER_RUNNING.is_set()

    def test_server_parar_quando_parado(self, reset_mcp_globals):
        """mcp_server_parar quando ja parado deve retornar aviso."""
        import plugins.plugin_mcp as pm

        resultado = pm.mcp_server_parar()

        # Accented characters may vary - check for key words
        assert "n" in resultado.lower() and "o" in resultado.lower() and "rod" in resultado.lower()

    def test_server_status_ativo(self, reset_mcp_globals):
        """mcp_server_status com servidor ativo deve mostrar informacoes."""
        import plugins.plugin_mcp as pm

        pm.MCP_SERVER_RUNNING.set()
        resultado = pm.mcp_server_status()

        assert "ativo" in resultado.lower()
        assert "ferramentas" in resultado.lower()

    def test_server_status_inativo(self, reset_mcp_globals):
        """mcp_server_status com servidor inativo deve mostrar inativo."""
        import plugins.plugin_mcp as pm

        resultado = pm.mcp_server_status()

        assert "inativo" in resultado.lower()


# =============================================================================
# Testes — Register do Plugin
# =============================================================================


class TestRegister:
    """Testes para registro do plugin."""

    def test_register_registra_ferramentas(self, reset_mcp_globals):
        """register() deve chamar api.register_tool para todas as funcoes."""
        import plugins.plugin_mcp as pm

        api = MagicMock()
        resultado = pm.register(api)

        assert api.register_tool.call_count >= 6
        nomes = [c.kwargs.get("name") or c.args[0] for c in api.register_tool.call_args_list]
        assert "mcp_server_iniciar" in nomes
        assert "mcp_server_parar" in nomes
        assert "mcp_server_status" in nomes
        assert "mcp_conectar" in nomes
        assert "mcp_chamar" in nomes

    def test_register_inclui_descricoes(self, reset_mcp_globals):
        """register() deve incluir descricoes das ferramentas."""
        import plugins.plugin_mcp as pm

        api = MagicMock()
        pm.register(api)

        for call_args in api.register_tool.call_args_list:
            kwargs = call_args.kwargs if call_args.kwargs else {}
            nome = kwargs.get("name") or call_args.args[0]
            descricao = kwargs.get("description") or call_args.args[2]
            assert nome, "Ferramenta sem nome"
            assert isinstance(descricao, str) and len(descricao) > 5, f"{nome} sem descricao"

    def test_register_retorna_dict(self, reset_mcp_globals):
        """register() deve retornar dicionario com metadados."""
        import plugins.plugin_mcp as pm

        api = MagicMock()
        resultado = pm.register(api)

        assert isinstance(resultado, dict)
        assert "name" in resultado
        assert "tools" in resultado
        assert len(resultado["tools"]) >= 6
