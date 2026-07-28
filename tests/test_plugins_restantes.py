"""
test_plugins_restantes.py
=========================
Testes automatizados para plugins SEM cobertura individual.

Cobre ~45 plugins com testes parametrizados eficientes:
- Importacao do modulo
- Funcao register() existe e e callable
- register() chama api.register_tool (pelo menos 1 tool)
- register() retorna dict com name, tools
- Cada tool registrada tem descricao valida (>5 chars)

Plugins com dependencias pesadas (torch, diffusers, docker) sao pulados.

Uso:
    pytest test_plugins_restantes.py -v --tb=short
"""

import pytest
import sys
import os
import importlib
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# Plugins que ja tem testes individuais (excluidos)
# =============================================================================
PLUGINS_COM_TESTES = {
    "plugin_playwright", "plugin_mcp", "plugin_rag",
    "plugin_fluxo_autonomo", "plugin_governanca_execucao",
    "plugin_validacao_universal", "plugin_operacao_profissional",
    "plugin_operacao_continua",
}

SKIP_IMPORT = {
    "plugin_image_processing", "plugin_media_geracao",
    "plugin_fine_tuning", "plugin_model_ensemble",
    "plugin_audio_avancado", "plugin_memoria_evolutiva",
    "plugin_code_analyzer",
    "plugin_sandbox", "plugin_sandbox_projeto",
    "plugin_avaliacoes_continuas",
}


def _descobrir_plugins():
    """Descobre plugins SEM teste dedicado."""
    import plugins
    plugins_dir = os.path.dirname(plugins.__file__)
    result = []
    for f in sorted(os.listdir(plugins_dir)):
        if f.endswith(".py") and f != "__init__.py":
            name = f[:-3]
            if name not in PLUGINS_COM_TESTES:
                result.append(name)
    return result


PLUGINS = _descobrir_plugins()


def _importar(plugin_name: str):
    """Importa plugin. Retorna (modulo, erro)."""
    full = f"plugins.{plugin_name}"
    if full in sys.modules:
        del sys.modules[full]
    try:
        return importlib.import_module(full), None
    except Exception as e:
        return None, str(e)


def _extrair_descricao(call_args) -> str:
    """Extrai descricao de uma chamada register_tool."""
    kw = call_args.kwargs or {}
    desc = kw.get("description", "")
    if not desc and len(call_args.args) >= 3:
        desc = call_args.args[2]
    return desc


# =============================================================================
# TESTES PARAMETRIZADOS — cobrem todos os plugins em 5 testes
# =============================================================================

class TestImportRegister:
    """Testes estruturais para todos os plugins sem testes dedicados."""

    @pytest.mark.parametrize("pn", PLUGINS)
    def test_import(self, pn):
        if pn in SKIP_IMPORT:
            pytest.skip(f"dependencias pesadas")
        mod, err = _importar(pn)
        assert err is None, f"{pn}: {err}"

    @pytest.mark.parametrize("pn", PLUGINS)
    def test_tem_register(self, pn):
        if pn in SKIP_IMPORT:
            pytest.skip(f"dependencias pesadas")
        mod, err = _importar(pn)
        if err:
            pytest.skip(err)
        assert hasattr(mod, "register"), f"{pn} sem register()"
        assert callable(mod.register)

    @pytest.mark.parametrize("pn", PLUGINS)
    def test_register_chama_api(self, pn):
        """register() deve chamar api.register_tool pelo menos 1x."""
        if pn in SKIP_IMPORT:
            pytest.skip(f"dependencias pesadas")
        mod, err = _importar(pn)
        if err or not hasattr(mod, "register"):
            pytest.skip(f"{pn}: {err or 'sem register'}")
        api = MagicMock()
        mod.register(api)
        assert api.register_tool.call_count >= 1, f"{pn}: 0 tools"

    @pytest.mark.parametrize("pn", PLUGINS)
    def test_metadados(self, pn):
        """register() retorna dict {'name': str, 'tools': list}."""
        if pn in SKIP_IMPORT:
            pytest.skip(f"dependencias pesadas")
        mod, err = _importar(pn)
        if err or not hasattr(mod, "register"):
            pytest.skip(f"{pn}: {err or 'sem register'}")
        res = mod.register(MagicMock())
        assert isinstance(res, dict), f"{pn}: devia ser dict"
        assert "name" in res, f"{pn}: sem 'name'"
        tools = res.get("tools", [])
        assert isinstance(tools, list), f"{pn}: tools nao e list"
        assert len(tools) >= 1, f"{pn}: lista tools vazia"

    @pytest.mark.parametrize("pn", PLUGINS)
    def test_descricoes(self, pn):
        """Cada tool registrada deve ter descricao > 5 caracteres."""
        if pn in SKIP_IMPORT:
            pytest.skip(f"dependencias pesadas")
        mod, err = _importar(pn)
        if err or not hasattr(mod, "register"):
            pytest.skip(f"{pn}: {err or 'sem register'}")
        api = MagicMock()
        mod.register(api)
        for c in api.register_tool.call_args_list:
            nome = c.kwargs.get("name", c.args[0] if c.args else "?")
            desc = _extrair_descricao(c)
            assert isinstance(desc, str) and len(desc) > 5, \
                f"{pn}: tool '{nome}' sem descricao valida"
