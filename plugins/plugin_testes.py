"""
plugin_testes.py
================
Ferramentas de teste e depuracao: execucao de testes Python,
analise de cobertura, profiling basico, assert helpers,
geracao de testes unitarios simples.
"""

import os
import sys
import json
import time
import traceback
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Testes e Depuracao"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data", "testes")
os.makedirs(DATA_DIR, exist_ok=True)


def register(api):
    def executar_testes(caminho: str, verbose: bool = False, capture_output: bool = True) -> str:
        """Executa testes com pytest em um arquivo ou diretorio."""
        try:
            import subprocess
            cmd = [sys.executable, "-m", "pytest", caminho, "--tb=short"]
            if verbose:
                cmd.append("-v")
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                saida = result.stdout + result.stderr
                lines = saida.split("\n")
                # filtra linhas relevantes
                relevant = [l for l in lines if any(p in l for p in ("PASSED", "FAILED", "ERROR", "passed", "failed", "error", "==", "test_"))]
                output = "\n".join(relevant[:50]) if relevant else saida[:2000]
                return f"Resultado ({caminho}):\n{output}\n\nCodigo: {result.returncode}"
            else:
                result = subprocess.run(cmd, timeout=120)
                return f"Testes concluidos em {caminho}. Codigo: {result.returncode}"
        except subprocess.TimeoutExpired:
            return f"Timeout ao executar testes em {caminho} (limite 120s)."
        except Exception as e:
            return f"Erro: {e}"

    def testar_funcao(codigo: str, funcao: str, args: str = "[]", kwargs: str = "{}") -> str:
        """Testa funcao especifica com argumentos. codigo: string com definicao da funcao."""
        try:
            namespace = {}
            exec(codigo, namespace)
            if funcao not in namespace:
                return f"Funcao '{funcao}' nao encontrada no codigo."
            fn = namespace[funcao]
            args_list = json.loads(args) if isinstance(args, str) else args
            kwargs_dict = json.loads(kwargs) if isinstance(kwargs, str) else kwargs
            inicio = time.time()
            result = fn(*args_list, **kwargs_dict)
            elapsed = time.time() - inicio
            return f"Resultado: {json.dumps(result, ensure_ascii=False, default=str)}\nTempo: {elapsed*1000:.2f}ms"
        except Exception as e:
            return f"Erro: {traceback.format_exc()}"

    def gerar_testes(codigo: str, nome_teste: str = "test_gerado") -> str:
        """Gera boilerplate de testes unitarios (assertEqual) para funcoes no codigo."""
        import ast
        try:
            tree = ast.parse(codigo)
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            if not functions:
                return "Nenhuma funcao encontrada no codigo."
            test_code = f"""import pytest


class Test{nome_teste.replace("test_", "").capitalize() if nome_teste.startswith("test_") else nome_teste}:
"""
            for fn in functions:
                args = [arg.arg for arg in fn.args.args if arg.arg != "self"]
                test_code += f"""
    def test_{fn.name}(self):
        # TODO: implementar teste para {fn.name}({', '.join(args)})
        # result = {fn.name}({', '.join(f'TODO_{a}' for a in args)})
        # assert result is not None
        pass
"""
            return test_code
        except SyntaxError as e:
            return f"Erro de sintaxe no codigo: {e}"
        except Exception as e:
            return f"Erro: {e}"

    def assert_helper(condicao: str, mensagem: str = "") -> str:
        """Avalia expressao condicional e retorna PASS/FAIL."""
        try:
            result = eval(condicao)
            if result:
                return f"PASS: {condicao}" + (f" - {mensagem}" if mensagem else "")
            return f"FAIL: {condicao}" + (f" - {mensagem}" if mensagem else "")
        except Exception as e:
            return f"ERROR ao avaliar '{condicao}': {e}"

    def profile_codigo(codigo: str, setup: str = "", iteracoes: int = 100) -> str:
        """Profile simples de codigo (tempo medio de execucao)."""
        try:
            namespace = {}
            if setup:
                exec(setup, namespace)
            exec(codigo, namespace)
            tempos = []
            for _ in range(iteracoes):
                inicio = time.perf_counter()
                exec(codigo, namespace)
                tempos.append(time.perf_counter() - inicio)
            media = sum(tempos) / len(tempos) * 1000
            minimo = min(tempos) * 1000
            maximo = max(tempos) * 1000
            return (
                f"Profile ({iteracoes} iteracoes):\n"
                f"  Media: {media:.4f}ms\n"
                f"  Min:   {minimo:.4f}ms\n"
                f"  Max:   {maximo:.4f}ms\n"
                f"  Total: {sum(tempos):.4f}s"
            )
        except Exception as e:
            return f"Erro: {traceback.format_exc()}"

    def verificar_sintaxe(arquivo: str) -> str:
        """Verifica sintaxe de um arquivo Python usando compileall."""
        import compileall
        try:
            result = compileall.compile_file(arquivo, ddir="", quiet=1)
            if result:
                return f"OK: Sintaxe valida - {arquivo}"
            return f"ERRO: Erro de sintaxe em {arquivo}"
        except Exception as e:
            return f"Erro ao verificar {arquivo}: {e}"

    def verificar_todos_plugins(pasta: str = "") -> str:
        """Verifica sintaxe de todos os plugins na pasta plugins/."""
        import compileall
        target = pasta or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        if not os.path.exists(target):
            return f"Pasta nao encontrada: {target}"
        results = []
        total = 0
        for fname in sorted(os.listdir(target)):
            if fname.endswith(".py"):
                fpath = os.path.join(target, fname)
                ok = compileall.compile_file(fpath, ddir="", quiet=1)
                results.append(f"  {'OK' if ok else 'FAIL'}: {fname}")
                total += 1
        status = "\n".join(results)
        return f"Verificacao de sintaxe ({total} plugins):\n{status}"

    api.register_tool("executar_testes", executar_testes,
        "Executa testes com pytest em arquivo ou diretorio.",
        {"caminho": {"type": "string", "description": "Arquivo ou diretorio de teste"}, "verbose": {"type": "boolean", "description": "Modo verbose (opcional)"}, "capture_output": {"type": "boolean", "description": "Capturar saida? (opcional)"}}, ["caminho"])

    api.register_tool("testar_funcao", testar_funcao,
        "Testa funcao com argumentos JSON. codigo: definicao da funcao.",
        {"codigo": {"type": "string", "description": "Codigo com definicao da funcao"}, "funcao": {"type": "string", "description": "Nome da funcao"}, "args": {"type": "string", "description": "JSON array de args posicionais (opcional)"}, "kwargs": {"type": "string", "description": "JSON object de kwargs (opcional)"}}, ["codigo", "funcao"])

    api.register_tool("gerar_testes", gerar_testes,
        "Gera boilerplate de testes unitarios para funcoes no codigo.",
        {"codigo": {"type": "string", "description": "Codigo Python"}, "nome_teste": {"type": "string", "description": "Nome da classe de teste (opcional)"}}, ["codigo"])

    api.register_tool("assert_helper", assert_helper,
        "Avalia condicao e retorna PASS/FAIL. Ex: '1+1==2'.",
        {"condicao": {"type": "string", "description": "Expressao condicional"}, "mensagem": {"type": "string", "description": "Mensagem opcional"}}, ["condicao"])

    api.register_tool("profile_codigo", profile_codigo,
        "Profile simples de codigo (tempo medio). setup: codigo de inicializacao.",
        {"codigo": {"type": "string", "description": "Codigo a profile"}, "setup": {"type": "string", "description": "Codigo de setup (opcional)"}, "iteracoes": {"type": "integer", "description": "Iteracoes (opcional)"}}, ["codigo"])

    api.register_tool("verificar_sintaxe", verificar_sintaxe,
        "Verifica sintaxe de arquivo Python com compileall.",
        {"arquivo": {"type": "string", "description": "Caminho do arquivo .py"}}, ["arquivo"])

    api.register_tool("verificar_todos_plugins", verificar_todos_plugins,
        "Verifica sintaxe de TODOS os plugins no diretorio plugins/.",
        {"pasta": {"type": "string", "description": "Pasta de plugins (opcional)"}}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Testes e depuracao: pytest, assert, profile, geracao de testes, verificacao de sintaxe",
        "tools": ["executar_testes", "testar_funcao", "gerar_testes", "assert_helper", "profile_codigo", "verificar_sintaxe", "verificar_todos_plugins"],
    }
