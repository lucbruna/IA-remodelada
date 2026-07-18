"""
agente_dashboard.py
===================
Dashboard interativo (terminal) para monitorar e controlar o agente.
Usa Rich para interface colorida com gráficos ASCII, timeline, pizza e métricas.

REQUISITOS: pip install rich
USO: python agente_dashboard.py

MELHORIAS:
  - Grafico de pizza ASCII das ferramentas mais usadas
  - Timeline de atividade dos ultimos 7 dias
  - Categorias de ferramentas com breakdown visual
  - Metricas de sessao e taxa de sucesso
  - Layout compacto com 3 colunas
"""

import os
import sys
import time
import json
from datetime import datetime, date, timedelta
from collections import Counter, defaultdict

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_data")
TURBO_CACHE_DIR = os.path.join(DATA_DIR, "turbo_cache")
ANALYTICS_DIR = os.path.join(DATA_DIR, "analytics")
MEMORY_EVOL_DIR = os.path.join(DATA_DIR, "memoria_evolutiva")

# Cores para o grafico de pizza
PIE_COLORS = ["cyan", "green", "yellow", "magenta", "blue", "red", "bright_cyan", 
              "bright_green", "bright_yellow", "bright_magenta"]


def _load_json(path, default=None):
    if default is None:
        default = {} if path and path.endswith(".json") else []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _get_size_mb(path):
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path) / 1024 / 1024
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
    except Exception:
        pass
    return total / 1024 / 1024


def _gerar_pizza_ascii(tools_data, max_width=30):
    """Gera um grafico de pizza ASCII com barras coloridas horizontais.
    
    Cada fatia e representada por uma barra proporcional ao valor.
    Usa blocos Unicode para efeito visual.
    """
    if not tools_data:
        return Text("(sem dados)", style="dim")
    
    total = sum(v for _, v in tools_data)
    if total == 0:
        return Text("(sem uso)", style="dim")
    
    linhas = []
    for i, (name, count) in enumerate(tools_data[:8]):
        pct = count / total * 100
        bar_len = max(1, int(pct / 100 * max_width))
        cor = PIE_COLORS[i % len(PIE_COLORS)]
        
        # Barra com blocos Unicode
        bar = "█" * bar_len
        nome_curto = name[:18].ljust(18)
        
        linha = Text()
        linha.append(f" {nome_curto} ", style="dim")
        linha.append(bar, style=cor)
        linha.append(f" {count}x ({pct:.1f}%)", style=f"bold {cor}")
        linhas.append(linha)
    
    # Junta tudo
    resultado = Text()
    for l in linhas:
        resultado.append(l)
        resultado.append("\n")
    
    return resultado


def _gerar_timeline_ascii(diario, max_bars=7, max_width=25):
    """Gera um grafico de barras horizontal mostrando atividade dos ultimos N dias."""
    hoje = date.today()
    datas = [(hoje - timedelta(days=i)).isoformat() for i in range(max_bars - 1, -1, -1)]
    
    max_msgs = 1
    valores = []
    for d in datas:
        dados = diario.get(d, {})
        msgs = dados.get("mensagens", 0) + dados.get("tool_calls", 0)
        valores.append(msgs)
        max_msgs = max(max_msgs, msgs)
    
    resultado = Text()
    for d, val in zip(datas, valores):
        # Nome do dia
        data_obj = date.fromisoformat(d)
        hoje_str = "Hoje" if d == hoje.isoformat() else data_obj.strftime("%d/%m")
        bar_len = max(1, int(val / max_msgs * max_width)) if val > 0 else 0
        
        linha = Text()
        linha.append(f" {hoje_str:5} ", style="dim")
        
        if val > 0:
            # Barra com blocos
            bar = "▓" * bar_len
            # Determina cor baseada no nivel de atividade
            pct = val / max_msgs
            if pct > 0.7:
                cor = "bright_green"
            elif pct > 0.4:
                cor = "green"
            elif pct > 0.2:
                cor = "yellow"
            else:
                cor = "bright_blue"
            linha.append(bar, style=cor)
            linha.append(f" {val}", style=cor)
        else:
            linha.append("·" * 3, style="dim")
            linha.append(" 0", style="dim")
        
        resultado.append(linha)
        resultado.append("\n")
    
    return resultado


