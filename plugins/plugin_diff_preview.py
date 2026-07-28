"""
plugin_diff_preview.py
======================
Preview de mudancas — diff visual, impacto, confirmacao antes de aplicar.

Funcionalidades:
  - Diff visual com cores (terminal)
  - Preview de mudancas em arquivos
  - Impacto analysis (quantos arquivos afeta, linhas)
  - Confirmacao interativa antes de aplicar
  - Undo/rollback de mudancas
  - Export de diff como HTML
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Diff Preview System"

import os
import re
import difflib
import logging
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "diff_backups")


def _backup_file(filepath: str) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = int(datetime.now().timestamp())
    safe_name = filepath.replace(":", "_").replace("\\", "_").replace("/", "_")
    backup_path = os.path.join(BACKUP_DIR, f"{safe_name}.{ts}.bak")
    try:
        shutil.copy2(filepath, backup_path)
        return backup_path
    except Exception:
        return ""


def _make_diff_text(old: str, new: str, filepath: str = "") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filepath}" if filepath else "a/original",
        tofile=f"b/{filepath}" if filepath else "b/modified",
        lineterm="",
    ))
    return "".join(diff)


def _colorize_diff(diff_text: str) -> str:
    lines = []
    for line in diff_text.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            lines.append(f"\033[1m{line}\033[0m")
        elif line.startswith("@@"):
            lines.append(f"\033[36m{line}\033[0m")
        elif line.startswith("+"):
            lines.append(f"\033[32m{line}\033[0m")
        elif line.startswith("-"):
            lines.append(f"\033[31m{line}\033[0m")
        else:
            lines.append(line)
    return "\n".join(lines)


def _diff_stats(diff_text: str) -> dict:
    added = sum(1 for l in diff_text.split("\n") if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_text.split("\n") if l.startswith("-") and not l.startswith("---"))
    return {
        "added": added,
        "removed": removed,
        "total_changes": added + removed,
        "net_lines": added - removed,
    }


def register(api):

    def diff_preview(file_a: str, file_b: str = "", new_content: str = "") -> str:
        if not os.path.exists(file_a):
            return f"❌ Arquivo nao encontrado: {file_a}"

        with open(file_a, "r", encoding="utf-8", errors="replace") as f:
            old_content = f.read()

        if file_b and os.path.exists(file_b):
            with open(file_b, "r", encoding="utf-8", errors="replace") as f:
                new_content = f.read()
            filepath = os.path.basename(file_b)
        elif new_content:
            filepath = os.path.basename(file_a) + " (modificado)"
        else:
            return "❌ Forneça file_b ou new_content."

        diff_text = _make_diff_text(old_content, new_content, filepath)
        if not diff_text:
            return "✅ Nenhuma diferenca encontrada."

        stats = _diff_stats(diff_text)
        colorized = _colorize_diff(diff_text)

        if len(colorized) > 4000:
            colorized = colorized[:4000] + "\n[...diff truncado...]"

        return (
            f"📊 **Preview de Mudancas** — {filepath}\n"
            f"+{stats['added']} -{stats['removed']} linhas (total: {stats['total_changes']})\n\n"
            f"{colorized}"
        )

    def diff_apply(
        filepath: str,
        new_content: str,
        confirm: bool = False,
        backup: bool = True,
    ) -> str:
        if not confirm:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    old_content = f.read()
                diff = _make_diff_text(old_content, new_content, os.path.basename(filepath))
                stats = _diff_stats(diff)
                return (
                    f"⚠️ **Confirmacao necessaria**\n\n"
                    f"Arquivo: {filepath}\n"
                    f"+{stats['added']} -{stats['removed']} linhas\n\n"
                    f"Use confirm=True para aplicar."
                )

        if backup and os.path.exists(filepath):
            _backup_file(filepath)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"✅ Mudanca aplicada: {filepath}"

    def diff_impact(files_json: str) -> str:
        try:
            files = json.loads(files_json) if isinstance(files_json, str) else files_json
        except Exception:
            files = [{"path": files_json}]

        total_added = 0
        total_removed = 0
        file_count = 0
        details = []

        for item in files:
            if isinstance(item, dict):
                filepath = item.get("path", "")
                new = item.get("content", "")
            else:
                filepath = str(item)
                new = ""

            if not filepath or not os.path.exists(filepath):
                continue

            if new:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    old = f.read()
                diff = _make_diff_text(old, new, os.path.basename(filepath))
                stats = _diff_stats(diff)
                total_added += stats["added"]
                total_removed += stats["removed"]
                file_count += 1
                details.append(f"  {os.path.basename(filepath)}: +{stats['added']} -{stats['removed']}")

        return (
            f"📊 **Analise de Impacto**\n\n"
            f"• Arquivos afetados: {file_count}\n"
            f"• Linhas adicionadas: +{total_added}\n"
            f"• Linhas removidas: -{total_removed}\n"
            f"• Mudanca liquida: {'+' if total_added - total_removed >= 0 else ''}{total_added - total_removed}\n\n"
            + "\n".join(details)
        )

    def diff_backup_list() -> str:
        if not os.path.exists(BACKUP_DIR):
            return "Nenhum backup encontrado."
        backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
        if not backups:
            return "Nenhum backup encontrado."
        lines = [f"📦 **{len(backups)} backups:**\n"]
        for b in backups[:20]:
            size = os.path.getsize(os.path.join(BACKUP_DIR, b))
            lines.append(f"  • {b} ({size} bytes)")
        return "\n".join(lines)

    def diff_rollback(filepath: str) -> str:
        if not os.path.exists(BACKUP_DIR):
            return "❌ Nenhum backup disponivel."
        safe_name = filepath.replace(":", "_").replace("\\", "_").replace("/", "_")
        backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith(safe_name)]
        if not backups:
            return f"❌ Nenhum backup para: {filepath}"
        latest = sorted(backups)[-1]
        backup_path = os.path.join(BACKUP_DIR, latest)
        shutil.copy2(backup_path, filepath)
        return f"✅ Rollback concluido: {filepath} ← {latest}"

    def diff_to_html(file_a: str, file_b: str = "", new_content: str = "") -> str:
        if not os.path.exists(file_a):
            return f"❌ Arquivo nao encontrado: {file_a}"
        with open(file_a, "r", encoding="utf-8", errors="replace") as f:
            old_content = f.read()
        if file_b and os.path.exists(file_b):
            with open(file_b, "r", encoding="utf-8", errors="replace") as f:
                new_content = f.read()
        elif not new_content:
            return "❌ Forneça file_b ou new_content."

        diff = _make_diff_text(old_content, new_content, os.path.basename(file_a))
        if not diff:
            return "✅ Nenhuma diferenca."

        diff_lines = []
        for line in diff.split("\n"):
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith("+"):
                diff_lines.append(f'<span style="color:#28a745;background:#e6ffed">{escaped}</span>')
            elif line.startswith("-"):
                diff_lines.append(f'<span style="color:#d73a49;background:#ffeef0">{escaped}</span>')
            elif line.startswith("@@"):
                diff_lines.append(f'<span style="color:#6f42c1;background:#f1f8ff">{escaped}</span>')
            else:
                diff_lines.append(escaped)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Diff Preview</title>
<style>
body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
pre {{ background: #161b22; padding: 16px; border-radius: 8px; overflow-x: auto; }}
h1 {{ color: #58a6ff; font-size: 18px; }}
</style></head><body>
<h1>📊 Diff Preview — {os.path.basename(file_a)}</h1>
<pre>{'<br>'.join(diff_lines)}</pre>
</body></html>"""

        html_path = os.path.join(BACKUP_DIR, f"diff_{int(datetime.now().timestamp())}.html")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return f"✅ Diff HTML exportado: {html_path}"

    api.register_tool("diff_preview", diff_preview,
        "Preview visual de mudancas entre dois arquivos/contents.",
        {"file_a": {"type": "string", "description": "Arquivo original"},
         "file_b": {"type": "string", "description": "Arquivo modificado (opcional)"},
         "new_content": {"type": "string", "description": "Novo conteudo (alternativa a file_b)"}},
        ["file_a"])

    api.register_tool("diff_apply", diff_apply,
        "Aplica mudanca em arquivo com confirmacao e backup.",
        {"filepath": {"type": "string"}, "new_content": {"type": "string"},
         "confirm": {"type": "boolean", "description": "True para aplicar"},
         "backup": {"type": "boolean", "description": "Criar backup antes"}},
        ["filepath", "new_content"])

    api.register_tool("diff_impact", diff_impact,
        "Analisa impacto de mudancas em multiplos arquivos.",
        {"files_json": {"type": "string", "description": "JSON array: [{path, content}]"}}, ["files_json"])

    api.register_tool("diff_backup_list", diff_backup_list,
        "Lista backups disponiveis para rollback.", {}, [])

    api.register_tool("diff_rollback", diff_rollback,
        "Faz rollback de um arquivo para o ultimo backup.",
        {"filepath": {"type": "string"}}, ["filepath"])

    api.register_tool("diff_to_html", diff_to_html,
        "Exporta diff como HTML visual.",
        {"file_a": {"type": "string"}, "file_b": {"type": "string"},
         "new_content": {"type": "string"}}, ["file_a"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Diff preview: visual, impacto, confirmacao, backup, rollback, export HTML.",
        "tools": ["diff_preview", "diff_apply", "diff_impact",
                   "diff_backup_list", "diff_rollback", "diff_to_html"],
    }
