from ._common import *
# =======================================================================
# FUNCOES TURBO INTEGRADAS (disponiveis mesmo sem import do modulo)
# =======================================================================

def task_decompose(task: str) -> str:
    """Decompõe uma tarefa complexa em subtarefas executáveis. Use para problemas grandes."""
    if TURBO_AVAILABLE:
        return agente_turbo.task_decompose(task)
    return agente_turbo.task_decompose(task) if TURBO_AVAILABLE else "Turbo nao disponivel."


def structured_reasoning(task: str, contexto: str = "") -> str:
    """Gera raciocínio passo-a-passo estruturado para resolver problemas complexos."""
    if TURBO_AVAILABLE:
        return agente_turbo.structured_reasoning(task, contexto)
    return "Turbo nao disponivel."


def code_review(code: str, linguagem: str = "python") -> str:
    """Revisa código fonte e aponta problemas, sugestões e melhorias."""
    if TURBO_AVAILABLE:
        return agente_turbo.code_review(code, linguagem)
    return "Turbo nao disponivel."


def turbo_diagnostico() -> str:
    """Diagnóstico completo do sistema turbo: cache, estratégias, configuração."""
    if TURBO_AVAILABLE:
        return agente_turbo.turbo_diagnostico()
    return "Modulo turbo nao carregado."


def turbo_cache_clear() -> str:
    """Limpa todo o cache de chamadas de ferramentas."""
    if TURBO_AVAILABLE:
        count = agente_turbo._cache_clear()
        return f"Cache limpo: {count} arquivos removidos."
    return "Turbo nao disponivel."


def smart_extract(text: str, query: str = "", max_chars: int = 2000) -> str:
    """Extrai partes relevantes de um texto grande. Se query for fornecida, prioriza trechos relacionados."""
    if TURBO_AVAILABLE:
        return agente_turbo.smart_extract(text, max_chars, query)
    return text[:max_chars] if len(text) > max_chars else text


def analyze_image_advanced(path: str, questions: str = "") -> str:
    """Análise multi-estágio de imagem: OCR + descrição + perguntas específicas."""
    if TURBO_AVAILABLE:
        qlist = [q.strip() for q in questions.split("|")] if questions else None
        return agente_turbo.analyze_image_advanced(path, qlist)
    from agente_core import describe_image
    return describe_image(path, questions or "Descreva esta imagem")


