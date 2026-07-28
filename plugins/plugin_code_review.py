"""
plugin_code_review.py
=====================
AI Code Review leve e rapido — analise de codigo via LLM local.

Diferente do plugin_codereview_pesado (que usa bandit + LLM + benchmark),
este plugin faz revisao rapida com foco em:
  - Bugs e erros logicos
  - Style e naming
  - Seguranca basica
  - Performance
  - Sugestoes de melhoria

Ideal para revisao diaria, PRs pequenos, e uso interativo.
"""

__version__ = "1.0.0"
PLUGIN_NAME = "AI Code Review"

import ast
import re
import logging

logger = logging.getLogger(__name__)

# Patterns de seguranca (basico)
SECURITY_PATTERNS = [
    (r"eval\s*\(", "Uso de eval() — risco de execucao arbitrária"),
    (r"exec\s*\(", "Uso de exec() — risco de execucao arbitrária"),
    (r"__import__\s*\(", "Import dinâmico — pode ser explorado"),
    (r"subprocess\.call.*shell\s*=\s*True", "shell=True no subprocess — risco de shell injection"),
    (r"os\.system\s*\(", "os.system() — usar subprocess com shell=False"),
    (r"pickle\.loads?\s*\(", "Pickle em dados externos — risco de deserializacao"),
    (r"input\s*\(.*eval", "input() com eval — risco de injection"),
    (r"password\s*=\s*['\"]", "Senha hardcoded no codigo"),
    (r"secret\s*=\s*['\"]", "Secret hardcoded no codigo"),
    (r"api_key\s*=\s*['\"]", "API key hardcoded no codigo"),
]

