from ._common import *
# =======================================================================
# SISTEMA DE PLUGINS (skills extensiveis)
# =======================================================================

# Diretório de plugins fica na raiz do projeto (onde está config.py / agente_core.py),
# não dentro de core/. Usamos BASE_DIR de config para robustez.
from config import BASE_DIR as _BASE_DIR
PLUGINS_DIR = os.path.join(_BASE_DIR, "plugins")


class PluginAPI:
    """API que cada plugin recebe para se registrar.

    Fornece metodos seguros para plugins interagirem com o nucleo
    do agente sem acesso direto as variaveis internas.
    """

    def __init__(self, functions_registry: dict, tools_list: list):
        self._functions = functions_registry
        self._tools = tools_list
        self._register = functions_registry
        self._tool_defs = tools_list

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: dict = None,
        required: list = None,
    ) -> None:
        """Registra uma nova ferramenta que o agente pode usar.

        Args:
            name: Nome unico da ferramenta (ex: 'consulta_cep')
            func: Funcao Python que implementa a ferramenta
            description: Descricao para o modelo entender quando usar
            parameters: Dict especificando os parametros no formato:
                        {"param_name": {"type": "string", "description": "..."}}
            required: Lista de nomes de parametros obrigatorios
        """
        if name in self._functions:
            logging.warning("Plugin tentou registrar ferramenta duplicada: %s", name)
            return

        if parameters is None:
            parameters = {}
        if required is None:
            required = []

        properties = {}
        for param_name, param_info in parameters.items():
            prop = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", ""),
            }
            properties[param_name] = prop

        self._functions[name] = func
        self._tool_defs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
        logging.info("Plugin registrou ferramenta: %s", name)

    @property
    def model(self) -> str:
        return MODEL

    @property
    def data_dir(self) -> str:
        return DATA_DIR


class PluginManager:
    """Gerenciador de plugins: descobre, carrega e gerencia plugins."""

    def __init__(self):
        self._plugins: dict[str, dict] = {}  # nome -> {info, tools, module}

    @property
    def loaded_plugins(self) -> dict:
        """Retorna dict com plugins carregados (nome -> metadados)."""
        return dict(self._plugins)

    def load_all(self, functions_registry: dict, tools_list: list) -> None:
        """Carrega todos os plugins do diretorio plugins/."""
        # Lê PLUGINS_DIR de forma dinâmica para respeitar patches de teste
        # feitos em agente_core.PLUGINS_DIR, sem import circular.
        _mod = sys.modules.get("agente_core")
        _PLUGINS_DIR = getattr(_mod, "PLUGINS_DIR", PLUGINS_DIR) if _mod else PLUGINS_DIR
        if not os.path.isdir(_PLUGINS_DIR):
            logging.info("Diretorio de plugins nao encontrado: %s", _PLUGINS_DIR)
            return

        import importlib.util

        # Procura por arquivos .py no diretorio de plugins
        for filename in sorted(os.listdir(_PLUGINS_DIR)):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue

            filepath = os.path.join(_PLUGINS_DIR, filename)
            module_name = f"plugins.{filename[:-3]}"

            try:
                # Importa o modulo dinamicamente
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec is None or spec.loader is None:
                    logging.warning("Nao foi possivel carregar plugin: %s", filename)
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Verifica se tem funcao register
                if not hasattr(module, "register"):
                    logging.info("Plugin %s nao tem funcao register(), ignorado.", filename)
                    continue

                # Cria a API e chama register
                api = PluginAPI(functions_registry, tools_list)
                resultado = module.register(api)

                # Extrai metadados do plugin
                info = {
                    "name": filename[:-3],
                    "file": filename,
                    "loaded": True,
                    "error": None,
                }

                # Se register retornar um dict, usa como info
                if isinstance(resultado, dict):
                    info.update(resultado)

                self._plugins[info["name"]] = info
                logging.info("Plugin carregado: %s", filename)

            except Exception as e:
                logging.error("Erro ao carregar plugin %s: %s", filename, e)
                self._plugins[filename[:-3]] = {
                    "name": filename[:-3],
                    "file": filename,
                    "loaded": False,
                    "error": str(e),
                }

    def clear(self) -> None:
        """Limpa todos os plugins carregados."""
        self._plugins.clear()

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    @property
    def loaded_count(self) -> int:
        return sum(1 for p in self._plugins.values() if p.get("loaded"))

    def list_plugins_text(self) -> str:
        """Retorna lista formatada dos plugins carregados."""
        if not self._plugins:
            return "Nenhum plugin carregado."

        lines = []
        for nome, info in sorted(self._plugins.items()):
            status = "✅" if info.get("loaded") else "❌"
            desc = info.get("description", "")
            versao = info.get("version", "")
            tools = info.get("tools", [])

            linha = f"  {status} {nome}"
            if versao:
                linha += f" v{versao}"
            if desc:
                linha += f"  — {desc}"
            lines.append(linha)

            if tools:
                for t in tools:
                    lines.append(f"     ├ 🔧 {t}")

            if not info.get("loaded"):
                lines.append(f"     └ ⚠ Erro: {info.get('error', 'desconhecido')}")

        return "\n".join(lines)