def _categorizar_ferramentas(tools_counter):
    """Agrupa ferramentas por categoria para breakdown visual."""
    categorias = {
        "Arquivos": [],
        "Sistema": [],
        "Web/Download": [],
        "Memoria": [],
        "Codigo": [],
        "Plugins/Outros": [],
    }
    
    cats_arquivos = {"create_folder", "write_file", "append_file", "read_file", 
                     "list_files", "search_files", "get_file_info", "move_file",
                     "copy_file", "delete_path", "search_and_replace", "grep_in_files",
                     "create_zip", "extract_zip", "file_diff", "extract_file"}
    
    cats_sistema = {"run_command", "get_system_info", "get_datetime", "calculate",
                    "process_list", "process_kill", "send_email",
                    "docker_run", "docker_ps", "docker_images",
                    "network_ping", "network_ports", "network_myip",
                    "task_schedule", "task_list", "task_remove",
                    "password_save", "password_get", "password_list",
                    "format_code", "qr_generate", "markdown_to_html",
                    "markdown_file_to_html", "session_save", "session_load",
                    "session_list"}
    
    cats_web = {"fetch_url", "web_search", "download_file", "git_clone", "pip_install",
                "install_plugin"}
    
    cats_memoria = {"remember", "recall", "forget", "list_memories",
                    "memoria_guardar", "memoria_buscar", "memoria_listar",
                    "memoria_esquecer", "memoria_estatisticas",
                    "perfil_mostrar", "perfil_aprender", "perfil_observar",
                    "grafo_adicionar", "grafo_visualizar", "grafo_listar",
                    "sumario_gerar", "sumario_mostrar",
                    "refletir", "aprender_com_erro", "erros_listar",
                    "processar_conversa", "memoria_contexto"}
    
    cats_codigo = {"run_python_code", "gerar_codigo", "sqlite_query",
                   "code_review", "task_decompose", "structured_reasoning",
                   "smart_extract", "turbo_diagnostico", "turbo_cache_clear",
                   "subagente_codigo", "subagente_analise", "subagente_criativo"}
    
    for name, count in tools_counter.items():
        if name in cats_arquivos:
            categorias["Arquivos"].append((name, count))
        elif name in cats_sistema:
            categorias["Sistema"].append((name, count))
        elif name in cats_web:
            categorias["Web/Download"].append((name, count))
        elif name in cats_memoria:
            categorias["Memoria"].append((name, count))
        elif name in cats_codigo:
            categorias["Codigo"].append((name, count))
        else:
            categorias["Plugins/Outros"].append((name, count))
    
    return categorias


