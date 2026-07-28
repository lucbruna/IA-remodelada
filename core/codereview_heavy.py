from ._common import *
from .llm import _call_ollama_with_timeout

# =======================================================================
# CODE REVIEW PESADO (estilo revisao de codigo critico do AGENTE_IA)
# -----------------------------------------------------------------------
# Combina em UMA chamada:
#   - code_static_audit  (analise estatica de seguranca, estilo bandit)
#   - code_review        (revisao semantica via Turbo/LLM, se disponivel)
#   - code_benchmark     (medicao de tempo/memoria)
#   - sintese do modelo  (veredito unificado)
# Nao altera o codigo, apenas audita. Ideal para codigo nao-confiavel ou
# critico antes de producao.
# =======================================================================


def codereview_pesado(code: str, linguagem: str = "python", medir: bool = True) -> str:
    """Revisao de codigo completa: seguranca estatica + revisao semantica + benchmark.

    Sempre roda code_static_audit (seguranca) e code_benchmark (se medir=True).
    Se o Turbo estiver disponivel, roda code_review (revisao semantica via LLM)
    e o modelo emite um veredito unificado.
    """
    code = code or ""
    if not code.strip():
        return "Codigo vazio."

    partes = []
    try:
        from .heavy_code import code_static_audit, code_benchmark
        audit = code_static_audit(code)
        partes.append("### 1. AUDITORIA ESTATICA DE SEGURANCA\n" + audit)
        if medir:
            bench = code_benchmark(code, repeat=3)
            partes.append("### 2. BENCHMARK DE PERFORMANCE\n" + bench)
    except Exception as e:
        partes.append(f"(auditoria/benchmark indisponiveis: {e})")

    review = ""
    try:
        from .turbo_api import code_review
        if TURBO_AVAILABLE:
            review = code_review(code, linguagem)
            if review and review != "Turbo nao disponivel.":
                partes.append("### 3. REVISAO SEMANTICA (LLM)\n" + review)
    except Exception:
        pass

    corpo = "\n\n".join(partes)
    try:
        import ollama
        resp = _call_ollama_with_timeout(
            ollama.chat, model=MODEL,
            messages=[{"role": "user", "content": (
                "Voce e um reviewer senior. Com base nas analises abaixo de um "
                "trecho de codigo, emita um VEREDITO curto: APROVADO / REQUER "
                "CORRECOES / REJEITADO, seguido dos 3 pontos mais criticos e se "
                "o codigo e seguro para producao. Em portugues.\n\n" + corpo)}],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        partes.append("### 4. VEREDITO UNIFICADO\n" + resp["message"]["content"])
    except Exception as e:
        partes.append(f"### 4. VEREDITO UNIFICADO\n(sintese indisponivel: {e})")

    return "CODE REVIEW PESADO:\n\n" + "\n\n".join(partes)
