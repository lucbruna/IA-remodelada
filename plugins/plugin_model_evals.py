"""
plugin_model_evals.py
=====================
Side-by-Side Model Evals — comparacao justificada de modelos.

Funcionalidades:
  - Comparacao lado a lado com scoring
  - Benchmark de tarefas (codigo, escrita, raciocinio, matematica)
  - Evaluacao automatica com metricas
  - A/B testing de modelos
  - Historico de evaluations para justificar roteador
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Side-by-Side Model Evals"

import os
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "model_evals")
HISTORY_FILE = os.path.join(DATA_DIR, "eval_history.json")

import ollama


def _load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(history: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-200:], f, indent=2, ensure_ascii=False)


def _query_model(model: str, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> dict:
    start = time.time()
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        elapsed = time.time() - start
        content = response.get("message", {}).get("content", "")
        return {
            "content": content,
            "time": round(elapsed, 2),
            "tokens": len(content.split()),
            "success": True,
        }
    except Exception as e:
        return {"content": "", "time": round(time.time() - start, 2), "tokens": 0, "success": False, "error": str(e)}


BENCHMARK_TASKS = {
    "coding": [
        {"name": "FizzBuzz", "prompt": "Write FizzBuzz in Python, compact.", "expected": "fizzbuzz"},
        {"name": "Binary Search", "prompt": "Write binary search in Python.", "expected": "binary_search"},
        {"name": "List Comprehension", "prompt": "Filter even squares from 1-100 using list comprehension.", "expected": "[x**2 for x in range(1, 101) if x**2 % 2 == 0]"},
    ],
    "reasoning": [
        {"name": "Logic Puzzle", "prompt": "If all roses are flowers and some flowers fade quickly, can we conclude all roses fade quickly? Explain.", "expected": "no"},
        {"name": "Math", "prompt": "What is 17 * 23? Show work.", "expected": "391"},
    ],
    "writing": [
        {"name": "Summarize", "prompt": "Summarize quantum computing in 3 sentences.", "expected": "quantum"},
        {"name": "Email", "prompt": "Write a professional email declining a meeting.", "expected": "decline"},
    ],
}


def register(api):

    def eval_compare(
        prompt: str,
        model_a: str,
        model_b: str,
        temperature: float = 0.3,
    ) -> str:
        avail = [m["name"] for m in ollama.list().get("models", [])]
        if model_a not in avail:
            return f"❌ Modelo '{model_a}' nao encontrado. Disponiveis: {', '.join(avail[:5])}"
        if model_b not in avail:
            return f"❌ Modelo '{model_b}' nao encontrado. Disponiveis: {', '.join(avail[:5])}"

        result_a = _query_model(model_a, prompt, temperature)
        result_b = _query_model(model_b, prompt, temperature)

        lines = [
            f"⚖️ **Side-by-Side Eval**",
            f"📝 Prompt: {prompt[:100]}",
            "",
            f"**🤖 Modelo A: {model_a}** ({result_a['time']}s, {result_a['tokens']} tokens)",
            f"{'✅' if result_a['success'] else '❌'} {result_a['content'][:500]}",
            "",
            f"**🤖 Modelo B: {model_b}** ({result_b['time']}s, {result_b['tokens']} tokens)",
            f"{'✅' if result_b['success'] else '❌'} {result_b['content'][:500]}",
            "",
            "**Comparacao:**",
            f"• Velocidade: {model_a}={result_a['time']}s vs {model_b}={result_b['time']}s",
            f"• Tamanho saida: {model_a}={result_a['tokens']}t vs {model_b}={result_b['tokens']}t",
        ]

        eval_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "model_a": model_a,
            "model_b": model_b,
            "result_a": result_a,
            "result_b": result_b,
        }
        history = _load_history()
        history.append(eval_entry)
        _save_history(history)

        return "\n".join(lines)

    def eval_benchmark(
        model: str,
        categories: str = "coding,reasoning,writing",
    ) -> str:
        avail = [m["name"] for m in ollama.list().get("models", [])]
        if model not in avail:
            return f"❌ Modelo '{model}' nao encontrado."

        cat_list = [c.strip() for c in categories.split(",")]
        results = []
        total_score = 0
        total_tasks = 0

        for cat in cat_list:
            tasks = BENCHMARK_TASKS.get(cat, [])
            if not tasks:
                continue
            for task in tasks:
                r = _query_model(model, task["prompt"], temperature=0.1, max_tokens=500)
                score = 0
                if r["success"]:
                    content_lower = r["content"].lower()
                    expected = task["expected"].lower()
                    if expected in content_lower:
                        score = 10
                    elif len(r["content"]) > 20:
                        score = 5
                total_score += score
                total_tasks += 1
                results.append({
                    "category": cat,
                    "name": task["name"],
                    "score": score,
                    "max": 10,
                    "time": r["time"],
                })

        avg = total_score / total_tasks if total_tasks > 0 else 0
        lines = [
            f"📊 **Benchmark: {model}**",
            f"Categorias: {', '.join(cat_list)}",
            f"Total: {total_score}/{total_tasks * 10} (media: {avg:.1f}/10)",
            "",
        ]
        for r in results:
            emoji = "✅" if r["score"] >= 8 else "🟡" if r["score"] >= 5 else "❌"
            lines.append(f"  {emoji} [{r['category']}] {r['name']}: {r['score']}/{r['max']} ({r['time']}s)")

        eval_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "benchmark",
            "model": model,
            "categories": cat_list,
            "total_score": total_score,
            "total_tasks": total_tasks,
            "average": avg,
            "details": results,
        }
        history = _load_history()
        history.append(eval_entry)
        _save_history(history)

        return "\n".join(lines)

    def eval_arena(
        prompt: str,
        models_csv: str,
        temperature: float = 0.3,
    ) -> str:
        models = [m.strip() for m in models_csv.split(",")]
        avail = [m["name"] for m in ollama.list().get("models", [])]

        results = []
        for model in models:
            if model not in avail:
                results.append({"model": model, "success": False, "error": "not found"})
                continue
            r = _query_model(model, prompt, temperature)
            results.append({"model": model, **r})

        lines = [f"🏟️ **Model Arena** — {len(models)} modelos", f"📝 {prompt[:80]}\n"]
        ranked = sorted(results, key=lambda x: x.get("tokens", 0), reverse=True)

        for i, r in enumerate(ranked, 1):
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            if r["success"]:
                lines.append(f"{medal} **{r['model']}** — {r['tokens']} tokens, {r['time']}s")
            else:
                lines.append(f"❌ **{r['model']}** — {r.get('error', 'erro')}")

        return "\n".join(lines)

    def eval_history(per_page: int = 10) -> str:
        history = _load_history()
        if not history:
            return "Nenhuma evaluation no historico."
        recent = history[-per_page:]
        lines = [f"📚 **{len(recent)} evaluations recentes:**\n"]
        for e in reversed(recent):
            ts = e.get("timestamp", "")[:16]
            if e.get("type") == "benchmark":
                lines.append(f"  📊 {ts} — {e.get('model', '?')} benchmark: {e.get('average', 0):.1f}/10")
            else:
                lines.append(f"  ⚖️ {ts} — {e.get('model_a', '?')} vs {e.get('model_b', '?')}")
        return "\n".join(lines)

    def eval_recommend_model(task_type: str = "general") -> str:
        history = _load_history()
        if not history:
            return "Nenhuma evaluation no historico. Rode 'eval_benchmark' primeiro."

        model_scores = {}
        for e in history:
            if e.get("type") == "benchmark":
                model = e.get("model", "")
                avg = e.get("average", 0)
                if model not in model_scores:
                    model_scores[model] = []
                model_scores[model].append(avg)

        if not model_scores:
            return "Nenhum benchmark encontrado no historico."

        rankings = []
        for model, scores in model_scores.items():
            avg_score = sum(scores) / len(scores)
            rankings.append((model, avg_score, len(scores)))
        rankings.sort(key=lambda x: -x[1])

        lines = ["🏆 **Recomendacao baseada em evaluations:**\n"]
        for i, (model, score, runs) in enumerate(rankings[:5], 1):
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} **{model}** — media {score:.1f}/10 ({runs} runs)")

        lines.append(f"\n💡 Para tarefa '{task_type}', recomendo: **{rankings[0][0]}**")
        return "\n".join(lines)

    api.register_tool("eval_compare", eval_compare,
        "Compara dois modelos lado a lado no mesmo prompt.",
        {"prompt": {"type": "string", "description": "Prompt para ambos"},
         "model_a": {"type": "string", "description": "Modelo A"},
         "model_b": {"type": "string", "description": "Modelo B"},
         "temperature": {"type": "integer"}}, ["prompt", "model_a", "model_b"])

    api.register_tool("eval_benchmark", eval_benchmark,
        "Benchmark completo de um modelo em multiplas categorias.",
        {"model": {"type": "string", "description": "Modelo a avaliar"},
         "categories": {"type": "string", "description": "Categorias: coding, reasoning, writing"}},
        ["model"])

    api.register_tool("eval_arena", eval_arena,
        "Arena com multiplos modelos compitindo no mesmo prompt.",
        {"prompt": {"type": "string"}, "models_csv": {"type": "string", "description": "Modelos separados por virgula"},
         "temperature": {"type": "integer"}}, ["prompt", "models_csv"])

    api.register_tool("eval_history", eval_history,
        "Historico de evaluations realizadas.",
        {"per_page": {"type": "integer"}}, [])

    api.register_tool("eval_recommend_model", eval_recommend_model,
        "Recomenda o melhor modelo baseado em evaluations anteriores.",
        {"task_type": {"type": "string", "description": "Tipo de tarefa: general, coding, writing"}}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Side-by-side model evals: comparacao, benchmark, arena, historico, recomendacao.",
        "tools": ["eval_compare", "eval_benchmark", "eval_arena", "eval_history", "eval_recommend_model"],
    }
