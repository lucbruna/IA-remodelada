from ._common import *
import ollama

# =======================================================================
# HINDSIGHT - memoria duradoura estilo OMP (oh-my-pi)
# -----------------------------------------------------------------------
# Implementa o padrao de "memory bank" do oh-my-pi:
#   retain   -> enfileira fatos duradouros no banco de memoria
#   recall   -> busca semantica leve (embeddings locais) por significado
#   reflect  -> pede ao modelo que sintetize uma resposta sobre o banco
#   checkpoint -> marca o estado da conversa para colapso/relatorio futuro
#   rewind   -> poda contexto exploratorio, mantendo um relatorio conciso
# =======================================================================

HINDSIGHT_FILE = os.path.join(DATA_DIR, "agente_data", "memoria_evolutiva", "hindsight.json")
CHECKPOINT_FILE = os.path.join(DATA_DIR, "agente_data", "memoria_evolutiva", "checkpoints.json")


def _ensure_dirs():
    os.makedirs(os.path.dirname(HINDSIGHT_FILE), exist_ok=True)


def _load_hindsight() -> dict:
    data = _load_json(HINDSIGHT_FILE, {"facts": []})
    if "facts" not in data:
        data["facts"] = []
    return data


def _save_hindsight(data: dict) -> None:
    _ensure_dirs()
    _save_json(HINDSIGHT_FILE, data)


def _embed(text: str) -> Optional[list]:
    """Gera embedding local via Ollama (modelo nomic-embed-text se disponivel)."""
    try:
        resp = _call_ollama_with_timeout(
            ollama.embeddings,
            model="nomic-embed-text",
            prompt=text,
        )
        return resp.get("embedding")
    except Exception:
        return None


def _cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def hindsight_retain(fact: str) -> str:
    """Enfileira um fato duradouro no banco de memoria (Hindsight).

    Use para guardar aprendizados, preferencias do usuario, decisoes e
    conclucoes que devem sobreviver entre sessoes. Substitui fatos
    semanticamente identicos para evitar duplicatas.
    """
    fact = (fact or "").strip()
    if not fact:
        return "Fato vazio, nada guardado."
    data = _load_hindsight()
    emb = _embed(fact)
    # Substitui fato similar (cosine > threshold) para dedup.
    if emb:
        for f in data["facts"]:
            if f.get("embedding") and _cosine(emb, f["embedding"]) > HINDSIGHT_DEDUP_THRESHOLD:
                f["text"] = fact
                f["ts"] = datetime.now().isoformat()
                f["embedding"] = emb
                _save_hindsight(data)
                return f"Fato atualizado no banco de memoria: '{fact}'"
    data["facts"].append({
        "text": fact,
        "ts": datetime.now().isoformat(),
        "embedding": emb,
    })
    _save_hindsight(data)
    return f"Fato guardado no banco de memoria (Hindsight): '{fact}'"


def hindsight_recall(query: str, top_k: int = 5) -> str:
    """Busca no banco de memoria por significado (nao so por palavra-chave).

    Retorna os fatos mais proximos da consulta, mesmo que usem palavras
    diferentes. Se nao houver embeddings, faz fallback a substring.
    """
    query = (query or "").strip()
    if not query:
        return "Consulta vazia."
    data = _load_hindsight()
    facts = data["facts"]
    if not facts:
        return "O banco de memoria (Hindsight) esta vazio. Use hindsight_retain para guardar fatos."
    q_emb = _embed(query)
    if q_emb:
        scored = []
        for f in facts:
            score = _cosine(q_emb, f.get("embedding")) if f.get("embedding") else 0.0
            scored.append((score, f["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [(s, t) for s, t in scored[:top_k] if s > 0.2]
        if not top:
            top = [(1.0, t) for _, t in scored[:top_k]]
    else:
        ql = query.lower()
        top = [(1.0, f["text"]) for f in facts if ql in f["text"].lower()][:top_k]
        if not top:
            top = [(1.0, f["text"]) for f in facts[:top_k]]
    linhas = [f"[{s:.2f}] {t}" for s, t in top]
    return "Banco de memoria (Hindsight) — fatos relacionados:\n" + "\n".join(linhas)


def hindsight_reflect(question: str) -> str:
    """Pede ao modelo que sintetize uma resposta sobre o banco de memoria.

    Reune os fatos mais relevantes e usa o LLM para responder a pergunta
    com base no que foi lembrado, em vez de apenas listar fatos.
    """
    question = (question or "").strip()
    if not question:
        return "Pergunta vazia."
    relevantes = hindsight_recall(question, top_k=8)
    try:
        resp = _call_ollama_with_timeout(
            ollama.chat,
            model=MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Voce e o banco de memoria de longo prazo de um assistente. "
                    "Com base EXCLUSIVAMENTE nos fatos abaixo, responda a pergunta "
                    "do usuario de forma sintetica e direta em portugues.\n\n"
                    "FATOS GUARDADOS:\n" + relevantes + "\n\nPERGUNTA: " + question
                ),
            }],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        return resp["message"]["content"]
    except Exception as e:
        return f"Nao consegui sintetizar (modelo indisponivel): {e}\n\n{relevantes}"


def hindsight_checkpoint(label: str = "") -> str:
    """Marca o estado atual da conversa para um colapso/relatorio futuro.

    Armazena um instantaneo da conversa (ate o momento) identificado por
    um rotulo. Depois pode ser usado por hindsight_rewind para resumir.
    """
    label = (label or "").strip() or datetime.now().isoformat()
    msgs = load_conversation_history()
    data = _load_json(CHECKPOINT_FILE, {"checkpoints": []})
    data["checkpoints"].append({
        "label": label,
        "ts": datetime.now().isoformat(),
        "snapshot_len": len(msgs),
    })
    _save_json(CHECKPOINT_FILE, data)
    return f"Checkpoint '{label}' marcado ({len(msgs)} mensagens no instantaneo)."


def hindsight_rewind(keep_report: bool = True) -> str:
    """Poda o contexto exploratorio, mantendo um relatorio conciso.

    Gera um resumo das ultimas conversas e limpa o historico ativo para
    liberar contexto, preservando apenas o relatorio. Use apos exploracoes
    longas para evitar estourar o limite de tokens.
    """
    msgs = load_conversation_history()
    if not msgs:
        return "Nada para reter no historico."
    texto = "\n".join(
        f"{m.get('role')}: {m.get('content', '')}" for m in msgs if m.get("content")
    )[:AUTO_CONTEXT_MAX_CHARS]
    try:
        resp = _call_ollama_with_timeout(
            ollama.chat,
            model=MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Resuma a conversa abaixo em um relatorio conciso (fatos, "
                    "decisoes e pendencias), em portugues:\n\n" + texto
                ),
            }],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        report = resp["message"]["content"]
    except Exception as e:
        report = f"(resumo indisponivel: {e})"
    if keep_report:
        save_conversation_history([
            {"role": "system", "content": "[Relatorio de rewind]: " + report}
        ])
        return "Contexto podado. Relatorio conciso mantido:\n" + report
    save_conversation_history([])
    return "Contexto podado (sem relatorio)."


