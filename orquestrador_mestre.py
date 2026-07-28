"""
orquestrador_mestre.py
=======================
Orquestrador Mestre — CEO AI que coordena agentes especializados.

FLUXO:
1. CEO recebe a tarefa e analisa o que precisa ser feito
2. Architect projeta a arquitetura/solução
3. CEO delega para agentes especialistas (codigo, debug, testes, etc.)
4. Cada agente executa e passa o resultado adiante
5. Self-Reflection revisa o resultado final
6. Se houver problemas, loop de correção

USO:
    from orquestrador_mestre import OrquestradorMestre
    orb = OrquestradorMestre()
    for step in orb.executar("Criar uma calculadora em Python"):
        print(step["status"], step.get("agente", ""))
"""

import time
import logging
from typing import Generator

logger = logging.getLogger("orquestrador_mestre")

# ─── Modelos para cada papel ────────────────────────────────────────
MODELO_CEO = None       # None = usa o modelo padrão do agente_core
MODELO_ARQUITETO = None
MODELO_CODIGO = None
MODELO_REVISOR = None


class OrquestradorMestre:
    """Orquestrador Mestre — CEO que coordena agentes especializados."""

    def __init__(self, model: str = None):
        self.model = model
        self.historico: list = []
        self.tarefa_original: str = ""
        self.plano: dict = {}
        self.resultados: dict = {}
        self._rag_contexto: str = ""

    def _buscar_rag(self, consulta: str) -> str:
        """Busca documentos relevantes no RAG e retorna como texto de contexto."""
        try:
            from plugins.plugin_rag import init_rag, search_rag
            init_rag()
            docs = search_rag(consulta, n_results=5)
            if not docs:
                return ""
            partes = ["📚 Documentos relevantes encontrados no RAG:\n"]
            for i, d in enumerate(docs, 1):
                meta = d.get("metadata", {})
                filename = meta.get("filename", "documento")
                texto = d["text"][:500]
                score = d.get("score", 0)
                partes.append(f"\n[{i}] {filename} (relevância: {score:.2f})")
                partes.append(f"    {texto}")
            return "\n".join(partes)
        except ImportError:
            return ""
        except Exception:
            return ""

    def _ollama_chat(self, system: str, prompt: str, temperature: float = 0.3, model: str = None) -> str:
        """Chama o Ollama com mensagens system + user."""
        import ollama
        from agente_core import _call_ollama_with_timeout, NUM_CTX

        modelo = model or self.model or MODELO_CEO
        if not modelo or str(modelo).strip() in ("", "?", "null", "None"):
            from agente_core import MODEL
            modelo = MODEL

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = _call_ollama_with_timeout(
                ollama.chat,
                model=modelo,
                messages=messages,
                options={"num_ctx": NUM_CTX, "temperature": temperature},
            )
            return response["message"]["content"].strip()
        except Exception as e:
            return f"[Erro na chamada ao modelo: {e}]"

    def _executar_subagente(self, nome: str, task: str, **kwargs) -> str:
        """Executa um subagente especializado via plugin_subagentes.

        Args:
            nome: Nome do subagente
            task: Descricao da tarefa
            **kwargs: Parametros adicionais (ex: cpu, memory_mb, timeout)
                     que sao passados diretamente a funcao do subagente
        """
        from agente_core import AVAILABLE_FUNCTIONS

        func = AVAILABLE_FUNCTIONS.get(nome)
        if func:
            try:
                if kwargs:
                    return func(task, **kwargs)
                return func(task)
            except Exception as e:
                return f"[Erro no subagente {nome}: {e}]"
        return f"[Subagente {nome} não encontrado]"

    def executar(self, tarefa: str, contexto: str = "") -> Generator[dict, None, dict]:
        """
        Executa o pipeline completo do orquestrador.

        Args:
            tarefa: Descrição da tarefa a ser executada
            contexto: Contexto adicional (código existente, arquivos, etc.)

        Yields:
            dict com status, agente, mensagem, e dados parciais

        Returns:
            dict com resultado final completo
        """
        self.tarefa_original = tarefa
        start_time = time.time()

        # ─── PASSO 1: CEO analisa a tarefa ─────────────────────────
        yield {"status": "inicio", "agente": "👑 CEO", "mensagem": "Analisando tarefa e consultando RAG...", "progresso": 5}

        # Busca documentos relevantes no RAG
        self._rag_contexto = self._buscar_rag(tarefa)
        if self._rag_contexto:
            yield {
                "status": "rag_contexto",
                "agente": "📚 RAG",
                "mensagem": f"Documentos relevantes encontrados",
                "contexto_rag": self._rag_contexto[:300],
                "progresso": 10,
            }

        analise = self._ollama_chat(
            "Você é o CEO de um time de engenharia de IA. Você delega tarefas para agentes especialistas. "
            "Seja objetivo e prático. Use os documentos fornecidos como contexto para suas decisões.",
            f"Analise a seguinte tarefa e decida QUAIS agentes especialistas serão necessários.\n\n"
            f"Agentes disponíveis:\n"
            f"- subagente_arquitetura: Projetar arquitetura de sistemas\n"
            f"- subagente_codigo: Escrever código\n"
            f"- subagente_debug: Diagnosticar e corrigir erros\n"
            f"- subagente_testes: Criar e executar testes\n"
            f"- subagente_frontend: Criar interfaces e UI\n"
            f"- subagente_backend: Criar APIs e backend\n"
            f"- subagente_analise: Analisar dados e fazer pesquisa\n"
            f"- subagente_criativo: Criar conteúdo criativo\n"
            f"- subagente_seguranca: Revisar vulnerabilidades\n"
            f"- subagente_devops: Configurar ambiente e deploy\n"
            f"- subagente_sandbox: Escreve e EXECUTA código no Sandbox Docker (configuravel: cpu, memory_mb, timeout)\n"
            f"- subagente_validar: VALIDA código executando no Sandbox Docker (configuravel: cpu, memory_mb, timeout)\n"
            f"- gerar_imagem_flux: Gerar imagens com FLUX AI\n"
            f"- gerar_comfyui: Executar workflows no ComfyUI\n"
            f"- gerar_video_wan: Gerar vídeos com Wan AI\n\n"
            f"TAREFA: {tarefa}\n\n"
            f"CONTEXTO DO USUÁRIO: {contexto if contexto else '(nenhum)'}\n\n"
            f"DOCUMENTOS DO RAG:\n{self._rag_contexto if self._rag_contexto else '(nenhum documento relevante encontrado)'}\n\n"
            f"Responda APENAS com:\n"
            f"PLANO: descrição breve do plano\n"
            f"AGENTES: lista separada por vírgula dos agentes necessários (máx 5)\n"
            f"ORDEM: a ordem de execução (separada por >)\n"
            f"Quando a tarefa envolver criação de IMAGENS, VÍDEOS ou DESIGN VISUAL, inclua 'gerar_imagem_flux' na ordem.\n"
            f"EXEMPLO: PLANO: Criar API REST em Python | AGENTES: subagente_arquitetura, subagente_codigo, subagente_testes | ORDEM: subagente_arquitetura > subagente_codigo > subagente_testes\n"
            f"EXEMPLO 2: PLANO: Gerar imagem de paisagem | AGENTES: gerar_imagem_flux | ORDEM: gerar_imagem_flux",
            temperature=0.3
        )

        # Parseia a resposta do CEO
        plano_texto = analise
        agentes_needed = []
        ordem = []

        for line in analise.split("\n"):
            line_lower = line.lower().strip()
            if line_lower.startswith("agentes:"):
                agentes_str = line.split(":", 1)[1].strip()
                agentes_needed = [a.strip() for a in agentes_str.split(",") if a.strip()]
            elif line_lower.startswith("ordem:"):
                ordem_str = line.split(":", 1)[1].strip()
                ordem = [a.strip() for a in ordem_str.split(">") if a.strip()]
            elif line_lower.startswith("plano:"):
                plano_texto = line.split(":", 1)[1].strip()

        if not ordem:
            ordem = agentes_needed or ["subagente_codigo"]

        self.plano = {
            "tarefa": tarefa,
            "contexto": contexto,
            "plano": plano_texto,
            "agentes": agentes_needed,
            "ordem": ordem,
        }

        yield {
            "status": "plano",
            "agente": "👑 CEO",
            "mensagem": f"Plano definido: {plano_texto}",
            "agentes": agentes_needed,
            "ordem": ordem,
            "progresso": 15,
        }

        # ─── PASSO 2: Architect (se necessário) ────────────────────
        resultado_arquitetura = ""
        if "arquitetura" in str(ordem).lower() or "arquitet" in tarefa.lower():
            yield {"status": "executando", "agente": "🧠 Architect", "mensagem": "Projetando arquitetura...", "progresso": 25}

            resultado_arquitetura = self._executar_subagente(
                "subagente_arquitetura",
                f"Projete a arquitetura para: {tarefa}\n\nContexto: {contexto}\n\n"
                f"Forneça: componentes, fluxo de dados, tecnologias recomendadas e plano de implementação."
            )
            self.resultados["arquitetura"] = resultado_arquitetura

            yield {
                "status": "resultado",
                "agente": "🧠 Architect",
                "mensagem": "Arquitetura projetada",
                "resultado": resultado_arquitetura[:500],
                "progresso": 30,
            }

        # ─── PASSO 3: Executa agentes em ordem ────────────────────
        contexto_atual = contexto or resultado_arquitetura
        progresso_base = 30
        passo_atual = 0
        total_passos = max(len(ordem), 1)

        for agente_nome in ordem:
            passo_atual += 1
            progresso = progresso_base + int((passo_atual / total_passos) * 50)

            # Pula architect se já executou
            if "arquitet" in agente_nome.lower() and resultado_arquitetura:
                continue

            # Mapa de nomes amigáveis (fonte única da verdade)
            nomes_amigaveis = {
                "subagente_codigo": "💻 Coder",
                "subagente_debug": "🔍 Debug",
                "subagente_testes": "🧪 Test",
                "subagente_frontend": "🎨 Frontend",
                "subagente_backend": "⚙️ Backend",
                "subagente_analise": "📊 Analyst",
                "subagente_criativo": "✨ Creative",
                "subagente_devops": "🚀 DevOps",
                "subagente_sandbox": "🛡️ Sandbox",
                "subagente_validar": "✅ Validator",
                "gerar_imagem_flux": "🎨 Designer",
                "gerar_comfyui": "🔧 ComfyUI",
                "gerar_video_wan": "🎬 Video Maker",
            }
            if agente_nome not in nomes_amigaveis:
                continue
            nome_exibicao = nomes_amigaveis[agente_nome]

            yield {
                "status": "executando",
                "agente": nome_exibicao,
                "mensagem": f"Executando {nome_exibicao}...",
                "progresso": progresso,
            }

            # Monta a task para o subagente
            task_agente = f"{tarefa}\n\n"
            if resultado_arquitetura:
                task_agente += f"Arquitetura definida:\n{resultado_arquitetura[:1000]}\n\n"
            if contexto_atual and contexto_atual != resultado_arquitetura:
                task_agente += f"Contexto adicional:\n{contexto_atual[:1000]}\n\n"

            if agente_nome == "subagente_sandbox":
                # Estima recursos baseado na complexidade da tarefa
                if any(p in tarefa.lower() for p in ["grande", "pesado", "ml", "mil", "milhao", "1000", "10000", "analise"]):
                    cpu_hint = 1.0
                    mem_hint = 512
                    timeout_hint = 120
                elif any(p in tarefa.lower() for p in ["simples", "rapido", "pequeno", "basico"]):
                    cpu_hint = 0.25
                    mem_hint = 128
                    timeout_hint = 15
                else:
                    cpu_hint = 0.5
                    mem_hint = 256
                    timeout_hint = 60
                task_agente = (
                    f"Escreva codigo Python e execute no Sandbox Docker para: {tarefa}\n\n"
                    f"Contexto:\n{contexto_atual[:1500] if contexto_atual else '(nenhum)'}"
                )
            elif agente_nome == "subagente_validar":
                task_agente = contexto_atual[:3000] if contexto_atual else tarefa
            elif agente_nome == "subagente_debug":
                task_agente += "Analise o código/resultado anterior, encontre problemas e corrija."
            elif agente_nome == "subagente_testes":
                task_agente += "Crie testes unitários completos para o código gerado."
            elif agente_nome == "subagente_frontend":
                task_agente += "Crie a interface do usuário completa e responsiva."
            elif agente_nome == "gerar_imagem_flux":
                # Task para geração de imagem - o prompt já é a descrição da imagem
                task_agente = tarefa
                # Se tiver arquitetura, usa como referência visual
                if resultado_arquitetura:
                    task_agente += f"\n\nReferência de design:\n{resultado_arquitetura[:500]}"
            elif agente_nome == "gerar_comfyui":
                task_agente = tarefa
            elif agente_nome == "gerar_video_wan":
                task_agente = tarefa

            if agente_nome == "subagente_sandbox":
                resultado = self._executar_subagente(
                    agente_nome, task_agente,
                    cpu=cpu_hint, memory_mb=mem_hint, timeout=timeout_hint,
                )
            elif agente_nome == "subagente_validar":
                resultado = self._executar_subagente(
                    agente_nome, task_agente,
                    cpu=0.5, memory_mb=256, timeout=30,
                )
            else:
                resultado = self._executar_subagente(agente_nome, task_agente)

            # Se for coder, salva como resultado principal
            if "codigo" in agente_nome:
                self.resultados["codigo"] = resultado
            else:
                self.resultados[agente_nome] = resultado

            contexto_atual = resultado

            yield {
                "status": "resultado",
                "agente": nome_exibicao,
                "mensagem": f"{nome_exibicao} concluído",
                "resultado": resultado[:500],
                "resultado_completo": resultado,
                "progresso": progresso + 5,
            }

        # ─── PASSO 4: Self-Reflection (Revisão Final) ─────────────
        yield {"status": "executando", "agente": "🤖 Self-Reflection", "mensagem": "Revisando resultado final...", "progresso": 85}

        # Monta o relatório completo
        relatorio_partes = []
        for agente, res in self.resultados.items():
            relatorio_partes.append(f"--- {agente.upper()} ---\n{res[:1500]}")

        relatorio_completo = "\n\n".join(relatorio_partes)

        revisao = self._ollama_chat(
            "Você é o Self-Reflection AI — o revisor final. Sua função é analisar criticamente "
            "o trabalho de TODOS os agentes e identificar problemas, inconsistências, e melhorias.",
            f"TAREFA ORIGINAL: {tarefa}\n\n"
            f"RESULTADO DOS AGENTES:\n{relatorio_completo[:3000]}\n\n"
            f"Analise criticamente:\n"
            f"1. A tarefa original foi completamente resolvida?\n"
            f"2. Há erros, bugs ou problemas de segurança?\n"
            f"3. O código/resultado está completo e funcional?\n"
            f"4. Sugira melhorias específicas.\n\n"
            f"Formato:\n"
            f"✅ PONTOS POSITIVOS: ...\n"
            f"⚠️ PROBLEMAS: ...\n"
            f"🔧 MELHORIAS: ...\n"
            f"📋 VEREDITO: Aprovado / Aprovado com ressalvas / Precisa de correções",
            temperature=0.2
        )

        tempo_total = time.time() - start_time

        resultado_final = {
            "tarefa": tarefa,
            "plano": plano_texto,
            "arquitetura": resultado_arquitetura,
            "resultados_dos_agentes": self.resultados,
            "revisao": revisao,
            "tempo_segundos": round(tempo_total, 1),
            "agentes_utilizados": ordem,
        }

        yield {
            "status": "concluido",
            "agente": "🤖 Self-Reflection",
            "mensagem": "Revisão final concluída",
            "revisao": revisao,
            "resultado_final": resultado_final,
            "progresso": 100,
            "tempo": f"{tempo_total:.1f}s",
        }

        return resultado_final

    def executar_simples(self, tarefa: str, contexto: str = "") -> dict:
        """Versão síncrona que executa todo o pipeline e retorna o resultado."""
        for _ in self.executar(tarefa, contexto):
            pass
        return self.resultados


