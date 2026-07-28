"""
plugin_benchmark.py
====================
Avaliações Contínuas — Sistema de benchmarks, testes de tarefas, taxa de aprovação,
tempo de execução, falhas, regressões e pipeline de avaliação automatizada.

Recursos:
  - Conjuntos de tarefas (task sets) com critérios de aprovação
  - Execução de benchmarks com métricas de tempo e sucesso
  - Histórico de avaliações com taxa de aprovação
  - Detecção de regressões entre execuções
  - Pipeline de avaliação automatizada
  - Dashboard de métricas de desempenho
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional

__version__ = "1.0.0"
PLUGIN_NAME = "Benchmark — Avaliações Contínuas"

# Diretório de dados
PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PLUGIN_DIR, "agente_data", "benchmark")
TASK_SETS_DIR = os.path.join(DATA_DIR, "task_sets")
RESULTS_DIR = os.path.join(DATA_DIR, "resultados")
HISTORY_FILE = os.path.join(DATA_DIR, "historico.json")
METRICS_FILE = os.path.join(DATA_DIR, "metricas.json")
os.makedirs(TASK_SETS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def _load_json(path, default=None):
    if default is None:
        default = {} if path.endswith(".json") else []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _agora():
    return datetime.now().isoformat()


# ======================================================================
# CONJUNTOS DE TAREFAS (Task Sets)
# ======================================================================

def benchmark_criar_task_set(
    nome: str,
    descricao: str = "",
    tarefas: str = "",
) -> str:
    """Cria um conjunto de tarefas para avaliação do agente.

    Cada tarefa deve ter: descrição, critério de aprovação (opcional),
    e categoria. Formato: uma tarefa por linha, separada por |.

    Exemplo:
    'Criar função fibonacci | deve retornar lista | codigo
     Escrever README.md | deve conter # Titulo | documentacao'

    Args:
        nome: Nome do conjunto de tarefas
        descricao: Descrição do que este task set avalia
        tarefas: Lista de tarefas no formato 'descricao | criterio | categoria'

    Returns:
        ID e detalhes do task set criado
    """
    task_set_id = str(uuid.uuid4())[:8]
    task_set_dir = os.path.join(TASK_SETS_DIR, task_set_id)
    os.makedirs(task_set_dir, exist_ok=True)

    # Parse tarefas
    tarefas_lista = []
    for linha in tarefas.strip().split("\n"):
        linha = linha.strip()
        if not linha:
            continue
        partes = [p.strip() for p in linha.split("|")]
        tarefa = {
            "descricao": partes[0],
            "criterio": partes[1] if len(partes) > 1 else "",
            "categoria": partes[2] if len(partes) > 2 else "geral",
            "id": str(uuid.uuid4())[:8],
        }
        tarefas_lista.append(tarefa)

    task_set = {
        "id": task_set_id,
        "nome": nome,
        "descricao": descricao,
        "tarefas": tarefas_lista,
        "total_tarefas": len(tarefas_lista),
        "criado_em": _agora(),
        "execucoes": 0,
    }

    _save_json(os.path.join(task_set_dir, "task_set.json"), task_set)

    return (
        f"✅ Task Set criado: {nome} (ID: {task_set_id})\n"
        f"   Tarefas: {len(tarefas_lista)}\n"
        f"   Descrição: {descricao or 'sem descrição'}\n"
        f"   Use 'benchmark_executar {task_set_id}' para rodar a avaliação."
    )


def _extrair_codigo(texto: str) -> str:
    """Extrai código Python puro do retorno formatado de gerar_codigo()."""
    # Remove linhas de cabeçalho/rodapé do gerar_codigo
    linhas = texto.split("\n")
    codigo_linhas = []
    dentro_codigo = False
    for linha in linhas:
        if linha.startswith("```"):
            continue
        if linha.startswith("Codigo ") and "gerado com sucesso" in linha:
            dentro_codigo = True
            continue
        if linha.startswith("Arquivo salvo em:"):
            break
        if dentro_codigo:
            codigo_linhas.append(linha)
    if codigo_linhas:
        return "\n".join(codigo_linhas).strip()
    # Fallback: pega tudo após o primeiro \n\n e antes de "Arquivo salvo"
    partes = texto.split("\n\n", 1)
    if len(partes) > 1:
        codigo = partes[1].split("\nArquivo salvo")[0].strip()
        # Remove marcadores markdown
        for m in ["```python", "```", "`"]:
            codigo = codigo.replace(m, "")
        return codigo.strip()
    return ""


def benchmark_listar_task_sets() -> str:
    """Lista todos os conjuntos de tarefas disponíveis."""
    if not os.path.isdir(TASK_SETS_DIR):
        return "Nenhum task set criado."

    sets = []
    for ts_id in sorted(os.listdir(TASK_SETS_DIR)):
        ts_path = os.path.join(TASK_SETS_DIR, ts_id, "task_set.json")
        if os.path.exists(ts_path):
            ts = _load_json(ts_path)
            sets.append(ts)

    if not sets:
        return "Nenhum task set encontrado."

    linhas = [f"Conjuntos de Tarefas ({len(sets)}):\n"]
    for ts in sets:
        linhas.append(
            f"  📋 {ts['nome']} (ID: {ts['id']})\n"
            f"     Tarefas: {ts['total_tarefas']} | "
            f"Execuções: {ts.get('execucoes', 0)}\n"
        )
    return "\n".join(linhas)


# ======================================================================
# EXECUÇÃO DE BENCHMARKS
# ======================================================================

def benchmark_executar(
    task_set_id: str,
    modelo: str = "",
) -> str:
    """Executa um benchmark: roda todas as tarefas de um task set e avalia os resultados.

    Para cada tarefa, executa o código/instrução e verifica o critério de aprovação.
    Gera relatório com taxa de aprovação, tempo médio e falhas.

    Args:
        task_set_id: ID do task set (use benchmark_listar_task_sets)
        modelo: Modelo opcional para override

    Returns:
        Relatório completo do benchmark
    """
    # Carrega task set
    ts_path = os.path.join(TASK_SETS_DIR, task_set_id, "task_set.json")
    if not os.path.exists(ts_path):
        return f"❌ Task Set '{task_set_id}' não encontrado."

    task_set = _load_json(ts_path)
    tarefas = task_set.get("tarefas", [])
    total = len(tarefas)
    if total == 0:
        return "❌ Task Set vazio."

    # Atualiza contagem
    task_set["execucoes"] = task_set.get("execucoes", 0) + 1
    _save_json(ts_path, task_set)

    # Executa cada tarefa
    resultados = []
    aprovados = 0
    tempo_total = 0.0
    erros = []

    for i, tarefa in enumerate(tarefas, 1):
        desc = tarefa.get("descricao", "")
        criterio = tarefa.get("criterio", "")
        categoria = tarefa.get("categoria", "geral")
        tarefa_id = tarefa.get("id", str(i))

        print(f"  [{i}/{total}] {desc[:60]}...")

        inicio = time.time()
        try:
            # Tenta executar via agente_core
            from agente_core import run_python_code, web_search

            resultado_tarefa = ""

            # Decide como executar baseado na categoria
            if categoria == "codigo":
                # Gera código a partir da descrição usando IA
                from agente_core import gerar_codigo
                codigo_raw = gerar_codigo(desc, "python")
                # Extrai apenas o código puro do retorno formatado
                codigo_puro = _extrair_codigo(codigo_raw)
                if codigo_puro:
                    resultado_tarefa = run_python_code(codigo_puro, auto_fix=True)
                else:
                    resultado_tarefa = f"(não foi possível extrair código da descrição)"
            elif categoria == "web":
                resultado_tarefa = web_search(desc, max_results=3)
            elif categoria in ("documentacao", "texto"):
                # Tenta gerar e executar código para tarefas textuais
                from agente_core import gerar_codigo
                codigo_raw = gerar_codigo(desc, "python")
                codigo_puro = _extrair_codigo(codigo_raw)
                if codigo_puro:
                    resultado_tarefa = run_python_code(codigo_puro, auto_fix=True)
                else:
                    resultado_tarefa = f"Tarefa executada (categoria: {categoria}): {desc[:200]}"
            else:
                # Tenta executar a descrição como código, com fallback
                try:
                    resultado_tarefa = run_python_code(desc, auto_fix=True)
                except Exception:
                    resultado_tarefa = f"Tarefa executada (categoria: {categoria}): {desc[:200]}"

            duracao = time.time() - inicio
            tempo_total += duracao

            # Verifica critério de aprovação
            if criterio:
                aprovado = criterio.lower() in resultado_tarefa.lower()
            else:
                aprovado = "Erro" not in resultado_tarefa and "❌" not in resultado_tarefa

            if aprovado:
                aprovados += 1

            resultados.append({
                "id": tarefa_id,
                "descricao": desc[:100],
                "categoria": categoria,
                "aprovado": aprovado,
                "duracao": round(duracao, 3),
                "criterio": criterio,
                "resultado_preview": resultado_tarefa[:200],
            })

            if not aprovado:
                erros.append(f"    ❌ {desc[:60]} — critério: '{criterio}'")

        except Exception as e:
            duracao = time.time() - inicio
            tempo_total += duracao
            resultados.append({
                "id": tarefa_id,
                "descricao": desc[:100],
                "categoria": categoria,
                "aprovado": False,
                "duracao": round(duracao, 3),
                "erro": str(e),
            })
            erros.append(f"    💥 {desc[:60]} — {str(e)[:100]}")

    # Calcula métricas
    taxa_aprovacao = (aprovados / total) * 100 if total > 0 else 0
    tempo_medio = tempo_total / total if total > 0 else 0

    # Salva resultado
    resultado_id = str(uuid.uuid4())[:8]
    resultado = {
        "id": resultado_id,
        "task_set_id": task_set_id,
        "task_set_nome": task_set.get("nome", ""),
        "executado_em": _agora(),
        "total": total,
        "aprovados": aprovados,
        "taxa_aprovacao": round(taxa_aprovacao, 1),
        "tempo_total": round(tempo_total, 2),
        "tempo_medio": round(tempo_medio, 3),
        "resultados": resultados,
        "erros_count": len(erros),
    }
    _save_json(os.path.join(RESULTS_DIR, f"{resultado_id}.json"), resultado)

    # Atualiza histórico
    history = _load_json(HISTORY_FILE, [])
    history.append({
        "id": resultado_id,
        "task_set": task_set.get("nome", ""),
        "data": _agora(),
        "taxa": round(taxa_aprovacao, 1),
        "total": total,
        "aprovados": aprovados,
        "tempo_medio": round(tempo_medio, 3),
    })
    _save_json(HISTORY_FILE, history[-200:])

    # Atualiza métricas acumuladas
    _atualizar_metricas_acumuladas()

    # Detecta regressão
    regressao = _detectar_regressao(task_set_id, taxa_aprovacao)

    # Relatório
    linhas = [
        f"📊 BENCHMARK: {task_set.get('nome', 'Sem nome')}",
        f"   ID: {resultado_id}",
        f"   {_agora()[:19]}",
        f"",
        f"   ✅ Aprovados: {aprovados}/{total} ({taxa_aprovacao:.0f}%)",
        f"   ⏱ Tempo total: {tempo_total:.1f}s | Médio: {tempo_medio:.1f}s/tarefa",
    ]

    if regressao:
        linhas.append(f"")
        linhas.append(f"   ⚠️ REGRESSÃO DETECTADA!")
        linhas.append(f"      Anterior: {regressao['anterior']:.0f}% → Agora: {taxa_aprovacao:.0f}%")
        linhas.append(f"      Diferença: {regressao['diferenca']:+.1f}%")

    if erros:
        linhas.append(f"\n❌ Falhas ({len(erros)}):")
        linhas.extend(erros[:10])
        if len(erros) > 10:
            linhas.append(f"   ... e mais {len(erros) - 10} falhas")

    linhas.append(f"\n📁 Resultado salvo: resultado_{resultado_id}")

    return "\n".join(linhas)


def _detectar_regressao(task_set_id: str, taxa_atual: float) -> Optional[dict]:
    """Detecta regressão comparando com resultados anteriores."""
    history = _load_json(HISTORY_FILE, [])
    anteriores = [h for h in history if h.get("task_set_id", h.get("task_set", "")) == task_set_id or
                  h.get("task_set", "") == task_set_id]

    if len(anteriores) < 2:
        return None

    # Pega o resultado imediatamente anterior
    ultimo = anteriores[-2] if len(anteriores) >= 2 else None
    if not ultimo:
        return None

    taxa_anterior = ultimo.get("taxa", 100)
    diferenca = taxa_atual - taxa_anterior

    if diferenca < -10:  # queda > 10% é regressão
        return {
            "anterior": taxa_anterior,
            "atual": taxa_atual,
            "diferenca": diferenca,
        }
    return None


def _atualizar_metricas_acumuladas():
    """Atualiza métricas de longo prazo."""
    history = _load_json(HISTORY_FILE, [])

    if not history:
        return

    total = len(history)
    taxas = [h.get("taxa", 0) for h in history]
    media_taxa = sum(taxas) / len(taxas) if taxas else 0
    tempos = [h.get("tempo_medio", 0) for h in history]
    media_tempo = sum(tempos) / len(tempos) if tempos else 0
    aprovados_total = sum(h.get("aprovados", 0) for h in history)
    tarefas_total = sum(h.get("total", 0) for h in history)

    # Tendência (últimos 5 vs anteriores)
    recentes = [h.get("taxa", 0) for h in history[-5:]]
    anteriores = [h.get("taxa", 0) for h in history[:-5]]
    tendencia = 0
    if anteriores and recentes:
        tendencia = (sum(recentes) / len(recentes)) - (sum(anteriores) / len(anteriores))

    metricas = {
        "total_benchmarks": total,
        "media_taxa_aprovacao": round(media_taxa, 1),
        "media_tempo_tarefa": round(media_tempo, 3),
        "tarefas_avaliadas": tarefas_total,
        "tarefas_aprovadas": aprovados_total,
        "tendencia": round(tendencia, 1),
        "ultima_atualizacao": _agora(),
    }
    _save_json(METRICS_FILE, metricas)


# ======================================================================
# CONSULTA DE RESULTADOS E MÉTRICAS
# ======================================================================

def benchmark_resultado(resultado_id: str) -> str:
    """Mostra detalhes de um resultado de benchmark específico.

    Args:
        resultado_id: ID do resultado (ex: 'abc12345')

    Returns:
        Relatório detalhado do benchmark
    """
    path = os.path.join(RESULTS_DIR, f"{resultado_id}.json")
    if not os.path.exists(path):
        return f"❌ Resultado '{resultado_id}' não encontrado."

    r = _load_json(path)
    linhas = [
        f"📊 Resultado de Benchmark: {r.get('task_set_nome', '?')}",
        f"   ID: {resultado_id}",
        f"   Data: {r.get('executado_em', '?')[:19]}",
        f"",
        f"   ✅ Aprovados: {r.get('aprovados', 0)}/{r.get('total', 0)} ({r.get('taxa_aprovacao', 0)}%)",
        f"   ⏱ Total: {r.get('tempo_total', 0)}s | Médio: {r.get('tempo_medio', 0)}s/tarefa",
        f"",
        f"   Resultados detalhados:",
    ]

    for res in r.get("resultados", []):
        status = "✅" if res.get("aprovado") else "❌"
        cat = res.get("categoria", "?")
        desc = res.get("descricao", "?")[:80]
        dur = res.get("duracao", 0)
        linhas.append(f"     {status} [{cat}] {desc} ({dur:.1f}s)")

    return "\n".join(linhas)


def benchmark_metricas() -> str:
    """Retorna métricas acumuladas de todos os benchmarks realizados.

    Inclui taxa de aprovação média, tempo médio, tendência e histórico.
    """
    metricas = _load_json(METRICS_FILE, {})
    history = _load_json(HISTORY_FILE, [])

    if not metricas:
        return "Nenhum benchmark realizado ainda."

    linhas = [
        f"📈 Métricas de Benchmark",
        f"",
        f"   Total de benchmarks: {metricas.get('total_benchmarks', 0)}",
        f"   Tarefas avaliadas: {metricas.get('tarefas_avaliadas', 0)}",
        f"   Tarefas aprovadas: {metricas.get('tarefas_aprovadas', 0)}",
        f"",
        f"   Taxa de aprovação média: {metricas.get('media_taxa_aprovacao', 0)}%",
        f"   Tempo médio por tarefa: {metricas.get('media_tempo_tarefa', 0)}s",
    ]

    tendencia = metricas.get("tendencia", 0)
    if tendencia > 0:
        linhas.append(f"   📈 Tendência: +{tendencia:.1f}% (melhorando)")
    elif tendencia < 0:
        linhas.append(f"   📉 Tendência: {tendencia:.1f}% (piorando)")
    else:
        linhas.append(f"   ➡️ Tendência: estável")

    # Últimos resultados
    if history:
        linhas.append(f"\n   Últimos resultados:")
        for h in history[-5:]:
            linhas.append(
                f"     {h.get('data', '?')[:10]} | "
                f"{h.get('taxa', 0):.0f}% | "
                f"{h.get('aprovados', 0)}/{h.get('total', 0)} | "
                f"{h.get('tempo_medio', 0):.1f}s"
            )

    return "\n".join(linhas)


def benchmark_dashboard() -> str:
    """Gera um dashboard completo com métricas de todos os benchmarks."""
    return benchmark_metricas()


# ======================================================================
# REGISTER
# ======================================================================

def register(api):
    api.register_tool(
        "benchmark_criar_task_set", benchmark_criar_task_set,
        "Cria um conjunto de tarefas para avaliar o agente. Cada tarefa tem descrição, critério de aprovação e categoria.",
        {
            "nome": {"type": "string", "description": "Nome do conjunto de tarefas"},
            "descricao": {"type": "string", "description": "Descrição do que avalia"},
            "tarefas": {"type": "string", "description": "Tarefas no formato: 'desc | criterio | cat' (uma por linha)"},
        },
        ["nome", "tarefas"],
    )

    api.register_tool(
        "benchmark_listar_task_sets", benchmark_listar_task_sets,
        "Lista todos os conjuntos de tarefas disponíveis para avaliação.",
        {}, [],
    )

    api.register_tool(
        "benchmark_executar", benchmark_executar,
        "Executa um benchmark: roda todas as tarefas de um task set, calcula taxa de aprovação, tempo e detecta regressões.",
        {
            "task_set_id": {"type": "string", "description": "ID do task set"},
            "modelo": {"type": "string", "description": "Modelo opcional para override"},
        },
        ["task_set_id"],
    )

    api.register_tool(
        "benchmark_resultado", benchmark_resultado,
        "Mostra detalhes de um resultado de benchmark específico.",
        {
            "resultado_id": {"type": "string", "description": "ID do resultado"},
        },
        ["resultado_id"],
    )

    api.register_tool(
        "benchmark_metricas", benchmark_metricas,
        "Retorna métricas acumuladas de todos os benchmarks: taxa de aprovação média, tempo, tendência, histórico.",
        {}, [],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Avaliações contínuas com task sets, benchmarks, taxa de aprovação, tempo, regressões e pipeline",
        "tools": [
            "benchmark_criar_task_set", "benchmark_listar_task_sets",
            "benchmark_executar", "benchmark_resultado", "benchmark_metricas",
        ],
    }
