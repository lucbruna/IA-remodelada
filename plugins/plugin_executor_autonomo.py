"""
plugin_executor_autonomo.py
===========================
Executor profissional para tarefas grandes: planeja, executa etapas seguras,
valida resultados, registra erros/solucoes e cria projetos por templates.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

__version__ = "1.0.0"
PLUGIN_NAME = "Executor Autonomo Profissional"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "agente_data" / "executor_autonomo"
ERROR_MEMORY_FILE = DATA_DIR / "memoria_erros.json"
TASKS_FILE = DATA_DIR / "tarefas.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    _ensure_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _slugify(text: str, fallback: str = "projeto_ia") -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:60] or fallback


def _safe_base_dir(base_dir: str = "") -> Path:
    base = Path(base_dir).expanduser().resolve() if base_dir else ROOT_DIR.resolve()
    root = ROOT_DIR.resolve()
    if base != root and root not in base.parents:
        raise ValueError(f"Base fora do workspace permitido: {base}")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_project_dir(project_name: str, base_dir: str = "") -> Path:
    base = _safe_base_dir(base_dir)
    target = (base / _slugify(project_name)).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"Destino fora da base permitida: {target}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_if_missing(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _run_cmd(args: list[str], cwd: Path, timeout: int = 120) -> dict:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "output": output[-5000:],
            "seconds": round(time.perf_counter() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")) if hasattr(exc, "stdout") else ""
        return {
            "ok": False,
            "code": "timeout",
            "output": f"Timeout apos {timeout}s.\n{output[-3000:]}",
            "seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": "error",
            "output": str(exc),
            "seconds": round(time.perf_counter() - started, 3),
        }


def _detect_error_signature(text: str) -> str:
    text = text or ""
    patterns = [
        r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        r"ImportError: No module named ['\"]([^'\"]+)['\"]",
        r"SyntaxError: ([^\n]+)",
        r"NameError: ([^\n]+)",
        r"TypeError: ([^\n]+)",
        r"AssertionError: ([^\n]*)",
        r"FAILED ([^\n]+)",
        r"ERROR ([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)[:180]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (lines[-1] if lines else "erro_desconhecido")[:180]


def _suggest_fix(error_text: str) -> str:
    lower = (error_text or "").lower()
    if "modulenotfounderror" in lower or "no module named" in lower:
        return "Instalar dependencia ausente com pip_install ou adicionar ao requirements.txt."
    if "syntaxerror" in lower:
        return "Abrir o arquivo indicado, corrigir sintaxe e rodar py_compile/pytest novamente."
    if "nameerror" in lower:
        return "Verificar nomes de variaveis/funcoes, imports e escopo antes de executar de novo."
    if "typeerror" in lower:
        return "Conferir assinatura da funcao, tipos recebidos e argumentos obrigatorios."
    if "failed" in lower or "assertionerror" in lower:
        return "Ler o teste que falhou, ajustar comportamento ou expectativa e repetir pytest."
    return "Isolar a menor reproducao, revisar logs e repetir a validacao apos cada correcao."


def _template_cli_python(project_name: str) -> dict[str, str]:
    module = _slugify(project_name, "app")
    return {
        "README.md": f"# {project_name}\n\nAplicacao CLI Python criada pelo Executor Autonomo.\n\n## Rodar\n\n```bash\npython -m {module}.main --help\n```\n\n## Testar\n\n```bash\npython -m pytest -q\n```\n",
        "requirements.txt": "pytest>=8.0\n",
        f"{module}/__init__.py": "",
        f"{module}/main.py": '''import argparse


def saudacao(nome: str) -> str:
    nome = nome.strip() or "mundo"
    return f"Ola, {nome}!"


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI gerada pelo Executor Autonomo")
    parser.add_argument("nome", nargs="?", default="mundo")
    args = parser.parse_args()
    print(saudacao(args.nome))


if __name__ == "__main__":
    main()
''',
        "tests/test_main.py": f'''from {module}.main import saudacao


def test_saudacao_padrao():
    assert saudacao("") == "Ola, mundo!"


def test_saudacao_nome():
    assert saudacao("Ana") == "Ola, Ana!"
''',
    }


def _template_fastapi(project_name: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nAPI FastAPI gerada pelo Executor Autonomo.\n\n## Rodar\n\n```bash\nuvicorn app.main:app --reload\n```\n\n## Testar\n\n```bash\npython -m pytest -q\n```\n",
        "requirements.txt": "fastapi>=0.110\nuvicorn>=0.29\npytest>=8.0\nhttpx>=0.27\n",
        "app/__init__.py": "",
        "app/main.py": '''from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="API gerada pelo Executor Autonomo")


class Item(BaseModel):
    nome: str
    quantidade: int = 1


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/items")
def criar_item(item: Item) -> dict:
    return {"item": item.model_dump(), "ok": True}
''',
        "tests/test_api.py": '''from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_criar_item():
    response = client.post("/items", json={"nome": "caneta", "quantidade": 2})
    assert response.status_code == 200
    assert response.json()["item"]["nome"] == "caneta"
''',
    }


def _template_site(project_name: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nSite estatico gerado pelo Executor Autonomo. Abra `index.html` no navegador.\n",
        "index.html": '''<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Projeto IA</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="app">
    <section class="panel">
      <h1>Projeto pronto</h1>
      <p>Base criada para evoluir rapidamente com HTML, CSS e JavaScript.</p>
      <button id="action">Executar</button>
      <output id="result">Aguardando acao.</output>
    </section>
  </main>
  <script src="script.js"></script>
</body>
</html>
''',
        "styles.css": '''* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, sans-serif;
  color: #172026;
  background: #f5f7fb;
}
.app {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}
.panel {
  width: min(680px, 100%);
  padding: 28px;
  border: 1px solid #d7dde8;
  border-radius: 8px;
  background: white;
}
button {
  min-height: 40px;
  padding: 0 16px;
  border: 0;
  border-radius: 6px;
  background: #1267d8;
  color: white;
  font-weight: 700;
}
output {
  display: block;
  margin-top: 16px;
}
''',
        "script.js": '''const button = document.querySelector("#action");
const result = document.querySelector("#result");

button.addEventListener("click", () => {
  result.textContent = `Executado em ${new Date().toLocaleString("pt-BR")}`;
});
''',
    }


def _template_streamlit(project_name: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nApp Streamlit gerado pelo Executor Autonomo.\n\n```bash\nstreamlit run app.py\n```\n",
        "requirements.txt": "streamlit>=1.36\npandas>=2.0\n",
        "app.py": '''import pandas as pd
import streamlit as st


st.set_page_config(page_title="App IA", layout="wide")
st.title("App gerado pelo Executor Autonomo")

nome = st.text_input("Nome", "Brasil")
st.write(f"Ola, {nome}.")

dados = pd.DataFrame({"categoria": ["A", "B", "C"], "valor": [10, 20, 15]})
st.bar_chart(dados, x="categoria", y="valor")
''',
    }


TEMPLATES = {
    "cli_python": _template_cli_python,
    "fastapi": _template_fastapi,
    "site_html": _template_site,
    "streamlit": _template_streamlit,
}


def _choose_template(objetivo: str, stack: str = "") -> str:
    text = f"{objetivo} {stack}".lower()
    if any(word in text for word in ("fastapi", "api", "backend", "rest")):
        return "fastapi"
    if any(word in text for word in ("streamlit", "dashboard", "dados", "painel")):
        return "streamlit"
    if any(word in text for word in ("site", "html", "css", "javascript", "landing")):
        return "site_html"
    return "cli_python"


def _validation_commands(template: str) -> list[list[str]]:
    if template in ("cli_python", "fastapi"):
        return [[sys.executable, "-m", "py_compile"]]
    if template == "streamlit":
        return [[sys.executable, "-m", "py_compile", "app.py"]]
    return []


def _py_compile_all(project_dir: Path) -> dict:
    py_files = [str(path.relative_to(project_dir)) for path in project_dir.rglob("*.py")]
    if not py_files:
        return {"ok": True, "code": 0, "output": "Nenhum arquivo Python para compilar.", "seconds": 0}
    return _run_cmd([sys.executable, "-m", "py_compile", *py_files], project_dir, timeout=60)


def _run_pytest_if_present(project_dir: Path) -> dict:
    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        return {"ok": True, "code": 0, "output": "Projeto sem pasta tests; pytest ignorado.", "seconds": 0}
    return _run_cmd([sys.executable, "-m", "pytest", "-q"], project_dir, timeout=120)


def register(api):
    def registrar_solucao_erro(erro: str, solucao: str, contexto: str = "", projeto: str = "") -> str:
        """Registra um erro e sua solucao para consultas futuras."""
        erro = (erro or "").strip()
        solucao = (solucao or "").strip()
        if not erro or not solucao:
            return "Informe erro e solucao."
        data = _load_json(ERROR_MEMORY_FILE, [])
        signature = _detect_error_signature(erro)
        for item in data:
            if item.get("signature") == signature:
                item["vezes"] = int(item.get("vezes", 1)) + 1
                item["solucao"] = solucao
                item["contexto"] = contexto[:1000]
                item["projeto"] = projeto[:120]
                item["atualizado_em"] = datetime.now().isoformat()
                _save_json(ERROR_MEMORY_FILE, data)
                return f"Solucao atualizada para: {signature}"
        data.append({
            "signature": signature,
            "erro": erro[:2000],
            "solucao": solucao[:2000],
            "contexto": contexto[:1000],
            "projeto": projeto[:120],
            "vezes": 1,
            "criado_em": datetime.now().isoformat(),
            "atualizado_em": datetime.now().isoformat(),
        })
        _save_json(ERROR_MEMORY_FILE, data[-300:])
        return f"Solucao registrada para: {signature}"

    def consultar_solucoes_erro(erro: str = "", limite: int = 5) -> str:
        """Consulta solucoes aprendidas para erros parecidos."""
        data = _load_json(ERROR_MEMORY_FILE, [])
        if not data:
            return "Nenhuma solucao de erro registrada ainda."
        erro_lower = (erro or "").lower()
        signature = _detect_error_signature(erro) if erro else ""
        scored = []
        for item in data:
            haystack = f"{item.get('signature', '')} {item.get('erro', '')} {item.get('contexto', '')}".lower()
            score = 0
            if signature and signature.lower() in haystack:
                score += 5
            for token in set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", erro_lower)):
                if token.lower() in haystack:
                    score += 1
            if score or not erro:
                scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], pair[1].get("vezes", 0)), reverse=True)
        if not scored:
            return "Nenhuma solucao parecida encontrada."
        lines = ["--- Solucoes de Erro Aprendidas ---"]
        for score, item in scored[: max(1, min(int(limite or 5), 20))]:
            lines.append(f"\nAssinatura: {item.get('signature')}")
            lines.append(f"Vezes: {item.get('vezes', 1)} | Score: {score}")
            if item.get("projeto"):
                lines.append(f"Projeto: {item.get('projeto')}")
            lines.append(f"Solucao: {item.get('solucao')}")
        return "\n".join(lines)

    def listar_templates_projeto() -> str:
        """Lista templates disponiveis para criacao rapida de projetos."""
        return (
            "--- Templates disponiveis ---\n"
            "cli_python: CLI Python com testes pytest.\n"
            "fastapi: API FastAPI com /health, POST /items e testes.\n"
            "site_html: Site HTML/CSS/JS estatico pronto para abrir.\n"
            "streamlit: Dashboard Streamlit simples com grafico."
        )

    def criar_projeto_template(nome: str, template: str = "auto", base_dir: str = "", validar: bool = True) -> str:
        """Cria um projeto por template e valida sintaxe/testes quando aplicavel."""
        nome = nome or "projeto_ia"
        selected = _choose_template(nome, template) if template in ("", "auto") else template
        if selected not in TEMPLATES:
            return f"Template desconhecido: {template}. Use listar_templates_projeto()."
        try:
            project_dir = _safe_project_dir(nome, base_dir)
            files = TEMPLATES[selected](nome)
            created = []
            skipped = []
            for rel_path, content in files.items():
                target = project_dir / rel_path
                if _write_if_missing(target, content):
                    created.append(rel_path)
                else:
                    skipped.append(rel_path)

            validations = []
            if validar:
                compile_result = _py_compile_all(project_dir)
                validations.append(("py_compile", compile_result))
                pytest_result = _run_pytest_if_present(project_dir)
                validations.append(("pytest", pytest_result))
                for name, result in validations:
                    if not result["ok"]:
                        registrar_solucao_erro(
                            result["output"],
                            _suggest_fix(result["output"]),
                            contexto=f"Validacao {name} no template {selected}",
                            projeto=str(project_dir),
                        )

            lines = [
                "--- Projeto criado por template ---",
                f"Nome: {nome}",
                f"Template: {selected}",
                f"Pasta: {project_dir}",
                f"Arquivos criados: {len(created)}",
            ]
            if created:
                lines.extend(f"  - {item}" for item in created)
            if skipped:
                lines.append(f"Arquivos preservados por ja existirem: {len(skipped)}")
            if validations:
                lines.append("Validacoes:")
                for name, result in validations:
                    status = "OK" if result["ok"] else "FALHOU"
                    lines.append(f"  - {name}: {status} ({result['seconds']}s, codigo {result['code']})")
                    if not result["ok"]:
                        lines.append(result["output"][-1200:])
            return "\n".join(lines)
        except Exception as exc:
            return f"Erro ao criar projeto: {exc}"

    def desenvolver_projeto(objetivo: str, stack: str = "auto", nome: str = "", base_dir: str = "", validar: bool = True) -> str:
        """Cria a primeira versao funcional de um projeto completo usando template adequado."""
        objetivo = (objetivo or "").strip()
        if not objetivo:
            return "Informe o objetivo do projeto."
        project_name = nome or _slugify(objetivo, "projeto_ia")
        template = _choose_template(objetivo, stack)
        resultado = criar_projeto_template(project_name, template, base_dir, validar)
        task = {
            "objetivo": objetivo[:500],
            "stack": stack,
            "nome": project_name,
            "template": template,
            "status": "criado",
            "data": datetime.now().isoformat(),
        }
        tasks = _load_json(TASKS_FILE, [])
        tasks.append(task)
        _save_json(TASKS_FILE, tasks[-200:])
        return (
            resultado
            + "\n\nProximas etapas recomendadas:\n"
            + "1. Descrever regras de negocio e telas/endpoints esperados.\n"
            + "2. Pedir ao agente para editar arquivos especificos.\n"
            + "3. Rodar testes e corrigir falhas com executor_autonomo."
        )

    def executor_autonomo(tarefa: str, pasta: str = "", max_iteracoes: int = 3, validar: bool = True) -> str:
        """Planeja, executa validacoes e aprende com erros. Nao apaga arquivos."""
        tarefa = (tarefa or "").strip()
        if not tarefa:
            return "Informe uma tarefa."
        max_iteracoes = max(1, min(int(max_iteracoes or 3), 8))
        try:
            workdir = _safe_base_dir(pasta) if pasta else ROOT_DIR
        except Exception as exc:
            return f"Pasta invalida: {exc}"

        try:
            from agente_core import autonomia_planejar
            plano = autonomia_planejar(tarefa)
        except Exception:
            plano = "Plano indisponivel; seguindo heuristicas locais."

        steps = []
        lower = tarefa.lower()
        if any(word in lower for word in ("crie projeto", "criar projeto", "desenvolva", "programa completo", "app completo")):
            steps.append(("desenvolver_projeto", desenvolver_projeto(tarefa, nome=_slugify(tarefa), base_dir=str(workdir), validar=validar)))
        elif any(word in lower for word in ("crie pasta", "criar pasta", "nova pasta")):
            folder = _slugify(tarefa.replace("crie", "").replace("criar", "").replace("pasta", ""), "nova_pasta")
            target = _safe_project_dir(folder, str(workdir))
            steps.append(("criar_pasta", f"Pasta criada/verificada: {target}"))
        else:
            steps.append(("planejamento", "Tarefa classificada. Execute ferramentas especializadas conforme o plano abaixo."))

        validations = []
        if validar and workdir.exists():
            py_files = list(workdir.rglob("*.py"))
            if py_files and len(py_files) <= 80:
                result = _py_compile_all(workdir)
                validations.append(("py_compile", result))
                if not result["ok"]:
                    registrar_solucao_erro(result["output"], _suggest_fix(result["output"]), contexto=tarefa, projeto=str(workdir))
            if (workdir / "tests").exists():
                result = _run_pytest_if_present(workdir)
                validations.append(("pytest", result))
                if not result["ok"]:
                    registrar_solucao_erro(result["output"], _suggest_fix(result["output"]), contexto=tarefa, projeto=str(workdir))

        report = {
            "tarefa": tarefa,
            "pasta": str(workdir),
            "iteracoes_maximas": max_iteracoes,
            "validar": validar,
            "plano": plano,
            "etapas": [{"nome": name, "resultado": result[:4000]} for name, result in steps],
            "validacoes": validations,
            "data": datetime.now().isoformat(),
        }
        tasks = _load_json(TASKS_FILE, [])
        tasks.append(report)
        _save_json(TASKS_FILE, tasks[-200:])

        lines = ["--- Executor Autonomo ---", plano, "", "Etapas executadas:"]
        for name, result in steps:
            lines.append(f"\n[{name}]\n{result}")
        if validations:
            lines.append("\nValidacoes:")
            for name, result in validations:
                status = "OK" if result["ok"] else "FALHOU"
                lines.append(f"  - {name}: {status} ({result['seconds']}s, codigo {result['code']})")
                if not result["ok"]:
                    lines.append(result["output"][-1200:])
        lines.append("\nRegistro salvo em agente_data/executor_autonomo/tarefas.json")
        return "\n".join(lines)

    def auto_melhorar_agente(escopo: str = "seguro", aplicar: bool = False) -> str:
        """Analisa o agente e sugere/aplica somente melhorias seguras e pequenas."""
        checks = []
        checks.append(("py_compile_core", _run_cmd([sys.executable, "-m", "py_compile", "agente_core.py"], ROOT_DIR, 90)))
        checks.append(("pytest_core", _run_cmd([sys.executable, "-m", "pytest", "test_agente_core.py", "-q"], ROOT_DIR, 180)))

        suggestions = [
            "Manter executor_autonomo como orquestrador principal para tarefas longas.",
            "Adicionar testes antes de ampliar templates ou subagentes.",
            "Registrar falhas repetidas com registrar_solucao_erro.",
            "Usar aplicar=False por padrao; aplicar mudancas automaticas so apos testes passarem.",
        ]
        if aplicar:
            suggestions.append("Aplicacao automatica ampla nao foi executada: esta ferramenta evita modificar codigo nucleo sem uma tarefa especifica.")

        lines = ["--- Auto-melhoria Controlada ---", f"Escopo: {escopo}", "Checks:"]
        for name, result in checks:
            lines.append(f"  - {name}: {'OK' if result['ok'] else 'FALHOU'} ({result['seconds']}s)")
            if not result["ok"]:
                registrar_solucao_erro(result["output"], _suggest_fix(result["output"]), contexto=f"auto_melhorar_agente/{name}", projeto=str(ROOT_DIR))
                lines.append(result["output"][-1200:])
        lines.append("Sugestoes:")
        lines.extend(f"  - {item}" for item in suggestions)
        return "\n".join(lines)

    api.register_tool(
        "executor_autonomo",
        executor_autonomo,
        "Executa uma tarefa com ciclo profissional: planejar, agir de forma segura, validar, registrar erros e sugerir correcao.",
        {
            "tarefa": {"type": "string", "description": "Pedido completo do usuario"},
            "pasta": {"type": "string", "description": "Pasta de trabalho dentro do workspace"},
            "max_iteracoes": {"type": "integer", "description": "Limite de ciclos de execucao/correcao"},
            "validar": {"type": "boolean", "description": "Rodar validacoes quando possivel"},
        },
        ["tarefa"],
    )
    api.register_tool(
        "desenvolver_projeto",
        desenvolver_projeto,
        "Cria um projeto completo inicial por template, com arquivos, README e validacoes.",
        {
            "objetivo": {"type": "string", "description": "Objetivo do programa/app/site"},
            "stack": {"type": "string", "description": "Stack desejada ou auto"},
            "nome": {"type": "string", "description": "Nome da pasta/projeto"},
            "base_dir": {"type": "string", "description": "Base dentro do workspace"},
            "validar": {"type": "boolean", "description": "Validar sintaxe/testes"},
        },
        ["objetivo"],
    )
    api.register_tool(
        "criar_projeto_template",
        criar_projeto_template,
        "Cria projeto a partir de template: cli_python, fastapi, site_html ou streamlit.",
        {
            "nome": {"type": "string", "description": "Nome do projeto"},
            "template": {"type": "string", "description": "Template ou auto"},
            "base_dir": {"type": "string", "description": "Base dentro do workspace"},
            "validar": {"type": "boolean", "description": "Validar apos criar"},
        },
        ["nome"],
    )
    api.register_tool("listar_templates_projeto", listar_templates_projeto, "Lista templates de projetos disponiveis.", {}, [])
    api.register_tool(
        "registrar_solucao_erro",
        registrar_solucao_erro,
        "Registra erro e solucao para aprendizado futuro.",
        {
            "erro": {"type": "string", "description": "Texto do erro/log"},
            "solucao": {"type": "string", "description": "Solucao aplicada ou recomendada"},
            "contexto": {"type": "string", "description": "Contexto da falha"},
            "projeto": {"type": "string", "description": "Projeto relacionado"},
        },
        ["erro", "solucao"],
    )
    api.register_tool(
        "consultar_solucoes_erro",
        consultar_solucoes_erro,
        "Busca solucoes aprendidas para um erro ou log semelhante.",
        {
            "erro": {"type": "string", "description": "Erro/log para buscar"},
            "limite": {"type": "integer", "description": "Quantidade maxima"},
        },
        [],
    )
    api.register_tool(
        "auto_melhorar_agente",
        auto_melhorar_agente,
        "Roda checks e sugere melhorias seguras do proprio agente. Nao altera codigo amplo automaticamente.",
        {
            "escopo": {"type": "string", "description": "Escopo da analise"},
            "aplicar": {"type": "boolean", "description": "Aplicar mudancas seguras quando existirem"},
        },
        [],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Executor autonomo com validacao, memoria de erros, templates e auto-melhoria controlada.",
        "tools": [
            "executor_autonomo",
            "desenvolver_projeto",
            "criar_projeto_template",
            "listar_templates_projeto",
            "registrar_solucao_erro",
            "consultar_solucoes_erro",
            "auto_melhorar_agente",
        ],
    }
