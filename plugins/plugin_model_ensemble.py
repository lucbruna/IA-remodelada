"""
plugin_model_ensemble.py
========================
Plugin de ensemble de modelos de linguagem. Fornece ferramentas para:
- Comparar saídas de múltiplos modelos
- Técnicas de ensemble (votação, média, etc.)
- Gerenciamento de modelos de fallback
- Otimização de seleção de modelo baseado no tipo de tarefa
"""

import os
import json
import statistics
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Importar o cliente Ollama para comunicação direta com modelos
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

__version__ = "1.0.0"
PLUGIN_NAME = "Ensemble de Modelos de Linguagem"

# Modelo padrão do sistema (deve coincidir com agente_core.py)
DEFAULT_MODEL = "qwen2.5:1.5b"


def _check_ollama_availability() -> tuple[bool, str]:
    """Verifica se o Ollama está disponível e responde."""
    if not OLLAMA_AVAILABLE:
        return False, "Biblioteca ollama não instalada. Execute: pip install ollama"

    try:
        # Tentar conectar ao Ollama
        ollama.list()
        return True, "Ollama disponível"
    except Exception as e:
        return False, f"Ollama não acessível: {str(e)}"


def get_available_models() -> str:
    """
    Lista todos os modelos disponíveis no Ollama local.

    Returns:
        String formatada com a lista de modelos disponíveis
    """
    avail, msg = _check_ollama_availability()
    if not avail:
        return f"❌ Erro: {msg}"

    try:
        models_data = ollama.list()
        models = models_data.get('models', [])

        if not models:
            return "📭 Nenhum modelo encontrado no Ollama local"

        result = ["📋 Modelos disponíveis no Ollama local:"]
        result.append("-" * 60)

        for model in models:
            name = model.get('name', 'unknown')
            size = model.get('size', 0)
            size_gb = size / (1024**3) if size else 0
            modified = model.get('modified_at', 'unknown')

            result.append(f"📦 {name}")
            result.append(f"   Tamanho: {size_gb:.2f} GB")
            result.append(f"   Modificado: {modified}")
            result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Erro ao listar modelos: {str(e)}"


def compare_model_outputs(
    prompt: str,
    models: List[str],
    temperature: float = 0.7,
    max_tokens: int = 500
) -> str:
    """
    Compara as saídas de múltiplos modelos para o mesmo prompt.

    Args:
        prompt: O prompt/input para enviar aos modelos
        models: Lista de nomes de modelos para comparar (ex: ["qwen2.5:1.5b", "llama3.2:3b"])
        temperature: Temperatura para geração (0.0 a 1.0)
        max_tokens: Máximo de tokens a gerar

    Returns:
        Comparação formatada das saídas de cada modelo
    """
    avail, msg = _check_ollama_availability()
    if not avail:
        return f"❌ Erro: {msg}"

    if not prompt.strip():
        return "❌ Erro: Prompt vazio fornecido"

    if not models:
        return "❌ Erro: Nenhum modelo especificado para comparação"

    # Validar modelos
    try:
        available_models = [m['name'] for m in ollama.list().get('models', [])]
        invalid_models = [m for m in models if m not in available_models]
        if invalid_models:
            return f"❌ Modelos não encontrados: {', '.join(invalid_models)}. Modelos disponíveis: {', '.join(available_models[:5])}{'...' if len(available_models) > 5 else ''}"
    except Exception as e:
        return f"❌ Erro ao verificar modelos disponíveis: {str(e)}"

    results = []
    errors = []

    for model_name in models:
        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            )

            output = response['message']['content'].strip()
            results.append({
                "model": model_name,
                "output": output,
                "length": len(output),
                "success": True
            })

        except Exception as e:
            errors.append({
                "model": model_name,
                "error": str(e)
            })
            results.append({
                "model": model_name,
                "output": f"[ERRO: {str(e)}]",
                "length": 0,
                "success": False
            })

    # Formatar resultados
    output_lines = [
        f"🔍 Comparação de {len(models)} modelos para o prompt:",
        f"   \"{prompt[:100]}{'...' if len(prompt) > 100 else ''}\"",
        "",
        "📊 Resultados:"
    ]

    for result in results:
        if result["success"]:
            output_lines.append(f"✅ {result['model']}:")
            output_lines.append(f"   Comprimento: {result['length']} caracteres")
            output_lines.append(f"   Saída: {result['output'][:200]}{'...' if len(result['output']) > 200 else ''}")
            output_lines.append("")
        else:
            output_lines.append(f"❌ {result['model']}: FALHA")
            output_lines.append(f"   Erro: {result['output']}")
            output_lines.append("")

    return "\n".join(output_lines)


