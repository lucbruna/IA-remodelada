"""
core/verification_catalog.py
============================
Catálogo de verificações mínimas inspirado no Fable 5 Methodology.

O Fable 5 define "verification catalog" - o menor check que falharia se
você estivesse errado. Este módulo implementa esse conceito para o agente local.

Princípio: "verify with the smallest check that would fail if you're wrong"

Categorias de verificação:
  - codigo: testes unitários, lint, type check
  - arquivo: existência, tamanho, hash
  - web: status code, conteúdo esperado
  - api: response schema, status code
  - dados: schema validation, row count
  - sistema: processo rodando, porta aberta

Uso:
    from core.verification_catalog import verify_task, get_catalog_entry

    # Verifica se um arquivo Python tem sintaxe válida
    result = verify_task("codigo", "python_syntax", "/caminho/para/arquivo.py")
    print(result)  # {"passed": True, "details": "..."}
"""

import os
import ast
import hashlib
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from ._common import os, _load_json, _save_json, DATA_DIR

VERIFICATION_DIR = os.path.join(DATA_DIR, "verifications")
os.makedirs(VERIFICATION_DIR, exist_ok=True)

_VERIFICATION_REGISTRY: Dict[str, Callable] = {}


def register_verification(category: str, name: str):
    """Decorator para registrar uma verificação."""
    def decorator(func: Callable) -> Callable:
        key = f"{category}:{name}"
        _VERIFICATION_REGISTRY[key] = func
        return func
    return decorator


@register_verification("codigo", "python_syntax")
def _verify_python_syntax(filepath: str) -> Dict[str, Any]:
    """Verifica se um arquivo Python tem sintaxe válida."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        return {"passed": True, "details": f"Sintaxe valida: {filepath}"}
    except SyntaxError as e:
        return {"passed": False, "details": f"Erro de sintaxe: {e}", "error": str(e)}
    except FileNotFoundError:
        return {"passed": False, "details": f"Arquivo nao encontrado: {filepath}", "error": "FileNotFoundError"}
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("codigo", "python_imports")
def _verify_python_imports(filepath: str) -> Dict[str, Any]:
    """Verifica se todos os imports do arquivo estão disponíveis."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        __import__(alias.name)
                    except ImportError:
                        missing.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    try:
                        __import__(node.module)
                    except ImportError:
                        missing.append(node.module)
        if missing:
            return {"passed": False, "details": f"Imports faltando: {missing}", "missing": missing}
        return {"passed": True, "details": "Todos os imports disponiveis"}
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("codigo", "python_compile")
def _verify_python_compile(filepath: str) -> Dict[str, Any]:
    """Compila o arquivo Python e verifica por erros."""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", filepath],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"passed": True, "details": "Compilacao bem-sucedida"}
        return {"passed": False, "details": result.stderr, "error": result.stderr}
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("codigo", "pytest_exists")
def _verify_pytest_exists(filepath: str) -> Dict[str, Any]:
    """Verifica se existem testes para o arquivo."""
    test_patterns = [
        filepath.replace(".py", "_test.py"),
        filepath.replace(".py", "_test.py").replace("src/", "tests/"),
        filepath.replace(".py", "_test.py").replace("core/", "tests/"),
        os.path.join("tests", os.path.basename(filepath).replace(".py", "_test.py")),
    ]
    for pattern in test_patterns:
        if os.path.exists(pattern):
            return {"passed": True, "details": f"Teste encontrado: {pattern}", "test_file": pattern}
    return {"passed": False, "details": "Nenhum arquivo de teste encontrado", "patterns_checked": test_patterns}


