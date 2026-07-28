"""Memoria de projeto, contratos de delegacao e avaliacoes operacionais."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "agente_data" / "operacao_profissional"


def _safe_target(path: str = "") -> Path:
    root = ROOT_DIR.resolve(); candidate = Path(path) if path else root
    target = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if target != root and root not in target.parents:
        raise ValueError("Projeto fora do workspace permitido.")
    if not target.exists():
        raise FileNotFoundError(f"Projeto inexistente: {target}")
    return target


def _write(name: str, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(name: str, default):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _expandir_tokens(tokens: list) -> set:
    """Expande tokens separados por underscore para busca lexical.
    
    Ex: "calcular_total" -> {"calcular_total", "calcular", "total"}
    Permite que busca por "calcular total" encontre calcular_total.
    """
    expandidos = set(tokens)
    for t in tokens:
        partes = t.split("_")
        if len(partes) > 1:
            expandidos.update(p for p in partes if len(p) >= 2)
    return sorted(expandidos)[:500]


def indexar_memoria_projeto(projeto: str = "") -> str:
    """Indexa codigo e documentacao localmente; nao envia dados para fora."""
    target = _safe_target(projeto)
    files = [target] if target.is_file() else [p for p in target.rglob("*") if p.suffix.lower() in {".py", ".md", ".txt", ".json", ".html", ".js", ".css"} and not any(x in p.parts for x in {".git", ".venv", "node_modules", "__pycache__"})]
    entries = []
    for file in files[:1000]:
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")[:12000]
            tokens_raw = sorted(set(re.findall(r"[a-zA-ZÀ-ÿ_][\wÀ-ÿ_]{2,}", text.lower())))[:500]
            # Expande tokens com underscore para busca parcial
            tokens = _expandir_tokens(tokens_raw)
            entries.append({"path": str(file), "tokens": tokens, "preview": text[:1200]})
        except OSError:
            pass
    index = _read("memoria_projetos.json", {})
    index[str(target)] = {"updated_at": datetime.now(timezone.utc).isoformat(), "entries": entries}
    _write("memoria_projetos.json", index)
    return f"Memoria de projeto indexada: {len(entries)} arquivos em {target}."


def _expandir_termos(consulta: str) -> set:
    """Extrai termos da consulta e também expande em partes separadas por underscore.
    
    Ex: "calcular_total" -> {"calcular_total", "calcular", "total"}
    Isso permite que a busca por "calcular total" encontre "calcular_total".
    """
    tokens = set(re.findall(r"[a-zA-ZÀ-ÿ_][\wÀ-ÿ_]{2,}", consulta.lower()))
    expandidos = set(tokens)
    for t in tokens:
        partes = t.split("_")
        if len(partes) > 1:
            expandidos.update(p for p in partes if len(p) >= 2)
    return expandidos


def buscar_memoria_projeto(consulta: str, projeto: str = "", limite: int = 5) -> str:
    """Busca lexical local na memoria de um projeto previamente indexado."""
    target = str(_safe_target(projeto)) if projeto else ""
    indices = _read("memoria_projetos.json", {})
    collections = {target: indices.get(target, {})} if target else indices
    terms = _expandir_termos(consulta)
    results = []
    for project, data in collections.items():
        for entry in data.get("entries", []):
            score = len(terms.intersection(entry.get("tokens", [])))
            if score:
                results.append((score, project, entry))
    results.sort(key=lambda item: item[0], reverse=True)
    if not results:
        return "Nenhum trecho encontrado. Indexe o projeto antes de buscar."
    lines = ["--- Memoria de Projeto ---"]
    for score, project, entry in results[:max(1, min(int(limite), 20))]:
        lines.append(f"[{score}] {entry['path']}\n{entry['preview'][:500]}")
    return "\n\n".join(lines)


def criar_contrato_delegacao(objetivo: str, agente: str, criterios: str = "") -> str:
    """Cria contrato JSON para delegacao com criterio verificavel de conclusao."""
    return json.dumps({"objetivo": objetivo, "agente": agente, "entregaveis": ["resultado", "arquivos_alterados", "testes_executados", "riscos"], "criterios_aceite": criterios or "Resultado verificavel; testes ou evidencia registrados.", "formato_resposta": "JSON"}, ensure_ascii=False, indent=2)


def validar_contrato_delegacao(resposta_json: str) -> str:
    """Verifica se a resposta de um agente possui os campos minimos do contrato."""
    try:
        response = json.loads(resposta_json)
    except json.JSONDecodeError as exc:
        return f"Contrato invalido: JSON malformado ({exc.msg})."
    required = {"resultado", "arquivos_alterados", "testes_executados", "riscos"}
    missing = sorted(key for key in required if key not in response)
    return "Contrato aprovado." if not missing else f"Contrato incompleto; faltam: {', '.join(missing)}."


def avaliar_prontidao_operacional() -> str:
    """Gera linha de base para sandbox, memoria, CI e observabilidade."""
    index = _read("memoria_projetos.json", {})
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sandbox_container": bool(shutil.which("docker")),
        "memorias_de_projeto": len(index),
        "ci_configurado": (ROOT_DIR / ".github" / "workflows" / "quality.yml").exists(),
        "fluxo_persistente": (ROOT_DIR / "agente_data" / "fluxo_autonomo" / "tarefas.json").exists(),
    }
    history = _read("avaliacoes.json", []); history.append(report); _write("avaliacoes.json", history[-100:])
    return json.dumps(report, ensure_ascii=False, indent=2)


def register(api):
    api.register_tool("indexar_memoria_projeto", indexar_memoria_projeto, "Indexa arquivos locais do projeto para memoria recuperavel.", {"projeto": {"type": "string", "description": "Pasta dentro do workspace"}}, [])
    api.register_tool("buscar_memoria_projeto", buscar_memoria_projeto, "Busca conhecimento em projeto previamente indexado.", {"consulta": {"type": "string", "description": "Busca"}, "projeto": {"type": "string", "description": "Projeto opcional"}, "limite": {"type": "integer", "description": "Resultados"}}, ["consulta"])
    api.register_tool("criar_contrato_delegacao", criar_contrato_delegacao, "Cria contrato JSON para delegar tarefa a agente especializado.", {"objetivo": {"type": "string", "description": "Objetivo"}, "agente": {"type": "string", "description": "Agente"}, "criterios": {"type": "string", "description": "Criterios de aceite"}}, ["objetivo", "agente"])
    api.register_tool("validar_contrato_delegacao", validar_contrato_delegacao, "Valida resposta JSON de um subagente contra contrato minimo.", {"resposta_json": {"type": "string", "description": "Resposta JSON"}}, ["resposta_json"])
    api.register_tool("avaliar_prontidao_operacional", avaliar_prontidao_operacional, "Mede prontidao de sandbox, memoria, CI e fluxo persistente.", {}, [])
    return {"name": "Operacao Profissional", "version": __version__, "description": "Memoria de projeto, contratos estruturados e avaliacoes operacionais.", "tools": ["indexar_memoria_projeto", "buscar_memoria_projeto", "criar_contrato_delegacao", "validar_contrato_delegacao", "avaliar_prontidao_operacional"]}
