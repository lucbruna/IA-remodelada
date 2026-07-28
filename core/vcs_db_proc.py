from ._common import *
def file_diff(file1: str, file2: str) -> str:
    """Compara dois arquivos de texto e mostra as diferencas (unified diff)."""
    try:
        import difflib
        with open(file1, "r", encoding="utf-8", errors="replace") as f:
            lines1 = f.readlines()
        with open(file2, "r", encoding="utf-8", errors="replace") as f:
            lines2 = f.readlines()
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=file1, tofile=file2,
            lineterm=""
        )
        result = "\n".join(diff)
        if not result:
            return "Os arquivos sao identicos."
        if len(result) > 5000:
            result = result[:5000] + "\n... (diff truncado, muito longo)"
        return result
    except FileNotFoundError as e:
        return f"Arquivo nao encontrado: {e}"
    except Exception as e:
        return f"Erro ao comparar arquivos: {e}"


# --- Git integration ---
def git_run(args: str, repo_path: str = "") -> str:
    """Executa um comando git em um repositorio. Use: clone, add, commit, push, pull, status, log, diff, branch, checkout, etc."""
    try:
        cmd = f"git {args}"
        cwd = repo_path if repo_path else None
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if not output:
                output = stderr
            else:
                output += f"\n[stderr]: {stderr}"
        return output or "(comando git executado, sem saida)"
    except subprocess.TimeoutExpired:
        return "Comando git excedeu o tempo limite (60s)."
    except FileNotFoundError:
        return "Git nao encontrado. Instale: https://git-scm.com"
    except Exception as e:
        return f"Erro ao executar git: {e}"


# --- SQLite database ---
def sqlite_query(db_path: str, query: str) -> str:
    """Executa uma consulta SQL em um banco SQLite e retorna os resultados como tabela."""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().upper().startswith(("SELECT", "PRAGMA", "EXPLAIN")):
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                return "Nenhum resultado."
            col_names = [d[0] for d in cursor.description]
            header = " | ".join(col_names)
            sep = "-" * len(header)
            lines = [header, sep]
            for row in rows[:50]:
                lines.append(" | ".join(str(row[c] or "") for c in col_names))
            if len(rows) > 50:
                lines.append(f"... e mais {len(rows) - 50} linhas.")
            conn.close()
            return "\n".join(lines)
        else:
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return f"Comando executado. Linhas afetadas: {affected}"
    except ImportError:
        return "Erro: sqlite3 nao disponivel (embutido no Python, deveria funcionar)."
    except Exception as e:
        return f"Erro SQLite: {e}"


# --- Process manager ---
def process_list(filter_str: str = "") -> str:
    """Lista processos em execucao. Opcional: filtrar por nome."""
    try:
        if sys.platform == "win32":
            cmd = "tasklist /FO CSV /NH"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split("\n")
            table = []
            for line in lines:
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    pid = parts[1]
                    name = parts[0]
                    mem = parts[4]
                    if filter_str and filter_str.lower() not in name.lower():
                        continue
                    table.append(f"{name:30s} PID: {pid:>6s}  Memoria: {mem}")
            if not table:
                filtro_msg = f' com filtro "{filter_str}"' if filter_str else ""
                return f"Nenhum processo encontrado{filtro_msg}."
            return "PROCESSOS:\n" + "\n".join(table[:60])
        else:
            cmd = "ps aux" if not filter_str else f"ps aux | grep -i '{filter_str}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()[:5000] or "Nenhum processo encontrado."
    except Exception as e:
        return f"Erro ao listar processos: {e}"


def process_kill(pid: int) -> str:
    """Mata um processo pelo numero do PID.

    Seguranca: recusa matar processos criticos do sistema (PID 0, 1, 4).
    No Windows, recusa processos do sistema. Em Unix, recusa init/systemd.
    """
    import os
    pid = int(pid) if pid else 0

    # Protecao: nao matar processos criticos
    critical_pids = {0, 1, 4}  # Windows system pids
    if sys.platform != "win32":
        critical_pids = {0, 1}  # init, systemd

    if pid in critical_pids:
        return f"RECUSADO: Nao e possivel matar processo critico PID {pid} (sistema)."

    # Verifica se e o proprio processo
    if pid == os.getpid():
        return f"RECUSADO: Nao e possivel matar o proprio processo (PID {pid})."

    try:
        if sys.platform == "win32":
            # Usa lista de argumentos (nao shell=True)
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, text=True, timeout=10
            )
        else:
            # Verifica se o processo existe antes de matar
            result = subprocess.run(
                ["kill", "-0", str(pid)],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return f"Processo PID {pid} nao encontrado ou ja encerrado."
            result = subprocess.run(
                ["kill", "-9", str(pid)],
                capture_output=True, text=True, timeout=10
            )
        return f"Processo PID {pid} encerrado."
    except subprocess.TimeoutExpired:
        return f"Timeout ao encerrar processo PID {pid}."
    except Exception as e:
        return f"Erro ao matar processo: {e}"


# --- Image generation (Stable Diffusion WebUI API) ---
