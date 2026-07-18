"""
plugin_analytics.py
====================
Plugin de Analytics e Estatísticas do Agente.
Rastreia conversas, ferramentas usadas, tempo de resposta e gera relatórios.

Armazena dados em agente_data/analytics/ para acompanhamento histórico.
"""

import json
import os
import time
import logging
from datetime import datetime, date
from collections import defaultdict, Counter

__version__ = "1.0.0"
PLUGIN_NAME = "Analytics e Estatísticas"

# ─── Config ─────────────────────────────────────────────────────────
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agente_data", "analytics"
)
EVENTS_FILE = os.path.join(DATA_DIR, "eventos.json")
STATS_FILE = os.path.join(DATA_DIR, "estatisticas.json")
DAILY_FILE = os.path.join(DATA_DIR, "diario.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path, default=None):
    if default is None:
        default = {} if path.endswith(".json") else []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning("Erro lendo %s: %s", path, e)
    return default


def _save_json(path, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _hoje():
    return date.today().isoformat()


# ─── Rastreamento ───────────────────────────────────────────────────

def _rastrear(evento: str, dados: dict = None):
    """Registra um evento no histórico de analytics."""
    eventos = _load_json(EVENTS_FILE, [])
    eventos.append({
        "ts": time.time(),
        "data": _hoje(),
        "evento": evento,
        "dados": dados or {},
    })
    # Mantém últimos 10k eventos
    if len(eventos) > 10000:
        eventos = eventos[-10000:]
    _save_json(EVENTS_FILE, eventos)


def _atualizar_diario():
    """Atualiza o resumo diário."""
    diario = _load_json(DAILY_FILE, {})
    hoje = _hoje()
    if hoje not in diario:
        diario[hoje] = {
            "mensagens": 0,
            "tool_calls": 0,
            "usuarios": 0,
            "agentes": 0,
            "erros": 0,
            "ferramentas": Counter(),
        }
    return diario


def track_tool_call(nome_ferramenta: str, sucesso: bool = True, duracao_ms: float = 0):
    """Rastreia uma chamada de ferramenta (chamado pelo agente_core)."""
    _rastrear("tool_call", {
        "ferramenta": nome_ferramenta,
        "sucesso": sucesso,
        "duracao_ms": round(duracao_ms, 1),
    })
    diario = _atualizar_diario()
    diario[_hoje()]["tool_calls"] += 1
    diario[_hoje()]["ferramentas"][nome_ferramenta] += 1
    _save_json(DAILY_FILE, diario)


def track_message(tipo: str, tamanho: int):
    """Rastreia uma mensagem (user/assistant/tool)."""
    _rastrear("message", {"tipo": tipo, "tamanho": tamanho})
    diario = _atualizar_diario()
    hoje = _hoje()
    diario[hoje]["mensagens"] += 1
    if tipo == "user":
        diario[hoje]["usuarios"] += 1
    elif tipo == "assistant":
        diario[hoje]["agentes"] += 1
    _save_json(DAILY_FILE, diario)


def track_error(origem: str, erro: str):
    """Rastreia um erro."""
    _rastrear("error", {"origem": origem, "erro": str(erro)[:200]})
    diario = _atualizar_diario()
    diario[_hoje()]["erros"] += 1
    _save_json(DAILY_FILE, diario)


# ─── Relatórios ─────────────────────────────────────────────────────

def relatorio_hoje() -> str:
    """Gera relatório de atividade do dia atual."""
    diario = _load_json(DAILY_FILE, {})
    hoje = _hoje()
    dados = diario.get(hoje, {})
    
    if not dados or dados.get("mensagens", 0) == 0:
        return f"📊 Nenhuma atividade registrada hoje ({hoje})."
    
    ferramentas = dados.get("ferramentas", {})
    top_tools = sorted(ferramentas.items(), key=lambda x: x[1], reverse=True)
    
    linhas = [
        f"📊 === Relatório Diário: {hoje} ===",
        f"  📝 Mensagens:      {dados.get('mensagens', 0)}",
        f"  👤 Usuário:        {dados.get('usuarios', 0)}",
        f"  🤖 Agente:         {dados.get('agentes', 0)}",
        f"  ⚙ Tool calls:     {dados.get('tool_calls', 0)}",
        f"  ❌ Erros:          {dados.get('erros', 0)}\n",
    ]
    
    if top_tools:
        linhas.append("  🔧 Ferramentas mais usadas hoje:")
        for nome, qtd in top_tools[:10]:
            linhas.append(f"    • {nome}: {qtd}x")
    
    return "\n".join(linhas)


def relatorio_semanal() -> str:
    """Gera relatório da última semana."""
    diario = _load_json(DAILY_FILE, {})
    
    from datetime import timedelta
    hoje = date.today()
    uma_semana = (hoje - timedelta(days=7)).isoformat()
    
    datas = sorted(d for d in diario.keys() if d >= uma_semana)
    
    if not datas:
        return "📊 Nenhum dado disponível para a última semana."
    
    total_msgs = 0
    total_tools = 0
    total_erros = 0
    todas_ferramentas = Counter()
    
    for d in datas:
        dados = diario[d]
        total_msgs += dados.get("mensagens", 0)
        total_tools += dados.get("tool_calls", 0)
        total_erros += dados.get("erros", 0)
        todas_ferramentas.update(dados.get("ferramentas", {}))
    
    media_diaria = total_msgs / len(datas) if datas else 0
    top_tools = todas_ferramentas.most_common(10)
    
    linhas = [
        f"📊 === Relatório Semanal ({datas[0]} a {datas[-1]}) ===",
        f"  📝 Total mensagens:    {total_msgs}",
        f"  📊 Média diária:       {media_diaria:.1f}",
        f"  ⚙ Total tool calls:   {total_tools}",
        f"  ❌ Total erros:        {total_erros}",
        f"  📅 Dias com atividade: {len(datas)}\n",
    ]
    
    # Atividade por dia
    linhas.append("  📆 Atividade diária:")
    for d in datas:
        dados = diario[d]
        barra = "█" * min(dados.get("mensagens", 0), 40)
        linhas.append(f"    {d}: {barra} ({dados.get('mensagens',0)} msgs)")
    
    if top_tools:
        linhas.append("\n  🔧 Top ferramentas da semana:")
        for nome, qtd in top_tools:
            barra = "▓" * min(qtd, 30)
            linhas.append(f"    {barra} {nome} ({qtd}x)")
    
    return "\n".join(linhas)


def relatorio_geral() -> str:
    """Gera relatório completo de todas as estatísticas."""
    eventos = _load_json(EVENTS_FILE, [])
    diario = _load_json(DAILY_FILE, {})
    
    if not eventos:
        return "📊 Nenhum dado de analytics disponível ainda."
    
    total_eventos = len(eventos)
    total_ferramentas = sum(1 for e in eventos if e["evento"] == "tool_call")
    total_erros = sum(1 for e in eventos if e["evento"] == "error")
    total_mensagens = sum(1 for e in eventos if e["evento"] == "message")
    
    # Tool calls por ferramenta
    tools_counter = Counter()
    for e in eventos:
        if e["evento"] == "tool_call":
            nome = e["dados"].get("ferramenta", "?")
            tools_counter[nome] += 1
    
    # Primeiro e último evento
    primeiro = datetime.fromtimestamp(eventos[0]["ts"]).strftime("%d/%m/%Y")
    ultimo = datetime.fromtimestamp(eventos[-1]["ts"]).strftime("%d/%m/%Y")
    
    linhas = [
        f"📊 === Relatório Geral do Agente ===",
        f"  Período: {primeiro} a {ultimo}",
        f"  📝 Total eventos:      {total_eventos}",
        f"  💬 Total mensagens:    {total_mensagens}",
        f"  ⚙ Total tool calls:   {total_ferramentas}",
        f"  ❌ Total erros:        {total_erros}",
        f"  📅 Dias com atividade: {len(diario)}\n",
    ]
    
    # Top ferramentas
    top_tools = tools_counter.most_common(15)
    if top_tools:
        linhas.append("  🔧 Top 15 ferramentas (geral):")
        for nome, qtd in top_tools:
            pct = qtd / total_ferramentas * 100 if total_ferramentas else 0
            barra = "▓" * min(int(pct / 2), 30)
            linhas.append(f"    {barra} {nome} ({qtd}x, {pct:.1f}%)")
    
    # Dias mais ativos
    dias_ordenados = sorted(
        diario.items(),
        key=lambda x: x[1].get("mensagens", 0),
        reverse=True,
    )[:5]
    
    if dias_ordenados:
        linhas.append("\n  📆 Dias mais ativos:")
        for d, dados in dias_ordenados:
            linhas.append(f"    {d}: {dados.get('mensagens',0)} msgs, {dados.get('tool_calls',0)} tools")
    
    return "\n".join(linhas)


def limpar_dados(dias_manter: int = 90) -> str:
    """Limpa dados de analytics mais antigos que N dias."""
    eventos = _load_json(EVENTS_FILE, [])
    diario = _load_json(DAILY_FILE, {})
    
    if not eventos:
        return "📊 Nenhum dado para limpar."
    
    corte = time.time() - (dias_manter * 86400)
    antes = len(eventos)
    eventos = [e for e in eventos if e["ts"] >= corte]
    depois = len(eventos)
    
    _save_json(EVENTS_FILE, eventos)
    
    # Limpa diário antigo
    from datetime import timedelta
    hoje = date.today()
    corte_data = (hoje - timedelta(days=dias_manter)).isoformat()
    diario_filtrado = {k: v for k, v in diario.items() if k >= corte_data}
    _save_json(DAILY_FILE, diario_filtrado)
    
    return f"📊 Limpos {antes - depois} eventos antigos (> {dias_manter} dias). Restam {depois}."


# ─── Register ───────────────────────────────────────────────────────

def register(api):
    api.register_tool(
        name="relatorio_diario",
        func=relatorio_hoje,
        description=(
            "Gera um relatório da atividade do agente HOJE: quantas mensagens, "
            "tool calls, erros e as ferramentas mais usadas no dia."
        ),
        parameters={},
        required=[],
    )

    api.register_tool(
        name="relatorio_semanal",
        func=relatorio_semanal,
        description=(
            "Gera um relatório da ÚLTIMA SEMANA de atividade do agente, "
            "incluindo gráficos de barras de atividade diária e ferramentas mais usadas."
        ),
        parameters={},
        required=[],
    )

    api.register_tool(
        name="relatorio_geral",
        func=relatorio_geral,
        description=(
            "Gera um relatório COMPLETO de toda a atividade do agente desde o início: "
            "totais, top ferramentas, dias mais ativos, etc."
        ),
        parameters={},
        required=[],
    )

    api.register_tool(
        name="analytics_limpar",
        func=limpar_dados,
        description=(
            "Limpa dados antigos de analytics para liberar espaço. "
            "Mantém apenas os últimos N dias de dados."
        ),
        parameters={
            "dias_manter": {
                "type": "integer",
                "description": "Quantidade de dias de dados para manter (padrão: 90)"
            },
        },
        required=[],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Analytics completo: rastreia uso, gera relatórios diários/semanais/gerais com gráficos",
        "tools": ["relatorio_diario", "relatorio_semanal", "relatorio_geral", "analytics_limpar"],
    }
