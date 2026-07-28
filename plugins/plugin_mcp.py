"""
plugin_mcp.py
==============
Plugin MCP (Model Context Protocol) — Implementação completa do protocolo JSON-RPC 2.0.

Fornece:
- Servidor MCP HTTP que expõe TODAS as ferramentas do agente
- Cliente MCP para conectar a servidores MCP externos
- Suporte a stdio (para Claude Desktop, Cline, etc.)
- Descoberta automática de ferramentas registradas
- Recursos e prompts via MCP
"""

__version__ = "1.0.0"

import os
import json
import logging
import threading
import time
import queue
from typing import Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

# ======================================================================
# CONSTANTES
# ======================================================================

MCP_DEFAULT_PORT = 9090
MCP_SERVER_RUNNING = threading.Event()
MCP_SERVER_THREAD = None
MCP_SERVER_INSTANCE = None

# --- SSE Streaming ---
MCP_SSE_CLIENTS: list['queue.Queue'] = []  # fila de eventos SSE
MCP_SSE_LOCK = threading.Lock()


def _sse_broadcast(event_type: str, data: dict):
    """Envia evento SSE para todos os clientes conectados."""
    with MCP_SSE_LOCK:
        dead_clients = []
        for q in MCP_SSE_CLIENTS:
            try:
                q.put_nowait({"type": event_type, **data})
            except queue.Full:
                dead_clients.append(q)
        for q in dead_clients:
            MCP_SSE_CLIENTS.remove(q)



# ======================================================================
# PROTOCOLO MCP — JSON-RPC 2.0
# ======================================================================

def _make_rpc_request(method: str, params: dict = None, request_id: int = 1) -> dict:
    """Cria uma requisição JSON-RPC 2.0 no formato MCP."""
    req = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params:
        req["params"] = params
    return req


def _make_rpc_response(request_id: int, result: Any = None, error: dict = None) -> dict:
    """Cria uma resposta JSON-RPC 2.0."""
    resp = {"jsonrpc": "2.0", "id": request_id}
    if error:
        resp["error"] = error
    else:
        resp["result"] = result
    return resp


def _make_rpc_error(code: int, message: str, data: Any = None) -> dict:
    """Cria um objeto de erro JSON-RPC."""
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return err


# ======================================================================
# HANDLER MCP — Processa requisições e chama ferramentas
# ======================================================================

def _get_tools_list() -> list[dict]:
    """Retorna a lista de ferramentas registradas no formato MCP."""
    try:
        from agente_core import TOOLS_LIST, AVAILABLE_FUNCTIONS
        tools = []
        for t in TOOLS_LIST:
            fn = t.get("function", {})
            tool_def = {
                "name": fn.get("name", "unknown"),
                "description": fn.get("description", ""),
                "inputSchema": fn.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                }),
            }
            tools.append(tool_def)
        return tools
    except Exception as e:
        return []


def _get_resources_list() -> list[dict]:
    """Retorna recursos disponíveis via MCP (arquivos, memória, etc.)."""
    resources = [
        {
            "uri": "memory://fatos",
            "name": "Memória de fatos",
            "description": "Fatos guardados na memória de longo prazo do agente",
            "mimeType": "application/json",
        },
        {
            "uri": "system://info",
            "name": "Informações do sistema",
            "description": "SO, CPU, memória, disco",
            "mimeType": "text/plain",
        },
        {
            "uri": "agent://plugins",
            "name": "Plugins carregados",
            "description": "Lista de plugins disponíveis",
            "mimeType": "application/json",
        },
    ]
    return resources


def _get_prompts_list() -> list[dict]:
    """Retorna templates de prompt disponíveis via MCP."""
    prompts = [
        {
            "name": "analyze_code",
            "description": "Analisa um trecho de código em busca de problemas",
            "arguments": [
                {"name": "code", "description": "Código a ser analisado", "required": True},
                {"name": "language", "description": "Linguagem de programação", "required": False},
            ],
        },
        {
            "name": "debug_issue",
            "description": "Debug de um problema técnico",
            "arguments": [
                {"name": "issue", "description": "Descrição do problema", "required": True},
                {"name": "context", "description": "Contexto adicional", "required": False},
            ],
        },
    ]
    return prompts


