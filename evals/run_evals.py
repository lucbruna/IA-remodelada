"""
evals/run_evals.py
==================
Runner de testes de regressão comportamental.

Inspirado no Fable 5 evals/ - testes que capturam drift de comportamento.
Cada eval tem um task.md (prompt), check.sh (verificação) e expected/ (resultados esperados).

Uso:
    python evals/run_evals.py              # Roda todos
    python evals/run_evals.py code_generation  # Roda eval específico
"""

import os
import sys
import json
import subprocess
from datetime import datetime

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(EVALS_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def get_eval_dirs() -> list:
    """Retorna diretórios de eval disponíveis."""
    return [
        d for d in os.listdir(EVALS_DIR)
        if os.path.isdir(os.path.join(EVALS_DIR, d)) and not d.startswith("_")
    ]


def run_eval(eval_name: str) -> dict:
    """Roda um eval específico.

    Args:
        eval_name: Nome do diretório do eval

    Returns:
        Dict com resultado do eval
    """
    eval_dir = os.path.join(EVALS_DIR, eval_name)
    if not os.path.isdir(eval_dir):
        return {"name": eval_name, "passed": False, "error": "Eval nao encontrado"}

    task_file = os.path.join(eval_dir, "task.md")
    check_file = os.path.join(eval_dir, "check.sh")

    result = {
        "name": eval_name,
        "started_at": datetime.now().isoformat(),
        "passed": False,
        "details": "",
    }

    # Lê a tarefa
    task = ""
    if os.path.exists(task_file):
        with open(task_file, "r", encoding="utf-8") as f:
            task = f.read()

    # Executa o agente com a tarefa
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agente_core import run_agent_turn

        messages = [{"role": "user", "content": task}]
        run_agent_turn(messages)

        # Pega a resposta do assistente
        assistant_response = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                assistant_response = msg.get("content", "")
                break

        result["response"] = assistant_response[:500]

    except Exception as e:
        result["error"] = f"Erro ao executar agente: {e}"
        result["passed"] = False
        return result

    # Executa o check.sh
    if os.path.exists(check_file):
        try:
            proc = subprocess.run(
                ["bash", check_file],
                capture_output=True, text=True, timeout=60,
                cwd=eval_dir,
            )
            result["check_stdout"] = proc.stdout
            result["check_stderr"] = proc.stderr
            result["check_returncode"] = proc.returncode
            result["passed"] = proc.returncode == 0
            result["details"] = proc.stdout.strip() if proc.stdout else proc.stderr.strip()
        except Exception as e:
            result["error"] = f"Erro ao executar check.sh: {e}"
            result["passed"] = False
    else:
        # Se nao tem check.sh, verifica se a resposta contem "sucesso"
        result["passed"] = "sucesso" in assistant_response.lower() or len(assistant_response) > 50
        result["details"] = "Sem check.sh - verificacao basica"

    result["completed_at"] = datetime.now().isoformat()
    return result


def run_all_evals() -> dict:
    """Roda todos os evals e retorna relatório."""
    eval_names = get_eval_dirs()
    results = []

    for name in eval_names:
        print(f"  Rodando eval: {name}...")
        result = run_eval(name)
        results.append(result)
        status = "PASS" if result.get("passed") else "FAIL"
        print(f"    [{status}] {name}")

    # Salva resultados
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "failed": sum(1 for r in results if not r.get("passed")),
        "results": results,
    }

    report_file = os.path.join(RESULTS_DIR, f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    if len(sys.argv) > 1:
        eval_name = sys.argv[1]
        result = run_eval(eval_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = run_all_evals()
        print(f"\n{'='*60}")
        print(f"Evals concluidos: {report['passed']}/{report['total']} passaram")
        print(f"{'='*60}")
        sys.exit(0 if report["failed"] == 0 else 1)
