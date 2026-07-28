"""
core/history_db.py
==================
Historico de conversas em SQLite (append-only, com indices).

Substitui o JSON puro do historico por um banco SQLite que:
  - E mais rapido para append e busca
  - Nao perde dados se o processo cai no meio de uma escrita
  - Suporta multiplas sessoes com indices
  - Permite queries por timestamp, session_id, role

Mantem compatibilidade com a API existente (load/save).
"""

import os
import json
import sqlite3
import threading
from datetime import datetime

from ._common import DATA_DIR

# Caminho do banco
DB_PATH = os.path.join(DATA_DIR, "historico.db")

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Retorna conexao SQLite thread-safe (uma por thread)."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_history_db():
    """Cria as tabelas se nao existirem."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT,
            timestamp TEXT,
            metadata TEXT,
            created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_role
            ON messages(session_id, role);
        CREATE INDEX IF NOT EXISTS idx_messages_created
            ON messages(created_at);

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            model TEXT,
            created_at TEXT,
            updated_at TEXT,
            message_count INTEGER DEFAULT 0
        );
    """)
    conn.commit()


# Inicializa na importacao
init_history_db()


def save_messages(messages: list, session_id: str = "default") -> None:
    """Salva lista de mensagens no SQLite (substitui o historico da sessao).

    Deleta mensagens anteriores da sessao e insere as novas (atomico).
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        for m in messages:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    m.get("role", ""),
                    m.get("content", ""),
                    m.get("timestamp", ""),
                    json.dumps(m.get("metadata", {}), ensure_ascii=False) if m.get("metadata") else None,
                ),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.rollback()
        raise


def load_messages(session_id: str = "default", limit: int = 200) -> list:
    """Carrega mensagens de uma sessao do SQLite."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp, metadata FROM messages "
        "WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    messages = []
    for row in reversed(rows):
        m = {"role": row["role"], "content": row["content"]}
        if row["timestamp"]:
            m["timestamp"] = row["timestamp"]
        if row["metadata"]:
            try:
                m["metadata"] = json.loads(row["metadata"])
            except Exception:
                pass
        messages.append(m)
    return messages


def append_message(role: str, content: str, session_id: str = "default",
                   timestamp: str = "", metadata: dict = None) -> None:
    """Append eficiente de uma unica mensagem."""
    conn = _get_conn()
    ts = timestamp or datetime.now().isoformat()
    meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp, metadata) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, ts, meta_json),
    )
    conn.commit()


def search_messages(query: str, session_id: str = "", limit: int = 50) -> list:
    """Busca textual nas mensagens."""
    conn = _get_conn()
    if session_id:
        rows = conn.execute(
            "SELECT session_id, role, content, timestamp FROM messages "
            "WHERE session_id = ? AND content LIKE ? LIMIT ?",
            (session_id, f"%{query}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT session_id, role, content, timestamp FROM messages "
            "WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "role": r["role"],
            "content": r["content"][:500],
            "timestamp": r["timestamp"],
        }
        for r in rows
    ]


def get_message_count(session_id: str = "default") -> int:
    """Retorna o numero de mensagens de uma sessao."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["cnt"] if row else 0


def list_sessions_db() -> list:
    """Lista todas as sessoes com metadados."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, model, created_at, updated_at, message_count "
        "FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    """Deleta uma sessao e todas as suas mensagens."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def get_stats() -> dict:
    """Retorna estatisticas do historico."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]
    sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as cnt FROM messages").fetchone()["cnt"]
    oldest = conn.execute("SELECT MIN(created_at) as ts FROM messages").fetchone()["ts"]
    newest = conn.execute("SELECT MAX(created_at) as ts FROM messages").fetchone()["ts"]
    return {
        "total_messages": total,
        "total_sessions": sessions,
        "oldest": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
        "newest": datetime.fromtimestamp(newest).isoformat() if newest else None,
    }
