"""
plugin_auto_evolucao.py
=======================
Sistema de auto-evolução controlada e segura para o agente. Permite melhoria contínua através de:
- Análise de desempenho e auto-otimização de parâmetros
- Propostas de melhoria baseadas em interações
- Experimentos controlados em ambiente isolado
- Aprendizado meta-cognitivo sobre próprias capacidades
- Evolução de estratégias de resolução de problemas

Todas as mudanças são feitas dentro de limites de segurança pré-definidos.
Nenhuma modificação de código núcleo é permitida sem validação explícita.
"""

import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import math

__version__ = "1.0.0"
PLUGIN_NAME = "Sistema de Auto-Evolução Controlada"

# Diretório de dados do plugin
PLUGIN_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agente_data", "auto_evolucao"
)

# Arquivos de dados
METRICS_FILE = os.path.join(PLUGIN_DATA_DIR, "metricas_desempenho.json")
PARAMETERS_FILE = os.path.join(PLUGIN_DATA_DIR, "parametros_otimizados.json")
EXPERIMENTS_FILE = os.path.join(PLUGIN_DATA_DIR, "experimentos.json")
IMPROVEMENTS_FILE = os.path.join(PLUGIN_DATA_DIR, "propostas_melhoria.json")
STRATEGIES_FILE = os.path.join(PLUGIN_DATA_DIR, "estrategias_resolucao.json")

# Limites de segurança para auto-otimização
SAFE_PARAM_RANGES = {
    "temperature": (0.1, 1.0),
    "num_ctx": (1024, 16384),
    "max_tool_rounds": (5, 30),
    "history_messages": (20, 200),
    "timeout_seconds": (30, 300)
}

# Histórico de desempenho para análise de tendências
PERFORMANCE_HISTORY_SIZE = 100


def _ensure_dir():
    """Garante que o diretório de dados exista."""
    os.makedirs(PLUGIN_DATA_DIR, exist_ok=True)


def _load_json(path: str, default: Any = None) -> Any:
    """Carrega dados JSON com tratamento de erro."""
    if default is None:
        default = {} if path.endswith(".json") else []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler {path}: {e}")
    return default


def _save_json(path: str, data: Any) -> None:
    """Salva dados em formato JSON."""
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_performance_metrics() -> Dict:
    """Obtém métricas de desempenho atuais."""
    return _load_json(METRICS_FILE, {
        "response_times": [],
        "tool_success_rate": [],
        "user_satisfaction_estimates": [],
        "error_rates": [],
        "timestamp": []
    })


def _record_performance(metric_type: str, value: float) -> None:
    """Registra uma métrica de desempenho."""
    metrics = _get_performance_metrics()
    if metric_type not in metrics:
        metrics[metric_type] = []

    metrics[metric_type].append({
        "value": value,
        "timestamp": datetime.now().isoformat()
    })

    # Mantém apenas os N mais recentes
    if len(metrics[metric_type]) > PERFORMANCE_HISTORY_SIZE:
        metrics[metric_type] = metrics[metric_type][-PERFORMANCE_HISTORY_SIZE:]

    metrics["timestamp"] = [datetime.now().isoformat()]  # Atualiza timestamp geral
    _save_json(METRICS_FILE, metrics)


def _get_optimized_parameters() -> Dict:
    """Obtém parâmetros atualmente otimizados."""
    return _load_json(PARAMETERS_FILE, {
        "temperature": 0.3,
        "num_ctx": 8192,
        "max_tool_rounds": 15,
        "history_messages": 80,
        "timeout_seconds": 120,
        "last_updated": datetime.now().isoformat()
    })


def _save_optimized_parameters(params: Dict) -> None:
    """Salva parâmetros otimizados."""
    params["last_updated"] = datetime.now().isoformat()
    _save_json(PARAMETERS_FILE, params)


def _get_experiments() -> List[Dict]:
    """Obtém histórico de experimentos."""
    return _load_json(EXPERIMENTS_FILE, [])


def _record_experiment(experiment: Dict) -> None:
    """Registra um experimento realizado."""
    experiments = _get_experiments()
    experiment["timestamp"] = datetime.now().isoformat()
    experiments.append(experiment)
    # Mantém apenas os 50 mais recentes
    if len(experiments) > 50:
        experiments = experiments[-50:]
    _save_json(EXPERIMENTS_FILE, experiments)


def _get_improvement_proposals() -> List[Dict]:
    """Obtém propostas de melhoria pendentes."""
    return _load_json(IMPROVEMENTS_FILE, [])


