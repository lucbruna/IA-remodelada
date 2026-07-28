"""
plugin_sandbox_projeto.py
=========================
Wrapper de compatibilidade para o sandbox principal.

Todas as funcionalidades foram migradas para plugin_sandbox.py.
Este modulo mantem compatibilidade com codigo existente que
importa ferramentas diretamente deste plugin.

Funcoes disponiveis:
  - sandbox_status()       -> plugin_sandbox.sandbox_status
  - executar_no_sandbox()  -> plugin_sandbox.sandbox_executar_comando
"""

from plugins.plugin_sandbox import (
    sandbox_status,
    sandbox_executar_comando as executar_no_sandbox,
    sandbox_criar_projeto,
    sandbox_listar_projetos,
    sandbox_executar,
    sandbox_instalar_pacotes,
    sandbox_historico,
)

__version__ = "2.0.0"
PLUGIN_NAME = "Sandbox por Projeto (compatibilidade)"

# Re-exporta a funcao original para compatibilidade
sandbox_status_original = sandbox_status


def register(api):
    """Registra ferramentas do sandbox (delega para plugin_sandbox)."""
    from plugins.plugin_sandbox import register as sandbox_register
    return sandbox_register(api)
