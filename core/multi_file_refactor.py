import os
import re
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime


def multi_file_refactor(task: str, repo_path: str = None, validate: bool = True) -> Dict[str, Any]:
    """Executa refatoracao multi-arquivo com sub-agentes isolados.

    Args:
        task: Descricao da refatoracao
        repo_path: Caminho do repositorio (padrao: atual)
        validate: Rodar checker independente apos execucao

    Returns:
        Dict com resultados por arquivo e status geral
    """
    if repo_path is None:
        repo_path = os.getcwd()

    # 1. Planeja a refatoracao
    plan = _plan_refactor(task, repo_path)

    # 2. Executa em sub-agentes isolados (um por arquivo)
    results = []
    for item in plan.get("files", []):
        filepath = item.get("file", "")
        change = item.get("change", "")
        try:
            result = _apply_change(filepath, change, repo_path)
            results.append({"file": filepath, "change": change, "status": result.get("status", "ok"), "diff": result.get("diff", "")})
        except Exception as e:
            results.append({"file": filepath, "change": change, "status": "error", "error": str(e)})

    # 3. Validacao
    validation = {"passed": True, "details": []}
    if validate:
        validation = _validate_refactor(results, repo_path)

    # 4. Sintese
    return {
        "task": task,
        "plan": plan,
        "results": results,
        "validation": validation,
        "all_passed": all(r.get("status") == "ok" for r in results) and validation.get("passed", False),
        "timestamp": datetime.now().isoformat(),
    }


def _plan_refactor(task: str, repo_path: str) -> Dict[str, Any]:
    """Planeja a refatoracao identificando arquivos afetados."""
    files_to_change = []
    description = task

    # Tenta usar o LLM para planejar se disponivel
    try:
        from core.llm_backend import get_backend, ChatMessage
        backend = get_backend()
        prompt = f"""Given this refactoring task: {task}

In the repo at {repo_path}, list the files that need to be changed and what change is needed in each.
Return ONLY a JSON array of objects with "file" (relative path) and "change" (description of change).
Example: [{{"file": "src/main.py", "change": "Add error handling to process_data()"}}]"""
        response = backend.chat([ChatMessage(role="user", content=prompt)], model=None, max_tokens=2000)
        content = response.content.strip()
        content = re.sub(r"^```(json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        files_to_change = json.loads(content) if content else []
    except Exception:
        files_to_change = [{"file": "", "change": task}]

    return {"description": description, "files": files_to_change if isinstance(files_to_change, list) else []}


def _apply_change(filepath: str, change: str, repo_path: str) -> Dict[str, Any]:
    """Aplica uma mudanca em um arquivo usando sub-agente isolado."""
    if not filepath or not os.path.exists(os.path.join(repo_path, filepath)):
        return {"status": "skipped", "reason": f"Arquivo nao encontrado: {filepath}"}

    full_path = os.path.join(repo_path, filepath)
    with open(full_path, "r") as f:
        original = f.read()

    try:
        from core.llm_backend import get_backend, ChatMessage
        backend = get_backend()
        prompt = f"""Refactor this file according to: {change}

Current content:
```python
{original[:8000]}
```

Return the COMPLETE new file content inside a code block.
Make ONLY the changes described, preserve everything else."""
        response = backend.chat([ChatMessage(role="user", content=prompt)], max_tokens=16000)
        new_content = response.content.strip()
        new_content = re.sub(r"^```[\w]*\n?", "", new_content)
        new_content = re.sub(r"\n?```$", "", new_content)

        if new_content and new_content != original:
            with open(full_path, "w") as f:
                f.write(new_content)
            try:
                diff = subprocess.run(["git", "diff", filepath], capture_output=True, text=True, cwd=repo_path).stdout
            except Exception:
                diff = "(git diff indisponivel)"
            return {"status": "ok", "diff": diff[:1000]}
        return {"status": "no_change", "reason": "Conteudo nao alterado"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _validate_refactor(results: List[Dict], repo_path: str) -> Dict[str, Any]:
    """Valida os resultados da refatoracao."""
    passed = True
    details = []

    for r in results:
        if r.get("status") == "ok":
            filepath = r.get("file", "")
            full_path = os.path.join(repo_path, filepath)
            if os.path.exists(full_path):
                details.append(f"{filepath}: alterado")
                try:
                    import ast
                    with open(full_path, "r") as f:
                        ast.parse(f.read())
                    details.append(f"{filepath}: sintaxe valida")
                except SyntaxError as e:
                    details.append(f"{filepath}: ERRO de sintaxe: {e}")
                    passed = False
            else:
                details.append(f"{filepath}: ARQUIVO NAO ENCONTRADO")
                passed = False
        elif r.get("status") == "error":
            details.append(f"{r.get('file')}: erro: {r.get('error')}")
            passed = False

    return {"passed": passed, "details": details}