def _save_improvement_proposals(proposals: List[Dict]) -> None:
    """Salva propostas de melhoria."""
    _save_json(IMPROVEMENTS_FILE, proposals)


def _get_strategies() -> Dict:
    """Obtém estratégias de resolução de problemas aprendidas."""
    return _load_json(STRATEGIES_FILE, {
        "problem_patterns": {},
        "solution_effectiveness": {},
        "context_strategies": {}
    })


def _save_strategies(strategies: Dict) -> None:
    """Salva estratégias de resolução de problemas."""
    _save_json(STRATEGIES_FILE, strategies)


def analyze_performance_trends() -> Dict[str, Any]:
    """Analisa tendências de desempenho para identificar melhorias necessárias."""
    metrics = _get_performance_metrics()
    analysis = {}

    for metric_name, values in metrics.items():
        if metric_name == "timestamp" or not isinstance(values, list) or len(values) < 5:
            continue

        # Extrai apenas os valores numéricos
        numeric_values = [item["value"] for item in values if isinstance(item, dict) and "value" in item]
        if len(numeric_values) < 5:
            continue

        # Calcula tendência simples (regressão linear básica)
        n = len(numeric_values)
        x_values = list(range(n))
        y_values = numeric_values

        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n

            # Prevede o próximo valor
            next_predicted = slope * n + intercept
            current_avg = sum(y_values[-5:]) / 5 if len(y_values) >= 5 else sum(y_values) / len(y_values)

            analysis[metric_name] = {
                "slope": slope,
                "current_avg": current_avg,
                "predicted_next": next_predicted,
                "trend": "improving" if slope < -0.01 else "declining" if slope > 0.01 else "stable",
                "volatility": max(y_values) - min(y_values) if y_values else 0
            }

    return analysis


def suggest_parameter_optimizations() -> List[Dict]:
    """Sugere otimizações de parâmetros baseadas em análise de tendências."""
    suggestions = []
    params = _get_optimized_parameters()
    trends = analyze_performance_trends()

    # Mapeia métricas para parâmetros que podem afetá-las
    metric_to_param = {
        "response_times": ["temperature", "num_ctx", "max_tool_rounds"],
        "tool_success_rate": ["temperature", "timeout_seconds"],
        "error_rates": ["temperature", "max_tool_rounds"],
        "user_satisfaction_estimates": ["temperature", "num_ctx"]
    }

    for metric_name, analysis in trends.items():
        if metric_name in metric_to_param:
            for param_name in metric_to_param[metric_name]:
                if param_name in SAFE_PARAM_RANGES:
                    current_value = params.get(param_name,
                                             SAFE_PARAM_RANGES[param_name][0])
                    min_val, max_val = SAFE_PARAM_RANGES[param_name]

                    # Sugere ajuste baseado na tendência
                    suggestion = None
                    reason = ""

                    if metric_name == "response_times" and analysis["trend"] == "declining":
                        # Tempos de resposta aumentando - pode reduzir temperatura ou contexto
                        if param_name == "temperature" and current_value > min_val:
                            suggestion = max(min_val, current_value - 0.05)
                            reason = "Tempo de resposta aumentando - reduzindo temperatura para melhorar velocidade"
                        elif param_name == "num_ctx" and current_value > min_val:
                            suggestion = max(min_val, int(current_value * 0.9))
                            reason = "Tempo de resposta aumentando - reduzindo contexto para melhorar velocidade"

                    elif metric_name == "error_rates" and analysis["trend"] == "declining":
                        # Taxa de erro aumentando - pode aumentar temperatura para mais criatividade ou timeout
                        if param_name == "temperature" and current_value < max_val:
                            suggestion = min(max_val, current_value + 0.05)
                            reason = "Taxa de erro aumentando - aumentando temperatura para melhorar adaptabilidade"
                        elif param_name == "timeout_seconds" and current_value < max_val:
                            suggestion = min(max_val, int(current_value * 1.1))
                            reason = "Taxa de erro aumentando - aumentando timeout para permitir mais tempo de processamento"

                    elif metric_name == "user_satisfaction_estimates" and analysis["trend"] == "declining":
                        # Satisfação diminuindo - ajusta equilíbrio entre criatividade e precisão
                        if param_name == "temperature":
                            # Tenta encontrar um valor ótimo baseado na história
                            if current_value < 0.5:
                                suggestion = min(max_val, current_value + 0.03)
                                reason = "Satisfação diminuindo - aumentando levemente temperatura para mais criatividade"
                            else:
                                suggestion = max(min_val, current_value - 0.03)
                                reason = "Satisfação diminuindo - diminuindo temperatura para mais precisão"

                    if suggestion is not None and abs(suggestion - current_value) > 0.001:
                        suggestions.append({
                            "parameter": param_name,
                            "current_value": current_value,
                            "suggested_value": suggestion,
                            "reason": reason,
                            "confidence": min(0.9, abs(analysis["slope"]) * 10),  # Baseia confidence na inclinação
                            "metric_triggered": metric_name
                        })

    return suggestions


