from ._common import *

# =======================================================================
# ORCHESTRATE HEAVY - tarefas complexas em etapas (estilo OMP)
# -----------------------------------------------------------------------
# Para tarefas PESADAS de codigo: divide em sub-tarefas, executa em
# paralelo via subagentes isolados (worktree), e faz merge/reduce do
# resultado. O plano e persistido em disco, podendo ser retomado. Combina
# task_decompose (turbo) com subagent_run_isolated (git worktree).
# =======================================================================

_PLAN_FILE = os.path.join(DATA_DIR, "agente_data", "memoria_evolutiva", "heavy_plan.json")


def heavy_plan_create(goal: str, subtasks: list) -> str:
    """Cria um plano persistido de tarefa pesada.

    goal: objetivo geral. subtasks: lista de strings (cada uma vira um
    subagente isolado). Retorna o plano com IDs. Salva em disco.
    """
    goal = (goal or "").strip()
    if not goal or not subtasks:
        return "Informe goal e uma lista de subtasks."
    plan = {
        "goal": goal,
        "created": datetime.now().isoformat(),
        "status": "planned",
        "tasks": [
            {"id": f"t{i+1}", "task": str(t).strip(), "status": "pending", "result": ""}
            for i, t in enumerate(subtasks)
        ],
    }
    _save_json(_PLAN_FILE, plan)
    return (f"Plano criado com {len(subtasks)} sub-tarefas para: '{goal}'.\n"
            f"Use heavy_plan_run para executar em paralelo (subagentes isolados).")


def heavy_plan_run(parallel: bool = True, validate: bool = True) -> str:
    """Executa as sub-tarefas do plano via subagentes isolados.

    Cada subtask roda em seu proprio git worktree (maker+checker), em
    paralelo se parallel=True. Ao terminar, faz reduce (sintese). Retorna
    o relatorio consolidado e atualiza o plano. Requer git.
    """
    plan = _load_json(_PLAN_FILE, {})
    if not plan.get("tasks"):
        return "Nenhum plano ativo. Use heavy_plan_create primeiro."
    try:
        from core.subagents_git import subagent_run_isolated
    except Exception as e:
        return f"Subagentes indisponiveis: {e}"

    pendentes = [t for t in plan["tasks"] if t["status"] == "pending"]
    if not pendentes:
        return "Todas as sub-tarefas ja foram executadas."

    relatorios = {}

    def _rodar(t):
        return t["id"], subagent_run_isolated(
            role=t["id"], task=t["task"], validate=validate)

    if parallel:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(4, len(pendentes))) as ex:
            for tid, out in ex.map(_rodar, pendentes):
                relatorios[tid] = out
    else:
        for t in pendentes:
            tid, out = _rodar(t)
            relatorios[tid] = out

    for t in plan["tasks"]:
        if t["id"] in relatorios:
            t["status"] = "done"
            t["result"] = relatorios[t["id"]]
    plan["status"] = "executed"
    _save_json(_PLAN_FILE, plan)

    # Reduce: sintese do modelo sobre os resultados
    try:
        import ollama
        ctx = "\n\n".join(f"[{tid}]\n{r}" for tid, r in relatorios.items())
        resp = _call_ollama_with_timeout(
            ollama.chat, model=MODEL,
            messages=[{"role": "user", "content": (
                f"Tarefa geral: {plan['goal']}\n\n"
                "Resultados das sub-tarefas (isoladas):\n" + ctx +
                "\n\nFaca um RELATORIO CONSOLIDADO (reduce): o que foi resolvido, "
                "o que ficou pendente e proximos passos. Em portugues.")}],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        reduce = resp["message"]["content"]
    except Exception as e:
        reduce = f"(sintese indisponivel: {e})"
    return "Execucao paralela concluida.\n\nRELATORIO CONSOLIDADO:\n" + reduce


def heavy_plan_status() -> str:
    """Mostra o estado do plano pesado atual."""
    plan = _load_json(_PLAN_FILE, {})
    if not plan.get("tasks"):
        return "Nenhum plano ativo."
    linhas = [f"Goal: {plan.get('goal')} | status: {plan.get('status')}"]
    for t in plan["tasks"]:
        linhas.append(f"  {t['id']} [{t['status']}] {t['task'][:80]}")
    return "\n".join(linhas)


def heavy_plan_reduce() -> str:
    """Re-sintetiza (reduce) os resultados ja executados do plano."""
    plan = _load_json(_PLAN_FILE, {})
    if not plan.get("tasks"):
        return "Nenhum plano ativo."
    try:
        import ollama
        ctx = "\n\n".join(f"[{t['id']}]\n{t.get('result','')}" for t in plan["tasks"])
        resp = _call_ollama_with_timeout(
            ollama.chat, model=MODEL,
            messages=[{"role": "user", "content": (
                f"Tarefa geral: {plan['goal']}\n\nResultados:\n{ctx}\n\n"
                "Relatorio consolidado em portugues.")}],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        return resp["message"]["content"]
    except Exception as e:
        return f"Erro no reduce: {e}"
