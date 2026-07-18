"""
plugin_subagentes.py
====================
Plugin de sub-agentes especializados. Permite que o agente principal
delegue tarefas complexas a agentes especialistas (codigo, arquivos,
web, matematica) e receba resultados estruturados.
"""

__version__ = "1.0.0"


def register(api):
    model = api.model

    def subagente_codigo(task: str) -> str:
        """Delega uma tarefa de programacao a um sub-agente especialista em codigo.
        O sub-agente pode analisar, escrever, revisar ou depurar codigo.
        """
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX, TEMPERATURE

            prompt = (
                "Voce e um engenheiro de software senior. Sua unica funcao e "
                "resolver tarefas de programacao com excelencia.\n\n"
                f"TAREFA: {task}\n\n"
                "Regras:\n"
                "- Escreva codigo completo, funcional e bem estruturado.\n"
                "- Explique brevemente o que o codigo faz.\n"
                "- Se houver erro, diagnostique e corrija.\n"
                "- Use boas praticas, docstrings e tipos quando viavel.\n"
                "- Responda APENAS com o codigo e uma breve explicacao."
            )
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.2},
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[Sub-agente codigo] Erro: {e}"

    def subagente_analise(task: str) -> str:
        """Delega uma tarefa de analise, pesquisa ou organizacao a um sub-agente
        especialista em raciocinio logico e sintese de informacao.
        """
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX, TEMPERATURE

            prompt = (
                "Voce e um analista senior especializado em sintetizar informacoes, "
                "fazer analises profundas e organizar ideias de forma clara.\n\n"
                f"TAREFA: {task}\n\n"
                "Regras:\n"
                "- Seja objetivo, direto e baseado em evidencias.\n"
                "- Estruture sua resposta em topicos claros.\n"
                "- Se houver dados numericos, apresente em tabelas.\n"
                "- Aponte prós e contras quando relevante.\n"
                "- Conclua com recomendacoes acionaveis."
            )
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.4},
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[Sub-agente analise] Erro: {e}"

    def subagente_criativo(task: str) -> str:
        """Delega uma tarefa criativa (escrever, criar, entreter) a um sub-agente
        especialista em criatividade.
        """
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX, TEMPERATURE

            prompt = (
                "Voce e um escritor e designer criativo profissional. "
                "Sua especialidade e criar conteudo original, envolvente e memoravel.\n\n"
                f"TAREFA: {task}\n\n"
                "Regras:\n"
                "- Seja criativo e original.\n"
                "- Use linguagem rica e expressiva.\n"
                "- Adapte o tom ao publico-alvo.\n"
                "- Surpreenda com ideias unicas.\n"
                "- Entregue conteudo pronto para uso."
            )
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.8},
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[Sub-agente criativo] Erro: {e}"

    api.register_tool(
        name="subagente_codigo",
        func=subagente_codigo,
        description=(
            "Delega uma tarefa de PROGRAMACAO a um sub-agente especialista. "
            "Use para: escrever codigo, debuggar, revisar, refatorar, "
            "explicar algoritmos, criar scripts. O sub-agente e um engenheiro "
            "de software senior e retorna codigo pronto."
        ),
        parameters={
            "task": {
                "type": "string",
                "description": "Descricao detalhada da tarefa de programacao"
            },
        },
        required=["task"],
    )

    api.register_tool(
        name="subagente_analise",
        func=subagente_analise,
        description=(
            "Delega uma tarefa de ANALISE E PESQUISA a um sub-agente especialista. "
            "Use para: analisar dados, comparar opcoes, sintetizar informacoes, "
            "organizar ideias, fazer recomendacoes, planejar projetos."
        ),
        parameters={
            "task": {
                "type": "string",
                "description": "Descricao detalhada da tarefa de analise"
            },
        },
        required=["task"],
    )

    api.register_tool(
        name="subagente_criativo",
        func=subagente_criativo,
        description=(
            "Delega uma tarefa CRIATIVA a um sub-agente especialista. "
            "Use para: escrever textos criativos, criar historias, "
            "gerar ideias de nomes/slogans, campanhas, conteudo para redes sociais, "
            "poesia, roteiros."
        ),
        parameters={
            "task": {
                "type": "string",
                "description": "Descricao detalhada da tarefa criativa"
            },
        },
        required=["task"],
    )

    return {
        "name": "Sub-Agentes Especialistas",
        "version": __version__,
        "description": "3 sub-agentes: codigo, analise e criativo. Delega tarefas complexas para especialistas.",
        "tools": ["subagente_codigo", "subagente_analise", "subagente_criativo"],
    }