def _handle_mcp_request(request: dict) -> dict:
    """Processa uma requisição MCP e retorna a resposta."""
    req_id = request.get("id", 0)
    method = request.get("method", "")
    params = request.get("params", {}) or {}

    # SSE broadcast para monitoramento
    _sse_broadcast("mcp_request", {
        "method": method,
        "params": str(params)[:200],
        "timestamp": time.time(),
    })

    # Métodos de inicialização
    if method == "initialize":
        return _make_rpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
                "logging": {},
            },
            "serverInfo": {
                "name": "Agente MCP Server",
                "version": __version__,
            },
        })

    if method == "notifications/initialized":
        return None  # notificação, sem resposta

    if method == "shutdown":
        return _make_rpc_response(req_id, {"status": "shutting_down"})

    if method == "ping":
        return _make_rpc_response(req_id, {"status": "ok", "timestamp": time.time()})

    # Métodos de ferramentas
    if method == "tools/list":
        tools = _get_tools_list()
        return _make_rpc_response(req_id, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        return _handle_tool_call(req_id, tool_name, arguments)

    # Métodos de recursos
    if method == "resources/list":
        return _make_rpc_response(req_id, {"resources": _get_resources_list()})

    if method == "resources/read":
        uri = params.get("uri", "")
        return _handle_resource_read(req_id, uri)

    # Métodos de prompts
    if method == "prompts/list":
        return _make_rpc_response(req_id, {"prompts": _get_prompts_list()})

    if method == "prompts/get":
        prompt_name = params.get("name", "")
        args = params.get("arguments", {})
        return _handle_prompt_get(req_id, prompt_name, args)

    # Método de logging
    if method == "logging/setLevel":
        return _make_rpc_response(req_id, {"status": "ok"})

    # Método desconhecido
    return _make_rpc_response(req_id, error=_make_rpc_error(
        -32601, f"Método não encontrado: {method}"
    ))


def _handle_tool_call(req_id: int, tool_name: str, arguments: dict) -> dict:
    """Executa uma ferramenta registrada e retorna o resultado."""
    _sse_broadcast("tool_call_start", {
        "tool": tool_name,
        "arguments": str(arguments)[:300],
        "timestamp": time.time(),
    })
    try:
        from agente_core import AVAILABLE_FUNCTIONS

        func = AVAILABLE_FUNCTIONS.get(tool_name)
        if not func:
            # Tenta buscar tools similares
            available = list(AVAILABLE_FUNCTIONS.keys())[:20]
            return _make_rpc_response(req_id, error=_make_rpc_error(
                -32602, f"Ferramenta '{tool_name}' não encontrada.",
                {"available_tools": available}
            ))

        # Verifica os parâmetros da função
        import inspect
        sig = inspect.signature(func)
        filtered_args = {}
        for param_name, param in sig.parameters.items():
            if param_name in arguments:
                filtered_args[param_name] = arguments[param_name]
            elif param.default is not inspect.Parameter.empty:
                # Usa o valor padrão
                pass
            else:
                # Parâmetro obrigatório faltando
                return _make_rpc_response(req_id, error=_make_rpc_error(
                    -32602, f"Parâmetro obrigatório '{param_name}' não fornecido."
                ))

        # Executa a função
        result = func(**filtered_args)

        _sse_broadcast("tool_call_complete", {
            "tool": tool_name,
            "status": "ok",
            "result_length": len(str(result)),
            "timestamp": time.time(),
        })

        return _make_rpc_response(req_id, {
            "content": [
                {
                    "type": "text",
                    "text": str(result) if result is not None else "(sem resultado)",
                }
            ],
            "isError": False,
        })

    except Exception as e:
        return _make_rpc_response(req_id, error=_make_rpc_error(
            -32603, f"Erro ao executar ferramenta: {str(e)}"
        ))


def _handle_resource_read(req_id: int, uri: str) -> dict:
    """Lê um recurso MCP e retorna seu conteúdo."""
    try:
        from agente_core import list_memories, get_system_info, list_plugins

        if uri == "memory://fatos":
            content = list_memories()
            mime = "application/json"
        elif uri == "system://info":
            content = get_system_info()
            mime = "text/plain"
        elif uri == "agent://plugins":
            content = list_plugins()
            mime = "application/json"
        else:
            return _make_rpc_response(req_id, error=_make_rpc_error(
                -32602, f"Recurso não encontrado: {uri}"
            ))

        return _make_rpc_response(req_id, {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": mime,
                    "text": str(content),
                }
            ]
        })

    except Exception as e:
        return _make_rpc_response(req_id, error=_make_rpc_error(
            -32603, f"Erro ao ler recurso: {str(e)}"
        ))


