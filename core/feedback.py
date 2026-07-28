"""
core/feedback.py
================
Sistema de feedback do usuario para aprendizado continuo.

Permite ao usuario avaliar respostas (thumbs up/down) e dar comentarios
que alimentam a memoria evolutiva para melhorar respostas futuras.
"""

import os
import json
from datetime import datetime
from typing import Optional

from ._common import DATA_DIR, _load_json, _save_json, logging

FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")
MAX_FEEDBACK = 1000


def _ensure_file():
    if not os.path.exists(FEEDBACK_FILE):
        _save_json(FEEDBACK_FILE, {"entries": []})


def submit_feedback(
    quality: int,
    comment: str = "",
    conversation_id: str = "",
    message_index: int = -1,
    tags: list = None,
) -> str:
    """Envia feedback do usuario sobre uma resposta.

    Args:
        quality: 1 = bom, -1 = ruim, 0 = neutro
        comment: Comentario opcional do usuario
        conversation_id: ID da conversa (para rastreabilidade)
        message_index: Indice da mensagem avaliada
        tags: Tags opcionais (ex: ["rapido", "incorreto", "lento"])

    Returns:
        Mensagem de confirmacao
    """
    _ensure_file()

    quality = max(-1, min(1, int(quality)))  # clamp para -1, 0, 1

    entry = {
        "timestamp": datetime.now().isoformat(),
        "quality": quality,
        "comment": comment[:500],
        "conversation_id": conversation_id,
        "message_index": message_index,
        "tags": tags or [],
    }

    data = _load_json(FEEDBACK_FILE, {"entries": []})
    data["entries"].append(entry)

    # Rotacao: mantem apenas MAX_FEEDBACK entradas
    if len(data["entries"]) > MAX_FEEDBACK:
        data["entries"] = data["entries"][-MAX_FEEDBACK:]

    _save_json(FEEDBACK_FILE, data)

    # Alimenta memoria evolutiva se o feedback for forte
    if quality != 0 and comment:
        try:
            from plugins.plugin_memoria_evolutiva import processar_conversa
            texto = f"Feedback do usuario: {'BOM' if quality > 0 else 'RUIM'}. Comentario: {comment}"
            processar_conversa(texto)
        except Exception:
            pass

    logging.info("Feedback recebido: quality=%d, comment=%s", quality, comment[:100])
    return f"Feedback registrado: {'positivo' if quality > 0 else 'negativo' if quality < 0 else 'neutro'}"


def get_feedback_stats() -> dict:
    """Retorna estatisticas do feedback."""
    _ensure_file()
    data = _load_json(FEEDBACK_FILE, {"entries": []})
    entries = data.get("entries", [])

    if not entries:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "sentiment_score": 0,
            "recent_comments": [],
        }

    positive = sum(1 for e in entries if e.get("quality", 0) > 0)
    negative = sum(1 for e in entries if e.get("quality", 0) < 0)
    neutral = sum(1 for e in entries if e.get("quality", 0) == 0)
    total = len(entries)

    sentiment = (positive - negative) / total if total else 0

    # Ultimos comentarios relevantes
    recent = [
        {
            "comment": e.get("comment", ""),
            "quality": e.get("quality", 0),
            "timestamp": e.get("timestamp", ""),
            "tags": e.get("tags", []),
        }
        for e in entries[-20:]
        if e.get("comment")
    ]

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "sentiment_score": round(sentiment, 2),
        "approval_rate": round(positive / total * 100, 1) if total else 0,
        "recent_comments": recent,
    }


def get_feedback_summary_for_model() -> str:
    """Retorna resumo do feedback para incluir no contexto do modelo.

    Usado pelo hindsight para ajustar comportamento baseado em feedback.
    """
    stats = get_feedback_stats()
    if stats["total"] == 0:
        return ""

    parts = [f"Feedback do usuario: {stats['total']} avaliacoes"]
    parts.append(f"Aprovacao: {stats['approval_rate']}%")

    # Top tags negativas (problemas recorrentes)
    data = _load_json(FEEDBACK_FILE, {"entries": []})
    negative_tags = {}
    for e in data.get("entries", []):
        if e.get("quality", 0) < 0:
            for tag in e.get("tags", []):
                negative_tags[tag] = negative_tags.get(tag, 0) + 1
    if negative_tags:
        top_issues = sorted(negative_tags.items(), key=lambda x: -x[1])[:3]
        parts.append("Problemas recorrentes: " + ", ".join(f"{t}({c})" for t, c in top_issues))

    return "\n".join(parts)


def list_feedback(limit: int = 50) -> list:
    """Lista os ultimos feedbacks."""
    _ensure_file()
    data = _load_json(FEEDBACK_FILE, {"entries": []})
    return data.get("entries", [])[-limit:]


def clear_feedback() -> str:
    """Limpa todo o feedback registrado."""
    _save_json(FEEDBACK_FILE, {"entries": []})
    return "Feedback limpo."