def hindsight_context_for_turn(user_text: str, top_k: int = 5) -> str:
    """Recupera memorias relevantes do Hindsight para o turno atual.

    Chamado no INICIO de cada turno: busca por significado os fatos mais
    proximos da mensagem do usuario e retorna um bloco de contexto para
    ser injetado no prompt (padrao 'recall' automatico do oh-my-pi).
    Retorna string vazia se nao houver memorias ou consulta.
    """
    user_text = (user_text or "").strip()
    if not user_text:
        return ""
    data = _load_hindsight()
    if not data.get("facts"):
        return ""
    try:
        ranked = hindsight_recall(user_text, top_k=top_k)
    except Exception:
        return ""
    # hindsight_recall ja retorna o cabecalho; simplifica para contexto.
    linhas = ranked.splitlines()
    if len(linhas) <= 1:
        return ""
    corpo = "\n".join(linhas[1:])
    return (
        "--- MEMORIA DE LONGO PRAZO (Hindsight) relevante para esta mensagem ---\n"
        + corpo +
        "\nUse esses fatos para personalizar a resposta, mas NAO os cite "
        "literalmente se nao forem solicitados."
    )


def hindsight_auto_learn(user_text: str, assistant_text: str) -> list:
    """Extrai fatos duradouros da interacao e guarda via hindsight_retain.

    Usa o LLM para identificar aprendizados, preferencias do usuario e
    decisoes que devem sobreviver entre sessoes (padrao 'retain' do OMP),
    e os guarda no banco de memoria. Retorna a lista de fatos guardados.
    Silencioso em caso de falha (nao deve quebrar o turno principal).
    """
    user_text = (user_text or "").strip()
    assistant_text = (assistant_text or "").strip()
    if not user_text or not assistant_text:
        return []

    prompt = (
        "Extraia, da interacao abaixo, fatos duradouros que devem ser "
        "lembrados em conversas FUTURAS com este usuario. Inclua: preferencias "
        "do usuario, decisoes tomadas, contexto do projeto, e aprendizados. "
        "NAO inclua fatos efemericos ou sobre a tarefa atual isolada. "
        "Responda APENAS com uma lista, um fato por linha, sem numeracao nem "
        "marcadores. Se nao houver fatos relevantes, responda com uma linha "
        "contendo apenas: NENHUM.\n\n"
        f"USUARIO: {user_text[:2000]}\n\nASSISTENTE: {assistant_text[:2000]}"
    )
    try:
        resp = _call_ollama_with_timeout(
            ollama.chat,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX, "temperature": 0.1},
        )
        conteudo = resp["message"]["content"].strip()
    except Exception as e:
        logging.warning("hindsight_auto_learn falhou: %s", e)
        return []

    guardados = []
    for linha in conteudo.splitlines():
        fato = linha.strip().lstrip("-*0123456789. ").strip()
        if not fato or fato.upper() == "NENHUM":
            continue
        if len(fato) < 5:
            continue
        try:
            hindsight_retain(fato)
            guardados.append(fato)
        except Exception:
            pass
    if guardados:
        logging.info("Hindsight retain automatico: %d fato(s)", len(guardados))
    return guardados