def ensemble_vote(
    prompt: str,
    models: List[str],
    num_samples: int = 3,
    temperature: float = 0.8,
    max_tokens: int = 300
) -> str:
    """
    Executa votação entre múltiplos modelos para melhorar a qualidade da resposta.
    Cada modelo gera múltiplas amostras, e a mais frequente é selecionada.

    Args:
        prompt: O prompt/input para enviar aos modelos
        models: Lista de nomes de modelos para usar no ensemble
        num_samples: Número de amostras por modelo para votação
        temperature: Temperatura para geração (maior = mais diversidade)
        max_tokens: Máximo de tokens a gerar

    Returns:
        Resposta vencedora da votação
    """
    avail, msg = _check_ollama_availability()
    if not avail:
        return f"❌ Erro: {msg}"

    if not prompt.strip():
        return "❌ Erro: Prompt vazio fornecido"

    if not models:
        return "❌ Erro: Nenhum modelo especificado para ensemble"

    # Validar modelos
    try:
        available_models = [m['name'] for m in ollama.list().get('models', [])]
        invalid_models = [m for m in models if m not in available_models]
        if invalid_models:
            return f"❌ Modelos não encontrados: {', '.join(invalid_models)}"
    except Exception as e:
        return f"❌ Erro ao verificar modelos disponíveis: {str(e)}"

    # Coletar amostras de todos os modelos
    all_samples = []
    model_stats = {}

    for model_name in models:
        model_samples = []
        for _ in range(num_samples):
            try:
                response = ollama.chat(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                )

                output = response['message']['content'].strip()
                model_samples.append(output)

            except Exception as e:
                # Ignorar amostras falhas, mas continuar
                pass

        if model_samples:
            all_samples.extend(model_samples)
            model_stats[model_name] = {
                "samples_generated": len(model_samples),
                "unique_samples": len(set(model_samples))
            }

    if not all_samples:
        return "❌ Erro: Nenhuma amostra pôde ser gerada por qualquer modelo"

    # Contar frequência de cada saída única
    sample_counts = Counter(all_samples)
    most_common_sample, count = sample_counts.most_common(1)[0]

    # Calcular porcentagem de acordo
    total_votes = len(all_samples)
    agreement_percentage = (count / total_votes) * 100

    # Formatar resultado
    result_lines = [
        f"🗳️  Resultado do Ensemble por Votação",
        f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
        f"🤖 Modelos utilizados: {', '.join(models)}",
        f"🔢 Amostras por modelo: {num_samples}",
        f"📊 Total de amostras: {total_votes}",
        f"🏆 Vencedor: {count} votos ({agreement_percentage:.1f}% de consenso)",
        "",
        "💬 Resposta selecionada:",
        f"   {most_common_sample}",
        "",
        "📈 Estatísticas por modelo:"
    ]

    for model_name, stats in model_stats.items():
        result_lines.append(f"   {model_name}: {stats['samples_generated']} amostras, {stats['unique_samples']} únicas")

    return "\n".join(result_lines)