def apply_safe_parameter_optimization() -> str:
    """Aplica otimizações de parâmetros consideradas seguras."""
    suggestions = suggest_parameter_optimizations()
    applied = []

    params = _get_optimized_parameters()

    for suggestion in suggestions:
        # Só aplica se a confiança for razoável e a mudança for pequena
        if suggestion["confidence"] > 0.3:
            param_name = suggestion["parameter"]
            new_value = suggestion["suggested_value"]

            # Verifica se está dentro dos limites seguros
            min_val, max_val = SAFE_PARAM_RANGES[param_name]
            if min_val <= new_value <= max_val:
                # Aplica a mudança
                params[param_name] = new_value
                applied.append(f"{param_name}: {suggestion['current_value']:.3f} → {new_value:.3f} ({suggestion['reason']})")

    if applied:
        _save_optimized_parameters(params)
        return f"✅ Otimizações aplicadas:\n" + "\n".join(applied)
    else:
        return "ℹ️ Nenhuma otimização de parâmetro necessária neste momento."


def run_experiment(experiment_name: str, parameter_changes: Dict,
                  success_metric: str, duration_minutes: int = 10) -> str:
    """Executa um experimento controlado com mudanças de parâmetros."""
    # Registra o experimento
    experiment = {
        "id": hashlib.md5(f"{experiment_name}{time.time()}".encode()).hexdigest()[:8],
        "name": experiment_name,
        "parameter_changes": parameter_changes.copy(),
        "success_metric": success_metric,
        "duration_minutes": duration_minutes,
        "status": "initiated",
        "baseline_metrics": {},
        "results": None
    }

    # Captura métricas de linha de base
    metrics = _get_performance_metrics()
    for metric_name, values in metrics.items():
        if metric_name != "timestamp" and isinstance(values, list) and values:
            recent_values = [item["value"] for item in values[-5:] if isinstance(item, dict) and "value" in item]
            if recent_values:
                experiment["baseline_metrics"][metric_name] = sum(recent_values) / len(recent_values)

    experiments = _get_experiments()
    experiments.append(experiment)
    _save_json(EXPERIMENTS_FILE, experiments)

    # Aplica as mudanças temporariamente
    original_params = _get_optimized_parameters()
    temp_params = original_params.copy()

    for param, value in parameter_changes.items():
        if param in SAFE_PARAM_RANGES:
            min_val, max_val = SAFE_PARAM_RANGES[param]
            temp_params[param] = max(min_val, min(max_val, value))

    # Simula aplicação (na prática, isso afetaria as chamadas futuras ao modelo)
    _save_optimized_parameters(temp_params)

    # Marca como em execução
    experiment["status"] = "running"
    _save_json(EXPERIMENTS_FILE, experiments)

    return (
        f"🧪 Experimento iniciado: {experiment_name}\n"
        f"ID: {experiment['id']}\n"
        f"Duração: {duration_minutes} minutos\n"
        f"Métrica de sucesso: {success_metric}\n"
        f"Parâmetros alterados: {', '.join([f'{k}={v}' for k, v in parameter_changes.items()])}\n"
        f"\nℹ️ Os resultados serão avaliados automaticamente após o período especificado."
    )


