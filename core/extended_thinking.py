"""
core/extended_thinking.py
========================
Padroes de raciocinio avancado: chain-of-thought, self-reflection,
extended thinking e self-correction.

Inspirado por:
  - Claude Extended Thinking: raciocinio passo a passo antes de responder
  - Fable 5 Self-Verification: loop adversarial de verificacao
  - OpenAI o1/o3: chain-of-thought profundo
  - Anthropic Prompt Engineering: structured reasoning

Funcionalidades:
  - Chain-of-Thought (CoT): raciocinio passo a passo
  - Self-Reflection: o modelo revisa sua propria resposta
  - Extended Thinking: pensar antes de responder
  - Self-Correction: detecta e corrige erros
  - Adversarial Verification: loop de verificacao adversarial
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ._common import logging, json, datetime


# --- Chain-of-Thought Prompts ---

COT_SYSTEM_PROMPT = """Voce e um assistente que pensa passo a passo antes de responder.

Para cada pergunta:
1. Analise o que esta sendo pedido
2. Identifique informacoes relevantes
3. Raciocine passo a passo
4. Chegue a uma conclusao
5. Apresente a resposta final

IMPORTANTE: Primeiro faca o raciocinio (pode ser omitido), depois a resposta final."""

REFLECTION_SYSTEM_PROMPT = """Voce e um assistente que revisa e melhora suas proprias respostas.

Apos gerar uma resposta:
1. Revise se esta correta e completa
2. Identifique possiveis erros ou lacunas
3. Melhore a resposta se necessario
4. Apresente a versao final revisada"""

SELF_CORRECTION_PROMPT = """Voce e um assistente que detecta e corrige erros automaticamente.

Quando receber uma tarefa:
1. Execute-a normalmente
2. Verifique o resultado por erros
3. Se encontrar erros, corrija-os
4. Apresente a versao corrigida

Sempre explique o que foi corrigido e por que."""


# --- Core Functions ---

def chain_of_thought(
    question: str,
    context: str = "",
    model_fn=None,
    show_reasoning: bool = False,
) -> str:
    """Aplica padrao Chain-of-Thought para responder uma pergunta.

    Args:
        question: A pergunta a ser respondida
        context: Contexto adicional opcional
        model_fn: Funcao do modelo (question) -> response
        show_reasoning: Se True, mostra o raciocinio

    Returns:
        Resposta com raciocinio aplicado
    """
    if model_fn is None:
        return f"[CoT] Raciocinio para: {question}\n\n( modelo nao configurado )"

    # Monta prompt com CoT
    cot_prompt = f"""Analise a pergunta abaixo passo a passo:

PERGUNTA: {question}
{f'CONTEXTO: {context}' if context else ''}

RACIOCINIO PASSO A PASSO:
1. Primeiro, identifique o que esta sendo pedido
2. Depois, reuna as informacoes relevantes
3. Em seguida, analise cada parte
4. Por fim, chegue a conclusao

RESPOSTA FINAL:"""

    response = model_fn(cot_prompt)

    if show_reasoning:
        return response
    else:
        # Tenta extrair apenas a resposta final
        lines = response.split("\n")
        final_lines = []
        in_answer = False
        for line in lines:
            lower = line.lower().strip()
            if any(marker in lower for marker in ["resposta final:", "conclusao:", "portanto:", "em resumo:"]):
                in_answer = True
            if in_answer:
                final_lines.append(line)

        if final_lines:
            return "\n".join(final_lines).strip()
        return response


def self_reflection(
    question: str,
    initial_answer: str,
    model_fn=None,
) -> str:
    """Faz o modelo revisar e melhorar sua propria resposta.

    Args:
        question: Pergunta original
        initial_answer: Resposta inicial gerada
        model_fn: Funcao do modelo

    Returns:
        Resposta revisada e melhorada
    """
    if model_fn is None:
        return initial_answer

    reflection_prompt = f"""REVISE a resposta abaixo para a pergunta dada.

PERGUNTA: {question}
RESPOSTA INICIAL: {initial_answer}

INSTRUCOES DE REVISAO:
1. A resposta esta correta?
2. Esta completa? Falta algo?
3. Ha erros logicos ou factuais?
4. Esta bem explicada?
5. Pode ser melhorada?

Se houver problemas, corrija. Caso contrario, confirme que esta boa.