def _coletar_metricas():
    metrics = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "data": datetime.now().strftime("%d/%m/%Y"),
    }
    
    # --- Memoria de fatos ---
    fatos_file = os.path.join(MEMORY_EVOL_DIR, "fatos_semanticos.json")
    fatos = _load_json(fatos_file, [])
    metrics["fatos_count"] = len(fatos)
    metrics["fatos_size_mb"] = _get_size_mb(fatos_file)
    
    # --- Perfil ---
    perfil_file = os.path.join(MEMORY_EVOL_DIR, "perfil_usuario.json")
    perfil = _load_json(perfil_file, {})
    metrics["interacoes"] = perfil.get("total_interacoes", 0)
    metrics["projetos"] = len(perfil.get("projetos", []))
    metrics["interesses"] = len(perfil.get("interesses", []))
    metrics["estilo"] = perfil.get("estilo_comunicacao", "neutro")
    metrics["lingua"] = perfil.get("lingua_preferida", "pt-br")
    
    # --- Grafo ---
    grafo_file = os.path.join(MEMORY_EVOL_DIR, "grafo_conhecimento.json")
    grafo = _load_json(grafo_file, {"nos": {}, "arestas": []})
    metrics["grafo_nos"] = len(grafo.get("nos", {}))
    metrics["grafo_arestas"] = len(grafo.get("arestas", []))
    
    # --- Cache turbo ---
    cache_count = 0
    cache_size = 0
    if os.path.isdir(TURBO_CACHE_DIR):
        for f in os.listdir(TURBO_CACHE_DIR):
            if f.endswith(".json"):
                cache_count += 1
                try:
                    cache_size += os.path.getsize(os.path.join(TURBO_CACHE_DIR, f))
                except Exception:
                    pass
    metrics["cache_count"] = cache_count
    metrics["cache_size_mb"] = cache_size / 1024 / 1024
    
    # --- Analytics ---
    eventos_file = os.path.join(ANALYTICS_DIR, "eventos.json")
    diario_file = os.path.join(ANALYTICS_DIR, "diario.json")
    
    eventos = _load_json(eventos_file, [])
    diario = _load_json(diario_file, {})
    metrics["diario"] = diario
    
    metrics["eventos_total"] = len(eventos)
    
    tool_calls = sum(1 for e in eventos if isinstance(e, dict) and e.get("evento") == "tool_call")
    erros = sum(1 for e in eventos if isinstance(e, dict) and e.get("evento") == "error")
    mensagens = sum(1 for e in eventos if isinstance(e, dict) and e.get("evento") == "message")
    
    metrics["tool_calls"] = tool_calls
    metrics["erros"] = erros
    metrics["mensagens"] = mensagens
    
    # Taxa de sucesso
    metrics["sucesso"] = (tool_calls - erros) / max(tool_calls, 1) * 100 if tool_calls > 0 else 100.0
    
    # Top ferramentas
    tools_counter = Counter()
    for e in eventos:
        if isinstance(e, dict) and e.get("evento") == "tool_call":
            name = e.get("dados", {}).get("ferramenta", "?")
            tools_counter[name] += 1
    metrics["top_tools"] = tools_counter.most_common(15)
    metrics["tools_counter"] = tools_counter
    
    # Categorias
    metrics["categorias"] = _categorizar_ferramentas(tools_counter)
    
    # Primeiro e ultimo evento (para tempo de sessao)
    if eventos:
        metrics["primeiro_evento"] = eventos[0].get("ts", time.time())
        metrics["ultimo_evento"] = eventos[-1].get("ts", time.time())
        metrics["sessao_horas"] = (metrics["ultimo_evento"] - metrics["primeiro_evento"]) / 3600
        metrics["msgs_por_hora"] = mensagens / max(metrics["sessao_horas"], 0.01)
    else:
        metrics["sessao_horas"] = 0
        metrics["msgs_por_hora"] = 0
    
    # Conversas
    conversas = [f for f in os.listdir(DATA_DIR) if f.startswith("conversa_") and f.endswith(".md")]
    metrics["conversas_count"] = len(conversas)
    
    # Historico
    history = _load_json(os.path.join(DATA_DIR, "historico.json"), [])
    metrics["historico_msgs"] = len(history)
    
    return metrics


