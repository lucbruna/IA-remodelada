"""Avaliacoes repetiveis de tarefas, com baseline e deteccao de regressao."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"
PLUGIN_NAME = "Avaliacoes Continuas"
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "agente_data" / "avaliacoes" / "execucoes.json"

def _load():
    try: return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return []

def _save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data[-500:], ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(DATA_FILE)

def executar_avaliacao(nome: str, comando: str, projeto: str = ".", timeout_segundos: int = 300) -> str:
    root = (ROOT_DIR / projeto).resolve()
    if root != ROOT_DIR and ROOT_DIR not in root.parents: raise ValueError("Projeto fora do workspace permitido.")
    started = time.monotonic()
    try:
        result = subprocess.run(comando, cwd=root, shell=True, capture_output=True, text=True, timeout=max(1, min(int(timeout_segundos), 900)))
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        result, timed_out = exc, True
    duration = round(time.monotonic() - started, 3)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "name": nome, "project": str(root), "command": comando, "passed": not timed_out and result.returncode == 0, "duration_seconds": duration, "exit_code": None if timed_out else result.returncode, "output": ((getattr(result, "stdout", "") or "") + "\n" + (getattr(result, "stderr", "") or ""))[-8000:]}
    history = _load(); prior = [r for r in history if r["name"] == nome and r["project"] == str(root) and r["passed"]]
    if prior:
        baseline = sum(r["duration_seconds"] for r in prior[-10:]) / min(len(prior), 10)
        record.update(regression=record["passed"] and duration > baseline * 1.5, baseline_seconds=round(baseline, 3))
    else: record["regression"] = False
    history.append(record); _save(history)
    return json.dumps(record, ensure_ascii=False)

def relatorio_avaliacoes() -> dict:
    records = _load(); total = len(records); passed = sum(1 for r in records if r["passed"])
    return {"total": total, "approved": passed, "approval_rate": round(100 * passed / total, 2) if total else 0.0, "failures": total - passed, "regressions": sum(1 for r in records if r.get("regression")), "average_seconds": round(sum(r["duration_seconds"] for r in records) / total, 3) if total else 0.0, "recent": records[-20:]}

def register(api):
    api.register_tool("executar_avaliacao", executar_avaliacao, "Executa uma avaliacao versionavel, registra aprovacao, tempo, falha e regressao.", {"nome": {"type": "string"}, "comando": {"type": "string"}, "projeto": {"type": "string"}, "timeout_segundos": {"type": "integer"}}, ["nome", "comando"])
    api.register_tool("relatorio_avaliacoes", relatorio_avaliacoes, "Retorna taxa de aprovacao, tempos, falhas e regressoes.", {}, [])
    return {"name": PLUGIN_NAME, "version": __version__, "description": "Metricas continuas de qualidade e regressao.", "tools": ["executar_avaliacao", "relatorio_avaliacoes"]}