RESPOSTA REVISADA:"""

    revised = model_fn(reflection_prompt)
    return revised


def extended_thinking(
    question: str,
    context: str = "",
    model_fn=None,
    thinking_budget: str = "moderado",
) -> str:
    """Aplica padrao Extended Thinking (pensar antes de responder).

    Inspirado no Claude Extended Thinking e OpenAI o1.

    Args:
        question: Pergunta complexa
        context: Contexto adicional
        model_fn: Funcao do modelo
        thinking_budget: "rapido", "moderado", "profundo"

    Returns:
        Resposta com raciocinio profundo
    """
    if model_fn is None:
        return f"[Extended Thinking] {question}\n\n( modelo nao configurado )"

    budget_instructions = {
        "rapido": "Pense brevemente (2-3 passos).",
        "moderado": "Pense cuidadosamente (5-7 passos).",
        "profundo": "Pense extensivamente (10+ passos), considere multiplas perspectivas.",
    }

    thinking_prompt = f"""EXTENDED THINKING MODE ATIVADO

{budget_instructions.get(thinking_budget, budget_instructions['moderado'])}

PERGUNTA: {question}
{f'CONTEXTO: {context}' if context else ''}

PENSE ANTES DE RESPONDER:

1. COMPRENSAO: O que exatamente esta sendo perguntado?
2. INFORMACOES: Que dados eu tenho? O que falta?
3. ANALISE: Qual a melhor abordagem?
4. ALTERNATIVAS: Ha outras formas de resolver?
5. VERIFICACAO: Minha conclusao faz sentido?
6. LIMITACOES: O que eu NAO sei?
7. RESPOSTA: Apresente a resposta final

PENSAIMENTO:"""

    response = model_fn(thinking_prompt)
    return response


def self_correction(
    task: str,
    code_or_answer: str,
    model_fn=None,
    error_context: str = "",
) -> str:
    """Detecta e corrige erros automaticamente.

    Args:
        task: Tarefa original
        code_or_answer: Codigo/resposta a ser verificado
        model_fn: Funcao do modelo
        error_context: Contexto do erro (se houver)

    Returns:
        Versao corrigida com explicacao
    """
    if model_fn is None:
        return code_or_answer

    correction_prompt = """Analise e corrija o codigo/resposta abaixo.

TAREFA: {task}
CONTEUDO:
{code_or_answer}
{f'CONTEXTO DO ERRO: {error_context}' if error_context else ''}

INSTRUCOES:
1. Identifique TODOS os erros (sintaxe, logica, seguranca, performance)
2. Para cada erro, explique o problema
3. Forneça a versao corrigida
4. Explique as correcoes feitas

VERIFICACAO:
- Codigo compila/roda sem erros?
- Logica esta correta?
- Ha vulnerabilities de seguranca?
- Performance e aceitavel?

CORRECAO:"""

    corrected = model_fn(correction_prompt.format(
        task=task,
        code_or_answer=code_or_answer,
    ))
    return corrected


def adversarial_verification(
    task: str,
    solution: str,
    model_fn=None,
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """Loop adversarial de verificacao (estilo Fable 5).

    Um revisor critico aponta falhas, o agente corrige, e o ciclo
    repete ate aprovar ou esgotar rounds.

    Args:
        task: Tarefa original
        solution: Solucao a ser verificada
        model_fn: Funcao do modelo
        max_rounds: Maximo de rodadas de verificacao

    Returns:
        Dict com solution, rounds, veredito, issues
    """
    if model_fn is None:
        return {
            "solution": solution,
            "rounds": 0,
            "verdict": "SEM_VERIFICACAO",
            "issues": [],
        }

    current_solution = solution
    history = []

    for round_num in range(1, max_rounds + 1):
        # Revisor adversarial
        review_prompt = f"""VOCE E UM REVISOR ADVERSARIAL EXTREMAMENTE CRITICO.

TAREFA: {task}
SOLUCAO ATUAL: {current_solution}

ANALISE RIGOROSAMENTE a solucao e encontre FALHAS:
- Erros logicos ou factuais
- Incompletudes
- Problemas de seguranca
- Code smells
- Casos de borda nao tratados
- Melhorias possiveis

Se a solucao estiver APROVADA, responda EXATAMENTE: VEREDITO: APROVADO
Caso contrario, liste os problemas encontrados.

VERIFICACAO:"""

        review = model_fn(review_prompt)

        # Verifica se aprovado
        if "APROVADO" in review.upper():
            history.append({"round": round_num, "review": review, "action": "aprovado"})
            return {
                "solution": current_solution,
                "rounds": round_num,
                "verdict": "APROVADO",
                "issues": [],
                "history": history,
            }

        # Extrai issues
        issues = [line.strip() for line in review.split("\n") if line.strip().startswith("-")]

        # Correcao
        correction_prompt = f"""A solucao anterior foi REJEITADA pelo revisor.

TAREFA: {task}
SOLUCAO ANTERIOR: {current_solution}
FEEDBACK DO REVISOR: {review}

CORRIJA a solucao com base no feedback. Entregue a versao CORRIGIDA:

