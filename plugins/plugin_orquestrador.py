"""
plugin_orquestrador.py
=======================
Plugin do Orquestrador Mestre — registra as ferramentas de orquestração
no sistema de plugins do agente.
"""

__version__ = "1.0.0"


def register(api):
    from orquestrador_mestre import orquestrar, OrquestradorMestre

    def ferramenta_orquestrar(tarefa: str, contexto: str = "") -> str:
        """Executa o Orquestrador Mestre completo: CEO analisa, delega para agentes especialistas, e Self-Reflection revisa o resultado final. Use para tarefas complexas que exigem múltiplas etapas."""
        return orquestrar(tarefa, contexto)

    def ferramenta_orquestrar_rapido(tarefa: str) -> str:
        """Versão rápida do Orquestrador Mestre — apenas CEO + agentes necessários + Self-Reflection, sem contexto adicional."""
        return orquestrar(tarefa, "")

    def ferramenta_status_orquestrador() -> str:
        """Retorna o status atual do Orquestrador Mestre e quais agentes estão disponíveis."""
        from agente_core import AVAILABLE_FUNCTIONS

        subagentes_disponiveis = [
            name for name in AVAILABLE_FUNCTIONS.keys()
            if name.startswith("subagente_")
        ]

        linhas = [
            "╔════════════════════════════════════════╗",
            "║   🤖 ORQUESTRADOR MESTRE — STATUS      ║",
            "╚════════════════════════════════════════╝",
            "",
            f"📊 Subagentes disponíveis: {len(subagentes_disponiveis)}",
        ]

        for s in sorted(subagentes_disponiveis):
            linhas.append(f"  ✅ {s}")

        linhas.append("")
        linhas.append("Use 'orquestrar' com uma tarefa para iniciar o pipeline completo.")
        linhas.append("Fluxo: CEO → Architect → Agentes → Self-Reflection")

        return "\n".join(linhas)

    api.register_tool(
        name="orquestrar",
        func=ferramenta_orquestrar,
        description=(
            "Executa o Orquestrador Mestre: CEO analisa a tarefa, delega para agentes "
            "especialistas (arquitetura, código, debug, testes, frontend, backend, etc.), "
            "e Self-Reflection revisa o resultado final. Ideal para tarefas complexas "
            "que exigem múltiplas habilidades."
        ),
        parameters={
            "tarefa": {
                "type": "string",
                "description": "Descrição detalhada da tarefa a ser executada"
            },
            "contexto": {
                "type": "string",
                "description": "Contexto adicional (código existente, arquivos, requisitos)"
            },
        },
        required=["tarefa"],
    )

    api.register_tool(
        name="orquestrar_rapido",
        func=ferramenta_orquestrar_rapido,
        description="Versão rápida do Orquestrador Mestre — executa CEO + agentes + Self-Reflection sem contexto adicional.",
        parameters={
            "tarefa": {
                "type": "string",
                "description": "Descrição da tarefa"
            },
        },
        required=["tarefa"],
    )

    api.register_tool(
        name="orquestrador_status",
        func=ferramenta_status_orquestrador,
        description="Mostra o status do Orquestrador Mestre e lista todos os subagentes disponíveis.",
        parameters={},
        required=[],
    )

    return {
        "name": "Orquestrador Mestre",
        "version": __version__,
        "description": "CEO AI + agentes especializados + Self-Reflection. Coordena todo o pipeline de desenvolvimento.",
        "tools": ["orquestrar", "orquestrar_rapido", "orquestrador_status"],
    }
