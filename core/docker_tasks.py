from ._common import *
# =======================================================================
# FERRAMENTAS FINAIS: Docker, agendador, senhas, formatador, QR code, markdown, rede
# =======================================================================

# --- Docker integration ---
def docker_run(args: str) -> str:
    """Executa comandos Docker (ps, images, pull, run, stop, rm, logs, etc.). Requer Docker instalado."""
    try:
        cmd = f"docker {args}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout.strip()
        if result.stderr.strip():
            stderr = result.stderr.strip()
            output = (stderr if not output else output + f"\n[stderr]: {stderr}")
        return output or "(comando docker executado, sem saida)"
    except FileNotFoundError:
        return "Docker nao encontrado. Instale: https://docker.com"
    except subprocess.TimeoutExpired:
        return "Comando docker excedeu o tempo limite (60s)."
    except Exception as e:
        return f"Erro Docker: {e}"


def docker_ps(all_containers: bool = False) -> str:
    """Lista containers Docker em execucao."""
    flag = "-a" if all_containers else ""
    return docker_run(f"ps {flag}")


def docker_images() -> str:
    """Lista imagens Docker baixadas."""
    return docker_run("images")


# --- Task scheduler (agendador simples) ---
TASKS_FILE = os.path.join(DATA_DIR, "tarefas_agendadas.json")
if not os.path.exists(TASKS_FILE):
    _save_json(TASKS_FILE, [])


def task_schedule(name: str, command: str, delay_seconds: int = 0, interval_seconds: int = 0) -> str:
    """Agenda uma tarefa para execucao futura (delay) ou periodica (interval). Use task_list para ver."""
    try:
        tasks = _load_json(TASKS_FILE, [])
        task_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:8]
        run_at = (datetime.now().timestamp() + delay_seconds) if delay_seconds > 0 else 0
        tasks.append({
            "id": task_id,
            "name": name,
            "command": command,
            "run_at": run_at,
            "interval": interval_seconds,
            "created": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })
        _save_json(TASKS_FILE, tasks)
        msg = f"Tarefa '{name}' agendada (ID: {task_id})."
        if delay_seconds > 0:
            msg += f" Executa em {delay_seconds}s."
        if interval_seconds > 0:
            msg += f" Repete a cada {interval_seconds}s."
        return msg
    except Exception as e:
        return f"Erro ao agendar tarefa: {e}"


def task_list() -> str:
    """Lista todas as tarefas agendadas pendentes."""
    try:
        tasks = _load_json(TASKS_FILE, [])
        now = time.time()
        pending = [t for t in tasks if t["run_at"] == 0 or t["run_at"] > now]
        if not pending:
            return "Nenhuma tarefa agendada."
        lines = []
        for t in pending:
            info = f"  [{t['id']}] {t['name']}: {t['command']}"
            if t["run_at"] > 0:
                remaining = int(t["run_at"] - now)
                info += f" (em {remaining}s)"
            if t["interval"] > 0:
                info += f" [a cada {t['interval']}s]"
            lines.append(info)
        return "Tarefas agendadas:\n" + "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar tarefas: {e}"


def task_remove(task_id: str) -> str:
    """Remove uma tarefa agendada pelo ID."""
    try:
        tasks = _load_json(TASKS_FILE, [])
        antes = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]
        if len(tasks) == antes:
            return f"Tarefa ID '{task_id}' nao encontrada."
        _save_json(TASKS_FILE, tasks)
        return f"Tarefa '{task_id}' removida."
    except Exception as e:
        return f"Erro ao remover tarefa: {e}"


def _run_pending_tasks() -> None:
    """Verifica e executa tarefas agendadas pendentes (chamado internamente)."""
    try:
        tasks = _load_json(TASKS_FILE, [])
        now = time.time()
        remaining = []
        for t in tasks:
            if t["run_at"] > 0 and t["run_at"] <= now:
                try:
                    subprocess.run(t["command"], shell=True, capture_output=True, text=True, timeout=30)
                    logging.info("Tarefa executada: %s", t["name"])
                except Exception as e:
                    logging.warning("Falha na tarefa %s: %s", t["name"], e)
                if t["interval"] > 0:
                    t["run_at"] = now + t["interval"]
                    remaining.append(t)
            else:
                remaining.append(t)
        _save_json(TASKS_FILE, remaining)
    except Exception:
        pass


# --- Password manager (criptografado) ---
PASSWORDS_FILE = os.path.join(DATA_DIR, "senhas.enc")


