"""
plugin_kanban.py
================
Agent Command Center — Kanban visual para gerenciar tarefas do agente.

Funcionalidades:
  - Board Kanban com colunas (Backlog, In Progress, Review, Done)
  - Cards com prioridade, tags, timestamps
  - Dashboard visual em terminal (Rich)
  - Exportacao HTML do board
  - Integracao com o ciclo Fable (Backlog → Evidencia → Plano → Execucao → Verificado)
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Agent Command Center"

import os
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "kanban")
BOARD_FILE = os.path.join(DATA_DIR, "board.json")

COLUMNS = ["backlog", "in_progress", "review", "done"]
COLUMN_LABELS = {
    "backlog": "📋 Backlog",
    "in_progress": "🔄 Em Progresso",
    "review": "🔍 Review",
    "done": "✅ Concluido",
}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _load_board() -> dict:
    if os.path.exists(BOARD_FILE):
        with open(BOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    board = {
        "columns": {col: [] for col in COLUMNS},
        "tags": ["bug", "feature", "docs", "refactor", "test", "deploy", "urgent"],
        "created_at": datetime.now().isoformat(),
    }
    _save_board(board)
    return board


def _save_board(board: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)


def _find_card(board: dict, card_id: str):
    for col in COLUMNS:
        for card in board["columns"][col]:
            if card["id"] == card_id:
                return card, col
    return None, None


def _render_text_board(board: dict) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("🏠 AGENT COMMAND CENTER — KANBAN BOARD")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    for col in COLUMNS:
        cards = board["columns"][col]
        label = COLUMN_LABELS[col]
        lines.append(f"\n{label} ({len(cards)})")
        lines.append("-" * 40)

        if not cards:
            lines.append("  (vazio)")
            continue

        sorted_cards = sorted(cards, key=lambda c: PRIORITY_ORDER.get(c.get("priority", "medium"), 2))
        for card in sorted_cards:
            pri = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                card.get("priority", "medium"), "⚪"
            )
            tags = " ".join(f"[{t}]" for t in card.get("tags", []))
            age = ""
            if card.get("created_at"):
                try:
                    created = datetime.fromisoformat(card["created_at"])
                    days = (datetime.now() - created).days
                    if days > 0:
                        age = f" ({days}d)"
                except Exception:
                    pass
            lines.append(
                f"  {pri} {card['id'][:8]} — {card['title'][:45]}{age}"
            )
            if tags:
                lines.append(f"       Tags: {tags}")

    lines.append("\n" + "=" * 80)
    total = sum(len(board["columns"][col]) for col in COLUMNS)
    lines.append(f"Total: {total} cards")
    return "\n".join(lines)


def register(api):

    def kanban_status() -> str:
        board = _load_board()
        return _render_text_board(board)

    def kanban_add_card(
        title: str,
        column: str = "backlog",
        description: str = "",
        priority: str = "medium",
        tags: str = "",
        assignee: str = "",
    ) -> str:
        board = _load_board()
        col = column.lower().strip()
        if col not in COLUMNS:
            return f"❌ Coluna invalida: {col}. Opcoes: {', '.join(COLUMNS)}"

        card_id = f"card-{int(time.time() * 1000) % 100000000}"
        card = {
            "id": card_id,
            "title": title,
            "description": description,
            "priority": priority,
            "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
            "assignee": assignee,
            "column": col,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": [{"action": "created", "column": col, "at": datetime.now().isoformat()}],
        }

        board["columns"][col].append(card)
        _save_board(board)
        return f"✅ Card criado: {card_id[:8]} — {title} em {COLUMN_LABELS[col]}"

    def kanban_move_card(card_id: str, to_column: str, reason: str = "") -> str:
        board = _load_board()
        card, from_col = _find_card(board, card_id)
        if not card:
            return f"❌ Card '{card_id}' nao encontrado."

        to_col = to_column.lower().strip()
        if to_col not in COLUMNS:
            return f"❌ Coluna invalida: {to_col}"

        if from_col == to_col:
            return f"⚠️ Card ja esta em {COLUMN_LABELS[to_col]}"

        board["columns"][from_col].remove(card)
        card["column"] = to_col
        card["updated_at"] = datetime.now().isoformat()
        card["history"].append({
            "action": "moved",
            "from": from_col,
            "to": to_col,
            "reason": reason,
            "at": datetime.now().isoformat(),
        })
        board["columns"][to_col].append(card)
        _save_board(board)
        return f"✅ {card_id[:8]} movido: {COLUMN_LABELS[from_col]} → {COLUMN_LABELS[to_col]}"

    def kanban_update_card(
        card_id: str,
        title: str = "",
        description: str = "",
        priority: str = "",
        tags: str = "",
    ) -> str:
        board = _load_board()
        card, _ = _find_card(board, card_id)
        if not card:
            return f"❌ Card '{card_id}' nao encontrado."

        if title:
            card["title"] = title
        if description:
            card["description"] = description
        if priority:
            card["priority"] = priority
        if tags:
            card["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        card["updated_at"] = datetime.now().isoformat()
        _save_board(board)
        return f"✅ Card {card_id[:8]} atualizado."

    def kanban_delete_card(card_id: str) -> str:
        board = _load_board()
        card, col = _find_card(board, card_id)
        if not card:
            return f"❌ Card '{card_id}' nao encontrado."
        board["columns"][col].remove(card)
        _save_board(board)
        return f"🗑️ Card {card_id[:8]} removido de {COLUMN_LABELS[col]}"

    def kanban_get_card(card_id: str) -> str:
        board = _load_board()
        card, col = _find_card(board, card_id)
        if not card:
            return f"❌ Card '{card_id}' nao encontrado."

        history = "\n".join(
            f"  • {h['action']}: {h.get('from', '')} → {h.get('to', '')} ({h.get('at', '')[:10]})"
            for h in card.get("history", [])
        )
        return (
            f"📋 **Card {card['id'][:8]}**\n\n"
            f"• Titulo: {card['title']}\n"
            f"• Coluna: {COLUMN_LABELS.get(col, col)}\n"
            f"• Prioridade: {card.get('priority', 'medium')}\n"
            f"• Tags: {', '.join(card.get('tags', [])) or 'nenhuma'}\n"
            f"• Assignee: {card.get('assignee', 'nenhum')}\n"
            f"• Criado: {card.get('created_at', '')[:10]}\n"
            f"• Atualizado: {card.get('updated_at', '')[:10]}\n"
            f"• Descricao: {card.get('description', 'nenhuma')}\n\n"
            f"**Historico:**\n{history}"
        )

    def kanban_export_html() -> str:
        board = _load_board()
        cards_html = ""
        for col in COLUMNS:
            cards = board["columns"][col]
            cards_inner = ""
            for card in cards:
                pri_color = {"critical": "#dc3545", "high": "#fd7e14", "medium": "#ffc107", "low": "#28a745"}.get(
                    card.get("priority", "medium"), "#6c757d"
                )
                tags_html = " ".join(f'<span class="tag">{t}</span>' for t in card.get("tags", []))
                cards_inner += f"""
                <div class="card" style="border-left: 4px solid {pri_color}">
                    <div class="card-id">{card['id'][:8]}</div>
                    <div class="card-title">{card['title']}</div>
                    <div class="card-tags">{tags_html}</div>
                </div>"""
            label = COLUMN_LABELS[col]
            cards_html += f"""
            <div class="column">
                <h3>{label} ({len(cards)})</h3>
                {cards_inner or '<div class="empty">Vazio</div>'}
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Agent Command Center</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 20px; }}
h1 {{ color: #58a6ff; text-align: center; }}
.board {{ display: flex; gap: 16px; overflow-x: auto; padding: 16px; }}
.column {{ min-width: 280px; background: #161b22; border-radius: 8px; padding: 12px; }}
.column h3 {{ margin: 0 0 12px 0; color: #58a6ff; font-size: 14px; }}
.card {{ background: #21262d; border-radius: 6px; padding: 10px; margin-bottom: 8px; cursor: pointer; }}
.card:hover {{ background: #30363d; }}
.card-id {{ font-size: 11px; color: #8b949e; font-family: monospace; }}
.card-title {{ font-size: 13px; margin-top: 4px; }}
.card-tags {{ margin-top: 6px; }}
.tag {{ background: #1f6feb33; color: #58a6ff; padding: 2px 6px; border-radius: 10px; font-size: 11px; margin-right: 4px; }}
.empty {{ color: #484f58; font-style: italic; font-size: 13px; }}
.stats {{ text-align: center; color: #8b949e; margin-top: 16px; }}
</style>
</head>
<body>
<h1>🏠 Agent Command Center</h1>
<div class="board">{cards_html}</div>
<div class="stats">Total: {sum(len(board['columns'][c]) for c in COLUMNS)} cards</div>
</body>
</html>"""
        html_path = os.path.join(DATA_DIR, "board.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return f"✅ Board exportado: {html_path}"

    def kanban_stats() -> str:
        board = _load_board()
        stats = []
        total = 0
        for col in COLUMNS:
            count = len(board["columns"][col])
            total += count
            stats.append(f"  {COLUMN_LABELS[col]}: {count}")

        all_cards = []
        for col in COLUMNS:
            all_cards.extend(board["columns"][col])

        pri_counts = {}
        for card in all_cards:
            p = card.get("priority", "medium")
            pri_counts[p] = pri_counts.get(p, 0) + 1

        tag_counts = {}
        for card in all_cards:
            for t in card.get("tags", []):
                tag_counts[t] = tag_counts.get(t, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]
        top_tags_str = ", ".join(f"{t}({c})" for t, c in top_tags) or "nenhuma"

        return (
            f"📊 **Estatisticas do Kanban**\n\n"
            + "\n".join(stats)
            + f"\n\n  Total: {total}\n"
            + f"\n  Por prioridade: {json.dumps(pri_counts)}\n"
            + f"  Top tags: {top_tags_str}"
        )

    api.register_tool("kanban_status", kanban_status,
        "Mostra o board Kanban completo.", {}, [])

    api.register_tool("kanban_add_card", kanban_add_card,
        "Adiciona um card ao Kanban.",
        {"title": {"type": "string", "description": "Titulo do card"},
         "column": {"type": "string", "description": "Coluna: backlog, in_progress, review, done"},
         "description": {"type": "string", "description": "Descricao detalhada"},
         "priority": {"type": "string", "description": "Prioridade: critical, high, medium, low"},
         "tags": {"type": "string", "description": "Tags separadas por virgula"},
         "assignee": {"type": "string", "description": "Responsavel"}},
        ["title"])

    api.register_tool("kanban_move_card", kanban_move_card,
        "Move um card para outra coluna.",
        {"card_id": {"type": "string", "description": "ID do card"},
         "to_column": {"type": "string", "description": "Coluna de destino"},
         "reason": {"type": "string", "description": "Motivo do movimento (opcional)"}},
        ["card_id", "to_column"])

    api.register_tool("kanban_update_card", kanban_update_card,
        "Atualiza campos de um card.",
        {"card_id": {"type": "string"}, "title": {"type": "string"},
         "description": {"type": "string"}, "priority": {"type": "string"},
         "tags": {"type": "string"}}, ["card_id"])

    api.register_tool("kanban_delete_card", kanban_delete_card,
        "Remove um card do Kanban.",
        {"card_id": {"type": "string"}}, ["card_id"])

    api.register_tool("kanban_get_card", kanban_get_card,
        "Retorna detalhes completos de um card.",
        {"card_id": {"type": "string"}}, ["card_id"])

    api.register_tool("kanban_export_html", kanban_export_html,
        "Exporta o board como HTML visual.", {}, [])

    api.register_tool("kanban_stats", kanban_stats,
        "Estatisticas do board (cards por coluna, prioridade, tags).", {}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Agent Command Center: Kanban visual, cards, exportacao HTML, estatisticas.",
        "tools": ["kanban_status", "kanban_add_card", "kanban_move_card",
                   "kanban_update_card", "kanban_delete_card", "kanban_get_card",
                   "kanban_export_html", "kanban_stats"],
    }
