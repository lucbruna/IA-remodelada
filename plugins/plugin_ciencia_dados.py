"""
plugin_ciencia_dados.py
=======================
Analise de dados: estatisticas descritivas, correlacao, normalizacao,
amostragem, deteccao de outliers, geracao de dados sinteticos,
matriz de confusao basica.
"""

import os
import json
import math
import statistics
import random
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Ciencia de Dados"


def register(api):
    def _parse_num_list(data_str):
        if isinstance(data_str, list):
            return [float(x) for x in data_str]
        return [float(x) for x in json.loads(data_str)]

    def estatisticas(dados: str) -> str:
        """Estatisticas descritivas: media, mediana, moda, desvio padrao, variancia, min, max, quartis."""
        try:
            nums = _parse_num_list(dados)
            n = len(nums)
            if n == 0:
                return "Lista vazia."
            media = statistics.mean(nums)
            sorted_nums = sorted(nums)
            mediana = statistics.median(sorted_nums)
            try:
                moda = statistics.mode(sorted_nums)
            except statistics.StatisticsError:
                moda = "N/A (multimodal)"
            desvio = statistics.stdev(nums) if n > 1 else 0
            variancia = statistics.variance(nums) if n > 1 else 0
            q1 = sorted_nums[n // 4]
            q3 = sorted_nums[(3 * n) // 4]
            return (
                f"Estatisticas ({n} valores):\n"
                f"  Media: {media:.4f}\n"
                f"  Mediana: {mediana:.4f}\n"
                f"  Moda: {moda}\n"
                f"  Desvio padrao: {desvio:.4f}\n"
                f"  Variancia: {variancia:.4f}\n"
                f"  Min: {min(nums):.4f}\n"
                f"  Max: {max(nums):.4f}\n"
                f"  Amplitude: {max(nums)-min(nums):.4f}\n"
                f"  Q1: {q1:.4f}\n"
                f"  Q3: {q3:.4f}\n"
                f"  IQR: {q3-q1:.4f}\n"
                f"  CV: {desvio/media*100:.2f}%" if media != 0 else ""
            )
        except Exception as e:
            return f"Erro: {e}"

    def correlacao(x: str, y: str) -> str:
        """Coeficiente de correlacao de Pearson entre dois arrays."""
        try:
            x_vals = _parse_num_list(x)
            y_vals = _parse_num_list(y)
            if len(x_vals) != len(y_vals):
                return "Arrays devem ter o mesmo tamanho."
            n = len(x_vals)
            if n < 2:
                return "Pelo menos 2 pontos necessarios."
            r = statistics.correlation(x_vals, y_vals)
            # forca bruta para versoes python sem correlation
            try:
                r = statistics.correlation(x_vals, y_vals)
            except AttributeError:
                mx, my = statistics.mean(x_vals), statistics.mean(y_vals)
                num = sum((xi-mx)*(yi-my) for xi, yi in zip(x_vals, y_vals))
                den = math.sqrt(sum((xi-mx)**2 for xi in x_vals)) * math.sqrt(sum((yi-my)**2 for yi in y_vals))
                r = num/den if den != 0 else 0
            intensidade = "forte" if abs(r) > 0.7 else "moderada" if abs(r) > 0.3 else "fraca"
            direcao = "positiva" if r > 0 else "negativa"
            return f"Correlacao Pearson: r = {r:.4f} ({intensidade}, {direcao})"
        except Exception as e:
            return f"Erro: {e}"

    def normalizar(dados: str, metodo: str = "minmax") -> str:
        """Normaliza dados. metodos: minmax (0-1), zscore, max (0-1/max)."""
        try:
            nums = _parse_num_list(dados)
            if not nums:
                return "Lista vazia."
            if metodo == "minmax":
                mn, mx = min(nums), max(nums)
                if mx == mn:
                    result = [0.5] * len(nums)
                else:
                    result = [(v - mn) / (mx - mn) for v in nums]
            elif metodo == "zscore":
                media = statistics.mean(nums)
                desvio = statistics.stdev(nums) if len(nums) > 1 else 1
                result = [(v - media) / desvio if desvio != 0 else 0 for v in nums]
            elif metodo == "max":
                mx = max(abs(v) for v in nums) or 1
                result = [v / mx for v in nums]
            else:
                return f"Metodo invalido: {metodo}. Use: minmax, zscore, max."
            return f"Normalizacao ({metodo}): " + json.dumps([round(v, 6) for v in result])
        except Exception as e:
            return f"Erro: {e}"

    def detectar_outliers(dados: str, metodo: str = "iqr", fator: float = 1.5) -> str:
        """Detecta outliers. metodos: iqr (Turkey), zscore (|z|>3)."""
        try:
            nums = _parse_num_list(dados)
            if len(nums) < 4:
                return "Pelo menos 4 valores necessarios."
            sorted_nums = sorted(nums)
            n = len(sorted_nums)
            outliers = []
            if metodo == "iqr":
                q1 = sorted_nums[n // 4]
                q3 = sorted_nums[(3 * n) // 4]
                iqr = q3 - q1
                lower, upper = q1 - fator * iqr, q3 + fator * iqr
                outliers = [v for v in nums if v < lower or v > upper]
                return (
                    f"Outliers (IQR, fator={fator}):\n"
                    f"  Limites: [{lower:.4f}, {upper:.4f}]\n"
                    f"  Q1={q1:.4f}, Q3={q3:.4f}, IQR={iqr:.4f}\n"
                    f"  Encontrados: {len(outliers)}/{len(nums)}\n"
                    + (f"  Valores: {json.dumps([round(v, 4) for v in outliers])}" if outliers else "")
                )
            elif metodo == "zscore":
                media = statistics.mean(nums)
                desvio = statistics.stdev(nums) if len(nums) > 1 else 1
                for v in nums:
                    z = abs(v - media) / desvio if desvio != 0 else 0
                    if z > fator:
                        outliers.append((v, z))
                return (
                    f"Outliers (Z-score, limite={fator}):\n"
                    f"  Media={media:.4f}, Desvio={desvio:.4f}\n"
                    f"  Encontrados: {len(outliers)}/{len(nums)}\n"
                    + ("\n".join(f"  {v:.4f} (z={z:.2f})" for v, z in outliers) if outliers else "")
                )
            return f"Metodo invalido: {metodo}"
        except Exception as e:
            return f"Erro: {e}"

    def amostrar(dados: str, tamanho: int = 10, com_reposicao: bool = False) -> str:
        """Amostragem aleatoria de dados."""
        try:
            nums = _parse_num_list(dados)
            if len(nums) < tamanho and not com_reposicao:
                return f"Lista tem apenas {len(nums)} itens, mas pediu {tamanho} sem reposicao."
            amostra = random.choices(nums, k=tamanho) if com_reposicao else random.sample(nums, min(tamanho, len(nums)))
            return f"Amostra ({tamanho}, reposicao={com_reposicao}): " + json.dumps([round(v, 6) for v in amostra])
        except Exception as e:
            return f"Erro: {e}"

    def dados_sinteticos(padrao: str = "linear", n: int = 50, ruido: float = 0.1) -> str:
        """Gera dados sinteticos para testes. padroes: linear, quadratico, seno, aleatorio, clusters."""
        import numpy as np
        try:
            rng = np.random.default_rng()
            x = np.linspace(0, 10, n)
            if padrao == "linear":
                y = 2 * x + 1 + rng.normal(0, ruido * 10, n)
            elif padrao == "quadratico":
                y = x ** 2 - 5 * x + 3 + rng.normal(0, ruido * 10, n)
            elif padrao == "seno":
                y = np.sin(x) + rng.normal(0, ruido, n)
            elif padrao == "aleatorio":
                y = rng.uniform(-10, 10, n)
            elif padrao == "clusters":
                centers = [(-5, 0), (0, 5), (5, -5)]
                x_vals, y_vals = [], []
                for _ in range(n):
                    cx, cy = rng.choice(centers)
                    x_vals.append(cx + rng.normal(0, 1))
                    y_vals.append(cy + rng.normal(0, 1))
                return json.dumps({"x": [round(v, 4) for v in x_vals], "y": [round(v, 4) for v in y_vals]})
            else:
                return f"Padrao invalido: {padrao}. Use: linear, quadratico, seno, aleatorio, clusters."
            data = {"x": [round(v, 4) for v in x.tolist()], "y": [round(v, 4) for v in y.tolist()]}
            return json.dumps(data)
        except Exception as e:
            return f"Erro: {e}"

    def matriz_confusao(verdadeiros: str, preditos: str, classes: str = "") -> str:
        """Gera matriz de confusao basica. Arrays JSON de rotulos."""
        try:
            y_true = json.loads(verdadeiros) if isinstance(verdadeiros, str) else verdadeiros
            y_pred = json.loads(preditos) if isinstance(preditos, str) else preditos
            all_classes = json.loads(classes) if isinstance(classes, str) and classes else sorted(set(y_true + y_pred))
            n = len(all_classes)
            cm = [[0] * n for _ in range(n)]
            for t, p in zip(y_true, y_pred):
                if t in all_classes and p in all_classes:
                    cm[all_classes.index(t)][all_classes.index(p)] += 1
            lines = ["Matriz de Confusao:"]
            header = "      " + " ".join(f"{c:>6}" for c in all_classes)
            lines.append(header)
            for i, row in enumerate(cm):
                lines.append(f"{all_classes[i]:>4} " + " ".join(f"{v:>6}" for v in row))
            acertos = sum(cm[i][i] for i in range(n))
            total = sum(sum(row) for row in cm)
            acc = acertos / total * 100 if total > 0 else 0
            lines.append(f"\nAcuracia: {acertos}/{total} = {acc:.2f}%")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    api.register_tool("estatisticas", estatisticas,
        "Estatisticas descritivas: media, mediana, moda, desvio, quartis.",
        {"dados": {"type": "string", "description": "JSON array de numeros"}}, ["dados"])

    api.register_tool("correlacao", correlacao,
        "Coeficiente de correlacao de Pearson entre dois arrays.",
        {"x": {"type": "string", "description": "JSON array X"}, "y": {"type": "string", "description": "JSON array Y"}}, ["x", "y"])

    api.register_tool("normalizar", normalizar,
        "Normaliza dados: minmax (0-1), zscore, max.",
        {"dados": {"type": "string", "description": "JSON array de numeros"}, "metodo": {"type": "string", "description": "minmax, zscore, max (opcional)"}}, ["dados"])

    api.register_tool("detectar_outliers", detectar_outliers,
        "Detecta outliers: iqr (Turkey) ou zscore.",
        {"dados": {"type": "string", "description": "JSON array de numeros"}, "metodo": {"type": "string", "description": "iqr ou zscore (opcional)"}, "fator": {"type": "number", "description": "Fator de sensibilidade (opcional)"}}, ["dados"])

    api.register_tool("amostrar", amostrar,
        "Amostragem aleatoria de dados, com ou sem reposicao.",
        {"dados": {"type": "string", "description": "JSON array de numeros"}, "tamanho": {"type": "integer", "description": "Tamanho da amostra (opcional)"}, "com_reposicao": {"type": "boolean", "description": "Amostragem com reposicao? (opcional)"}}, ["dados"])

    api.register_tool("dados_sinteticos", dados_sinteticos,
        "Gera dados sinteticos para testes. Padroes: linear, quadratico, seno, aleatorio, clusters.",
        {"padrao": {"type": "string", "description": "linear, quadratico, seno, aleatorio, clusters (opcional)"}, "n": {"type": "integer", "description": "Numero de pontos (opcional)"}, "ruido": {"type": "number", "description": "Nivel de ruido (opcional)"}}, [])

    api.register_tool("matriz_confusao", matriz_confusao,
        "Gera matriz de confusao a partir de arrays de rotulos verdadeiros e preditos.",
        {"verdadeiros": {"type": "string", "description": "JSON array de rotulos verdadeiros"}, "preditos": {"type": "string", "description": "JSON array de rotulos preditos"}, "classes": {"type": "string", "description": "JSON array de classes (opcional)"}}, ["verdadeiros", "preditos"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Analise de dados: estatisticas, correlacao, normalizacao, outliers, amostragem, dados sinteticos",
        "tools": ["estatisticas", "correlacao", "normalizar", "detectar_outliers", "amostrar", "dados_sinteticos", "matriz_confusao"],
    }
