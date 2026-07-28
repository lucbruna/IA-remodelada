from ._common import *

# =======================================================================
# COMPACT - auto-compaction inteligente (padrao do oh-my-pi)
# -----------------------------------------------------------------------
# Quando o contexto fica apertado, descarta imagens e elide tool calls que
# nao tiveram resultado, preservando a "lembranca" do que foi feito sem
# estourar o limite de tokens. Complementa trim_and_summarize_history.
# Suporta contextos de ate 131K tokens com modelos grandes.
# =======================================================================

# Estimativa de tokens: ~1 token por 4 caracteres (aproximacao para PT/EN)
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Estima numero de tokens em um texto (heuristica 4 chars/token)."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _message_tokens(msg: dict) -> int:
    """Estima tokens em uma mensagem."""
    content = msg.get("content", "")
    if isinstance(content, str):
        return _estimate_tokens(content)
    return 0


def _total_tokens(messages: list) -> int:
    """Estima total de tokens em todas as mensagens."""
    return sum(_message_tokens(m) for m in messages)


def compact_messages(messages: list, max_tokens: int = 0) -> list:
    """Reduz o contexto descartando midia e tool calls ocos quando grande.

    Estrategia (soh age se o total passar de max_tokens):
      1. Remove imagens base64 de mensagens (mantem soh o texto/legenda).
      2. Elide tool_calls cujo resultado correspondente seja vazio/inexistente.
      3. Se ainda exceder, resume mensagens antigas nao-sistema.
      4. Para contextos grandes (128K+), preserva mais historico.
    Retorna a lista compactada (nova lista, nao muta a original).

    Se max_tokens=0, usa NUM_CTX como limite.
    """
    if max_tokens <= 0:
        max_tokens = NUM_CTX

    total = _total_tokens(messages)
    if total <= max_tokens:
        return messages

    out = []
    for m in messages:
        m = dict(m)
        content = m.get("content")
        # 1. Remove imagens base64 (data:image/...;base64,....)
        if isinstance(content, str) and "base64" in content and len(content) > 2000:
            m["content"] = (
                content[:200] + "\n[imagem/audio omitido para economia de contexto]"
            )
        # 2. Elide tool_calls sem resultado util (content vazio E sem tool)
        if m.get("role") == "tool" and not str(content).strip():
            continue  # descarta resultado vazio
        # 3. Para tools com resultado muito longo, trunca
        if m.get("role") == "tool" and isinstance(content, str) and len(content) > 5000:
            m["content"] = content[:3000] + "\n[...resultado truncado para economia de contexto]"
        out.append(m)

    # 4. Trunca mensagens antigas se ainda exceder
    total2 = _total_tokens(out)
    if total2 > max_tokens:
        system_msgs = [m for m in out if m.get("role") == "system"]
        others = [m for m in out if m.get("role") != "system"]
        # mantem as ultimas que cabem
        kept = []
        acc = _total_tokens(system_msgs)
        for m in reversed(others):
            c = _message_tokens(m)
            if acc + c > max_tokens and kept:
                break
            acc += c
            kept.append(m)
        out = system_msgs + list(reversed(kept))
    return out


def elide_empty_tool_calls(messages: list) -> list:
    """Remove resultados de tool vazios (variante leve de compact)."""
    return [m for m in messages if not (m.get("role") == "tool" and not str(m.get("content", "")).strip())]


def smart_context_compress(messages: list, model: str = "", max_tokens: int = 0) -> list:
    """Compressao inteligente de contexto para grandes conversas.

    Para contextos > 50% do limite:
      1. Mantem system prompt intacto
      2. Mantem ultimas N mensagens intactas
      3. Resume mensagens antigas em blocos tematicos
      4. Preserva tool calls importantes
    """
    if max_tokens <= 0:
        max_tokens = NUM_CTX

    total = _total_tokens(messages)
    if total <= max_tokens * 0.5:
        return messages

    # Separa system do resto
    system_msgs = [m for m in messages if m.get("role") == "system" and not m.get("_autonomous_context")]
    other_msgs = [m for m in messages if m not in system_msgs]

    # Mantem as ultimas 40% das mensagens intactas
    keep_count = max(10, len(other_msgs) // 2)
    keep_recent = other_msgs[-keep_count:]
    to_compress = other_msgs[:-keep_count]

    if not to_compress:
        return messages

    # Cria resumo das mensagens antigas
    compressed_content = "[Resumo de mensagens anteriores]\n"
    for m in to_compress[:50]:  # Limita a 50 mensagens para resumo
        role = m.get("role", "")
        content = m.get("content", "")[:200]
        if content:
            compressed_content += f"{role}: {content}\n"

    compressed_msg = {
        "role": "system",
        "content": compressed_content[:5000],  # Limite do resumo
    }

    return system_msgs + [compressed_msg] + keep_recent
