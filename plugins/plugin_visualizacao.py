"""
plugin_visualizacao.py
=======================
Geracao de graficos e visualizacoes de dados: linhas, barras, pizza,
histograma, dispersao, e exportacao para PNG/SVG/HTML.
"""

import os
import json
import math
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Visualizacao de Dados"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data", "graficos")
os.makedirs(DATA_DIR, exist_ok=True)


def register(api):
    def _safe_import():
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            return plt, np
        except ImportError:
            return None, None

    def plot_linhas(x: str, y: str, titulo: str = "", salvar: str = "") -> str:
        """Gera grafico de linhas. x e y sao JSON arrays: '[1,2,3]' e '[4,5,6]'."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            x_data = json.loads(x) if isinstance(x, str) else x
            y_data = json.loads(y) if isinstance(y, str) else y
            plt.figure(figsize=(10, 6))
            plt.plot(x_data, y_data, marker="o", linestyle="-", color="#89b4fa", linewidth=2)
            plt.title(titulo or "Grafico de Linhas")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"linhas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Grafico salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_barras(categorias: str, valores: str, titulo: str = "", horizontal: bool = False, salvar: str = "") -> str:
        """Gera grafico de barras. categorias e valores sao JSON arrays."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            cats = json.loads(categorias) if isinstance(categorias, str) else categorias
            vals = json.loads(valores) if isinstance(valores, str) else valores
            plt.figure(figsize=(12, 6))
            colors = ["#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8", "#cba6f7", "#94e2d5"]
            if horizontal:
                plt.barh(cats, vals, color=colors[:len(cats)])
            else:
                plt.bar(cats, vals, color=colors[:len(cats)])
            plt.title(titulo or "Grafico de Barras")
            plt.grid(True, alpha=0.3, axis="x" if horizontal else "y")
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"barras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Grafico salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_pizza(rotulos: str, valores: str, titulo: str = "", salvar: str = "") -> str:
        """Gera grafico de pizza. rotulos e valores sao JSON arrays."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            labels = json.loads(rotulos) if isinstance(rotulos, str) else rotulos
            vals = json.loads(valores) if isinstance(valores, str) else valores
            plt.figure(figsize=(8, 8))
            colors = ["#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8", "#cba6f7", "#94e2d5", "#fab387", "#b4befe"]
            plt.pie(vals, labels=labels, autopct="%1.1f%%", colors=colors[:len(labels)], startangle=90)
            plt.title(titulo or "Grafico de Pizza")
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"pizza_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Grafico salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_histograma(dados: str, bins: int = 10, titulo: str = "", salvar: str = "") -> str:
        """Gera histograma. dados eh JSON array de numeros."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            data = json.loads(dados) if isinstance(dados, str) else dados
            plt.figure(figsize=(10, 6))
            plt.hist(data, bins=bins, color="#89b4fa", edgecolor="white", alpha=0.8)
            plt.title(titulo or "Histograma")
            plt.grid(True, alpha=0.3, axis="y")
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Histograma salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_dispersao(x: str, y: str, titulo: str = "", salvar: str = "") -> str:
        """Gera grafico de dispersao (scatter plot). x e y sao JSON arrays."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            x_data = json.loads(x) if isinstance(x, str) else x
            y_data = json.loads(y) if isinstance(y, str) else y
            plt.figure(figsize=(10, 6))
            plt.scatter(x_data, y_data, color="#89b4fa", alpha=0.6, s=50)
            plt.title(titulo or "Grafico de Dispersao")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"scatter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Grafico salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_multi(y_series: str, labels: str = "", titulo: str = "", salvar: str = "") -> str:
        """Multiplas series no mesmo grafico. y_series: JSON de listas [[1,2,3],[4,5,6]]. labels: JSON de strings."""
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            series = json.loads(y_series) if isinstance(y_series, str) else y_series
            lbls = json.loads(labels) if isinstance(labels, str) and labels else []
            colors = ["#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8", "#cba6f7", "#94e2d5"]
            plt.figure(figsize=(10, 6))
            for i, s in enumerate(series):
                lbl = lbls[i] if i < len(lbls) else f"Serie {i+1}"
                plt.plot(s, marker=".", label=lbl, color=colors[i % len(colors)], linewidth=2)
            plt.title(titulo or "Multiplas Series")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            path = salvar or os.path.join(DATA_DIR, f"multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(path, dpi=150)
            plt.close()
            return f"Grafico salvo: {path}"
        except Exception as e:
            return f"Erro: {e}"

    def plot_from_csv(csv_path: str, col_x: str = "", col_y: str = "", tipo: str = "linhas", titulo: str = "", salvar: str = "") -> str:
        """Gera grafico a partir de colunas de arquivo CSV."""
        import csv
        plt, np = _safe_import()
        if plt is None:
            return "Instale: pip install matplotlib numpy"
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            if not rows:
                return "CSV vazio."
            headers = reader.fieldnames
            if not col_x:
                col_x = headers[0]
            if not col_y:
                col_y = headers[1] if len(headers) > 1 else headers[0]
            x_data = [r[col_x] for r in rows]
            y_data = [float(r[col_y]) for r in rows]
            if tipo in ("bar", "barras"):
                return plot_barras(json.dumps(x_data), json.dumps(y_data), titulo, salvar=salvar)
            if tipo in ("pizza", "pie"):
                return plot_pizza(json.dumps(x_data), json.dumps(y_data), titulo, salvar=salvar)
            return plot_linhas(json.dumps(list(range(len(x_data)))), json.dumps(y_data), titulo, salvar)
        except Exception as e:
            return f"Erro: {e}"

    api.register_tool("plot_linhas", plot_linhas,
        "Gera grafico de linhas a partir de arrays JSON. Use [1,2,3] para x e y.",
        {"x": {"type": "string", "description": "Array JSON para eixo X"}, "y": {"type": "string", "description": "Array JSON para eixo Y"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho para salvar (opcional)"}}, ["x", "y"])

    api.register_tool("plot_barras", plot_barras,
        "Gera grafico de barras. categorias e valores sao arrays JSON.",
        {"categorias": {"type": "string", "description": "Array JSON de categorias"}, "valores": {"type": "string", "description": "Array JSON de valores"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "horizontal": {"type": "boolean", "description": "Barras horizontais? (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["categorias", "valores"])

    api.register_tool("plot_pizza", plot_pizza,
        "Gera grafico de pizza. rotulos e valores sao arrays JSON.",
        {"rotulos": {"type": "string", "description": "Array JSON de rotulos"}, "valores": {"type": "string", "description": "Array JSON de valores"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["rotulos", "valores"])

    api.register_tool("plot_histograma", plot_histograma,
        "Gera histograma. dados eh array JSON de numeros.",
        {"dados": {"type": "string", "description": "Array JSON de numeros"}, "bins": {"type": "integer", "description": "Numero de bins (opcional, padrao 10)"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["dados"])

    api.register_tool("plot_dispersao", plot_dispersao,
        "Gera grafico de dispersao (scatter plot). x e y sao arrays JSON.",
        {"x": {"type": "string", "description": "Array JSON X"}, "y": {"type": "string", "description": "Array JSON Y"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["x", "y"])

    api.register_tool("plot_multi", plot_multi,
        "Multiplas series no mesmo grafico. y_series: JSON de listas [[1,2,3],[4,5,6]].",
        {"y_series": {"type": "string", "description": "JSON de listas de valores"}, "labels": {"type": "string", "description": "JSON array de labels (opcional)"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["y_series"])

    api.register_tool("plot_from_csv", plot_from_csv,
        "Gera grafico a partir de colunas de arquivo CSV. tipos: linhas, barras, pizza.",
        {"csv_path": {"type": "string", "description": "Caminho do CSV"}, "col_x": {"type": "string", "description": "Coluna para eixo X (opcional)"}, "col_y": {"type": "string", "description": "Coluna para eixo Y (opcional)"}, "tipo": {"type": "string", "description": "Tipo: linhas, barras, pizza (opcional)"}, "titulo": {"type": "string", "description": "Titulo (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, ["csv_path"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Geracao de graficos: linhas, barras, pizza, histograma, dispersao, multiplas series, CSV",
        "tools": ["plot_linhas", "plot_barras", "plot_pizza", "plot_histograma", "plot_dispersao", "plot_multi", "plot_from_csv"],
    }
