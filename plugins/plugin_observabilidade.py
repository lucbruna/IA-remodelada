"""Rastros locais para modelos, agentes, MCPs e ferramentas multimodais."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"
PLUGIN_NAME = "Observabilidade"
FILE = Path(__file__).resolve().parent.parent / "agente_data" / "observabilidade" / "traces.json"

def _load():
    try: return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return []

def registrar_trace(tipo: str, nome: str, sucesso: bool = True, duracao_ms: float = 0, detalhes: str = "") -> dict:
    traces = _load(); record = {"timestamp": datetime.now(timezone.utc).isoformat(), "type": tipo, "name": nome, "success": bool(sucesso), "duration_ms": round(float(duracao_ms), 2), "details": detalhes[:1000]}
    traces.append(record); FILE.parent.mkdir(parents=True, exist_ok=True); temp = FILE.with_suffix(".tmp"); temp.write_text(json.dumps(traces[-10000:], ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(FILE)
    return record

def resumo_observabilidade() -> dict:
    traces = _load(); total = len(traces); by_type = {}
    for trace in traces: by_type[trace["type"]] = by_type.get(trace["type"], 0) + 1
    return {"total": total, "failures": sum(1 for t in traces if not t["success"]), "average_ms": round(sum(t["duration_ms"] for t in traces) / total, 2) if total else 0, "by_type": by_type, "recent": traces[-50:]}

def register(api):
    api.register_tool("registrar_trace", registrar_trace, "Registra trace local de modelo, agente, MCP ou ferramenta multimodal.", {"tipo": {"type": "string"}, "nome": {"type": "string"}, "sucesso": {"type": "boolean"}, "duracao_ms": {"type": "number"}, "detalhes": {"type": "string"}}, ["tipo", "nome"])
    api.register_tool("resumo_observabilidade", resumo_observabilidade, "Resume traces, falhas e tempos por tipo.", {}, [])
    return {"name": PLUGIN_NAME, "version": __version__, "description": "Observabilidade local estruturada.", "tools": ["registrar_trace", "resumo_observabilidade"]}