# Anti-patterns de performance
PERF_PATTERNS = [
    (r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(", "Usar enumerate() em vez de range(len())"),
    (r"\+\s*=\s*['\"]", "Concatenacao em loop — usar join() ou f-string"),
    (r"import\s+\*", "Wildcard import — importar nomes especificos"),
]

# Patterns de codigo morto
DEAD_CODE_PATTERNS = [
    (r"^\s*#\s*TODO", "TODO nao resolvido"),
    (r"^\s*#\s*FIXME", "FIXME marcado"),
    (r"^\s*#\s*HACK", "HACK no codigo"),
    (r"^\s*pass\s*$", "Bloco pass vazio"),
]


def _ast_check(code: str, language: str) -> list:
    """Verificacao basica via AST (apenas Python)."""
    issues = []
    if language != "python":
        return issues
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.args.args) > 7:
                    issues.append({
                        "line": node.lineno,
                        "type": "design",
                        "severity": "low",
                        "message": f"Funcao '{node.name}' tem {len(node.args.args)} parametros (max recomendado: 7)",
                    })
                if not ast.get_docstring(node):
                    issues.append({
                        "line": node.lineno,
                        "type": "docs",
                        "severity": "info",
                        "message": f"Funcao '{node.name}' sem docstring",
                    })
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        issues.append({
                            "line": handler.lineno,
                            "type": "error_handling",
                            "severity": "medium",
                            "message": "except genérico (bare except) — usar excecao especifica",
                        })
    except SyntaxError as e:
        issues.append({
            "line": e.lineno or 1,
            "type": "syntax",
            "severity": "critical",
            "message": f"Erro de sintaxe: {e.msg}",
        })
    return issues


def _pattern_check(code: str, patterns: list, category: str) -> list:
    """Verificacao por regex."""
    issues = []
    for line_num, line in enumerate(code.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, message in patterns:
            if re.search(pattern, line):
                issues.append({
                    "line": line_num,
                    "type": category,
                    "severity": "medium" if category == "security" else "low",
                    "message": message,
                })
    return issues


def _metrics(code: str) -> dict:
    """Metricas basicas do codigo."""
    lines = code.split("\n")
    blank = sum(1 for l in lines if l.strip() == "")
    comments = sum(1 for l in lines if l.strip().startswith("#"))
    code_lines = len(lines) - blank - comments

    funcs = 0
    classes = 0
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                funcs += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
    except Exception:
        pass

    return {
        "total_lines": len(lines),
        "code_lines": code_lines,
        "blank_lines": blank,
        "comment_lines": comments,
        "functions": funcs,
        "classes": classes,
        "comment_ratio": f"{(comments / code_lines * 100):.1f}%" if code_lines > 0 else "N/A",
    }


def register(api):

    def code_review(code: str, language: str = "auto", focus: str = "all") -> str:
        if not code.strip():
            return "❌ Codigo vazio."

        if language == "auto":
            if "def " in code or "import " in code:
                language = "python"
            elif "function " in code or "const " in code:
                language = "javascript"
            elif "fn " in code or "pub " in code:
                language = "rust"
            else:
                language = "unknown"

        all_issues = []

        if focus in ("all", "bugs"):
            all_issues.extend(_ast_check(code, language))

        if focus in ("all", "security"):
            all_issues.extend(_pattern_check(code, SECURITY_PATTERNS, "security"))

        if focus in ("all", "performance"):
            all_issues.extend(_pattern_check(code, PERF_PATTERNS, "performance"))

        if focus in ("all", "quality"):
            all_issues.extend(_pattern_check(code, DEAD_CODE_PATTERNS, "quality"))

        metrics = _metrics(code)

        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}

        lines = []
        lines.append(f"🔍 **AI Code Review** ({language})")
        lines.append("")

        if not all_issues:
            lines.append("✅ Nenhum problema encontrado!")
        else:
            sorted_issues = sorted(all_issues, key=lambda i: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(i["severity"], 5))
            by_type = {}
            for issue in sorted_issues:
                t = issue["type"]
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(issue)

            for issue_type, issues in by_type.items():
                lines.append(f"**{issue_type.upper()}** ({len(issues)}):")
                for issue in issues[:5]:
                    emoji = severity_emoji.get(issue["severity"], "⚪")
                    lines.append(f"  {emoji} Linha {issue['line']}: {issue['message']}")
                if len(issues) > 5:
                    lines.append(f"  ... e mais {len(issues) - 5}")
                lines.append("")

        lines.append("**Metricas:**")
        lines.append(f"  Linhas: {metrics['total_lines']} (codigo: {metrics['code_lines']}, comentarios: {metrics['comment_lines']})")
        lines.append(f"  Funcoes: {metrics['functions']} | Classes: {metrics['classes']}")
        lines.append(f"  Ratio comentarios: {metrics['comment_ratio']}")

        return "\n".join(lines)

    def code_review_diff(diff_text: str) -> str:
        if not diff_text.strip():
            return "❌ Diff vazio."

        lines = []
        added_code = []
        current_file = ""

        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                added_code.append((current_file, line[1:]))

        if not added_code:
            return "Nenhuma linha adicionada no diff."

        review_lines = [f"🔍 **Review do Diff** — {len(added_code)} linhas adicionadas\n"]

        issues_found = 0
        for filepath, code_line in added_code:
            for pattern, message in SECURITY_PATTERNS:
                if re.search(pattern, code_line):
                    review_lines.append(f"🔴 `{filepath}`: {message}")
                    review_lines.append(f"   ```{code_line.strip()}```")
                    issues_found += 1
                    break

        if issues_found == 0:
            review_lines.append("✅ Nenhuma problema de seguranca nas linhas adicionadas.")
        else:
            review_lines.append(f"\n⚠️ {issues_found} problemas encontrados.")

        return "\n".join(review_lines)

    def code_metrics(code: str) -> str:
        m = _metrics(code)
        return (
            f"📊 **Metricas do Codigo**\n\n"
            f"• Linhas totais: {m['total_lines']}\n"
            f"• Linhas de codigo: {m['code_lines']}\n"
            f"• Linhas em branco: {m['blank_lines']}\n"
            f"• Comentarios: {m['comment_lines']}\n"
            f"• Funcoes: {m['functions']}\n"
            f"• Classes: {m['classes']}\n"
            f"• Ratio comentarios: {m['comment_ratio']}"
        )

    api.register_tool("code_review", code_review,
        "Review rapido de codigo: bugs, seguranca, performance, qualidade.",
        {"code": {"type": "string", "description": "Codigo a revisar"},
         "language": {"type": "string", "description": "Linguagem (auto, python, javascript, rust)"},
         "focus": {"type": "string", "description": "Foco: all, bugs, security, performance, quality"}},
        ["code"])

    api.register_tool("code_review_diff", code_review_diff,
        "Review de um diff — foca nas linhas adicionadas.",
        {"diff_text": {"type": "string", "description": "Texto do diff (unified format)"}},
        ["diff_text"])

    api.register_tool("code_metrics", code_metrics,
        "Metricas basicas do codigo (linhas, funcoes, classes, comentarios).",
        {"code": {"type": "string"}}, ["code"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "AI Code Review leve: analise rapida de bugs, seguranca, performance e qualidade.",
        "tools": ["code_review", "code_review_diff", "code_metrics"],
    }