SOLUCAO CORRIGIDA:"""

        current_solution = model_fn(correction_prompt)
        history.append({
            "round": round_num,
            "review": review[:200],
            "issues": issues,
            "action": "corrigido",
        })

    # Esgotou rounds
    return {
        "solution": current_solution,
        "rounds": max_rounds,
        "verdict": "REQUER_REVISAO_HUMANA",
        "issues": issues,
        "history": history,
    }


def structured_reasoning(
    question: str,
    reasoning_type: str = "auto",
    model_fn=None,
) -> str:
    """Raciocinio estruturado adaptativo.

    Args:
        question: Pergunta
        reasoning_type: "auto", "dedutivo", "indutivo", "abduutivo", "analogico"
        model_fn: Funcao do modelo

    Returns:
        Resposta com raciocinio estruturado
    """
    if model_fn is None:
        return f"[Structured Reasoning] {question}"

    # Auto-detecta tipo de raciocinio
    if reasoning_type == "auto":
        q_lower = question.lower()
        if any(w in q_lower for w in ["por que", "cause", "motivo", "razao"]):
            reasoning_type = "dedutivo"
        elif any(w in q_lower for w in ["exemplo", "caso", "padrao", "tendencia"]):
            reasoning_type = "indutivo"
        elif any(w in q_lower for w in ["hipotese", "possivelmente", "provavelmente"]):
            reasoning_type = "abduutivo"
        elif any(w in q_lower for w in ["parecido", "similar", "como", "assim como"]):
            reasoning_type = "analogico"
        else:
            reasoning_type = "dedutivo"

    prompts = {
        "dedutivo": """RACIOCINIO DEDUTIVO (Geral -> Especifico):
1. Principio geral: qual e a regra/teoria?
2. Condicoes especificas: o que se aplica ao caso?
3. Conclusao logica: o que se segue necessariamente?

PERGUNTA: {q}
RACIOCINIO:""",

        "indutivo": """RACIOCINIO INDUTIVO (Especifico -> Geral):
1. Observacoes: quais sao os dados/casos?
2. Padroes: o que se repete?
3. Generalizacao: qual e a tendencia/regra?

PERGUNTA: {q}
RACIOCINIO:""",

        "abduutivo": """RACIOCINIO ABDUCTIVO (Melhor explicacao):
1. Observacao: o que esta acontecendo?
2. Hipoteses: quais sao as explicacoes possiveis?
3. Avaliacao: qual e a mais provavel?

PERGUNTA: {q}
RACIOCINIO:""",

        "analogico": """RACIOCINIO ANALOGICO (Similaridade):
1. Dominio original: como funciona o caso conhecido?
2. Mapeamento: quais sao as correspondencias?
3. Transferencia: o que vale no novo caso?

PERGUNTA: {q}
RACIOCINIO:""",
    }

    prompt = prompts.get(reasoning_type, prompts["dedutivo"]).format(q=question)
    return model_fn(prompt)


# --- Ferramentas para o agente ---

def cot_reasoning_tool(question: str) -> str:
    """Ferramenta: Chain-of-Thought reasoning."""
    from .llm_backend import get_backend, ChatMessage
    backend = get_backend()

    def model_fn(q):
        resp = backend.chat([
            ChatMessage(role="system", content=COT_SYSTEM_PROMPT),
            ChatMessage(role="user", content=q),
        ], temperature=0.3)
        return resp.content

    return chain_of_thought(question, model_fn=model_fn)


def self_reflection_tool(question: str, answer: str) -> str:
    """Ferramenta: Self-reflection na resposta."""
    from .llm_backend import get_backend, ChatMessage
    backend = get_backend()

    def model_fn(q):
        resp = backend.chat([
            ChatMessage(role="system", content=REFLECTION_SYSTEM_PROMPT),
            ChatMessage(role="user", content=q),
        ], temperature=0.3)
        return resp.content

    return self_reflection(question, answer, model_fn=model_fn)


def extended_thinking_tool(question: str, budget: str = "moderado") -> str:
    """Ferramenta: Extended thinking profundo."""
    from .llm_backend import get_backend, ChatMessage
    backend = get_backend()

    def model_fn(q):
        resp = backend.chat([
            ChatMessage(role="system", content="Pense passo a passo antes de responder."),
            ChatMessage(role="user", content=q),
        ], temperature=0.3, max_tokens=2000)
        return resp.content

    return extended_thinking(question, model_fn=model_fn, thinking_budget=budget)


def adversarial_verify_tool(task: str, solution: str) -> str:
    """Ferramenta: Verificacao adversarial (Fable 5 style)."""
    from .llm_backend import get_backend, ChatMessage
    backend = get_backend()

    def model_fn(q):
        resp = backend.chat([
            ChatMessage(role="user", content=q),
        ], temperature=0.3)
        return resp.content

    result = adversarial_verification(task, solution, model_fn=model_fn, max_rounds=3)
    return json.dumps(result, ensure_ascii=False, indent=2)
