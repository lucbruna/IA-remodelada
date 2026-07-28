from ._common import *
from .registry import *
from .plugins_api import _plugin_manager
# =======================================================================
# Integracao com Memoria Evolutiva (plugin)
# =======================================================================

def run_memory_pipeline(texto_usuario: str) -> str:
    """Processa automaticamente uma mensagem do usuario pela memoria evolutiva.
    Retorna feedback se algo foi aprendido, ou string vazia.
    Instale o plugin plugin_memoria_evolutiva.py para ativar.
    """
    try:
        from plugins.plugin_memoria_evolutiva import processar_conversa, aplicar_decay
        resultado = processar_conversa(texto_usuario)
        # Aplica decay periodico (a cada 10 interacoes, aproximadamente)
        aplicar_decay()

        # Também executa o ciclo de auto-evolucao periodicamente
        # (a cada N interacoes para nao sobrecarregar)
        try:
            from plugins.plugin_auto_evolucao import auto_evolve
            # Evolucao menos frequente que a memoria para evitar overhead excessivo
            # Usa hash simples do texto para determinar quando evoluir
            hash_val = hash(texto_usuario) % AUTO_EVOLVE_INTERVAL
            if hash_val == 0:  # Aproximadamente 1 em N chamadas
                evolucao_result = auto_evolve()
                # Aplica os parâmetros otimizados em runtime (sem reiniciar).
                reload_config()
                if evolucao_result and evolucao_result.strip():
                    # Combina os resultados
                    if resultado:
                        resultado += "\n\n" + evolucao_result
                    else:
                        resultado = evolucao_result
        except Exception:
            # Silenciosamente ignora erros de evolucao para nao quebrar a pipeline principal
            pass

        return resultado or ""
    except Exception:
        return ""


def get_memory_context_str() -> str:
    """Retorna contexto da memoria evolutiva para incluir no prompt."""
    try:
        from plugins.plugin_memoria_evolutiva import gerar_contexto_memoria
        return gerar_contexto_memoria()
    except Exception:
        return ""


# Atalho: TOOLS aponta para TOOLS_LIST (compatibilidade)
TOOLS = TOOLS_LIST

# Carrega plugins automaticamente
_plugin_manager.load_all(AVAILABLE_FUNCTIONS, TOOLS_LIST)

def _get_memoria_evolutiva_context() -> str:
    """Tenta carregar contexto da memoria evolutiva (plugin), se disponivel."""
    try:
        from plugins.plugin_memoria_evolutiva import gerar_contexto_memoria
        return "\n" + gerar_contexto_memoria()
    except Exception:
        return ""


def _build_system_prompt() -> str:
    """Gera o system prompt OTIMIZADO a partir das ferramentas registradas."""
    lines = [
        "# IDENTIDADE E IDIOMA",
        "Voce e o Agente Local. Responda SEMPRE em PORTUGUES DO BRASIL.",
        "",
        "# MANDAMENTOS",
        "1. Use ferramentas para agir, nunca descreva acoes. Nao recuse pedidos.",
        "2. Raciocine em voz alta: [PASSO 1: ...] antes de cada tool call.",
        "3. Quebre tarefas complexas em subtarefas. Delegue a sub-agentes se >3 etapas.",
        "4. Mostre resultados reais (caminhos, tamanhos, linhas de codigo).",
        "5. Para acoes irreversiveis, peca confirmacao primeiro.",
        "6. Aprenda com cada interacao: memoria, perfil, grafo, hindsight.",
        "7. Auto-verifique: self_verify(task) para validacao adversarial.",
        "8. Use o Metodo Fable (.agents/fable-method/) para tarefas complexas:",
        "   classifique o pedido, defina 'pronto', colete evidencias, decida,",
        "   aja cirurgicamente, verifique por observacao, relate conclusao primeiro.",
        "",
        "--- FERRAMENTAS ---",
    ]
    for t in TOOLS_LIST:
        name = t["function"]["name"]
        desc = t["function"]["description"]
        params = t["function"].get("parameters", {}).get("properties", {})
        param_str = ", ".join(params.keys()) if params else ""
        lines.append(f"  {name}({param_str}): {desc.split('.')[0]}.")

    lines.append("")
    lines.append("# GERENCIAMENTO DE MODELOS")
    lines.append("  model_detect: detecta hardware (RAM/VRAM/GPU)")
    lines.append("  model_recommend: recomenda melhor modelo para seu hardware")
    lines.append("  model_list: lista instalados e disponiveis")
    lines.append("  model_download: baixa novo modelo do Ollama")
    lines.append("  model_benchmark: mede velocidade/qualidade do modelo")
    lines.append("  model_switch: altera modelo padrao em runtime")
    lines.append("")
    lines.append("# SUB-AGENTES (delegue tarefas complexas)")
    lines.append("  subagente_codigo: engenheiro senior (scripts, debug, refactor, testes)")
    lines.append("  subagente_analise: pesquisador/analista (comparacoes, planejamento)")
    lines.append("  subagente_criativo: escritor/designer (nomes, textos, brainstorming)")
    lines.append("  subagent_run_isolated(role, task): sub-agente isolado em worktree git")
    lines.append("")
    lines.append("# FLUXOS ESPECIALIZADOS")
    lines.append("  CODIGO: gerar_codigo -> code_review -> run_python_code -> self_verify_code")
    lines.append("  DOWNLOAD: download_file/git_clone -> extract_file -> ler resultado")
    lines.append("  MEMORIA: memoria_contexto() no inicio, hindsight_retain() para fatos importantes")
    lines.append("  SEGURANCA: code_static_audit antes de rodar codigo; use resolve_* para destrutivas")
    lines.append("  FABLE METHOD: /fable-method loop completo; /fable-method plan (para/plano); /fable-judge (verificacao adversarial)")
    lines.append("  HEAVY: heavy_plan_create + heavy_plan_run + heavy_plan_reduce para tarefas grandes")
    lines.append("  MCP: mcp_call/mcp_list_tools para servicos MCP externos")
    lines.append("  CRYPTO: crypto_aes_* (GCM), crypto_rsa_*, crypto_pqc_* (pos-quantico)")
    lines.append("  HOOKS: hook_register/hook_list para observabilidade")
    lines.append("  LAUNCH: launch_start/logs/stop/list para servicos de longa duracao")
    lines.append("  DASHBOARD: abrir_dashboard() para metricas em tempo real")
    lines.append("  API: python agente_api_server.py para REST API")

    resultado = "\n".join(lines)
    resultado += "\n\n--- LEMBRETE FINAL ---\n"
    resultado += "TODA resposta em PORTUGUES DO BRASIL. Use ferramentas, nao apenas converse.\n"
    resultado += _get_memoria_evolutiva_context()
    return resultado


SYSTEM_PROMPT = _build_system_prompt()


