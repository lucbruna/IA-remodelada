from ._common import *
import subprocess
import time

# =======================================================================
# LAUNCH - servicos de longa duracao (padrao 'launch' do oh-my-pi)
# -----------------------------------------------------------------------
# Gerencia processos/shared services com readiness probe, logs limitados,
# reinicio e teardown automatico. Substitui executar servicos "soltos"
# (ex: agente_api_server.py, Docker) por um gerenciador central.
# =======================================================================

LAUNCH_FILE = os.path.join(DATA_DIR, "agente_data", "memoria_evolutiva", "launches.json")
_launch_procs = {}  # id -> Popen (em memoria, perde em restart)


def _load_launches() -> dict:
    return _load_json(LAUNCH_FILE, {})


def _save_launches(d: dict) -> None:
    os.makedirs(os.path.dirname(LAUNCH_FILE), exist_ok=True)
    _save_json(LAUNCH_FILE, d)


def launch_start(name: str, command: str, readiness_probe: str = "",
                 restart: bool = False, cwd: str = "") -> str:
    """Inicia um servico de longa duracao gerenciado.

    name: identificador unico. command: comando a executar (shell).
    readiness_probe: comando que deve retornar 0 para o servico estar pronto
    (opcional). restart: reinicia automaticamente se o processo morrer.
    """
    name = (name or "").strip()
    if not name or not command.strip():
        return "Informe name e command."
    try:
        proc = subprocess.Popen(
            command, shell=True, cwd=cwd or None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception as e:
        return f"Falha ao iniciar '{name}': {e}"

    _launch_procs[name] = {"proc": proc, "command": command,
                           "restart": restart, "probe": readiness_probe, "cwd": cwd}
    launches = _load_launches()
    launches[name] = {"command": command, "pid": proc.pid,
                      "started": datetime.now().isoformat(),
                      "restart": restart, "probe": readiness_probe}
    _save_launches(launches)

    # Readiness probe
    status = f"iniciado (pid={proc.pid})"
    if readiness_probe.strip():
        ok = False
        for _ in range(15):
            time.sleep(1)
            code = subprocess.run(readiness_probe, shell=True,
                                  capture_output=True).returncode
            if code == 0:
                ok = True
                break
        status = "PRONTO" if ok else "iniciado, porem probe de prontidao falhou"
    return f"Servico '{name}' {status}."


def launch_logs(name: str, lines: int = 50) -> str:
    """Retorna os ultimos logs (stdout/stderr) de um servico."""
    info = _launch_procs.get(name)
    if not info:
        return f"Servico '{name}' nao esta ativo nesta sessao."
    proc = info["proc"]
    try:
        out = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
    except Exception:
        out = ""
    if not out:
        return f"Sem logs de '{name}' ainda (ou stdout consumido)."
    linhas = out.splitlines()[-lines:]
    return f"Logs de '{name}':\n" + "\n".join(linhas)


def launch_stop(name: str) -> str:
    """Encerra (teardown) um servico gerenciado."""
    info = _launch_procs.pop(name, None)
    launches = _load_launches()
    launches.pop(name, None)
    _save_launches(launches)
    if not info:
        return f"Servico '{name}' nao estava ativo nesta sessao (removido do registro)."
    proc = info["proc"]
    try:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return f"Servico '{name}' encerrado."
    except Exception as e:
        return f"Erro ao encerrar '{name}': {e}"


def launch_list() -> str:
    """Lista servicos gerenciados."""
    launches = _load_launches()
    if not launches:
        return "Nenhum servico gerenciado."
    linhas = []
    for n, d in launches.items():
        alive = n in _launch_procs and _launch_procs[n]["proc"].poll() is None
        linhas.append(f"{n}: pid={d.get('pid')} ativo={alive} cmd={d.get('command')}")
    return "Servicos (launch):\n" + "\n".join(linhas)


def launch_supervise() -> None:
    """Reinicia servicos marcados com restart que morreram (chamar periodicamente)."""
    for name, info in list(_launch_procs.items()):
        proc = info["proc"]
        if proc.poll() is not None and info.get("restart"):
            try:
                new = subprocess.Popen(
                    info["command"], shell=True, cwd=info.get("cwd") or None,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                info["proc"] = new
                launches = _load_launches()
                if name in launches:
                    launches[name]["pid"] = new.pid
                    _save_launches(launches)
                logging.info("launch: reiniciado servico '%s'", name)
            except Exception as e:
                logging.warning("launch: falha ao reiniciar '%s': %s", name, e)
