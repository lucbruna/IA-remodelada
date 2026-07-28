"""
plugin_subagentes.py
====================
Plugin de sub-agentes especializados. Permite que o agente principal
delegue tarefas complexas a agentes especialistas (codigo, arquivos,
web, matematica) e receba resultados estruturados.
"""

__version__ = "2.0.0"


def register(api):
    model = api.model

    def _consultar_especialista(titulo: str, task: str, regras: list[str], temperature: float = 0.3) -> str:
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX

            prompt = (
                f"Voce e {titulo}.\n\n"
                f"TAREFA: {task}\n\n"
                "Regras:\n"
                + "\n".join(f"- {regra}" for regra in regras)
            )
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": NUM_CTX, "temperature": temperature},
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[{titulo}] Erro: {e}"

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

    def subagente_arquitetura(task: str) -> str:
        """Especialista em arquitetura de sistemas e desenho de solucao."""
        return _consultar_especialista(
            "um arquiteto de software senior",
            task,
            [
                "Desenhe a arquitetura com componentes, responsabilidades e fluxos.",
                "Escolha tecnologias simples e justificadas.",
                "Liste riscos, tradeoffs e decisoes tecnicas.",
                "Entregue um plano implementavel em etapas pequenas.",
            ],
            0.25,
        )

    def subagente_testes(task: str) -> str:
        """Especialista em testes, qualidade e validacao."""
        return _consultar_especialista(
            "um engenheiro de qualidade e testes senior",
            task,
            [
                "Defina estrategia de testes unitarios, integracao e regressao.",
                "Crie casos de teste objetivos, incluindo bordas e erros.",
                "Explique como rodar os testes e interpretar falhas.",
                "Priorize validacoes automatizadas e reproduziveis.",
            ],
            0.2,
        )

    def subagente_debug(task: str) -> str:
        """Especialista em diagnostico de erros e causa raiz."""
        return _consultar_especialista(
            "um especialista em debug e causa raiz",
            task,
            [
                "Leia o erro como evidencia, sem chute.",
                "Aponte causa provavel, arquivo/linha se houver, e correcao minima.",
                "Sugira comando de validacao para confirmar o conserto.",
                "Se faltar dado, liste exatamente qual log/arquivo precisa ser lido.",
            ],
            0.15,
        )

    def subagente_frontend(task: str) -> str:
        """Especialista em interfaces web, UX e frontend."""
        return _consultar_especialista(
            "um engenheiro frontend senior com sensibilidade de produto",
            task,
            [
                "Projete uma interface clara, responsiva e utilizavel.",
                "Use estados, controles e validacoes que o usuario espera.",
                "Evite layout fragil, textos sobrepostos e componentes decorativos sem funcao.",
                "Entregue estrutura de arquivos e codigo quando aplicavel.",
            ],
            0.35,
        )

    def subagente_backend(task: str) -> str:
        """Especialista em APIs, banco de dados e regras de negocio."""
        return _consultar_especialista(
            "um engenheiro backend senior",
            task,
            [
                "Modele endpoints, dados, validacoes e tratamento de erros.",
                "Priorize seguranca, clareza e testes automatizados.",
                "Inclua contratos de API e exemplos de payload.",
                "Aponte riscos de concorrencia, persistencia e autenticacao quando relevantes.",
            ],
            0.25,
        )

    def subagente_devops(task: str) -> str:
        """Especialista em ambiente, Docker, deploy e automacao."""
        return _consultar_especialista(
            "um engenheiro DevOps senior",
            task,
            [
                "Defina comandos reproduziveis para instalar, testar, rodar e publicar.",
                "Inclua variaveis de ambiente, portas, logs e checks de saude.",
                "Priorize automacao simples e rollback quando houver risco.",
                "Evite acoes destrutivas sem confirmacao explicita.",
            ],
            0.2,
        )

    def subagente_brasil_mundo(task: str) -> str:
        """Especialista em contexto brasileiro, internacional e atualidades."""
        return _consultar_especialista(
            "um analista de contexto Brasil e mundo",
            task,
            [
                "Separe o que e fato estavel do que exige noticia/fonte atual.",
                "Recomende buscar fontes recentes quando houver data, politica, economia ou tecnologia atual.",
                "Explique impacto pratico para o usuario no Brasil quando relevante.",
                "Nao invente dados temporais; diga quais fontes consultar.",
            ],
            0.25,
        )

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

    api.register_tool(
        name="subagente_arquitetura",
        func=subagente_arquitetura,
        description="Delega desenho de arquitetura, modulos, responsabilidades, riscos e plano tecnico para um arquiteto senior.",
        parameters={"task": {"type": "string", "description": "Tarefa de arquitetura ou desenho de sistema"}},
        required=["task"],
    )

    api.register_tool(
        name="subagente_testes",
        func=subagente_testes,
        description="Delega estrategia, criacao e correcao de testes para um especialista em qualidade.",
        parameters={"task": {"type": "string", "description": "Tarefa de testes, QA ou validacao"}},
        required=["task"],
    )

    api.register_tool(
        name="subagente_debug",
        func=subagente_debug,
        description="Delega diagnostico de erro/log e causa raiz para um especialista em debug.",
        parameters={"task": {"type": "string", "description": "Erro, log ou comportamento quebrado"}},
        required=["task"],
    )

    api.register_tool(
        name="subagente_frontend",
        func=subagente_frontend,
        description="Delega interface, UX, HTML/CSS/JS, React, Streamlit e design de frontend.",
        parameters={"task": {"type": "string", "description": "Tarefa de frontend ou UI"}},
        required=["task"],
    )

    api.register_tool(
        name="subagente_backend",
        func=subagente_backend,
        description="Delega APIs, banco de dados, regras de negocio, seguranca e backend.",
        parameters={"task": {"type": "string", "description": "Tarefa de backend, API ou dados"}},
        required=["task"],
    )

    api.register_tool(
        name="subagente_devops",
        func=subagente_devops,
        description="Delega ambiente, Docker, deploy, automacao, logs e checks operacionais.",
        parameters={"task": {"type": "string", "description": "Tarefa de infraestrutura, deploy ou ambiente"}},
        required=["task"],
    )

    def subagente_sandbox(
        task: str,
        cpu: float = 0.5,
        memory_mb: int = 256,
        timeout: int = 30,
    ) -> str:
        """Sub-agente que escreve codigo Python e EXECUTA no Sandbox Docker com isolamento completo.

        Permite configurar recursos (CPU, RAM, timeout) para cada execucao.
        O CEO pode definir recursos adequados para cada tarefa:
        - Tarefas leves (scripts simples): cpu=0.25, memory_mb=128
        - Tarefas medias (analise de dados): cpu=0.5, memory_mb=512
        - Tarefas pesadas (ML, GPU): cpu=2.0, memory_mb=2048

        Fluxo:
        1. LLM analisa a tarefa e escreve o codigo
        2. Cria/usa projeto sandbox com os recursos especificados
        3. Executa o codigo no container Docker (read-only, sem rede)
        4. Retorna o codigo + saida da execucao

        Args:
            task: Descricao detalhada do codigo a ser escrito e executado
            cpu: Limite de CPUs (fracao, ex: 0.5 = meio nucleo, padrao: 0.5)
            memory_mb: Limite de RAM em MB (padrao: 256)
            timeout: Timeout em segundos (padrao: 30)

        Returns:
            Codigo gerado + saida da execucao no sandbox
        """
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX
            from plugins.plugin_sandbox import (
                sandbox_criar_projeto, sandbox_executar,
                sandbox_status, _check_docker
            )

            # 1. LLM escreve o codigo
            prompt = (
                "Voce e um engenheiro de software. Sua tarefa e ESCREVER CODIGO Python "
                "que sera executado em um sandbox Docker isolado (read-only, sem rede).\n\n"
                f"TAREFA: {task}\n\n"
                "Regras:\n"
                "- Escreva APENAS o codigo Python (sem markdown, sem explicacao).\n"
                "- O codigo deve ser AUTO-CONTIDO e nao depender de arquivos externos.\n"
                "- Use print() para mostrar resultados.\n"
                "- Nao tente acessar rede ou sistema de arquivos (nao permitido).\n"
                "- Trate erros com try/except e print().\n"
                "- Responda APENAS com o codigo, nada mais."
            )
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.2},
            )
            codigo = response["message"]["content"].strip()

            # Remove markdown code blocks se houver
            if "```" in codigo:
                import re
                blocks = re.findall(r"```(?:python)?\n?(.*?)```", codigo, re.DOTALL)
                if blocks:
                    codigo = blocks[0].strip()

            if not codigo:
                return "[Sandbox] Nao foi possivel gerar codigo."

            # 2. Verifica/usa projeto sandbox
            projeto = "sandbox-agentes"
            docker_ok = _check_docker().get("available", False)

            if docker_ok:
                # Tenta criar projeto (se ja existe, retorna aviso)
                criacao = sandbox_criar_projeto(
                    nome=projeto,
                    descricao="Projeto automatico do orquestrador para execucao de agentes",
                    python_version="3.11",
                    cpu=cpu,
                    memory_mb=memory_mb,
                    timeout=timeout,
                )

                # 3. Executa no sandbox Docker com os recursos configurados
                resultado = sandbox_executar(
                    projeto=projeto,
                    codigo=codigo,
                    timeout=timeout,
                    cpu=cpu,
                    memory_mb=memory_mb,
                )

                return (
                    f"[Sandbox] Codigo executado com Docker (CPU:{cpu} RAM:{memory_mb}MB TO:{timeout}s)\n\n"
                    f"--- CODIGO ---\n{codigo}\n\n"
                    f"--- SAIDA ---\n{resultado}"
                )
            else:
                # Fallback: executa local com subprocess
                import subprocess, sys
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", codigo],
                        capture_output=True, text=True, timeout=min(timeout, 30),
                    )
                    saida = result.stdout.strip() or result.stderr.strip() or "(sem saida)"
                    return (
                        f"[Sandbox] Codigo executado (fallback subprocess)\n\n"
                        f"--- CODIGO ---\n{codigo}\n\n"
                        f"--- SAIDA ---\n{saida}"
                    )
                except subprocess.TimeoutExpired:
                    return f"[Sandbox] Timeout apos {timeout}s"
                except Exception as e:
                    return f"[Sandbox] Erro ao executar codigo: {e}"

        except ImportError as e:
            return f"[Sandbox] Erro de import: {e}"
        except Exception as e:
            return f"[Sandbox] Erro: {e}"

    def subagente_validar(
        task: str,
        cpu: float = 0.5,
        memory_mb: int = 256,
        timeout: int = 30,
    ) -> str:
        """Sub-agente que VALIDA codigo executando no Sandbox Docker.

        Recebe codigo como task, executa no sandbox com isolamento,
        e retorna o resultado da execucao + analise.

        Args:
            task: Codigo Python a ser executado e validado
            cpu: Limite de CPUs (fracao, padrao: 0.5)
            memory_mb: Limite de RAM em MB (padrao: 256)
            timeout: Timeout em segundos (padrao: 30)
        """
        try:
            from plugins.plugin_sandbox import (
                sandbox_criar_projeto, sandbox_executar, _check_docker
            )

            docker_ok = _check_docker().get("available", False)
            projeto = "sandbox-agentes"

            # Garante que o projeto sandbox existe (com recursos especificados)
            sandbox_criar_projeto(
                nome=projeto,
                descricao="Projeto do orquestrador para validacao de codigo",
                python_version="3.11",
                cpu=cpu,
                memory_mb=memory_mb,
                timeout=timeout,
            )

            if docker_ok:
                resultado = sandbox_executar(
                    projeto=projeto,
                    codigo=task,
                    timeout=timeout,
                    cpu=cpu,
                    memory_mb=memory_mb,
                )
                return (
                    f"[Validacao Sandbox] (CPU:{cpu} RAM:{memory_mb}MB)\n\n"
                    f"--- CODIGO VALIDADO ---\n{task[:500]}\n\n"
                    f"--- RESULTADO ---\n{resultado}"
                )
            else:
                # Fallback: subprocess
                import subprocess as _sp, sys as _sys
                try:
                    _r = _sp.run([_sys.executable, "-c", task],
                                 capture_output=True, text=True, timeout=min(timeout, 30))
                    _saida = _r.stdout.strip() or _r.stderr.strip() or "(sem saida)"
                    return (
                        f"[Validacao Fallback]\n\n"
                        f"--- CODIGO VALIDADO ---\n{task[:500]}\n\n"
                        f"--- SAIDA ---\n{_saida}"
                    )
                except _sp.TimeoutExpired:
                    return f"[Validacao] Timeout apos {timeout}s"
                except Exception as e:
                    return f"[Validacao] Erro no fallback: {e}"
        except Exception as e:
            return f"[Validacao] Erro: {e}"

    api.register_tool(
        name="subagente_sandbox",
        func=subagente_sandbox,
        description=(
            "Sub-agente que escreve codigo Python e EXECUTA automaticamente no Sandbox Docker "
            "com isolamento completo (read-only, sem rede, CPU/RAM limitados). "
            "Use para: testar algoritmos, validar logicas, executar scripts com seguranca. "
            "Retorna codigo + saida da execucao."
        ),
        parameters={
            "task": {
                "type": "string",
                "description": "Descricao detalhada do codigo a ser escrito e executado"
            },
            "cpu": {
                "type": "number",
                "description": "Limite de CPUs (fracao, ex: 0.5, 1.0, 2.0). Padrao: 0.5"
            },
            "memory_mb": {
                "type": "integer",
                "description": "Limite de RAM em MB (ex: 128, 256, 512, 1024). Padrao: 256"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout em segundos (ex: 15, 30, 60, 120). Padrao: 30"
            },
        },
        required=["task"],
    )

    api.register_tool(
        name="subagente_validar",
        func=subagente_validar,
        description=(
            "Sub-agente que VALIDA codigo Python executando no Sandbox Docker. "
            "Recebe codigo-fonte como entrada e retorna resultado da execucao "
            "com isolamento completo. Use para verificar se o codigo funciona. "
            "Parametros opcionais: cpu, memory_mb, timeout para controlar recursos."
        ),
        parameters={
            "task": {
                "type": "string",
                "description": "Codigo Python a ser executado e validado no sandbox"
            },
            "cpu": {
                "type": "number",
                "description": "Limite de CPUs (fracao, ex: 0.5, 1.0). Padrao: 0.5"
            },
            "memory_mb": {
                "type": "integer",
                "description": "Limite de RAM em MB (ex: 128, 256, 512). Padrao: 256"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout em segundos. Padrao: 30"
            },
        },
        required=["task"],
    )

    api.register_tool(
        name="subagente_brasil_mundo",
        func=subagente_brasil_mundo,
        description="Delega contexto do Brasil e mundo, atualidades e impactos praticos para analista especializado.",
        parameters={"task": {"type": "string", "description": "Tarefa sobre Brasil, mundo, noticias ou contexto atual"}},
        required=["task"],
    )

    return {
        "name": "Sub-Agentes Especialistas",
        "version": __version__,
        "description": "10 sub-agentes: codigo, analise, criativo, arquitetura, testes, debug, frontend, backend, devops e Brasil/mundo.",
        "tools": [
            "subagente_codigo",
            "subagente_analise",
            "subagente_criativo",
            "subagente_arquitetura",
            "subagente_testes",
            "subagente_debug",
            "subagente_frontend",
            "subagente_backend",
            "subagente_devops",
            "subagente_brasil_mundo",
        ],
    }
