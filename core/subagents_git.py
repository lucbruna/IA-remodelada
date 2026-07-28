from ._common import *

# =======================================================================
# SUBAGENTES ISOLADOS (padrao maker/checker do oh-my-pi)
# -----------------------------------------------------------------------
# Cada subagente trabalha em um git worktree isolado (branch proprio),
# entao um nao estraga o trabalho do outro. O orquestrador pode depois
# validar (checker) e fazer merge. Requer git instalado.
# =======================================================================

WORKTREE_ROOT = os.path.join(DATA_DIR, "agente_data", "executor_autonomo", "worktrees")


def subagent_run_isolated(role: str, task: str, repo_path: str = ".",
                          validate: bool = True) -> str:
    """Executa uma tarefa em subagente isolado por git worktree.

    Cria um worktree em branch ``agent/<role>-<ts>``, pede ao modelo que
    resolva a tarefa (descricao + comandos sugeridos), e opcionalmente
    roda um checker independente que valida o resultado. Retorna o
    relatorio e o caminho do worktree.
    """
    role = (role or "task").strip().replace(" ", "_").lower()
    try:
        os.makedirs(WORKTREE_ROOT, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        branch = f"agent/{role}-{ts}"
        wt_path = os.path.join(WORKTREE_ROOT, branch.replace("/", "_"))

        # Cria worktree + branch
        init = subprocess.run(
            f'git worktree add -b {branch} "{wt_path}" HEAD',
            shell=True, capture_output=True, text=True, cwd=repo_path, timeout=60,
        )
        if init.returncode != 0:
            return (f"Nao consegui criar worktree isolado (git): "
                    f"{init.stderr.strip() or init.stdout.strip()}")

        # Maker: modelo resolve a tarefa no contexto do worktree
        maker = _run_maker(role, task, wt_path)

        # Checker independente (isolado do raciocinio do maker)
        checker = ""
        if validate:
            checker = _run_checker(role, task, maker, wt_path)

        return (
            f"[SUBAGENTE ISOLADO] role={role} branch={branch}\n"
            f"worktree: {wt_path}\n\n"
            f"--- MAKER ---\n{maker}\n\n"
            f"--- CHECKER ---\n{checker}\n\n"
            f"Para mesclar: git merge {branch}  (ou descartar: "
            f"git worktree remove '{wt_path}' --force)"
        )
    except subprocess.TimeoutExpired:
        return "Subagente isolado excedeu o tempo limite (60s)."
    except FileNotFoundError:
        return "Git nao encontrado. Instale: https://git-scm.com"
    except Exception as e:
        return f"Erro no subagente isolado: {e}"


def _run_maker(role: str, task: str, wt_path: str) -> str:
    try:
        import ollama
        prompt = (
            f"Voce e um sub-agente executor (papel: {role}) trabalhando em um "
            f"worktree isolado em: {wt_path}\n\n"
            f"TAREFA: {task}\n\n"
            "Resolva a tarefa. Se envolver arquivos, descreva exatamente quais "
            "criar/modificar e o conteudo. Seja conclusivo e pratico. Responda em "
            "portugues."
        )
        resp = _call_ollama_with_timeout(
            ollama.chat, model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        return resp["message"]["content"]
    except Exception as e:
        return f"[maker] erro: {e}"


def _run_checker(role: str, task: str, maker_output: str, wt_path: str) -> str:
    try:
        import ollama
        prompt = (
            "Voce e um VERIFICADOR independente. Nao sabe como o trabalho foi "
            "feito, apenas valida o resultado.\n\n"
            f"TAREFA ORIGINAL: {task}\n\n"
            f"RESULTADO DO EXECUTOR:\n{maker_output}\n\n"
            f"ARQUIVOS NO WORKTREE: {wt_path}\n\n"
            "Verifique: (1) a tarefa foi atendida? (2) ha erros obvios ou "
            "inconsistencias? (3) o que falta? Responda APENAS com um veredito "
            "curto: APROVADO / PARCIAL / REPROVADO, seguido de justificativa."
        )
        resp = _call_ollama_with_timeout(
            ollama.chat, model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX, "temperature": 0.1},
        )
        return resp["message"]["content"]
    except Exception as e:
        return f"[checker] erro: {e}"


def subagent_cleanup(worktree_path: str) -> str:
    """Remove um worktree criado por subagent_run_isolated."""
    try:
        res = subprocess.run(
            f'git worktree remove "{worktree_path}" --force',
            shell=True, capture_output=True, text=True, timeout=60,
        )
        if res.returncode == 0:
            return f"Worktree removido: {worktree_path}"
        return f"Falha ao remover: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return f"Erro ao remover worktree: {e}"
