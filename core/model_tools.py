
from .model_manager import (
    detect_system as _detect_system,
    recommend_model as _recommend_model,
    list_available_models as _list_available_models,
    get_model_info as _get_model_info,
    download_model as _download_model,
    benchmark_model as _benchmark_model,
    set_default_model as _set_default_model,
    _get_ollama_models as _get_installed_models,
)


def model_detect() -> str:
    """Detecta hardware e status do Ollama."""
    try:
        sys_info = _detect_system()
        lines = [
            f"RAM: {sys_info['ram_gb']}GB",
            f"VRAM: {sys_info['vram_gb']}GB" if sys_info['vram_gb'] else "VRAM: N/A (sem GPU detectada)",
            f"GPU: {'Sim' if sys_info['has_gpu'] else 'Nao'}",
            f"Tier: {sys_info['tier']}",
            f"Ollama: {sys_info['ollama_message']}",
            f"Plataforma: {sys_info['platform']}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao detectar sistema: {e}"


def model_recommend(task_type: str = "text") -> str:
    try:
        rec = _recommend_model(task_type)
        model = rec["recommended"]
        tier = rec["system"]["tier"]
        lines = [
            f"Sistema: {rec['system']['ram_gb']}GB RAM / {rec['system']['vram_gb']}GB VRAM (tier: {tier})",
            f"Recomendado: {model['name']}",
            f"  Qualidade: {model['quality']}",
            f"  Tamanho: ~{model.get('size_gb', '?')}GB",
            f"  Contexto: {model.get('ctx', '?')} tokens",
            f"  Status: {'Ja instalado' if rec['already_have'] else 'Precisa baixar'}",
        ]
        if not rec["already_have"]:
            lines.append(f"\nPara baixar: use model_download('{model['name']}')")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao recomendar modelo: {e}"


def model_list() -> str:
    """Lista todos os modelos disponiveis no Ollama e no catalogo."""
    try:
        installed = _get_installed_models()
        catalog = _list_available_models()

        lines = ["--- Instalados ---"]
        if installed:
            for m in installed:
                lines.append(f"  {m['name']} ({m['size_gb']}GB)")
        else:
            lines.append("  Nenhum modelo instalado.")

        lines.append("\n--- Disponiveis para download ---")
        seen = set()
        for m in catalog:
            if m["name"] not in seen:
                seen.add(m["name"])
                tag = m.get("tier", "")
                qual = m.get("quality", "")
                ctx = m.get("ctx", "?")
                installed_mark = " ✅" if any(m["name"] in i["name"] for i in installed) else ""
                lines.append(f"  {m['name']} [{tag}] {qual} ctx:{ctx} {installed_mark}")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar modelos: {e}"


def model_info(model_name: str) -> str:
    """Mostra informacoes detalhadas sobre um modelo especifico.

    Args:
        model_name: Nome do modelo (ex: qwen2.5:7b)
    """
    try:
        info = _get_model_info(model_name)
        installed = _get_installed_models()
        is_installed = any(model_name in m["name"] for m in installed)

        if info:
            lines = [
                f"Modelo: {info['name']}",
                f"  Tipo: {info.get('type', '?')}",
                f"  Qualidade: {info.get('quality', '?')}",
                f"  Tamanho: ~{info.get('size_gb', '?')}GB",
                f"  Contexto: {info.get('ctx', '?')} tokens",
                f"  Categoria: {info.get('tier', info.get('tier_desc', '?'))}",
                f"  Instalado: {'Sim' if is_installed else 'Nao'}",
            ]
        else:
            if is_installed:
                for m in installed:
                    if model_name in m["name"]:
                        lines = [
                            f"Modelo: {m['name']}",
                            f"  Tamanho: {m['size_gb']}GB",
                            f"  Modificado: {m.get('modified', '?')}",
                            f"  Instalado: Sim (no Ollama, fora do catalogo)",
                        ]
                        break
            else:
                return f"Modelo '{model_name}' nao encontrado."

        return "\n".join(lines)
    except Exception as e:
        return f"Erro: {e}"


def model_download(model_name: str) -> str:
    try:
        result = _download_model(model_name)
        if result.get("success"):
            return f"Download concluido: {model_name}"
        return f"Erro no download: {result.get('error', 'desconhecido')}"
    except Exception as e:
        return f"Erro: {e}"


def model_benchmark(model_name: str = "", quick: bool = True) -> str:
    try:
        if not model_name:
            from config import MODEL
            model_name = MODEL
        result = _benchmark_model(model_name, quick)
        if "error" in result:
            return f"Erro: {result['error']}"

        lines = [f"Benchmark: {model_name}", ""]
        for r in result.get("results", []):
            if "error" in r:
                lines.append(f"  {r['test']}: ERRO - {r['error']}")
            else:
                lines.append(f"  {r['test']}: {r['latency_ms']}ms | {r['tokens_per_sec']} tok/s")

        summary = result.get("summary", {})
        lines.extend([
            "",
            f"Resumo: {summary.get('successful', 0)}/{summary.get('total_tasks', 0)} tarefas",
            f"Latencia media: {summary.get('avg_latency_ms', '?')}ms",
            f"Vazao media: {summary.get('avg_tokens_per_sec', '?')} tok/s",
        ])
        return "\n".join(lines)
    except Exception as e:
        return f"Erro: {e}"


def model_switch(model_name: str) -> str:
    try:
        result = _set_default_model(model_name)
        if result.get("success"):
            return f"Modelo padrao alterado para {model_name}."
        return f"Erro: {result.get('error', 'desconhecido')}"
    except Exception as e:
        return f"Erro: {e}"
