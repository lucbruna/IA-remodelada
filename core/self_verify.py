from ._common import *
from .llm import _call_ollama_with_timeout
import ollama

# =======================================================================
# SELF VERIFY - loop de auto-verificacao adversarial (estilo Fable 5)
# -----------------------------------------------------------------------
# Adaptado do SelfVerificationLoop do projeto AGENTE_IA: o agente EXECUTA
# a tarefa, um REVISOR ADVERSARIAL (modelo com prompt critico) aponta
# falhas, o agente CORRIGE e o ciclo repete ate PASSAR ou esgotar
# max_rounds. Ao final anexa um relatorio de verificacao. Combina com
# codereview_pesado para validacao autonoma de codigo/criterios.
# =======================================================================

_VERIFY_DIR = os.path.join(DATA_DIR, "memoria_evolutiva", "verify")
os.makedirs(_VERIFY_DIR, exist_ok=True)


def self_verify(task: str, max_rounds: int = 3, review_depth: str = "normal") -> str:
    """Executa uma tarefa com loop de auto-verificacao adversarial.

    Fluxo:
      1. Agente (modelo) resolve a tarefa.
      2. Revisor adversarial aponta falhas/riscos (prompt critico).
      3. Se houver falhas bloqueantes, agente corrige e repete.
      4. Ate passar ou esgotar max_rounds.

    Retorna o resultado final + relatorio de verificacao (rounds, issues,
    veredito). Para codigo, use combined com codereview_pesado.
    """
    task = (task or "").strip()
    if not task:
        return "Tarefa vazia."

    depth_map = {"quick": "checagem rapida (apenas erros obvios)",
                 "normal": "revisao completa (bugs, seguranca, casos de borda)",
                 "deep": "auditoria profunda (todas as categorias + sugestoes)"}
    depth = depth_map.get(review_depth, depth_map["normal"])

    historico = []
    current_solution = ""

    for r in range(1, max_rounds + 1):
        # 1. Executa (ou re-executa com feedback)
        if r == 1:
            exec_prompt = (
                f"Resolva a tarefa abaixo de forma completa e pronta. "
                f"Se for codigo, entregue o codigo funcional.\n\nTAREFA: {task}"
            )
        else:
            feedback = historico[-1]["review"]
            exec_prompt = (
                f"Tarefa: {task}\n\nSua solucao anterior foi criticada. "
                f"CORRIJA com base no feedback abaixo e entregue a versao "
                f"revisada e final:\n\nFEEDBACK DO REVISOR:\n{feedback}"
            )
        try:
            sol = _call_ollama_with_timeout(
                ollama.chat, model=MODEL,
                messages=[{"role": "user", "content": exec_prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.3},
            )
            current_solution = sol["message"]["content"]
        except Exception as e:
            return f"Erro ao executar tarefa (round {r}): {e}"

        # 2. Revisor adversarial
        review_prompt = (
            f"Voce e um REVISOR ADVERSARIAL extremamente critico. Analise a "
            f"solucao abaixo para a tarefa. Faca uma {depth}. Responda EM "
            f"PORTUGUES com formato rigido:\n"
            f"VEREDITO: APROVADO | REQUER_CORRECAO | REJEITADO\n"
            f"ISSUAS:\n- [severidade] descricao (onde)\n"
            f"(severidade: CRITICA, MAJOR, MENOR, SUGESTAO). Se APROVADO, nao "
            f"liste issues.\n\nTAREFA: {task}\n\nSOLUCAO:\n{current_solution}"
        )
        try:
            rev = _call_ollama_with_timeout(
                ollama.chat, model=MODEL,
                messages=[{"role": "user", "content": review_prompt}],
                options={"num_ctx": NUM_CTX, "temperature": 0.1},
            )
            review = rev["message"]["content"]
        except Exception as e:
            review = f"(revisor indisponivel: {e})"

        veredito = "REQUER_CORRECAO"
        for linha in review.splitlines():
            if linha.strip().upper().startswith("VEREDITO"):
                veredito = linha.split(":", 1)[-1].strip().upper()
                break

        historico.append({
            "round": r, "solution": current_solution, "review": review,
            "verdict": veredito,
        })

        if "APROVADO" in veredito:
            break

    # Relatorio final
    aprovado = any(h["verdict"] == "APROVADO" for h in historico)
    relatorio = (
        f"[SELF-VERIFY] rounds={len(historico)}/{max_rounds} "
        f"veredito_final={'APROVADO' if aprovado else 'NAO APROVADO'}\n\n"
    )
    for h in historico:
        relatorio += (
            f"--- Round {h['round']} [{h['verdict']}] ---\n"
            f"{h['review'][:1500]}\n\n"
        )
    relatorio += "=== SOLUCAO FINAL (revisada) ===\n" + current_solution

    # Salva relatorio
    try:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        _save_json(os.path.join(_VERIFY_DIR, f"verify_{ts}.json"), {
            "task": task, "rounds": historico, "approved": aprovado,
        })
    except Exception:
        pass

    return relatorio


def self_verify_code(task: str, linguagem: str = "python", max_rounds: int = 3) -> str:
    """Variante para codigo: combina self_verify com codereview_pesado.

    O agente gera/corrige o codigo em loop adversarial e, ao final, roda
    codereview_pesado (auditoria estatica + benchmark) sobre a solucao
    aprovada. Retorna codigo final + revisao pesada + relatorio de verify.
    """
    task = (task or "").strip()
    if not task:
        return "Tarefa vazia."

    verify = self_verify(
        f"Gere/corrija codigo {linguagem} para: {task}. Entregue APENAS o "
        f"codigo fonte completo e funcional, sem explicacoes.",
        max_rounds=max_rounds,
    )
    # Extrai a solucao final do relatorio de verify
    if "=== SOLUCAO FINAL (revisada) ===" in verify:
        codigo = verify.split("=== SOLUCAO FINAL (revisada) ===", 1)[-1].strip()
    else:
        codigo = verify

    try:
        from .codereview_heavy import codereview_pesado
        review = codereview_pesado(codigo, linguagem=linguagem, medir=False)
    except Exception as e:
        review = f"(codereview indisponivel: {e})"

    return (
        "SELF-VERIFY DE CODIGO:\n\n"
        "### CODIGO FINAL\n```" + linguagem + "\n" + codigo + "\n```\n\n"
        "### RELATORIO DE VERIFICACAO\n" + verify[:2000] + "\n\n"
        "### CODE REVIEW PESADO\n" + review
    )