@register_verification("arquivo", "exists")
def _verify_file_exists(filepath: str) -> Dict[str, Any]:
    """Verifica se um arquivo existe."""
    exists = os.path.exists(filepath)
    if exists:
        stat = os.stat(filepath)
        return {
            "passed": True,
            "details": f"Arquivo existe: {filepath} ({stat.st_size} bytes)",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    return {"passed": False, "details": f"Arquivo nao existe: {filepath}"}


@register_verification("arquivo", "hash")
def _verify_file_hash(filepath: str, expected_hash: str = None) -> Dict[str, Any]:
    """Verifica o hash de um arquivo."""
    try:
        with open(filepath, "rb") as f:
            content = f.read()
        actual_hash = hashlib.sha256(content).hexdigest()
        if expected_hash:
            passed = actual_hash == expected_hash
            return {
                "passed": passed,
                "details": f"Hash: {actual_hash}" + (f" (esperado: {expected_hash})" if not passed else ""),
                "hash": actual_hash,
                "expected": expected_hash,
            }
        return {"passed": True, "details": f"Hash: {actual_hash}", "hash": actual_hash}
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("arquivo", "size")
def _verify_file_size(filepath: str, max_size_mb: int = 10) -> Dict[str, Any]:
    """Verifica se o arquivo esta dentro do limite de tamanho."""
    try:
        size = os.path.getsize(filepath)
        max_bytes = max_size_mb * 1024 * 1024
        passed = size <= max_bytes
        return {
            "passed": passed,
            "details": f"Tamanho: {size} bytes (limite: {max_bytes} bytes)",
            "size": size,
            "limit": max_bytes,
        }
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("web", "status_code")
def _verify_web_status(url: str, expected_status: int = 200) -> Dict[str, Any]:
    """Verifica o status code de uma URL."""
    try:
        import requests
        resp = requests.get(url, timeout=15, allow_redirects=True)
        passed = resp.status_code == expected_status
        return {
            "passed": passed,
            "details": f"Status: {resp.status_code} (esperado: {expected_status})",
            "status": resp.status_code,
            "url": resp.url,
        }
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("web", "content_contains")
def _verify_web_content(url: str, text: str) -> Dict[str, Any]:
    """Verifica se o conteúdo de uma URL contém um texto."""
    try:
        import requests
        resp = requests.get(url, timeout=15)
        passed = text.lower() in resp.text.lower()
        return {
            "passed": passed,
            "details": f"Texto '{text}' " + ("encontrado" if passed else "nao encontrado"),
            "found": passed,
        }
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("api", "json_schema")
def _verify_api_json_schema(data: Any, required_keys: List[str]) -> Dict[str, Any]:
    """Verifica se um JSON tem as chaves requeridas."""
    if not isinstance(data, dict):
        return {"passed": False, "details": "Dados nao sao um dict", "error": "TypeError"}
    missing = [k for k in required_keys if k not in data]
    if missing:
        return {"passed": False, "details": f"Chaves faltando: {missing}", "missing": missing}
    return {"passed": True, "details": f"Todas as chaves presentes: {required_keys}"}


@register_verification("dados", "row_count")
def _verify_dados_row_count(filepath: str, min_rows: int = 1) -> Dict[str, Any]:
    """Verifica o numero de linhas em um arquivo CSV/JSON."""
    try:
        if filepath.endswith(".csv"):
            import csv
            with open(filepath, "r") as f:
                count = sum(1 for _ in csv.reader(f)) - 1
        elif filepath.endswith(".json"):
            data = _load_json(filepath, [])
            count = len(data) if isinstance(data, list) else 1
        else:
            return {"passed": False, "details": "Formato nao suportado"}
        passed = count >= min_rows
        return {
            "passed": passed,
            "details": f"Linhas: {count} (minimo: {min_rows})",
            "count": count,
            "min": min_rows,
        }
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("sistema", "process_running")
def _verify_sistema_process(name: str) -> Dict[str, Any]:
    """Verifica se um processo esta rodando."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            if name.lower() in proc.info["name"].lower():
                return {"passed": True, "details": f"Processo rodando: {proc.info['name']}", "pid": proc.pid}
        return {"passed": False, "details": f"Processo nao encontrado: {name}"}
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


@register_verification("sistema", "port_open")
def _verify_sistema_port(port: int, host: str = "localhost") -> Dict[str, Any]:
    """Verifica se uma porta esta aberta."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        passed = result == 0
        return {
            "passed": passed,
            "details": f"Porta {port} " + ("aberta" if passed else "fechada"),
            "port": port,
            "host": host,
        }
    except Exception as e:
        return {"passed": False, "details": f"Erro: {e}", "error": str(e)}


def verify_task(category: str, name: str, *args, **kwargs) -> Dict[str, Any]:
    """Executa uma verificação do catálogo.

    Args:
        category: Categoria (codigo, arquivo, web, api, dados, sistema)
        name: Nome da verificação
        *args, **kwargs: Argumentos para a verificação

    Returns:
        Dict com passed, details e metadados

    Exemplo:
        verify_task("codigo", "python_syntax", "/path/to/file.py")
        verify_task("arquivo", "exists", "/path/to/file.txt")
        verify_task("web", "status_code", "https://example.com", 200)
    """
    key = f"{category}:{name}"
    func = _VERIFICATION_REGISTRY.get(key)
    if not func:
        return {"passed": False, "details": f"Verificacao nao encontrada: {key}", "error": "KeyError"}

    try:
        result = func(*args, **kwargs)
        result["category"] = category
        result["name"] = name
        result["timestamp"] = datetime.now().isoformat()
        return result
    except Exception as e:
        return {
            "passed": False,
            "details": f"Erro ao executar verificacao: {e}",
            "error": str(e),
            "category": category,
            "name": name,
            "timestamp": datetime.now().isoformat(),
        }


def get_catalog_entry(category: str, name: str) -> Optional[Callable]:
    """Retorna a função de uma verificação do catálogo."""
    return _VERIFICATION_REGISTRY.get(f"{category}:{name}")


def list_catalog() -> Dict[str, List[str]]:
    """Lista todas as verificações disponíveis, organizadas por categoria."""
    catalog: Dict[str, List[str]] = {}
    for key in _VERIFICATION_REGISTRY:
        category, name = key.split(":", 1)
        catalog.setdefault(category, []).append(name)
    return catalog


def verify_all_for_task(task_type: str, target: str) -> List[Dict[str, Any]]:
    """Executa todas as verificações aplicáveis para um tipo de tarefa.

    Args:
        task_type: "python_file", "web_page", "api_endpoint", "json_file"
        target: Caminho/URL do alvo

    Returns:
        Lista de resultados de verificação
    """
    checks = {
        "python_file": [
            ("codigo", "python_syntax", (target,)),
            ("codigo", "python_imports", (target,)),
            ("codigo", "python_compile", (target,)),
            ("codigo", "pytest_exists", (target,)),
            ("arquivo", "exists", (target,)),
            ("arquivo", "size", (target, 10)),
        ],
        "web_page": [
            ("web", "status_code", (target, 200)),
        ],
        "api_endpoint": [
            ("web", "status_code", (target, 200)),
        ],
        "json_file": [
            ("arquivo", "exists", (target,)),
            ("arquivo", "size", (target, 10)),
        ],
    }

    results = []
    for category, name, args in checks.get(task_type, []):
        results.append(verify_task(category, name, *args))
    return results


def save_verification_result(task_id: str, result: Dict[str, Any]) -> None:
    """Salva o resultado de uma verificação."""
    file_path = os.path.join(VERIFICATION_DIR, f"{task_id}.json")
    _save_json(file_path, result)


def load_verification_result(task_id: str) -> Optional[Dict[str, Any]]:
    """Carrega o resultado de uma verificação."""
    file_path = os.path.join(VERIFICATION_DIR, f"{task_id}.json")
    return _load_json(file_path, None)


def run_preflight_check(target: str, task_type: str) -> Dict[str, Any]:
    """Executa verificação pré-completa (preflight) antes de uma tarefa.

    Inspirado no Fable 5 preflight.sh - verifica se o ambiente esta pronto.
    """
    results = verify_all_for_task(task_type, target)
    all_passed = all(r.get("passed", False) for r in results)
    failed = [r for r in results if not r.get("passed", False)]

    return {
        "passed": all_passed,
        "target": target,
        "task_type": task_type,
        "total_checks": len(results),
        "passed_checks": len(results) - len(failed),
        "failed_checks": len(failed),
        "results": results,
        "failed_details": failed,
        "timestamp": datetime.now().isoformat(),
    }