# ─── Função principal para uso como ferramenta ──────────────────────

def orquestrar(tarefa: str, contexto: str = "", model: str = None) -> str:
    """
    Executa o Orquestrador Mestre com CEO + agentes especializados + Self-Reflection.

    Use para tarefas complexas que exigem múltiplas habilidades:
    - Criar um projeto completo (arquitetura + código + testes)
    - Debug + correção + testes de um sistema
    - Análise + planejamento + execução de tarefas grandes

    Args:
        tarefa: Descrição da tarefa
        contexto: Contexto adicional (opcional)
        model: Modelo específico (opcional)

    Returns:
        String com o resultado completo formatado
    """
    orb = OrquestradorMestre(model=model)
    resultado_final = None

    for step in orb.executar(tarefa, contexto):
        if step["status"] == "concluido":
            resultado_final = step

    if not resultado_final:
        return "[Orquestrador] Erro: não foi possível concluir a tarefa."

    # Formata resultado
    linhas = [
        "╔══════════════════════════════════════════════════╗",
        "║        🤖 ORQUESTRADOR MESTRE — RELATÓRIO       ║",
        "╚══════════════════════════════════════════════════╝",
        "",
        f"📋 TAREFA: {tarefa}",
        f"⏱ Tempo: {resultado_final.get('tempo', 'N/A')}",
        f"📊 Agentes: {len(resultado_final.get('resultado_final', {}).get('agentes_utilizados', []))}",
        "",
        "─── REVISÃO FINAL (Self-Reflection) ───",
        resultado_final.get("revisao", "N/A"),
        "",
        "─── RESULTADOS DOS AGENTES ───",
    ]

    rf = resultado_final.get("resultado_final", {})
    for agente, res in rf.get("resultados_dos_agentes", {}).items():
        linhas.append(f"\n▶ {agente}:")
        linhas.append(res[:1000])
        if len(res) > 1000:
            linhas.append("... (truncado)")

    return "\n".join(linhas)
