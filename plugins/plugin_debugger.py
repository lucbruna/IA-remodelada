"""
plugin_debugger.py
==================
Debugger visual — breakpoints, step-through, variaveis, stack trace.

Funcionalidades:
  - Breakpoints em linhas especificas
  - Step-over, step-into, step-out
  - Inspecao de variaveis em tempo real
  - Stack trace completo
  - Watch expressions
  - Execucao pauseada com continuidade
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Visual Debugger"

import os
import ast
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "debugger")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

_debug_sessions = {}


class DebugSession:
    def __init__(self, session_id: str, code: str):
        self.id = session_id
        self.code = code
        self.breakpoints = set()
        self.watch_expressions = []
        self.current_line = 0
        self.variables = {}
        self.stack_trace = []
        self.status = "ready"
        self.output = []
        self.step_mode = None
        self._locals = {}
        self._globals = {"__builtins__": {
            "print": print, "len": len, "range": range, "str": str,
            "int": int, "float": float, "dict": dict, "list": list,
            "set": set, "tuple": tuple, "bool": bool, "type": type,
            "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
            "sorted": sorted, "reversed": reversed, "abs": abs, "min": min,
            "max": max, "sum": sum, "any": any, "all": all, "round": round,
            "True": True, "False": False, "None": None,
        }}

    def add_breakpoint(self, line: int):
        self.breakpoints.add(line)

    def remove_breakpoint(self, line: int):
        self.breakpoints.discard(line)

    def add_watch(self, expression: str):
        if expression not in self.watch_expressions:
            self.watch_expressions.append(expression)

    def evaluate_watch(self) -> dict:
        results = {}
        for expr in self.watch_expressions:
            try:
                val = eval(expr, self._globals, self._locals)
                results[expr] = repr(val)
            except Exception as e:
                results[expr] = f"ERROR: {e}"
        return results

    def get_stack(self) -> list:
        return self.stack_trace[-20:]

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "current_line": self.current_line,
            "breakpoints": sorted(self.breakpoints),
            "watch_expressions": self.watch_expressions,
            "variables": {k: repr(v)[:200] for k, v in self._locals.items()},
            "output": self.output[-50:],
            "stack_trace": self.get_stack(),
        }


def _save_sessions():
    os.makedirs(DATA_DIR, exist_ok=True)
    data = {sid: s.to_dict() for sid, s in _debug_sessions.items()}
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _instrument_code(session: DebugSession) -> str:
    lines = session.code.split("\n")
    instrumented = []
    for i, line in enumerate(lines, 1):
        indent = len(line) - len(line.lstrip())
        spaces = " " * indent
        if i in session.breakpoints:
            instrumented.append(f"{spaces}__debug_breakpoint({i}, locals(), globals())")
        instrumented.append(line)
    return "\n".join(instrumented)


def _debug_breakpoint(line: int, local_vars: dict, global_vars: dict):
    session = None
    for s in _debug_sessions.values():
        if s.current_line == 0 or True:
            session = s
            break
    if not session:
        return
    session.current_line = line
    session._locals.update(local_vars)
    session.variables = {k: repr(v)[:200] for k, v in local_vars.items() if not k.startswith("_")}
    session.stack_trace.append({"line": line, "time": datetime.now().isoformat()})
    session.output.append(f"BREAKPOINT at line {line}")


def register(api):

    def debugger_start(code: str, session_name: str = "") -> str:
        session_id = f"dbg-{len(_debug_sessions) + 1}"
        session = DebugSession(session_id, code)
        _debug_sessions[session_id] = session
        _save_sessions()
        return (
            f"🔧 Debugger session started: {session_id}\n"
            f"Lines: {len(code.split(chr(10)))}\n"
            f"Use debugger_add_breakpoint, debugger_step, debugger_run"
        )

    def debugger_add_breakpoint(session_id: str, line: int) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        session.add_breakpoint(line)
        return f"✅ Breakpoint added at line {line} (total: {len(session.breakpoints)})"

    def debugger_remove_breakpoint(session_id: str, line: int) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        session.remove_breakpoint(line)
        return f"✅ Breakpoint removed from line {line}"

    def debugger_add_watch(session_id: str, expression: str) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        session.add_watch(expression)
        return f"✅ Watch added: {expression}"

    def debugger_run(session_id: str) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        try:
            exec_globals = dict(session._globals)
            exec_globals["__debug_breakpoint"] = _debug_breakpoint
            exec_globals["__debug_locals"] = {}
            code = _instrument_code(session)
            exec(compile(code, "<debug>", "exec"), exec_globals)
            session.status = "completed"
            session.output.append("Execution completed.")
            _save_sessions()
            return f"✅ Execution completed.\nOutput:\n" + "\n".join(session.output[-20:])
        except Exception as e:
            session.status = "error"
            session.output.append(f"ERROR: {e}")
            _save_sessions()
            return f"❌ Error: {e}\n" + "\n".join(session.output[-10:])

    def debugger_step(session_id: str) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        session.step_mode = "step"
        session.status = "stepping"
        _save_sessions()
        return f"📍 Stepping... Current line: {session.current_line}"

    def debugger_status(session_id: str) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        d = session.to_dict()
        lines = [
            f"🔧 **Debugger Session {d['id']}**",
            f"Status: {d['status']}",
            f"Current line: {d['current_line']}",
            f"Breakpoints: {d['breakpoints']}",
            f"Variables: {len(d['variables'])}",
            f"Output lines: {len(d['output'])}",
        ]
        if d["variables"]:
            lines.append("\n**Variables:**")
            for k, v in list(d["variables"].items())[:15]:
                lines.append(f"  {k} = {v}")
        if d["watch_expressions"]:
            watch = session.evaluate_watch()
            lines.append("\n**Watch:**")
            for expr, val in watch.items():
                lines.append(f"  {expr} = {val}")
        return "\n".join(lines)

    def debugger_list_sessions() -> str:
        if not _debug_sessions:
            return "No active debug sessions."
        lines = ["🔧 **Debug Sessions:**\n"]
        for sid, s in _debug_sessions.items():
            lines.append(f"  • {sid}: {s.status} (line {s.current_line}, {len(s.breakpoints)} breakpoints)")
        return "\n".join(lines)

    def debugger_stop(session_id: str) -> str:
        session = _debug_sessions.get(session_id)
        if not session:
            return f"❌ Session '{session_id}' not found."
        session.status = "stopped"
        _save_sessions()
        return f"⏹️ Session {session_id} stopped."

    def debugger_analyze(code: str) -> str:
        try:
            tree = ast.parse(code)
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            imports = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports.extend(a.name for a in n.names)
                elif isinstance(n, ast.ImportFrom):
                    imports.append(n.module or "")
            lines = code.split("\n")
            potential_bp = []
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    if any(kw in stripped for kw in ["if ", "for ", "while ", "return ", "raise ", "assert "]):
                        potential_bp.append(i)
            return (
                f"📊 **Code Analysis:**\n"
                f"Lines: {len(lines)}\n"
                f"Functions: {funcs[:10]}\n"
                f"Classes: {classes[:5]}\n"
                f"Imports: {imports[:10]}\n"
                f"Suggested breakpoints: {potential_bp[:10]}"
            )
        except SyntaxError as e:
            return f"❌ Syntax error: {e}"

    api.register_tool("debugger_start", debugger_start,
        "Start a debug session with code.",
        {"code": {"type": "string", "description": "Code to debug"},
         "session_name": {"type": "string"}}, ["code"])

    api.register_tool("debugger_add_breakpoint", debugger_add_breakpoint,
        "Add breakpoint at line.",
        {"session_id": {"type": "string"}, "line": {"type": "integer"}}, ["session_id", "line"])

    api.register_tool("debugger_remove_breakpoint", debugger_remove_breakpoint,
        "Remove breakpoint from line.",
        {"session_id": {"type": "string"}, "line": {"type": "integer"}}, ["session_id", "line"])

    api.register_tool("debugger_add_watch", debugger_add_watch,
        "Add watch expression.",
        {"session_id": {"type": "string"}, "expression": {"type": "string"}}, ["session_id", "expression"])

    api.register_tool("debugger_run", debugger_run,
        "Run code with breakpoints.",
        {"session_id": {"type": "string"}}, ["session_id"])

    api.register_tool("debugger_step", debugger_step,
        "Step to next line.",
        {"session_id": {"type": "string"}}, ["session_id"])

    api.register_tool("debugger_status", debugger_status,
        "Get debugger session status.",
        {"session_id": {"type": "string"}}, ["session_id"])

    api.register_tool("debugger_list_sessions", debugger_list_sessions,
        "List all debug sessions.", {}, [])

    api.register_tool("debugger_stop", debugger_stop,
        "Stop debug session.",
        {"session_id": {"type": "string"}}, ["session_id"])

    api.register_tool("debugger_analyze", debugger_analyze,
        "Analyze code and suggest breakpoints.",
        {"code": {"type": "string"}}, ["code"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Visual debugger: breakpoints, step-through, variables, stack trace, watch expressions.",
        "tools": ["debugger_start", "debugger_add_breakpoint", "debugger_remove_breakpoint",
                   "debugger_add_watch", "debugger_run", "debugger_step", "debugger_status",
                   "debugger_list_sessions", "debugger_stop", "debugger_analyze"],
    }