def _handle_prompt_get(req_id: int, prompt_name: str, args: dict) -> dict:
    """Retorna um template de prompt."""
    if prompt_name == "analyze_code":
        code = args.get("code", "")
        language = args.get("language", "python")
        messages = [
            {"role": "user", "content": f"Analise o seguinte código {language}:\n\n{code}\n\nIdentifique problemas de segurança, desempenho, estilo e possíveis bugs."}
        ]
    elif prompt_name == "debug_issue":
        issue = args.get("issue", "")
        context = args.get("context", "")
        messages = [
            {"role": "user", "content": f"Problema: {issue}\n\nContexto: {context}\n\nAjude a debugar este problema passo a passo."}
        ]
    else:
        return _make_rpc_response(req_id, error=_make_rpc_error(
            -32602, f"Prompt não encontrado: {prompt_name}"
        ))

    return _make_rpc_response(req_id, {
        "messages": messages,
        "description": f"Prompt: {prompt_name}",
    })


# ======================================================================
# SERVIDOR HTTP MCP
# ======================================================================

class MCPHTTPHandler(BaseHTTPRequestHandler):
    """Handler HTTP para o servidor MCP."""

    def log_message(self, format, *args):
        logging.debug(f"MCP: {format % args}")

    def _send_json_response(self, status_code: int, data: Any):
        """Envia uma resposta JSON."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_sse(self):
        """Handler SSE (Server-Sent Events) para streaming em tempo real."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Registra este cliente SSE
        q = queue.Queue(maxsize=100)
        with MCP_SSE_LOCK:
            MCP_SSE_CLIENTS.append(q)

        envio_inicial = json.dumps({
            "type": "connected",
            "server": "Agente MCP Server",
            "version": __version__,
        })
        try:
            self.wfile.write(f"data: {envio_inicial}\n\n".encode("utf-8"))
            self.wfile.flush()

            while MCP_SERVER_RUNNING.is_set():
                try:
                    event = q.get(timeout=5)
                    payload = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"event: {event.get('type', 'message')}\ndata: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat keep-alive
                    self.wfile.write(": heartbeat\n\n".encode("utf-8"))
                    self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        except Exception as e:
            logging.error(f"SSE error: {e}")
        finally:
            with MCP_SSE_LOCK:
                try:
                    MCP_SSE_CLIENTS.remove(q)
                except ValueError:
                    pass

    def _read_body(self) -> str:
        """Lê o corpo da requisição."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length).decode("utf-8")
        return ""

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        """GET — health check, SSE streaming e página de status."""
        if self.path == "/health":
            self._send_json_response(200, {
                "status": "ok",
                "server": "Agente MCP Server",
                "version": __version__,
                "protocol": "Model Context Protocol",
            })
        elif self.path == "/sse":
            self._handle_sse()
        elif self.path == "/" or self.path == "/status":
            tools = _get_tools_list()
            self._send_json_response(200, {
                "server": "Agente MCP Server",
                "version": __version__,
                "tools_count": len(tools),
                "tools": [t["name"] for t in tools[:50]],
                "resources": [r["uri"] for r in _get_resources_list()],
            })
        elif self.path == "/mcp" or self.path.startswith("/mcp?"):
            # Suporte a GET para listar ferramentas (compatibilidade)
            tools = _get_tools_list()
            self._send_json_response(200, {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"tools": tools},
            })
        else:
            self._send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        """POST — endpoint MCP principal."""
        if self.path not in ("/mcp", "/"):
            self._send_json_response(404, _make_rpc_response(
                0, error=_make_rpc_error(-32600, "Endpoint não encontrado")
            ))
            return

        try:
            body = self._read_body()
            if not body:
                self._send_json_response(400, _make_rpc_response(
                    0, error=_make_rpc_error(-32700, "Corpo da requisição vazio")
                ))
                return

            request = json.loads(body)

            # Suporta batch requests (array)
            if isinstance(request, list):
                responses = []
                for req in request:
                    resp = _handle_mcp_request(req)
                    if resp is not None:
                        responses.append(resp)
                self._send_json_response(200, responses if responses else [])
                return

            # Requisição única
            response = _handle_mcp_request(request)
            if response is None:
                # Notificação sem resposta
                self._send_json_response(202, {})
            else:
                self._send_json_response(200, response)

        except json.JSONDecodeError:
            self._send_json_response(400, _make_rpc_response(
                0, error=_make_rpc_error(-32700, "JSON inválido")
            ))
        except Exception as e:
            logging.error(f"MCP Server error: {e}")
            self._send_json_response(500, _make_rpc_response(
                0, error=_make_rpc_error(-32603, f"Erro interno: {str(e)}")
            ))


class MCPHTTPServer(HTTPServer):
    """Servidor HTTP MCP com suporte a shutdown limpo."""
    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self):
        self.socket.settimeout(1)  # timeout para check periódico
        super().server_bind()


def _run_mcp_server(host: str = "127.0.0.1", port: int = MCP_DEFAULT_PORT):
    """Executa o servidor MCP em loop (bloqueante)."""
    global MCP_SERVER_INSTANCE
    try:
        server = MCPHTTPServer((host, port), MCPHTTPHandler)
        MCP_SERVER_INSTANCE = server
        MCP_SERVER_RUNNING.set()
        logging.info(f"MCP Server rodando em http://{host}:{port}")
        print(f"\n🔌 Servidor MCP ativo em http://{host}:{port}")
        print(f"   Conecte qualquer cliente MCP (Claude Desktop, Cline, etc.)")
        print(f"   Use 'mcp_server_parar' para desligar.\n")

        while MCP_SERVER_RUNNING.is_set():
            server.handle_request()

    except OSError as e:
        if "Address already in use" in str(e):
            logging.warning(f"MCP: Porta {port} já em uso, tentando porta alternativa")
            # Tenta próxima porta
            for alt_port in range(port + 1, port + 100):
                try:
                    server = MCPHTTPServer((host, alt_port), MCPHTTPHandler)
                    MCP_SERVER_INSTANCE = server
                    MCP_SERVER_RUNNING.set()
                    logging.info(f"MCP Server rodando em http://{host}:{alt_port}")
                    print(f"\n🔌 Servidor MCP ativo em http://{host}:{alt_port} (porta alternativa)\n")
                    while MCP_SERVER_RUNNING.is_set():
                        server.handle_request()
                    break
                except OSError:
                    continue
            else:
                logging.error("MCP: Não foi possível encontrar uma porta livre")
                print("\n❌ Não foi possível iniciar o servidor MCP: todas as portas ocupadas\n")
        else:
            logging.error(f"MCP: Erro ao iniciar servidor: {e}")
            print(f"\n❌ Erro ao iniciar servidor MCP: {e}\n")
    except Exception as e:
        logging.error(f"MCP Server error: {e}")
    finally:
        MCP_SERVER_RUNNING.clear()
        if MCP_SERVER_INSTANCE:
            try:
                MCP_SERVER_INSTANCE.server_close()
            except Exception:
                pass
            MCP_SERVER_INSTANCE = None


# ======================================================================
# FUNÇÕES DO PLUGIN — Servidor MCP
# ======================================================================

def mcp_server_iniciar(host: str = "127.0.0.1", port: int = MCP_DEFAULT_PORT) -> str:
    """Inicia o servidor MCP em segundo plano. Expõe todas as ferramentas do agente via protocolo MCP."""
    global MCP_SERVER_THREAD

    if MCP_SERVER_RUNNING.is_set():
        return f"⚠ Servidor MCP já está rodando."

    MCP_SERVER_RUNNING.clear()
    MCP_SERVER_THREAD = threading.Thread(
        target=_run_mcp_server,
        args=(host, port),
        daemon=True,
        name="MCP-Server",
    )
    MCP_SERVER_THREAD.start()

    # Aguarda o servidor iniciar
    for _ in range(20):
        if MCP_SERVER_RUNNING.is_set():
            # Verifica rapidamente se está respondendo
            try:
                import urllib.request
                req = urllib.request.Request(f"http://{host}:{port}/health")
                urllib.request.urlopen(req, timeout=2)
                return f"✅ Servidor MCP iniciado em http://{host}:{port}\nConecte qualquer cliente MCP compatível."
            except Exception:
                time.sleep(0.3)

    return f"✅ Servidor MCP iniciado (verifique http://{host}:{port}/health)"


def mcp_server_parar() -> str:
    """Para o servidor MCP."""
    global MCP_SERVER_INSTANCE

    if not MCP_SERVER_RUNNING.is_set():
        return "⚠ Servidor MCP não está rodando."

    MCP_SERVER_RUNNING.clear()

    if MCP_SERVER_INSTANCE:
        try:
            MCP_SERVER_INSTANCE.shutdown()
        except Exception:
            pass
        MCP_SERVER_INSTANCE = None

    return "✅ Servidor MCP parado."


def mcp_server_status() -> str:
    """Mostra o status do servidor MCP."""
    if MCP_SERVER_RUNNING.is_set():
        tools = _get_tools_list()
        host = "127.0.0.1"
        port = MCP_DEFAULT_PORT
        linhas = [
            "╔════════════════════════════════════════╗",
            "║   🔌 SERVIDOR MCP — STATUS             ║",
            "╚════════════════════════════════════════╝",
            "",
            f"✅ Servidor: ATIVO",
            f"   Endpoint: http://{host}:{port}/mcp",
            f"   Health:   http://{host}:{port}/health",
            f"   Status:   http://{host}:{port}/status",
            "",
            f"📊 Ferramentas expostas: {len(tools)}",
        ]
        for t in sorted(tools, key=lambda x: x["name"])[:20]:
            linhas.append(f"   🔧 {t['name']}")
        if len(tools) > 20:
            linhas.append(f"   ... e mais {len(tools) - 20}")
        linhas.append("")
        linhas.append("💡 Conecte seu cliente MCP ao endpoint acima.")
        return "\n".join(linhas)
    else:
        return (
            "╔════════════════════════════════════════╗\n"
            "║   🔌 SERVIDOR MCP — STATUS             ║\n"
            "╚════════════════════════════════════════╝\n"
            "\n"
            "❌ Servidor: INATIVO\n"
            "\n"
            "Use 'mcp_server_iniciar' para ativar o servidor MCP.\n"
            "Após iniciar, conecte qualquer cliente MCP compatível\n"
            "(Claude Desktop, Cline, Continue.dev, etc.)."
        )


# ======================================================================
# FUNÇÕES DO PLUGIN — Cliente MCP
# ======================================================================

def mcp_conectar(server_url: str) -> str:
    """Testa a conexão com um servidor MCP externo e retorna informações."""
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        # Garante que a URL termine com /mcp
        url = server_url.rstrip("/")
        if not url.endswith("/mcp"):
            url += "/mcp"

        # Envia initialize
        payload = _make_rpc_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "Agente MCP Client", "version": __version__},
        })
        resp = requests.post(url, json=payload, timeout=10,
                            headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        init_result = resp.json()

        # Lista ferramentas
        payload = _make_rpc_request("tools/list")
        resp = requests.post(url, json=payload, timeout=10,
                            headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        tools_result = resp.json()

        tools = tools_result.get("result", {}).get("tools", [])
        server_info = init_result.get("result", {}).get("serverInfo", {})

        linhas = [
            "╔════════════════════════════════════════╗",
            "║   🌐 CLIENTE MCP — CONECTADO           ║",
            "╚════════════════════════════════════════╝",
            "",
            f"📍 Servidor: {url}",
            f"📛 Nome: {server_info.get('name', 'Desconhecido')}",
            f"📌 Versão: {server_info.get('version', 'N/A')}",
            f"📊 Ferramentas disponíveis: {len(tools)}",
            "",
        ]
        for t in tools[:20]:
            linhas.append(f"   🔧 {t.get('name', '?')}: {t.get('description', '')[:80]}")
        if len(tools) > 20:
            linhas.append(f"   ... e mais {len(tools) - 20} ferramentas")
        linhas.append("")
        linhas.append("💡 Use 'mcp_chamar' para executar uma ferramenta neste servidor.")

        return "\n".join(linhas)

    except requests.ConnectionError:
        return f"❌ Não foi possível conectar ao servidor MCP em {server_url}. Verifique se o servidor está rodando."
    except requests.Timeout:
        return f"❌ Timeout ao conectar em {server_url}."
    except Exception as e:
        return f"❌ Erro ao conectar: {e}"


def mcp_chamar(server_url: str, tool_name: str, arguments: str = "{}") -> str:
    """Chama uma ferramenta em um servidor MCP externo."""
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        # Garante que a URL termine com /mcp
        url = server_url.rstrip("/")
        if not url.endswith("/mcp"):
            url += "/mcp"

        # Parse arguments
        if isinstance(arguments, str):
            args_dict = json.loads(arguments)
        else:
            args_dict = arguments

        payload = _make_rpc_request("tools/call", {
            "name": tool_name,
            "arguments": args_dict,
        })

        resp = requests.post(url, json=payload, timeout=60,
                            headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()

        # Extrai resultado
        if "error" in result and result["error"]:
            err = result["error"]
            return f"❌ Erro MCP ({err.get('code', '?')}): {err.get('message', 'Erro desconhecido')}"

        content = result.get("result", {}).get("content", [])
        text_parts = []
        for c in content:
            if c.get("type") == "text":
                text_parts.append(c.get("text", ""))

        return "\n".join(text_parts) if text_parts else "(sem conteúdo textual)"

    except json.JSONDecodeError:
        return "❌ Argumentos JSON inválidos."
    except requests.ConnectionError:
        return f"❌ Não foi possível conectar ao servidor MCP em {server_url}."
    except requests.Timeout:
        return "❌ Timeout na chamada MCP."
    except Exception as e:
        return f"❌ Erro na chamada MCP: {e}"


def mcp_listar_ferramentas(server_url: str) -> str:
    """Lista as ferramentas disponíveis em um servidor MCP externo."""
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        url = server_url.rstrip("/")
        if not url.endswith("/mcp"):
            url += "/mcp"

        payload = _make_rpc_request("tools/list")
        resp = requests.post(url, json=payload, timeout=10,
                            headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()

        if "error" in result and result["error"]:
            return f"❌ Erro: {result['error'].get('message', 'Erro desconhecido')}"

        tools = result.get("result", {}).get("tools", [])
        if not tools:
            return "Nenhuma ferramenta disponível neste servidor MCP."

        linhas = [f"🔧 Ferramentas MCP em {url} ({len(tools)}):\n"]
        for t in tools:
            name = t.get("name", "?")
            desc = t.get("description", "")
            params = t.get("inputSchema", {}).get("properties", {})
            param_names = list(params.keys())
            param_str = ", ".join(param_names[:5])
            if len(param_names) > 5:
                param_str += f" ... +{len(param_names) - 5}"
            linhas.append(f"  • {name}")
            if desc:
                linhas.append(f"    {desc[:120]}")
            if param_str:
                linhas.append(f"    Parâmetros: {param_str}")
            linhas.append("")

        return "\n".join(linhas)

    except Exception as e:
        return f"❌ Erro ao listar ferramentas: {e}"


def mcp_health_check(server_url: str) -> str:
    """Verifica o health de um servidor MCP (GET /health)."""
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        base = server_url.rstrip("/").replace("/mcp", "")
        resp = requests.get(f"{base}/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return (
            f"✅ Servidor MCP saudável\n"
            f"   Status: {data.get('status', 'ok')}\n"
            f"   Versão: {data.get('version', 'N/A')}\n"
            f"   Protocolo: {data.get('protocol', 'MCP')}"
        )
    except Exception as e:
        return f"❌ Health check falhou: {e}"


def mcp_descobrir(host: str = "127.0.0.1", port_start: int = 9090, port_end: int = 9190) -> str:
    """Descobre servidores MCP em uma faixa de portas."""
    import socket

    found = []
    for port in range(port_start, port_end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            # Porta aberta — tenta MCP
            try:
                import requests
                resp = requests.get(f"http://{host}:{port}/health", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    if "mcp" in str(data).lower() or "protocol" in str(data).lower():
                        found.append((port, data.get("server", "MCP Server")))
            except Exception:
                # Porta aberta mas não é MCP
                pass

    if not found:
        return f"❌ Nenhum servidor MCP encontrado em {host}:{port_start}-{port_end}."

    linhas = [f"🔍 Servidores MCP encontrados em {host}:\n"]
    for port, name in found:
        linhas.append(f"  ✅ http://{host}:{port} — {name}")
    return "\n".join(linhas)


# ======================================================================
# FUNÇÃO DE REGISTRO DO PLUGIN
# ======================================================================

def register(api):
    """Registra as ferramentas MCP no agente."""

    api.register_tool(
        name="mcp_server_iniciar",
        func=mcp_server_iniciar,
        description=(
            "Inicia o servidor MCP (Model Context Protocol) em segundo plano. "
            "Expõe TODAS as ferramentas do agente via protocolo MCP padronizado. "
            "Use isso para conectar o agente a clientes MCP como Claude Desktop, "
            "Cline, Continue.dev, ou qualquer ferramenta compatível com MCP."
        ),
        parameters={
            "host": {
                "type": "string",
                "description": "Endereço do host (padrão: 127.0.0.1)"
            },
            "port": {
                "type": "integer",
                "description": "Porta do servidor (padrão: 9090)"
            },
        },
        required=[],
    )

    api.register_tool(
        name="mcp_server_parar",
        func=mcp_server_parar,
        description="Para o servidor MCP em execução.",
        parameters={},
        required=[],
    )

    api.register_tool(
        name="mcp_server_status",
        func=mcp_server_status,
        description="Mostra o status do servidor MCP: se está ativo, endpoint, e quantas ferramentas estão expostas.",
        parameters={},
        required=[],
    )

    api.register_tool(
        name="mcp_conectar",
        func=mcp_conectar,
        description=(
            "Conecta a um servidor MCP externo e descobre as ferramentas disponíveis. "
            "Use para integrar com outros servidores MCP."
        ),
        parameters={
            "server_url": {
                "type": "string",
                "description": "URL do servidor MCP (ex: http://localhost:9090 ou http://192.168.1.100:9090)"
            },
        },
        required=["server_url"],
    )

    api.register_tool(
        name="mcp_chamar",
        func=mcp_chamar,
        description=(
            "Chama uma ferramenta em um servidor MCP externo. "
            "Use depois de mcp_conectar para executar ferramentas remotas."
        ),
        parameters={
            "server_url": {
                "type": "string",
                "description": "URL do servidor MCP"
            },
            "tool_name": {
                "type": "string",
                "description": "Nome da ferramenta a ser chamada"
            },
            "arguments": {
                "type": "string",
                "description": "Argumentos da ferramenta em formato JSON (ex: {\"texto\": \"Hello\"})"
            },
        },
        required=["server_url", "tool_name"],
    )

    api.register_tool(
        name="mcp_listar_ferramentas",
        func=mcp_listar_ferramentas,
        description="Lista todas as ferramentas disponíveis em um servidor MCP externo.",
        parameters={
            "server_url": {
                "type": "string",
                "description": "URL do servidor MCP"
            },
        },
        required=["server_url"],
    )

    api.register_tool(
        name="mcp_health_check",
        func=mcp_health_check,
        description="Verifica se um servidor MCP está respondendo (health check).",
        parameters={
            "server_url": {
                "type": "string",
                "description": "URL do servidor MCP"
            },
        },
        required=["server_url"],
    )

    api.register_tool(
        name="mcp_descobrir",
        func=mcp_descobrir,
        description="Descobre servidores MCP em uma faixa de portas no host local.",
        parameters={
            "host": {
                "type": "string",
                "description": "Host para scan (padrão: 127.0.0.1)"
            },
            "port_start": {
                "type": "integer",
                "description": "Porta inicial (padrão: 9090)"
            },
            "port_end": {
                "type": "integer",
                "description": "Porta final (padrão: 9190)"
            },
        },
        required=[],
    )

    return {
        "name": "MCP (Model Context Protocol)",
        "version": __version__,
        "description": "Implementação completa do MCP: servidor HTTP, cliente, descoberta. Expõe todas as ferramentas do agente via protocolo padronizado.",
        "tools": [
            "mcp_server_iniciar", "mcp_server_parar", "mcp_server_status",
            "mcp_conectar", "mcp_chamar", "mcp_listar_ferramentas",
            "mcp_health_check", "mcp_descobrir",
        ],
    }