def _render_dashboard():
    m = _coletar_metricas()
    
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    
    # 3 colunas no body
    layout["body"].split_row(
        Layout(name="col_esq"),
        Layout(name="col_centro"),
        Layout(name="col_dir"),
    )
    
    # Coluna esquerda: Memoria + Grafo
    layout["body"]["col_esq"].split(
        Layout(name="memoria"),
        Layout(name="grafo"),
        Layout(name="perfil"),
    )
    
    # Coluna centro: Analytics + Timeline + Cache
    layout["body"]["col_centro"].split(
        Layout(name="analytics"),
        Layout(name="timeline"),
        Layout(name="cache"),
    )
    
    # Coluna direita: Pizza + Categorias
    layout["body"]["col_dir"].split(
        Layout(name="pizza"),
        Layout(name="categorias"),
    )
    
    # ==================== HEADER ====================
    header_text = Text()
    header_text.append("🚀  AGENTE LOCAL ", style="bold cyan")
    header_text.append("DASHBOARD", style="bold bright_cyan")
    header_text.append(f"  │  {m['data']} ", style="yellow")
    header_text.append(f"{m['timestamp']}", style="bright_yellow")
    
    sessao_h = int(m['sessao_horas'])
    sessao_m = int((m['sessao_horas'] - sessao_h) * 60)
    if sessao_h > 0 or sessao_m > 0:
        header_text.append(f"  │  ⏱ {sessao_h}h{sessao_m}m", style="green")
    
    layout["header"].update(Panel(header_text, style="blue", box=box.ROUNDED))
    
    # ==================== MEMORIA ====================
    mem_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    mem_table.add_column("Metrica", style="cyan", width=16)
    mem_table.add_column("Valor", style="green", justify="right")
    
    mem_table.add_row("🧠 Fatos", str(m["fatos_count"]))
    mem_table.add_row("💬 Interacoes", str(m["interacoes"]))
    mem_table.add_row("📁 Projetos", str(m["projetos"]))
    mem_table.add_row("🎯 Interesses", str(m["interesses"]))
    
    # Barra visual de memoria
    if m["fatos_count"] > 0:
        bar = "█" * min(m["fatos_count"] // 5 + 1, 20)
        mem_table.add_row("", f"[green]{bar}[/green]")
    
    layout["memoria"].update(Panel(mem_table, title="🧠 Memoria Evolutiva", 
                                    border_style="magenta", box=box.ROUNDED))
    
    # ==================== GRAFO ====================
    grafo_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    grafo_table.add_column("Metrica", style="cyan", width=16)
    grafo_table.add_column("Valor", style="green", justify="right")
    
    grafo_table.add_row("🔗 Nos no grafo", str(m["grafo_nos"]))
    grafo_table.add_row("🔗 Arestas", str(m["grafo_arestas"]))
    grafo_table.add_row("💾 Em disco", f"{m['fatos_size_mb']:.2f} MB")
    
    layout["grafo"].update(Panel(grafo_table, title="🔗 Grafo Conhecimento",
                                  border_style="bright_magenta", box=box.ROUNDED))
    
    # ==================== PERFIL ====================
    perfil_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    perfil_table.add_column("Metrica", style="cyan", width=16)
    perfil_table.add_column("Valor", style="green")
    
    estilo_emoji = {"educado": "😊", "direto": "🎯", "neutro": "😐"}
    emoji = estilo_emoji.get(m["estilo"], "😐")
    perfil_table.add_row("🎭 Estilo", f"{emoji} {m['estilo'].title()}")
    
    lingua_nome = {"pt-br": "🇧🇷 Portugues", "en": "🇺🇸 Ingles"}
    lingua = lingua_nome.get(m["lingua"], m["lingua"])
    perfil_table.add_row("🌐 Lingua", lingua)
    
    layout["perfil"].update(Panel(perfil_table, title="👤 Perfil Usuario",
                                   border_style="bright_blue", box=box.ROUNDED))
    
    # ==================== ANALYTICS ====================
    ana_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    ana_table.add_column("Metrica", style="cyan", width=18)
    ana_table.add_column("Valor", style="green", justify="right")
    
    ana_table.add_row("📊 Eventos totais", str(m["eventos_total"]))
    ana_table.add_row("⚙ Tool calls", str(m["tool_calls"]))
    ana_table.add_row("💬 Mensagens", str(m["mensagens"]))
    ana_table.add_row("📝 Conversas exportadas", str(m["conversas_count"]))
    
    # Taxa de sucesso com cor
    sucesso = m["sucesso"]
    sucesso_cor = "bright_green" if sucesso >= 95 else ("yellow" if sucesso >= 80 else "red")
    ana_table.add_row("✅ Taxa de sucesso", f"[{sucesso_cor}]{sucesso:.1f}%[/{sucesso_cor}]")
    
    # Msgs por hora
    msgs_h = m["msgs_por_hora"]
    ana_table.add_row("📈 Msgs/hora", f"{msgs_h:.1f}")
    
    # Erros
    erros = m["erros"]
    erros_cor = "green" if erros == 0 else ("yellow" if erros < 5 else "red")
    ana_table.add_row(f"❌ Erros", f"[{erros_cor}]{erros}[/{erros_cor}]")
    
    layout["analytics"].update(Panel(ana_table, title="📊 Analytics",
                                      border_style="green", box=box.ROUNDED))
    
    # ==================== TIMELINE ====================
    if m["diario"]:
        timeline = _gerar_timeline_ascii(m["diario"])
        timeline_panel = Panel(timeline, title="📅 Ultimos 7 Dias",
                                border_style="bright_yellow", box=box.ROUNDED)
    else:
        timeline_panel = Panel(Text("Sem dados de atividade diaria ainda.\nUse o agente para gerar metricas!", 
                                     style="dim"), 
                                title="📅 Ultimos 7 Dias",
                                border_style="bright_yellow", box=box.ROUNDED)
    layout["timeline"].update(timeline_panel)
    
    # ==================== CACHE ====================
    cache_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    cache_table.add_column("Metrica", style="cyan", width=18)
    cache_table.add_column("Valor", style="green", justify="right")
    
    cache_table.add_row("📦 Arquivos em cache", str(m["cache_count"]))
    if m["cache_size_mb"] > 0:
        cache_table.add_row("💾 Tamanho", f"{m['cache_size_mb']:.2f} MB")
        bar = "█" * min(int(m["cache_size_mb"] * 5), 20)
        cache_table.add_row("", f"[yellow]{bar}[/yellow]")
    else:
        cache_table.add_row("💾 Tamanho", "0 MB")
    
    layout["cache"].update(Panel(cache_table, title="📦 Cache Turbo",
                                  border_style="yellow", box=box.ROUNDED))
    
    # ==================== PIZZA (grafico de ferramentas) ====================
    if m["top_tools"]:
        pizza = _gerar_pizza_ascii(m["top_tools"])
        pizza_panel = Panel(pizza, title="🔧 Top Ferramentas",
                             border_style="cyan", box=box.ROUNDED)
    else:
        pizza_panel = Panel(Text("Nenhuma ferramenta usada ainda.\nInteraja com o agente para ver dados!", 
                                  style="dim"),
                             title="🔧 Top Ferramentas",
                             border_style="cyan", box=box.ROUNDED)
    layout["pizza"].update(pizza_panel)
    
    # ==================== CATEGORIAS ====================
    cat_lines = []
    categorias = m["categorias"]
    total_geral = sum(sum(c for _, c in tools) for cat, tools in categorias.items() if tools)
    
    cat_cores = {
        "Arquivos": "cyan",
        "Sistema": "green", 
        "Web/Download": "yellow",
        "Memoria": "magenta",
        "Codigo": "blue",
        "Plugins/Outros": "bright_black",
    }
    
    for cat_name in ["Arquivos", "Sistema", "Web/Download", "Memoria", "Codigo", "Plugins/Outros"]:
        tools = categorias.get(cat_name, [])
        if not tools:
            continue
        
        cat_total = sum(c for _, c in tools)
        pct = cat_total / max(total_geral, 1) * 100
        cor = cat_cores.get(cat_name, "white")
        
        # Barra de categoria
        bar_len = max(1, int(pct / 100 * 20))
        bar = "▓" * bar_len
        
        linha = Text()
        linha.append(f" {cat_name:15} ", style=f"bold {cor}")
        linha.append(bar, style=cor)
        linha.append(f" {cat_total}x ({pct:.0f}%)", style=f"dim {cor}")
        cat_lines.append(linha)
        
        # Sub-itens (ate 3)
        for name, count in sorted(tools, key=lambda x: x[1], reverse=True)[:3]:
            sub_bar = "▌" * min(count, 15)
            linha_sub = Text()
            linha_sub.append(f"  {name:22} ", style="dim")
            linha_sub.append(sub_bar, style=f"dim {cor}")
            linha_sub.append(f" {count}x", style="dim")
            cat_lines.append(linha_sub)
    
    if cat_lines:
        cat_text = Text()
        for l in cat_lines:
            cat_text.append(l)
            cat_text.append("\n")
        cat_panel = Panel(cat_text, title="📂 Categorias Ferramentas",
                           border_style="green", box=box.ROUNDED)
    else:
        cat_panel = Panel(Text("(sem dados)", style="dim"),
                           title="📂 Categorias Ferramentas",
                           border_style="green", box=box.ROUNDED)
    layout["categorias"].update(cat_panel)
    
    # ==================== FOOTER ====================
    footer_parts = []
    
    # Indicador de saude geral
    if m["erros"] == 0:
        footer_parts.append("🟢 Saudavel")
    elif m["erros"] < 5:
        footer_parts.append("🟡 Atencao")
    else:
        footer_parts.append("🔴 Crítico")
    
    footer_parts.append(f"🧠 {m['fatos_count']} fatos")
    footer_parts.append(f"🔗 {m['grafo_nos']} nos no grafo")
    footer_parts.append(f"⚙ {m['tool_calls']} tools")
    
    if m["fatos_count"] > 0 or m["tool_calls"] > 0:
        footer_parts.append(f"✅ {m['sucesso']:.0f}% sucesso")
    
    if m["sessao_horas"] > 0:
        footer_parts.append(f"⏱ {sessao_h}h{sessao_m}m sessao")
    
    footer_info = "  │  ".join(footer_parts)
    layout["footer"].update(Panel(footer_info, style="dim", box=box.ROUNDED))
    
    return layout


def run_dashboard():
    if not RICH_AVAILABLE:
        print("=" * 50)
        print("  AGENTE LOCAL DASHBOARD")
        print("=" * 50)
        print()
        print("Para a versão com gráficos e painéis, instale Rich:")
        print("  pip install rich")
        print()
        print("Versão texto simples:")
        print("-" * 30)
        while True:
            m = _coletar_metricas()
            os.system("cls" if os.name == "nt" else "clear")
            print(f"🚀 AGENTE LOCAL DASHBOARD  |  {m['data']} {m['timestamp']}")
            print("=" * 50)
            print(f"\n🧠 MEMORIA:")
            print(f"  Fatos: {m['fatos_count']}  |  Interacoes: {m['interacoes']}")
            print(f"  Grafo: {m['grafo_nos']} nos, {m['grafo_arestas']} arestas")
            print(f"\n📊 ANALYTICS:")
            print(f"  Tool calls: {m['tool_calls']}  |  Erros: {m['erros']}  |  Sucesso: {m['sucesso']:.1f}%")
            print(f"  Msgs: {m['mensagens']}  |  Sessao: {m['sessao_horas']:.1f}h")
            print(f"\n🔧 Top ferramentas:")
            for i, (name, cnt) in enumerate(m["top_tools"][:5], 1):
                bar = "█" * min(cnt, 20)
                print(f"  {i}. {name:20} {bar} {cnt}x")
            print(f"\n📂 Categorias:")
            for cat, tools in m["categorias"].items():
                if tools:
                    total = sum(c for _, c in tools)
                    print(f"  {cat}: {total}x")
            print(f"\nPressione Ctrl+C para sair. Atualizando em 5s...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                print("\nDashboard encerrado.")
                break
        return

    console = Console()
    console.print("[bold cyan]🚀 Iniciando Dashboard do Agente Local...[/bold cyan]")
    console.print("[dim]Pressione Ctrl+C para encerrar | Atualiza a cada 3s[/dim]")
    time.sleep(1)

    try:
        with Live(_render_dashboard(), refresh_per_second=2, screen=True) as live:
            while True:
                time.sleep(3)
                live.update(_render_dashboard())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Dashboard encerrado.[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Erro: {e}[/bold red]")


if __name__ == "__main__":
    run_dashboard()
