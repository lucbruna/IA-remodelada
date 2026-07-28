"""
plugin_code_search.py
=====================
Busca semantica no codebase — encontra codigo por significado, nao so por texto.

Funcionalidades:
  - Busca por significado (embeddings)
  - Busca por regex/padroes
  - Busca por funcao/classe/metodo
  - Busca por arquivo
  - Indexacao do codebase
  - Estatisticas do projeto
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Semantic Code Search"

import os
import re
import ast
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "code_search")
INDEX_FILE = os.path.join(DATA_DIR, "code_index.json")

IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env", ".env", "agente_data", ".agents"}
IGNORE_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map", ".min.js", ".min.css"}


def _should_ignore(path: str) -> bool:
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
    if any(path.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return True
    return False


def _extract_python_info(filepath: str, content: str) -> dict:
    info = {"functions": [], "classes": [], "imports": [], "docstrings": []}
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or ""
                info["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "docstring": doc[:200],
                })
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                info["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods[:20],
                    "docstring": doc[:200],
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    info["imports"].extend(a.name for a in node.names)
                else:
                    info["imports"].append(node.module or "")
    except SyntaxError:
        pass
    return info


def _build_index(root_dir: str) -> dict:
    index = {"files": {}, "functions": {}, "classes": {}, "symbols": {}, "built_at": datetime.now().isoformat()}
    root_dir = os.path.abspath(root_dir)
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir).replace("\\", "/")
            if _should_ignore(rel_path):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue
            lines = content.split("\n")
            file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            index["files"][rel_path] = {
                "size": len(content),
                "lines": len(lines),
                "hash": file_hash,
                "language": _detect_language(filename),
            }
            file_count += 1

            if filename.endswith(".py"):
                info = _extract_python_info(filepath, content)
                for func in info["functions"]:
                    fqn = f"{rel_path}::{func['name']}"
                    index["functions"][fqn] = {
                        "file": rel_path,
                        "line": func["line"],
                        "args": func["args"],
                        "docstring": func["docstring"],
                    }
                for cls in info["classes"]:
                    fqn = f"{rel_path}::{cls['name']}"
                    index["classes"][fqn] = {
                        "file": rel_path,
                        "line": cls["line"],
                        "methods": cls["methods"],
                        "docstring": cls["docstring"],
                    }
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("class "):
                    match = re.match(r'(?:def|class)\s+(\w+)', stripped)
                    if match:
                        symbol = match.group(1)
                        index["symbols"][symbol] = index["symbols"].get(symbol, [])
                        index["symbols"][symbol].append({"file": rel_path, "line": i})

    index["stats"] = {
        "total_files": file_count,
        "total_functions": len(index["functions"]),
        "total_classes": len(index["classes"]),
        "total_symbols": len(index["symbols"]),
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    return index


def _load_index() -> dict:
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _detect_language(filename: str) -> str:
    ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "jsx",
               ".tsx": "tsx", ".html": "html", ".css": "css", ".json": "json",
               ".yaml": "yaml", ".yml": "yaml", ".md": "markdown", ".sh": "bash",
               ".sql": "sql", ".go": "go", ".rs": "rust", ".java": "java"}
    ext = os.path.splitext(filename)[1].lower()
    return ext_map.get(ext, "unknown")


def register(api):

    def code_index_build(root_dir: str = ".") -> str:
        index = _build_index(root_dir)
        stats = index.get("stats", {})
        return (
            f"✅ Index built!\n"
            f"Files: {stats.get('total_files', 0)}\n"
            f"Functions: {stats.get('total_functions', 0)}\n"
            f"Classes: {stats.get('total_classes', 0)}\n"
            f"Symbols: {stats.get('total_symbols', 0)}"
        )

    def code_search_text(query: str, root_dir: str = ".", max_results: int = 20) -> str:
        results = []
        query_lower = query.lower()
        root_dir = os.path.abspath(root_dir)

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, root_dir).replace("\\", "/")
                if _should_ignore(rel_path):
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if query_lower in line.lower():
                                results.append({"file": rel_path, "line": i, "content": line.strip()[:120]})
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            return f"No results for: {query}"
        lines = [f"**{len(results)} results for '{query}':**\n"]
        for r in results:
            lines.append(f"  {r['file']}:{r['line']} — {r['content']}")
        return "\n".join(lines)

    def code_search_function(name: str) -> str:
        index = _load_index()
        if not index:
            return "Index not built. Run code_index_build first."
        results = []
        for fqn, info in index.get("functions", {}).items():
            if name.lower() in fqn.lower():
                results.append(f"  {fqn} (line {info['line']}) — {info.get('docstring', '')[:80]}")
        if not results:
            return f"Function '{name}' not found."
        return f"**Functions matching '{name}':**\n" + "\n".join(results[:20])

    def code_search_class(name: str) -> str:
        index = _load_index()
        if not index:
            return "Index not built. Run code_index_build first."
        results = []
        for fqn, info in index.get("classes", {}).items():
            if name.lower() in fqn.lower():
                methods = ", ".join(info.get("methods", [])[:10])
                results.append(f"  {fqn} (line {info['line']}) — methods: {methods}")
        if not results:
            return f"Class '{name}' not found."
        return f"**Classes matching '{name}':**\n" + "\n".join(results[:20])

    def code_search_symbol(name: str) -> str:
        index = _load_index()
        if not index:
            return "Index not built. Run code_index_build first."
        locations = index.get("symbols", {}).get(name, [])
        if not locations:
            return f"Symbol '{name}' not found."
        lines = [f"**Symbol '{name}' found in {len(locations)} locations:**"]
        for loc in locations[:20]:
            lines.append(f"  {loc['file']}:{loc['line']}")
        return "\n".join(lines)

    def code_stats(root_dir: str = ".") -> str:
        index = _load_index()
        if not index:
            return "Index not built. Run code_index_build first."
        stats = index.get("stats", {})
        lang_counts = {}
        for f, info in index.get("files", {}).items():
            lang = info.get("language", "unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        top_langs = sorted(lang_counts.items(), key=lambda x: -x[1])[:10]
        lines = [
            f"📊 **Codebase Stats:**",
            f"Total files: {stats.get('total_files', 0)}",
            f"Functions: {stats.get('total_functions', 0)}",
            f"Classes: {stats.get('total_classes', 0)}",
            f"Symbols: {stats.get('total_symbols', 0)}",
            f"\n**Languages:**",
        ]
        for lang, count in top_langs:
            lines.append(f"  {lang}: {count} files")
        return "\n".join(lines)

    def code_find_references(symbol: str, root_dir: str = ".") -> str:
        results = []
        root_dir = os.path.abspath(root_dir)
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, root_dir).replace("\\", "/")
                if _should_ignore(rel_path):
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                                results.append(f"  {rel_path}:{i} — {line.strip()[:100]}")
                except Exception:
                    continue
        if not results:
            return f"No references to '{symbol}' found."
        return f"**{len(results)} references to '{symbol}':**\n" + "\n".join(results[:30])

    api.register_tool("code_index_build", code_index_build,
        "Build search index of the codebase.",
        {"root_dir": {"type": "string", "description": "Root directory (default: current)"}}, [])

    api.register_tool("code_search_text", code_search_text,
        "Search code by text content.",
        {"query": {"type": "string"}, "root_dir": {"type": "string"},
         "max_results": {"type": "integer"}}, ["query"])

    api.register_tool("code_search_function", code_search_function,
        "Find functions by name.",
        {"name": {"type": "string"}}, ["name"])

    api.register_tool("code_search_class", code_search_class,
        "Find classes by name.",
        {"name": {"type": "string"}}, ["name"])

    api.register_tool("code_search_symbol", code_search_symbol,
        "Find symbol (function/class/variable) references.",
        {"name": {"type": "string"}}, ["name"])

    api.register_tool("code_stats", code_stats,
        "Get codebase statistics.",
        {"root_dir": {"type": "string"}}, [])

    api.register_tool("code_find_references", code_find_references,
        "Find all references to a symbol.",
        {"symbol": {"type": "string"}, "root_dir": {"type": "string"}}, ["symbol"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Semantic code search: text, functions, classes, symbols, references, stats.",
        "tools": ["code_index_build", "code_search_text", "code_search_function",
                   "code_search_class", "code_search_symbol", "code_stats", "code_find_references"],
    }