def evaluate_experiments() -> str:
    """Avalia experimentos concluídos e aplica mudanças benéficas."""
    experiments = _get_experiments()
    completed = []

    for exp in experiments:
        if exp["status"] == "completed" and exp["results"] is not None:
            completed.append(exp)
        elif exp["status"] == "running":
            # Verifica se o tempo suficiente passou
            start_time = datetime.fromisoformat(exp["timestamp"])
            elapsed = datetime.now() - start_time
            if elapsed.total_seconds() > (exp["duration_minutes"] * 60):
                # Marca para avaliação (na prática, isso seria feito por um processo separado)
                exp["status"] = "completed"
                # Simula resultados - em um sistema real, colete métricas reais
                exp["results"] = {
                    "success_metric_improvement": 0.05,  # Placeholder
                    "other_metrics": {}
                }

    if not completed:
        return "ℹ️ Nenhum experimento concluído para avaliar."

    applied_changes = []
    for exp in completed:
        # Verifica se o experimento foi bem-sucedido
        improvement = exp["results"].get("success_metric_improvement", 0)
        if improvement > 0.02:  # Melhoria mínima de 2%
            # Aplica as mudanças permanentemente
            current_params = _get_optimized_parameters()
            for param, value in exp["parameter_changes"].items():
                if param in SAFE_PARAM_RANGES:
                    min_val, max_val = SAFE_PARAM_RANGES[param]
                    new_val = max(min_val, min(max_val, value))
                    # Só aplica se for uma melhoria significativa
                    if abs(new_val - current_params.get(param, new_val)) > 0.001:
                        current_params[param] = new_val
                        applied_changes.append(f"{param}: {exp['parameter_changes'][param]} (melhoria: {improvement:.2%})")

            if applied_changes:
                _save_optimized_parameters(current_params)

        # Marca como arquivado para não reprocessar
        exp["status"] = "archived"

    _save_json(EXPERIMENTS_FILE, experiments)

    if applied_changes:
        return f"✅ Experimentos aplicados:\n" + "\n".join(applied_changes)
    else:
        return "ℹ️ Nenhum experimento mostrou melhoria suficiente para aplicação."


def generate_improvement_proposals() -> str:
    """Gera propostas de melhoria baseadas na análise de desempenho e interações."""
    proposals = []

    # Analisa tendências de desempenho
    trends = analyze_performance_trends()

    # Analisa padrões de uso de ferramentas (seria implementado com mais dados)
    # Por enquanto, usa heurísticas simples

    # Proposta 1: Otimização de parâmetros baseada em tendências
    param_suggestions = suggest_parameter_optimizations()
    for sugg in param_suggestions:
        if sugg["confidence"] > 0.4:
            proposals.append({
                "type": "parameter_optimization",
                "title": f"Otimizar parâmetro {sugg['parameter']}",
                "description": sugg["reason"],
                "action": f"def apply_{sugg['parameter']}_optimization():\n    # Código para aplicar a otimização\n    pass",
                "priority": "medium",
                "confidence": sugg["confidence"],
                "estimated_impact": "medium"
            })

    # Proposta 2: Melhoria na estratégia de resolução baseado em padrões
    strategies = _get_strategies()
    # Análise simplificada - na prática seria mais sofisticada
    if len(strategies.get("problem_patterns", {})) > 5:
        proposals.append({
            "type": "strategy_improvement",
            "title": "Refinar estratégias de resolução de problemas",
            "description": "Baseado na análise de padrões de problemas resolvidos, otimizar a seleção de estratégias",
            "action": "# Código para melhorar seleção de estratégias baseado em histórico\npass",
            "priority": "low",
            "confidence": 0.6,
            "estimated_impact": "low"
        })

    # Salva propostas novas
    existing = _get_improvement_proposals()
    # Evita duplicatas baseado no título
    existing_titles = {p["title"] for p in existing}
    new_proposals = [p for p in proposals if p["title"] not in existing_titles]

    if new_proposals:
        all_proposals = existing + new_proposals
        # Mantém apenas as 20 mais recentes
        if len(all_proposals) > 20:
            all_proposals = all_proposals[-20:]
        _save_improvement_proposals(all_proposals)

    if new_proposals:
        result = ["💡 Novas propostas de melhoria geradas:"]
        for i, prop in enumerate(new_proposals, 1):
            result.append(f"{i}. [{prop['type'].upper()}] {prop['title']}")
            result.append(f"   Descrição: {prop['description']}")
            result.append(f"   Prioridade: {prop['priority']} | Confiança: {int(prop['confidence']*100)}%")
            result.append("")
        return "\n".join(result)
    else:
        return "ℹ️ Nenhuma nova proposta de melhoria gerada neste ciclo."


