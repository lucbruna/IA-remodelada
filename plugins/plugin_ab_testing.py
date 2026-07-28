"""
plugin_ab_testing.py
====================
A/B testing de modelos — split traffic, metrics comparativas, decisao.

Funcionalidades:
  - Criar experimentos A/B entre modelos
  - Split de trafego (50/50, 80/20, etc)
  - Metricas: latency, tokens, qualidade, custo
  - Resultados estatisticos
  - Recomendacao de modelo vencedor
"""

__version__ = "1.0.0"
PLUGIN_NAME = "A/B Testing"

import os
import json
import time
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "ab_testing")
EXPERIMENTS_FILE = os.path.join(DATA_DIR, "experiments.json")


def _load_experiments() -> list:
    if os.path.exists(EXPERIMENTS_FILE):
        try:
            with open(EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_experiments(exps: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(exps[-100:], f, indent=2, ensure_ascii=False)


def register(api):

    def ab_create_experiment(
        name: str,
        model_a: str,
        model_b: str,
        split_ratio: float = 0.5,
        description: str = "",
    ) -> str:
        import ollama
        avail = [m["name"] for m in ollama.list().get("models", [])]
        if model_a not in avail:
            return f"❌ Model A '{model_a}' not found."
        if model_b not in avail:
            return f"❌ Model B '{model_b}' not found."
        exp = {
            "id": f"exp-{int(time.time() * 1000) % 100000}",
            "name": name,
            "model_a": model_a,
            "model_b": model_b,
            "split_ratio": split_ratio,
            "description": description,
            "status": "created",
            "results_a": [],
            "results_b": [],
            "created_at": datetime.now().isoformat(),
        }
        exps = _load_experiments()
        exps.append(exp)
        _save_experiments(exps)
        return (
            f"✅ Experiment created: {exp['id']}\n"
            f"A: {model_a} vs B: {model_b}\n"
            f"Split: {split_ratio*100:.0f}/{(1-split_ratio)*100:.0f}"
        )

    def ab_run_trial(experiment_id: str, prompt: str, temperature: float = 0.3) -> str:
        import ollama
        exps = _load_experiments()
        exp = next((e for e in exps if e["id"] == experiment_id), None)
        if not exp:
            return f"❌ Experiment '{experiment_id}' not found."
        use_a = random.random() < exp["split_ratio"]
        model = exp["model_a"] if use_a else exp["model_b"]
        side = "A" if use_a else "B"
        start = time.time()
        try:
            resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": 500},
            )
            elapsed = time.time() - start
            content = resp.get("message", {}).get("content", "")
            result = {
                "prompt": prompt[:200],
                "response": content[:500],
                "time": round(elapsed, 2),
                "tokens": len(content.split()),
                "timestamp": datetime.now().isoformat(),
            }
            if use_a:
                exp["results_a"].append(result)
            else:
                exp["results_b"].append(result)
            _save_experiments(exps)
            return f"✅ Trial {side}: {model} ({elapsed:.2f}s, {len(content.split())} tokens)"
        except Exception as e:
            return f"❌ Trial failed: {e}"

    def ab_get_results(experiment_id: str) -> str:
        exps = _load_experiments()
        exp = next((e for e in exps if e["id"] == experiment_id), None)
        if not exp:
            return f"❌ Experiment '{experiment_id}' not found."
        ra = exp.get("results_a", [])
        rb = exp.get("results_b", [])
        def avg(lst, key):
            vals = [r[key] for r in lst if key in r]
            return sum(vals) / len(vals) if vals else 0
        avg_time_a = avg(ra, "time")
        avg_time_b = avg(rb, "time")
        avg_tokens_a = avg(ra, "tokens")
        avg_tokens_b = avg(rb, "tokens")
        winner = ""
        if avg_time_a > 0 and avg_time_b > 0:
            if avg_time_a < avg_time_b:
                winner = f"🏆 Model A ({exp['model_a']}) is faster"
            else:
                winner = f"🏆 Model B ({exp['model_b']}) is faster"
        return (
            f"📊 **Results: {exp['name']}**\n\n"
            f"**A: {exp['model_a']}** ({len(ra)} trials)\n"
            f"  Avg time: {avg_time_a:.2f}s\n"
            f"  Avg tokens: {avg_tokens_a:.0f}\n\n"
            f"**B: {exp['model_b']}** ({len(rb)} trials)\n"
            f"  Avg time: {avg_time_b:.2f}s\n"
            f"  Avg tokens: {avg_tokens_b:.0f}\n\n"
            f"{winner}"
        )

    def ab_list_experiments() -> str:
        exps = _load_experiments()
        if not exps:
            return "No experiments."
        lines = ["🧪 **A/B Experiments:**\n"]
        for e in exps[-10:]:
            trials = len(e.get("results_a", [])) + len(e.get("results_b", []))
            lines.append(f"  • {e['id']} — {e['name']} ({e['model_a']} vs {e['model_b']}) [{trials} trials]")
        return "\n".join(lines)

    def ab_delete_experiment(experiment_id: str) -> str:
        exps = _load_experiments()
        before = len(exps)
        exps = [e for e in exps if e["id"] != experiment_id]
        if len(exps) == before:
            return f"❌ Experiment '{experiment_id}' not found."
        _save_experiments(exps)
        return f"🗑️ Experiment '{experiment_id}' deleted."

    def ab_recommend_model(experiment_id: str) -> str:
        exps = _load_experiments()
        exp = next((e for e in exps if e["id"] == experiment_id), None)
        if not exp:
            return f"❌ Experiment '{experiment_id}' not found."
        ra = exp.get("results_a", [])
        rb = exp.get("results_b", [])
        if not ra or not rb:
            return "Need at least 1 trial per model."
        avg_time_a = sum(r["time"] for r in ra) / len(ra)
        avg_time_b = sum(r["time"] for r in rb) / len(rb)
        avg_tokens_a = sum(r["tokens"] for r in ra) / len(ra)
        avg_tokens_b = sum(r["tokens"] for r in rb) / len(rb)
        score_a = (1 / avg_time_a) * avg_tokens_a if avg_time_a > 0 else 0
        score_b = (1 / avg_time_b) * avg_tokens_b if avg_time_b > 0 else 0
        if score_a > score_b:
            rec = exp["model_a"]
            reason = f"faster ({avg_time_a:.2f}s vs {avg_time_b:.2f}s)"
        else:
            rec = exp["model_b"]
            reason = f"faster ({avg_time_b:.2f}s vs {avg_time_a:.2f}s)"
        return (
            f"🏆 **Recommendation:** {rec}\n"
            f"Reason: {reason}\n"
            f"Scores: A={score_a:.2f} B={score_b:.2f}"
        )

    def ab_quick_test(model_a: str, model_b: str, prompt: str, trials: int = 3) -> str:
        import ollama
        avail = [m["name"] for m in ollama.list().get("models", [])]
        if model_a not in avail:
            return f"❌ Model A '{model_a}' not found."
        if model_b not in avail:
            return f"❌ Model B '{model_b}' not found."
        times_a, times_b = [], []
        for i in range(trials):
            start = time.time()
            try:
                ollama.chat(model=model_a, messages=[{"role": "user", "content": prompt}],
                           options={"temperature": 0.1, "num_predict": 200})
                times_a.append(time.time() - start)
            except Exception:
                times_a.append(999)
            start = time.time()
            try:
                ollama.chat(model=model_b, messages=[{"role": "user", "content": prompt}],
                           options={"temperature": 0.1, "num_predict": 200})
                times_b.append(time.time() - start)
            except Exception:
                times_b.append(999)
        avg_a = sum(times_a) / len(times_a)
        avg_b = sum(times_b) / len(times_b)
        winner = model_a if avg_a < avg_b else model_b
        return (
            f"⚡ **Quick Test ({trials} trials):**\n"
            f"A: {model_a} — avg {avg_a:.2f}s\n"
            f"B: {model_b} — avg {avg_b:.2f}s\n"
            f"🏆 Winner: {winner}"
        )

    api.register_tool("ab_create_experiment", ab_create_experiment,
        "Create A/B experiment between two models.",
        {"name": {"type": "string"}, "model_a": {"type": "string"},
         "model_b": {"type": "string"}, "split_ratio": {"type": "number"},
         "description": {"type": "string"}}, ["name", "model_a", "model_b"])

    api.register_tool("ab_run_trial", ab_run_trial,
        "Run a trial in an experiment.",
        {"experiment_id": {"type": "string"}, "prompt": {"type": "string"},
         "temperature": {"type": "number"}}, ["experiment_id", "prompt"])

    api.register_tool("ab_get_results", ab_get_results,
        "Get experiment results with metrics.",
        {"experiment_id": {"type": "string"}}, ["experiment_id"])

    api.register_tool("ab_list_experiments", ab_list_experiments,
        "List all A/B experiments.", {}, [])

    api.register_tool("ab_delete_experiment", ab_delete_experiment,
        "Delete an experiment.",
        {"experiment_id": {"type": "string"}}, ["experiment_id"])

    api.register_tool("ab_recommend_model", ab_recommend_model,
        "Recommend winning model from experiment.",
        {"experiment_id": {"type": "string"}}, ["experiment_id"])

    api.register_tool("ab_quick_test", ab_quick_test,
        "Quick speed comparison between two models.",
        {"model_a": {"type": "string"}, "model_b": {"type": "string"},
         "prompt": {"type": "string"}, "trials": {"type": "integer"}},
        ["model_a", "model_b", "prompt"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "A/B testing: experiments, split traffic, metrics, recommendations.",
        "tools": ["ab_create_experiment", "ab_run_trial", "ab_get_results",
                   "ab_list_experiments", "ab_delete_experiment", "ab_recommend_model",
                   "ab_quick_test"],
    }
