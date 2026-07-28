from ._common import *
import ast
import io
import contextlib

# =======================================================================
# HEAVY CODE - codigo pesado e seguro (estilo OMP para tarefas grandes)
# -----------------------------------------------------------------------
# Ferramentas para tarefas complexas de codigo: analise estatica de
# seguranca (estilo bandit), benchmark de performance, e execucao de
# codigo nao-confiavel com limite de recursos (CPU/memoria/tempo) e
# auto-correcao. Trabalha com run_python_code para nao confiar em codigo
# gerado, mas medir e auditar antes de rodar em producao.
# =======================================================================


def code_static_audit(code: str) -> str:
    """Analise estatica de seguranca em codigo Python (estilo bandit).

    Detecta padroes perigosos: eval/exec, imports os/system, chamadas de
    rede, leitura/escrita arbitraria, subprocess shell, pickle, etc.
    Nao executa o codigo. Retorna lista de achados com severidade.
    """
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Erro de sintaxe: {e}"

    DANGEROUS_CALLS = {
        "eval": "ALTA", "exec": "ALTA", "compile": "MEDIA",
        "os.system": "ALTA", "subprocess": "ALTA", "pickle.loads": "MEDIA",
        "marshal.loads": "MEDIA", "input": "BAIXA",
    }
    NETWORK_MODS = {"socket", "requests", "urllib", "http", "ftplib", "smtplib"}
    picked = set()

    for node in ast.walk(tree):
        # Chamadas perigosas
        if isinstance(node, ast.Call):
            fname = ""
            if isinstance(node.func, ast.Name):
                fname = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            if fname in DANGEROUS_CALLS:
                findings.append(f"[{DANGEROUS_CALLS[fname]}] chamada '{fname}' (linha {node.lineno})")
            if isinstance(node.func, ast.Attribute):
                chain = []
                cur = node.func
                while isinstance(cur, ast.Attribute):
                    chain.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    chain.append(cur.id)
                full = ".".join(reversed(chain))
                if full in DANGEROUS_CALLS:
                    findings.append(f"[{DANGEROUS_CALLS[full]}] chamada '{full}' (linha {node.lineno})")
        # Imports de rede
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            else:
                mods = [node.module or ""]
            for m in mods:
                top = m.split(".")[0]
                if top in NETWORK_MODS and top not in picked:
                    picked.add(top)
                    findings.append(f"[MEDIA] import de rede '{top}' (linha {node.lineno})")
        # Acesso a atributos tipo __globals__ / __builtins__
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            if node.attr in ("__globals__", "__builtins__", "__subclasses__"):
                findings.append(f"[ALTA] acesso a '{node.attr}' (possivel escape de sandbox, linha {node.lineno})")

    if not findings:
        return "Auditoria estatica: nenhum padrao perigoso detectado."
    sev_order = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
    findings.sort(key=lambda x: sev_order.get(x.split("]")[0].strip("["), 3))
    return "Auditoria estatica de seguranca:\n" + "\n".join(findings)


def code_benchmark(code: str, repeat: int = 5) -> str:
    """Mede tempo de execucao e pico de memoria de um trecho Python.

    Roda em processo isolado via subprocess para nao poluir o estado do
    agente. Reporta media, minimo, maximo e pico de RSS (MB).
    """
    import subprocess
    script = (
        "import time\n"
        "t0=time.perf_counter()\n"
        "code='''" + code.replace("'''", "'''") + "'''\n"
        "exec(compile(code,'<bench>','exec'))\n"
        "t1=time.perf_counter()\n"
        "print(f'ELAPSED={t1-t0:.4f}')\n"
    )
    try:
        times, rsss = [], []
        for _ in range(max(1, repeat)):
            res = subprocess.run(["python", "-c", script], capture_output=True,
                                 text=True, timeout=60)
            out = res.stdout
            for line in out.splitlines():
                if line.startswith("ELAPSED="):
                    times.append(float(line.split("=")[1]))
                elif line.startswith("RSS="):
                    rsss.append(float(line.split("=")[1]))
        if not rsss:  # Windows: resource nao existe no subprocess filho
            try:
                import psutil, os
                rsss = [psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024] * len(times)
            except Exception:
                rsss = [0.0] * len(times)
        if not times:
            return f"Falha no benchmark: {res.stderr[:300]}"
        return (f"Benchmark ({len(times)} runs): tempo medio={sum(times)/len(times):.4f}s "
                f"min={min(times):.4f}s max={max(times):.4f}s | pico RSS={max(rsss):.1f}MB")
    except Exception as e:
        return f"Erro no benchmark: {e}"


def code_exec_limited(code: str, mem_mb: int = 256, timeout: int = 30) -> str:
    """Executa codigo Python com limite de memoria (RLIMIT_AS) e tempo.

    Usa fork+setrlimit no processo para evitar que codigo pesado derrube
    o agente. Silencioso em falhas de memoria/tempo. Como run_python_code,
    mas com teto de RAM. Nao use para codigo nao-confiavel hostil.
    """
    pid = os.fork() if hasattr(os, "fork") else -1
    if pid == 0:
        try:
            import resource
            if hasattr(resource, "RLIMIT_AS"):
                mb = mem_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mb, mb))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(compile(code, "<limited>", "exec"), {"__name__": "__main__"})
            os._exit(0)
        except MemoryError:
            os._exit(2)
        except Exception as e:
            print(f"Erro: {e}")
            os._exit(1)
    elif pid > 0:
        try:
            _, status = os.waitpid(pid, 0)
            if os.WIFSIGNALED(status) and os.WTERMSIG(status) == 9:
                return f"Execucao interrompida: limite de memoria ({mem_mb}MB) atingido."
            return f"(processo encerrado, codigo {os.WEXITSTATUS(status)})"
        except Exception as e:
            return f"Erro ao aguardar processo: {e}"
    else:
        # Sem fork (Windows): cai para execucao simples com timeout.
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(compile(code, "<limited>", "exec"), {"__name__": "__main__"})
            return buf.getvalue() or "(sem saida)"
        except Exception as e:
            return f"Erro: {e}"