def smart_model_selector(
    task_type: str,
    complexity: str = "medium"
) -> str:
    """
    Sugere o melhor modelo disponível para um tipo de tarefa específico.

    Args:
        task_type: Tipo de tarefa ("code", "text", "analysis", "creative", "reasoning")
        complexity: Nível de complexidade ("low", "medium", "high")

    Returns:
        Recomendação de modelo com justificativa
    """
    avail, msg = _check_ollama_availability()
    if not avail:
        return f"❌ Erro: {msg}"

    try:
        available_models = [m['name'] for m in ollama.list().get('models', [])]
    except Exception as e:
        return f"❌ Erro ao obter modelos disponíveis: {str(e)}"

    if not available_models:
        return "❌ Nenhum modelo disponível no Ollama"

    # Mapeamento de tarefa para características de modelo desejadas
    task_preferences = {
        "code": {
            "preferred": ["codellama", "starcoder", "wizardcoder", "phi"],
            "avoid": [],
            "reason": "Modelos especializados em código têm melhor compreensão de sintaxe e lógica de programação"
        },
        "text": {
            "preferred": ["llama", "mistral", "nemotron", "zephyr"],
            "avoid": [],
            "reason": "Modelos de linguagem geral são bons para geração e compreensão de texto natural"
        },
        "analysis": {
            "preferred": ["mistral", "nemotron", "yi", "qwen"],
            "avoid": [],
            "reason": "Modelos com forte raciocínio lógico são melhores para análise e raciocínio complexo"
        },
        "creative": {
            "preferred": ["wizard", "orca", "dolphin", "llama"],
            "avoid": [],
            "reason": "Modelos com criatividade aprimorada são melhores para geração de conteúdo original"
        },
        "reasoning": {
            "preferred": ["nemotron", "wizard", "orca", "phi"],
            "avoid": [],
            "reason": "Modelos treinados para raciocínio lógico e resolução de problemas"
        },
        "general": {
            "preferred": ["llama", "mistral", "qwen"],
            "avoid": [],
            "reason": "Modelos equilibrados para uso geral"
        }
    }

    # Obter preferências para o tipo de tarefa
    prefs = task_preferences.get(task_type.lower(), task_preferences["general"])

    # Procurar por modelos que correspondam às preferências
    recommended = []
    for model in available_models:
        model_lower = model.lower()
        # Verificar se o nome do modelo contém alguma das preferências
        if any(pref in model_lower for pref in prefs["preferred"]):
            recommended.append(model)

    # Se não encontrou correspondência específica, usar os primeiros disponíveis
    if not recommended:
        recommended = available_models[:3]  # Top 3 disponíveis

    # Ajustar recomendação baseado na complexidade
    def estimate_size(model_name):
        name_lower = model_name.lower()
        if any(x in name_lower for x in ["70b", "65b", "48b", "34b"]):
            return 3
        elif any(x in name_lower for x in ["30b", "27b", "20b", "15b", "14b", "13b"]):
            return 2
        elif any(x in name_lower for x in ["10b", "8b", "7b"]):
            return 1
        return 0

    recommended.sort(key=estimate_size, reverse=(complexity == "high"))

    # Formatar recomendação
    primary_recommendation = recommended[0] if recommended else available_models[0]
    alternatives = recommended[1:4] if len(recommended) > 1 else available_models[1:4]

    result_lines = [
        f"🎯 Recomendação de Modelo para Tarefa",
        f"📋 Tipo de tarefa: {task_type}",
        f"⚙️  Complexidade: {complexity}",
        "",
        f"✅ Modelo recomendado: {primary_recommendation}",
        f"💡 Justificativa: {prefs['reason']}",
        ""
    ]

    if alternatives:
        result_lines.append("🔄 Modelos alternativos:")
        for model in alternatives:
            result_lines.append(f"   • {model}")
        result_lines.append("")

    result_lines.append("📋 Todos os modelos disponíveis:")
    for model in sorted(available_models):
        marker = " 👑" if model == primary_recommendation else ""
        result_lines.append(f"   • {model}{marker}")

    return "\n".join(result_lines)


# Registro das funções no sistema de plugins
def register(api):
    """Registra todas as ferramentas de ensemble de modelos."""

    api.register_tool(
        name="get_available_models",
        func=get_available_models,
        description="Lista todos os modelos disponíveis no Ollama local",
        parameters={},
        required=[]
    )

    api.register_tool(
        name="compare_model_outputs",
        func=compare_model_outputs,
        description="Compara as saídas de múltiplos modelos para o mesmo prompt",
        parameters={
            "prompt": {"type": "string", "description": "Prompt/input para enviar aos modelos"},
            "models": {"type": "array", "items": {"type": "string"}, "description": "Lista de nomes de modelos para comparar"},
            "temperature": {"type": "number", "description": "Temperatura para geração (padrão: 0.7)"},
            "max_tokens": {"type": "integer", "description": "Máximo de tokens a gerar (padrão: 500)"}
        },
        required=["prompt", "models"]
    )

    api.register_tool(
        name="ensemble_vote",
        func=ensemble_vote,
        description="Executa votação entre múltiplos modelos para melhorar a qualidade da resposta",
        parameters={
            "prompt": {"type": "string", "description": "Prompt/input para enviar aos modelos"},
            "models": {"type": "array", "items": {"type": "string"}, "description": "Lista de nomes de modelos para usar no ensemble"},
            "num_samples": {"type": "integer", "description": "Número de amostras por modelo para votação (padrão: 3)"},
            "temperature": {"type": "number", "description": "Temperatura para geração (padrão: 0.8)"},
            "max_tokens": {"type": "integer", "description": "Máximo de tokens a gerar (padrão: 300)"}
        },
        required=["prompt", "models"]
    )

    api.register_tool(
        name="smart_model_selector",
        func=smart_model_selector,
        description="Sugere o melhor modelo disponível para um tipo de tarefa específico",
        parameters={
            "task_type": {"type": "string", "description": "Tipo de tarefa (code, text, analysis, creative, reasoning, general)"},
            "complexity": {"type": "string", "description": "Nível de complexidade (low, medium, high, padrão: medium)"}
        },
        required=["task_type"]
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Ensemble de modelos de linguagem: comparação, votação e seleção inteligente de modelos",
        "tools": [
            "get_available_models",
            "compare_model_outputs",
            "ensemble_vote",
            "smart_model_selector"
        ],
    }
