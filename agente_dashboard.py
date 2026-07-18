"""
agente_dashboard.py
===================
Dashboard interativo (terminal) para monitorar e controlar o agente.
Usa Rich para interface colorida com painéis, gráficos e métricas em tempo real.

REQUISITOS: pip install rich
USO: python agente_dashboard.py
"""

import os
import sys
import time
import json
import threading
from datetime import datetime
from collections import Counter, defaultdict

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_data")
TURBO_CACHE_DIR = os.path.join(DATA_DIR, "turbo_cache")
ANALYTICS_DIR = os.path.join(DATA_DIR, "analytics")
MEMORY_EVOL_DIR = os.path.join(DATA_DIR, "memoria_evolutiva")


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


def _coletar_metricas():
    metrics = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "data": datetime.now().strftime("%d/%m/%Y"),
    }

    # Memoria de fatos
    fatos_file = os.path.join(MEMORY_EVOL_DIR, "fatos_semanticos.json")
    fatos = _load_json(fatos_file, [])
    metrics["fatos_count"] = len(fatos)
    metrics["fatos_size_mb"] = _get_size_mb(fatos_file)

    # Perfil
    perfil_file = os.path.join(MEMORY_EVOL_DIR, "perfil_usuario.json")
    perfil = _load_json(perfil_file, {})
    metrics["interacoes"] = perfil.get("total_interacoes", 0)
    metrics["projetos"] = len(perfil.get("projetos", []))
    metrics["interesses"] = len(perfil.get("interesses", []))

    # Grafo
    grafo_file = os.path.join(MEMORY_EVOL_DIR, "grafo_conhecimento.json")
    grafo = _load_json(grafo_file, {"nos": {}, "arestas": []})
    metrics["grafo_nos"] = len(grafo.get("nos", {}))
    metrics["grafo_arestas"] = len(grafo.get("arestas", []))

    # Cache turbo
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

    # Analytics
    eventos_file = os.path.join(ANALYTICS_DIR, "eventos.json")
    eventos = _load_json(eventos_file, [])
    metrics["eventos_total"] = len(eventos)

    tool_calls = sum(1 for e in eventos if isinstance(e, dict) and e.get("evento") == "tool_call")
    erros = sum(1 for e in eventos if isinstance(e, dict) and e.get("evento") == "error")
    metrics["tool_calls"] = tool_calls
    metrics["erros"] = erros

    # Top ferramentas
    tools_counter = Counter()
    for e in eventos:
        if isinstance(e, dict) and e.get("evento") == "tool_call":
            name = e.get("dados", {}).get("ferramenta", "?")
            tools_counter[name] += 1
    metrics["top_tools"] = tools_counter.most_common(10)

    # Conversas
    conversas = [f for f in os.listdir(DATA_DIR) if f.startswith("conversa_") and f.endswith(".md")]
    metrics["conversas_count"] = len(conversas)

    # Histórico
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
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["body"]["left"].split(
        Layout(name="memoria"),
        Layout(name="cache"),
    )
    layout["body"]["right"].split(
        Layout(name="analytics"),
        Layout(name="tools"),
    )

    # Header
    header_text = Text(f"🚀 AGENTE LOCAL DASHBOARD", style="bold cyan")
    header_text.append(f"  |  {m['data']} {m['timestamp']}", style="yellow")
    layout["header"].update(Panel(header_text, style="blue"))

    # Memoria
    mem_table = Table(box=box.SIMPLE)
    mem_table.add_column("Metrica", style="cyan")
    mem_table.add_column("Valor", style="green")
    mem_table.add_row("Fatos semanticos", str(m["fatos_count"]))
    mem_table.add_row("Interacoes", str(m["interacoes"]))
    mem_table.add_row("Projetos", str(m["projetos"]))
    mem_table.add_row("Interesses", str(m["interesses"]))
    mem_table.add_row("Grafo nos", str(m["grafo_nos"]))
    mem_table.add_row("Grafo arestas", str(m["grafo_arestas"]))
    mem_table.add_row("Fatos em disco", f"{m['fatos_size_mb']:.2f} MB")
    layout["memoria"].update(Panel(mem_table, title="🧠 Memoria", border_style="magenta"))

    # Cache
    cache_table = Table(box=box.SIMPLE)
    cache_table.add_column("Metrica", style="cyan")
    cache_table.add_column("Valor", style="green")
    cache_table.add_row("Arquivos em cache", str(m["cache_count"]))
    cache_table.add_row("Tamanho do cache", f"{m['cache_size_mb']:.2f} MB")
    layout["cache"].update(Panel(cache_table, title="📦 Cache Turbo", border_style="yellow"))

    # Analytics
    ana_table = Table(box=box.SIMPLE)
    ana_table.add_column("Metrica", style="cyan")
    ana_table.add_column("Valor", style="green")
    ana_table.add_row("Eventos totais", str(m["eventos_total"]))
    ana_table.add_row("Tool calls", str(m["tool_calls"]))
    ana_table.add_row("Erros", str(m["erros"]))
    ana_table.add_row("Conversas exportadas", str(m["conversas_count"]))
    ana_table.add_row("Historico mensagens", str(m["historico_msgs"]))
    if m["erros"] > 0:
        ratio = m["erros"] / max(m["tool_calls"], 1) * 100
        ana_table.add_row("Taxa de erro", f"{ratio:.1f}%", style="red" if ratio > 10 else "green")
    layout["analytics"].update(Panel(ana_table, title="📊 Analytics", border_style="green"))

    # Top Tools
    tools_table = Table(box=box.SIMPLE)
    tools_table.add_column("#", style="dim", width=3)
    tools_table.add_column("Ferramenta", style="cyan")
    tools_table.add_column("Chamadas", style="yellow", justify="right")
    for i, (name, count) in enumerate(m["top_tools"], 1):
        bar = "▌" * min(count, 30)
        tools_table.add_row(str(i), name, f"{count} {bar}")
    if not m["top_tools"]:
        tools_table.add_row("", "Nenhuma ferramenta usada ainda", "")
    layout["tools"].update(Panel(tools_table, title="🔧 Top Ferramentas", border_style="blue"))

    # Footer
    footer_info = (
        f"Memoria: {m['fatos_count']} fatos  |  "
        f"Grafo: {m['grafo_nos']} nos  |  "
        f"Cache: {m['cache_count']} arquivos ({m['cache_size_mb']:.2f} MB)  |  "
        f"Tool calls: {m['tool_calls']}"
    )
    layout["footer"].update(Panel(footer_info, style="dim"))

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
        # Versão fallback sem Rich
        while True:
            m = _coletar_metricas()
            os.system("cls" if os.name == "nt" else "clear")
            print(f"🚀 AGENTE LOCAL DASHBOARD  |  {m['data']} {m['timestamp']}")
            print("=" * 50)
            print(f"\n🧠 MEMORIA:")
            print(f"  Fatos semanticos: {m['fatos_count']}")
            print(f"  Interacoes: {m['interacoes']}")
            print(f"  Grafo: {m['grafo_nos']} nos, {m['grafo_arestas']} arestas")
            print(f"\n📦 CACHE:")
            print(f"  Arquivos: {m['cache_count']} ({m['cache_size_mb']:.2f} MB)")
            print(f"\n📊 ANALYTICS:")
            print(f"  Tool calls: {m['tool_calls']}  |  Erros: {m['erros']}")
            print(f"  Top ferramentas:")
            for i, (name, cnt) in enumerate(m["top_tools"][:5], 1):
                print(f"    {i}. {name}: {cnt}x")
            print(f"\nPressione Ctrl+C para sair. Atualizando em 5s...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                print("\nDashboard encerrado.")
                break
        return

    console = Console()
    console.print("[bold cyan]🚀 Iniciando Dashboard do Agente Local...[/bold cyan]")
    console.print("[dim]Pressione Ctrl+C para encerrar[/dim]")
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