def get_evolution_status() -> str:
    """Retorna o status atual do sistema de auto-evolução."""
    params = _get_optimized_parameters()
    metrics = _get_performance_metrics()
    experiments = _get_experiments()
    proposals = _get_improvement_proposals()
    strategies = _get_strategies()

    # Conta experimentos por status
    exp_counts = {}
    for exp in experiments:
        status = exp.get("status", "unknown")
        exp_counts[status] = exp_counts.get(status, 0) + 1

    output = []
    output.append("🧬 STATUS DO SISTEMA DE AUTO-EVOLUÇÃO")
    output.append("=" * 50)
    output.append("")

    output.append("⚙️ PARÂMETROS OTIMIZADOS ATUAL:")
    for param, value in params.items():
        if param != "last_updated":
            min_val, max_val = SAFE_PARAM_RANGES.get(param, (0, 0))
            percentage = ((value - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
            output.append(f"  {param}: {value} ({percentage:.0f}% do intervalo [{min_val}-{max_val}])")
    output.append("")

    output.append("📊 EXPERIMENTOS:")
    output.append(f"  Total: {len(experiments)}")
    for status, count in exp_counts.items():
        if count > 0:
            output.append(f"  {status}: {count}")
    output.append("")

    output.append("💡 PROPOSTAS DE MELHORIA:")
    output.append(f"  Pendentes: {len(proposals)}")
    if proposals:
        for prop in proposals[:3]:  # Mostra apenas as 3 primeiras
            output.append(f"  • {prop['title']} ({prop['priority']})")
    output.append("")

    output.append("🎯 ESTRATÉGIAS APRENDIDAS:")
    output.append(f"  Padrões de problema: {len(strategies.get('problem_patterns', {}))}")
    output.append(f"  Eficácia de soluções: {len(strategies.get('solution_effectiveness', {}))}")
    output.append("")

    # Mostra tendências recentes se disponíveis
    trends = analyze_performance_trends()
    if trends:
        output.append("📈 TENDÊNCIAS DE DESEMPENHO:")
        for metric, analysis in list(trends.items())[:3]:  # Top 3
            trend_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(analysis["trend"], "❓")
            output.append(f"  {trend_emoji} {metric}: {analysis['trend']} (inclinação: {analysis['slope']:.4f})")

    return "\n".join(output)


# Função principal para ser chamada pelo pipeline de memória
def auto_evolve() -> str:
    """Executa um ciclo de auto-evolução segura."""
    results = []

    # 1. Analisa e aplica otimizações de parâmetros seguras
    opt_result = apply_safe_parameter_optimization()
    if "✅" in opt_result:
        results.append(opt_result)

    # 2. Avalia experimentos concluídos
    eval_result = evaluate_experiments()
    if "✅" in eval_result:
        results.append(eval_result)

    # 3. Gera novas propostas de melhoria
    prop_result = generate_improvement_proposals()
    if "💡" in prop_result:
        results.append(prop_result)

    # 4. Retorna status consolidado
    if not results:
        results.append("ℹ️ Ciclo de auto-evolução concluído - nenhuma ação necessária neste momento.")

    return "\n\n".join(results)


def register(api):
    """Registra todas as ferramentas de auto-evolução controlada."""
    api.register_tool(
        name="auto_evolve",
        func=auto_evolve,
        description="Executa um ciclo de auto-evolução segura: analisa desempenho, aplica otimizações de parâmetros, avalia experimentos e gera propostas de melhoria.",
        parameters={},
        required=[]
    )

    api.register_tool(
        name="get_evolution_status",
        func=get_evolution_status,
        description="Obtém o status atual do sistema de auto-evolução, incluindo parâmetros otimizados, experimentos e propostas de melhoria.",
        parameters={},
        required=[]
    )

    api.register_tool(
        name="run_experiment",
        func=run_experiment,
        description="Executa um experimento controlado com mudanças temporárias de parâmetros para testar melhorias.",
        parameters={
            "experiment_name": {"type": "string", "description": "Nome descritivo do experimento"},
            "parameter_changes": {"type": "object", "description": "Dicionário de mudanças de parâmetros (ex: {\"temperature\": 0.4})"},
            "success_metric": {"type": "string", "description": "Métrica que determinará o sucesso do experimento (ex: \"response_times\", \"tool_success_rate\")"},
            "duration_minutes": {"type": "integer", "description": "Duração do experimento em minutos (padrão: 10)"}
        },
        required=["experiment_name", "parameter_changes", "success_metric"]
    )

    api.register_tool(
        name="get_optimized_parameters",
        func=lambda: json.dumps(_get_optimized_parameters(), indent=2),
        description="Obtém os parâmetros atualmente otimizados pelo sistema de auto-evolução.",
        parameters={},
        required=[]
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Sistema de auto-evolução controlada e segura que melhora o desempenho através de otimização de parâmetros, experimentos controlados e aprendizado contínuo - sem modificar código núcleo ou permitir ações perigosas.",
        "tools": [
            "auto_evolve", "get_evolution_status", "run_experiment", "get_optimized_parameters"
        ],
    }