# Instancia global do gerenciador de plugins
_plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """Retorna a instancia global do gerenciador de plugins."""
    return _plugin_manager


def list_plugins() -> str:
    """Retorna lista dos plugins carregados (ferramenta para o agente)."""
    # Lê _plugin_manager de forma dinâmica p/ respeitar patches de teste
    # feitos em agente_core._plugin_manager.
    _mod = sys.modules.get("agente_core")
    _pm = getattr(_mod, "_plugin_manager", _plugin_manager) if _mod else _plugin_manager
    return _pm.list_plugins_text()


def reload_plugins() -> str:
    """Recarrega todos os plugins do disco (ferramenta para o agente)."""
    _mod = sys.modules.get("agente_core")
    _pm = getattr(_mod, "_plugin_manager", _plugin_manager) if _mod else _plugin_manager
    _pm.load_all(AVAILABLE_FUNCTIONS, TOOLS_LIST)
    loaded = _pm.loaded_count
    total = _pm.plugin_count
    return f"Plugins recarregados: {loaded} carregados de {total} encontrados."


# =======================================================================
# PLUGIN STORE: instalar e listar plugins via URL
# =======================================================================

_PLUGIN_STORE_URL = "https://raw.githubusercontent.com/"


def install_plugin_from_url(url: str) -> str:
    """Baixa e instala um plugin de uma URL remota (arquivo .py).

    Args:
        url: URL direta para o arquivo .py do plugin

    Returns:
        Mensagem de confirmacao ou erro
    """
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        if not url.endswith(".py"):
            return "A URL deve apontar para um arquivo .py"

        filename = url.split("/")[-1]
        if not filename.endswith(".py"):
            return "A URL deve terminar em .py"

        # Valida nome (seguranca)
        if not re.match(r"^[a-zA-Z0-9_\-]+\.py$", filename):
            return f"Nome de arquivo invalido: {filename}"

        dest = os.path.join(_PLUGINS_DIR, filename)

        # Download
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AgenteLocal/1.0)"
        })
        resp.raise_for_status()

        content = resp.text

        # Validacao basica: deve conter funcao register
        if "def register" not in content:
            return "O arquivo baixado nao contem uma funcao register(). Plugin invalido."

        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)

        # Recarrega plugins (reusa logica de reload_plugins)
        resultado_reload = reload_plugins()
        size = len(content)
        return f"Plugin instalado: {filename} ({size} caracteres).\n{resultado_reload}"
    except requests.Timeout:
        return "Timeout ao baixar plugin. Verifique a URL e a conexao."
    except requests.RequestException as e:
        return f"Erro ao baixar plugin: {e}"
    except Exception as e:
        return f"Erro ao instalar plugin: {e}"


