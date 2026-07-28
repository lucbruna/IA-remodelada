"""
plugin_multi_file_refactor.py
=============================
Refatoracao coordenada em multiplos arquivos — edits sincronizados.

Funcionalidades:
  - Renomear simbolos em todo o projeto
  - Mover funcoes/ classes entre arquivos
  - Extrair funcao de bloco de codigo
  - Aplicar refactorings comuns (extract, inline, move)
  - Preview de mudancas antes de aplicar
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Multi-File Refactor"

import os
import re
import ast
import logging

logger = logging.getLogger(__name__)

IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "agente_data", ".agents"}


def _find_files(root: str, ext: str = ".py") -> list:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f.endswith(ext):
                files.append(os.path.join(dirpath, f))
    return files


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def register(api):

    def refactor_rename_symbol(symbol: str, new_name: str, root_dir: str = ".") -> str:
        files = _find_files(root_dir)
        changed = []
        for filepath in files:
            content = _read_file(filepath)
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, content):
                new_content = re.sub(pattern, new_name, content)
                if new_content != content:
                    _write_file(filepath, new_content)
                    rel = os.path.relpath(filepath, root_dir).replace("\\", "/")
                    count = len(re.findall(pattern, content))
                    changed.append(f"  {rel} ({count} replacements)")
        if not changed:
            return f"No references to '{symbol}' found."
        return f"✅ Renamed '{symbol}' → '{new_name}' in {len(changed)} files:\n" + "\n".join(changed)

    def refactor_move_function(func_name: str, from_file: str, to_file: str, root_dir: str = ".") -> str:
        from_path = os.path.join(root_dir, from_file)
        to_path = os.path.join(root_dir, to_file)
        if not os.path.exists(from_path):
            return f"❌ Source file not found: {from_file}"
        content = _read_file(from_path)
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return f"❌ Syntax error in {from_file}: {e}"
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                func_node = node
                break
        if not func_node:
            return f"❌ Function '{func_name}' not found in {from_file}"
        lines = content.split("\n")
        start = func_node.lineno - 1
        end = func_node.end_lineno if hasattr(func_node, 'end_lineno') else start + 1
        func_lines = lines[start:end]
        func_code = "\n".join(func_lines)
        new_lines = lines[:start] + lines[end:]
        _write_file(from_path, "\n".join(new_lines))
        to_content = _read_file(to_path) if os.path.exists(to_path) else ""
        new_to = to_content + "\n\n" + func_code if to_content else func_code + "\n"
        _write_file(to_path, new_to)
        return f"✅ Moved '{func_name}' from {from_file} → {to_file}"

    def refactor_extract_function(
        file_path: str, start_line: int, end_line: int, func_name: str, root_dir: str = "."
    ) -> str:
        full_path = os.path.join(root_dir, file_path)
        if not os.path.exists(full_path):
            return f"❌ File not found: {file_path}"
        content = _read_file(full_path)
        lines = content.split("\n")
        block = lines[start_line - 1:end_line]
        indent = len(block[0]) - len(block[0].lstrip())
        dedented = [l[indent:] if len(l) >= indent else l.lstrip() for l in block]
        func_def = f"def {func_name}():\n" + "\n".join("    " + l for l in dedented)
        call = " " * indent + f"{func_name}()"
        new_lines = lines[:start_line - 1] + [call] + lines[end_line:]
        new_content = "\n".join(new_lines)
        _write_file(full_path, new_content)
        existing = _read_file(full_path)
        _write_file(full_path, existing + "\n\n" + func_def)
        return f"✅ Extracted lines {start_line}-{end_line} → {func_name}() in {file_path}"

    def refactor_inline_function(func_name: str, file_path: str, root_dir: str = ".") -> str:
        full_path = os.path.join(root_dir, file_path)
        if not os.path.exists(full_path):
            return f"❌ File not found: {file_path}"
        content = _read_file(full_path)
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return f"❌ Syntax error: {e}"
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                func_node = node
                break
        if not func_node:
            return f"❌ Function '{func_name}' not found."
        lines = content.split("\n")
        func_body = lines[func_node.lineno:func_node.end_lineno]
        body_indent = len(func_body[0]) - len(func_body[0].lstrip())
        body_dedented = [l[body_indent:] if len(l) >= body_indent else l.strip() for l in func_body]
        new_content = content
        pattern = r'(?<!\w)' + re.escape(func_name) + r'\s*\(\s*\)'
        replacement = "\n".join(body_dedented)
        new_content = re.sub(pattern, replacement, new_content)
        func_start = func_node.lineno - 1
        func_end = func_node.end_lineno
        final_lines = new_content.split("\n")[:func_start] + new_content.split("\n")[func_end:]
        _write_file(full_path, "\n".join(final_lines))
        return f"✅ Inlined '{func_name}' in {file_path}"

    def refactor_find_usages(symbol: str, root_dir: str = ".") -> str:
        files = _find_files(root_dir)
        results = []
        for filepath in files:
            content = _read_file(filepath)
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                    rel = os.path.relpath(filepath, root_dir).replace("\\", "/")
                    results.append(f"  {rel}:{i} — {line.strip()[:100]}")
        if not results:
            return f"No usages of '{symbol}' found."
        return f"**{len(results)} usages of '{symbol}':**\n" + "\n".join(results[:30])

    def refactor_preview_rename(symbol: str, new_name: str, root_dir: str = ".") -> str:
        files = _find_files(root_dir)
        preview = []
        for filepath in files:
            content = _read_file(filepath)
            pattern = r'\b' + re.escape(symbol) + r'\b'
            matches = re.findall(pattern, content)
            if matches:
                rel = os.path.relpath(filepath, root_dir).replace("\\", "/")
                preview.append(f"  {rel}: {len(matches)} occurrences")
        if not preview:
            return f"No occurrences of '{symbol}' found."
        return f"**Preview: '{symbol}' → '{new_name}':**\n" + "\n".join(preview)

    api.register_tool("refactor_rename_symbol", refactor_rename_symbol,
        "Rename symbol across all files.",
        {"symbol": {"type": "string"}, "new_name": {"type": "string"},
         "root_dir": {"type": "string"}}, ["symbol", "new_name"])

    api.register_tool("refactor_move_function", refactor_move_function,
        "Move function between files.",
        {"func_name": {"type": "string"}, "from_file": {"type": "string"},
         "to_file": {"type": "string"}, "root_dir": {"type": "string"}},
        ["func_name", "from_file", "to_file"])

    api.register_tool("refactor_extract_function", refactor_extract_function,
        "Extract code block into new function.",
        {"file_path": {"type": "string"}, "start_line": {"type": "integer"},
         "end_line": {"type": "integer"}, "func_name": {"type": "string"},
         "root_dir": {"type": "string"}}, ["file_path", "start_line", "end_line", "func_name"])

    api.register_tool("refactor_inline_function", refactor_inline_function,
        "Inline a function at all call sites.",
        {"func_name": {"type": "string"}, "file_path": {"type": "string"},
         "root_dir": {"type": "string"}}, ["func_name", "file_path"])

    api.register_tool("refactor_find_usages", refactor_find_usages,
        "Find all usages of a symbol.",
        {"symbol": {"type": "string"}, "root_dir": {"type": "string"}}, ["symbol"])

    api.register_tool("refactor_preview_rename", refactor_preview_rename,
        "Preview rename before applying.",
        {"symbol": {"type": "string"}, "new_name": {"type": "string"},
         "root_dir": {"type": "string"}}, ["symbol", "new_name"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Multi-file refactor: rename, move, extract, inline, find usages, preview.",
        "tools": ["refactor_rename_symbol", "refactor_move_function", "refactor_extract_function",
                   "refactor_inline_function", "refactor_find_usages", "refactor_preview_rename"],
    }
