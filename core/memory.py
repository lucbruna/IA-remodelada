from ._common import *
import ollama
# =======================================================================
# MEMORIA PERSISTENTE (fatos que o agente lembra entre sessoes)
# =======================================================================

def remember(key: str, value: str) -> str:
    """Guarda um fato na memoria de longo prazo, para lembrar em conversas futuras."""
    memory = _load_json(MEMORY_FILE, {})
    memory[key] = value
    _save_json(MEMORY_FILE, memory)
    return f"Guardado na memoria: '{key}' = '{value}'"


def recall(key: str) -> str:
    """Busca um fato guardado anteriormente na memoria, pela chave."""
    memory = _load_json(MEMORY_FILE, {})
    if key in memory:
        return memory[key]
    return f"Nao encontrei nada guardado com a chave '{key}'."


def forget(key: str) -> str:
    """Remove um fato da memoria de longo prazo."""
    memory = _load_json(MEMORY_FILE, {})
    if key in memory:
        del memory[key]
        _save_json(MEMORY_FILE, memory)
        return f"Removido da memoria: '{key}'"
    return f"Nao havia nada guardado com a chave '{key}'."


def list_memories() -> str:
    """Lista todos os fatos guardados na memoria de longo prazo."""
    memory = _load_json(MEMORY_FILE, {})
    if not memory:
        return "A memoria esta vazia."
    return "\n".join(f"{k}: {v}" for k, v in memory.items())


def load_conversation_history() -> list:
    """Carrega o historico de conversas salvo em sessoes anteriores.

    Usa SQLite (history_db) se disponivel, senao fallback para JSON.
    """
    try:
        from .history_db import load_messages
        return load_messages("default")
    except Exception:
        return _load_json(HISTORY_FILE, [])


def save_conversation_history(messages: list) -> None:
    """Salva o historico de conversas para a proxima sessao.

    Usa SQLite (history_db) se disponivel, senao fallback para JSON.
    Guarda apenas os campos serializaveis (role/content/timestamp).
    """
    try:
        from .history_db import save_messages
        save_messages(messages, "default")
    except Exception:
        # Fallback: salva em JSON
        clean = []
        for m in messages:
            entry = {"role": m.get("role"), "content": m.get("content", "")}
            if m.get("timestamp"):
                entry["timestamp"] = m["timestamp"]
            clean.append(entry)
        _save_json(HISTORY_FILE, clean)


def trim_and_summarize_history(messages: list, model: str) -> list:
    from agente_core import _call_ollama_with_timeout  # lazy p/ suportar patches de teste
    """
    Evita que a conversa cresca infinitamente e trave o modelo por excesso
    de contexto: quando passa de MAX_HISTORY_MESSAGES, resume as mensagens
    mais antigas em um unico bloco de texto e mantem as mais recentes
    inteiras. Isso preserva a "lembranca" do que foi conversado sem
    sobrecarregar cada chamada.
    """
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]

    keep_recent = other_msgs[-(MAX_HISTORY_MESSAGES - 5):]
    to_summarize = other_msgs[: -(MAX_HISTORY_MESSAGES - 5)]

    if not to_summarize:
        return messages

    text_to_summarize = "\n".join(
        f"{m.get('role')}: {m.get('content', '')}" for m in to_summarize if m.get("content")
    )

    try:
        import ollama
        summary_response = _call_ollama_with_timeout(
            ollama.chat,
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Resuma a conversa abaixo em um paragrafo curto, guardando "
                        "apenas fatos e decisoes importantes:\n\n" + text_to_summarize
                    ),
                }
            ],
            options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        )
        summary_text = summary_response["message"]["content"]
    except Exception as e:
        logging.warning("Falha ao resumir historico antigo: %s", e)
        summary_text = "(resumo indisponivel - contexto antigo descartado)"

    summary_msg = {
        "role": "system",
        "content": f"[Resumo de mensagens anteriores]: {summary_text}",
    }

    return system_msgs + [summary_msg] + keep_recent


