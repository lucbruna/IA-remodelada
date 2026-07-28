"""Validador universal de entregas com evidencias persistentes.

Este plugin fecha o ciclo de trabalho do agente: inspeciona o alvo, executa
validacoes deterministicas e salva um relatorio que pode ser consultado pelo
orquestrador, pelo dashboard ou pelo proprio usuario.  Ele nunca usa shell e
somente opera dentro do workspace do agente.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "1.0.0"
PLUGIN_NAME = "Validador Universal"

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_FILE = ROOT_DIR / "agente_data" / "validacao_universal" / "relatorios.json"
MAX_OUTPUT = 6_000


def _safe_target(path: str = "") -> Path:
    """Resolve um alvo e impede que a ferramenta saia do workspace."""
    root = ROOT_DIR.resolve()
    candidate = Path(path).expanduser() if path else root
    target = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if target != root and root not in target.parents:
        raise ValueError("O alvo precisa estar dentro do workspace do agente.")
    if not target.exists():
        raise FileNotFoundError(f"Alvo inexistente: {target}")
    return target


def _load_reports() -> list[dict[str, Any]]:
    try:
        return json.loads(REPORTS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _save_report(report: dict[str, Any]) -> None:
    REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    reports = _load_reports()
    reports.append(report)
    temporary = REPORTS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(reports[-100:], ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REPORTS_FILE)


def _run(args: list[str], cwd: Path, timeout: int = 120) -> dict[str, Any]:
    start = time.monotonic()
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=False)
        output = ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")).strip()
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "seconds": round(time.monotonic() - start, 2),
            "output": output[-MAX_OUTPUT:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": None, "seconds": round(time.monotonic() - start, 2), "output": "Timeout"}
    except OSError as exc:
        return {"ok": False, "code": None, "seconds": round(time.monotonic() - start, 2), "output": str(exc)}


def _source_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix == ".py" else []
    ignored = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
    return [path for path in target.rglob("*.py") if not any(part in ignored for part in path.parts)]


def _quality_scan(files: list[Path]) -> dict[str, Any]:
    markers: list[str] = []
    broad_excepts: list[str] = []
    for file in files:
        try:
            for line_number, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(r"\b(TODO|FIXME|XXX)\b", line, flags=re.IGNORECASE):
                    markers.append(f"{file.name}:{line_number}: {line.strip()[:120]}")
                if re.match(r"\s*except\s+Exception\s*:\s*$", line):
                    broad_excepts.append(f"{file.name}:{line_number}")
        except OSError:
            continue
    return {"ok": True, "markers": markers[:50], "bare_exception_count": len(broad_excepts), "bare_exceptions": broad_excepts[:50]}


def validar_entrega(alvo: str = "", executar_testes: bool = True, timeout: int = 120) -> str:
    """Valida sintaxe, testes disponiveis e sinais basicos de qualidade."""
    target = _safe_target(alvo)
    cwd = target if target.is_dir() else target.parent
    files = _source_files(target)
    checks: list[dict[str, Any]] = []

    if files:
        checks.append({"nome": "compilacao_python", **_run([sys.executable, "-m", "py_compile", *map(str, files)], cwd, timeout)})
    else:
        checks.append({"nome": "compilacao_python", "ok": True, "code": 0, "seconds": 0, "output": "Nenhum arquivo Python no alvo."})

    test_files = [path for path in (cwd.rglob("test_*.py") if cwd.is_dir() else []) if ".venv" not in path.parts]
    if executar_testes and test_files:
        checks.append({"nome": "pytest", **_run([sys.executable, "-m", "pytest", "-q", *map(str, test_files)], cwd, timeout)})
    elif executar_testes:
        checks.append({"nome": "pytest", "ok": True, "code": 0, "seconds": 0, "output": "Nenhum teste descoberto."})

    quality = _quality_scan(files)
    report = {
        "id": f"validation-{int(time.time() * 1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": str(target),
        "source_files": len(files),
        "checks": checks,
        "quality": quality,
        "approved": all(check["ok"] for check in checks),
    }
    _save_report(report)

    lines = ["--- Validacao Universal ---", f"Alvo: {target}", f"Arquivos Python: {len(files)}"]
    for check in checks:
        lines.append(f"- {check['nome']}: {'APROVADO' if check['ok'] else 'FALHOU'} ({check['seconds']}s)")
        if not check["ok"] and check["output"]:
            lines.append(check["output"][-1500:])
    lines.append(f"- Qualidade: {len(quality['markers'])} marcador(es), {quality['bare_exception_count']} except Exception sem tipo")
    lines.append(f"Veredito: {'APROVADO' if report['approved'] else 'PRECISA DE CORRECAO'}")
    lines.append("Evidencia salva em agente_data/validacao_universal/relatorios.json")
    return "\n".join(lines)


def status_validacoes(limite: int = 10) -> str:
    """Lista as ultimas validacoes persistidas."""
    reports = _load_reports()[-max(1, min(int(limite), 50)):]
    if not reports:
        return "Nenhuma validacao registrada."
    lines = ["--- Historico de Validacoes ---"]
    for report in reversed(reports):
        status = "APROVADO" if report.get("approved") else "FALHOU"
        lines.append(f"- {status} | {report.get('timestamp')} | {report.get('target')}")
    return "\n".join(lines)


def register(api):
    api.register_tool(
        "validar_entrega", validar_entrega,
        "Executa validacao deterministica de uma entrega: compilacao, testes e sinais de qualidade; salva evidencia.",
        {
            "alvo": {"type": "string", "description": "Arquivo ou pasta dentro do workspace"},
            "executar_testes": {"type": "boolean", "description": "Executar pytest quando houver testes"},
            "timeout": {"type": "integer", "description": "Timeout por verificacao, em segundos"},
        }, [],
    )
    api.register_tool(
        "status_validacoes", status_validacoes,
        "Mostra o historico recente de validacoes e seus vereditos.",
        {"limite": {"type": "integer", "description": "Quantidade de relatorios"}}, [],
    )
    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Valida entregas com compilacao, testes, sinais de qualidade e evidencia persistente.",
        "tools": ["validar_entrega", "status_validacoes"],
    }
