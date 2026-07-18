"""
plugin_previsao_temporal.py
===========================
Plugin de previsão temporal e análise de dados. Fornece ferramentas para:
- Previsão de séries temporais simples (médias móveis, suavização exponencial)
- Detecção de anomalias básica em dados
- Simulação de cenários (Monte Carlo simples)
- Análise de tendências e sazonalidade básica
"""

import math
import random
import statistics
from typing import List, Tuple, Optional, Any
from datetime import datetime, timedelta

__version__ = "1.0.0"
PLUGIN_NAME = "Previsão Temporal e Análise de Dados"


def _media_movel_simples(dados: List[float], janela: int) -> List[float]:
    """Calcula a média móvel simples."""
    if len(dados) < janela:
        return []

    medias = []
    for i in range(len(dados) - janela + 1):
        janela_dados = dados[i:i + janela]
        media = sum(janela_dados) / len(janela_dados)
        medias.append(media)

    return medias


def _suavizacao_exponencial(dados: List[float], alpha: float = 0.3) -> List[float]:
    """Aplica suavização exponencial simples."""
    if not dados:
        return []

    resultado = [dados[0]]  # Primeiro valor é o mesmo
    for i in range(1, len(dados)):
        suavizado = alpha * dados[i] + (1 - alpha) * resultado[-1]
        result.append(suavizado)

    return resultado


def _regressao_linear_simples(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Calcula regressão linear simples (y = mx + b). Retorna (inclinacao, intercepto)."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0

    soma_x = sum(x)
    soma_y = sum(y)
    soma_xy = sum(xi * yi for xi, yi in zip(x, y))
    soma_x2 = sum(xi * xi for xi in x)

    denominador = n * soma_x2 - soma_x * soma_x
    if denominador == 0:
        return 0.0, soma_y / n

    m = (n * soma_xy - soma_x * soma_y) / denominador
    b = (soma_y - m * soma_x) / n

    return m, b


def prever_tendencia_linear(dados: List[float], passos_futuros: int = 5) -> List[float]:
    """Prevê valores futuros usando regressão linear simples."""
    if len(dados) < 2:
        return [0.0] * max(0, passos_futuros)

    # Criar eixo x (0, 1, 2, ..., n-1)
    x = list(range(len(dados)))
    y = dados

    # Calcular regressão linear
    m, b = _regressao_linear_simples(x, y)

    # Prever pontos futuros
    previsoes = []
    for i in range(passos_futuros):
        x_futuro = len(dados) + i
        y_previsto = m * x_futuro + b
        previsoes.append(y_previsto)

    return previsoes


def prever_media_movel(dados: List[float], janela: int, passos_futuros: int = 5) -> List[float]:
    """Prevê valores futuros usando a média móvel dos últimos 'janela' pontos."""
    if len(dados) < janela:
        # Se não temos dados suficientes, usar média de todos
        if not dados:
            return [0.0] * passos_futuros
        media_geral = sum(dados) / len(dados)
        return [media_geral] * passos_futuros

    # Usar a média dos últimos 'janela' pontos
    ultimos_valores = dados[-janela:]
    media = sum(ultimos_valores) / len(ultimos_valores)

    return [media] * passos_futuros


def detectar_anomalias_desvio_padrao(dados: List[float],
                                   num_desvios: float = 2.0) -> List[Tuple[int, float, bool]]:
    """
    Detecta anomalias usando desvio padrão.
    Retorna lista de tuplas: (indice, valor, eh_anomalia)
    """
    if len(dados) < 2:
        return [(i, valor, False) for i, valor in enumerate(dados)]

    media = statistics.mean(dados)
    desvio_padrao = statistics.stdev(dados) if len(dados) >= 2 else 0.0

    limite_superior = media + (num_desvios * desvio_padrao)
    limite_inferior = media - (num_desvios * desvio_padrao)

    resultado = []
    for i, valor in enumerate(dados):
        eh_anomalia = valor > limite_superior or valor < limite_inferior
        resultado.append((i, valor, eh_anomalia))

    return resultado


def detectar_anomalias_iqr(dados: List[float],
                          fator: float = 1.5) -> List[Tuple[int, float, bool]]:
    """
    Detecta anomalias usando Interquartile Range (IQR).
    Retorna lista de tuplas: (indice, valor, eh_anomalia)
    """
    if len(dados) < 4:
        return [(i, valor, False) for i, valor in enumerate(dados)]

    dados_ordenados = sorted(dados)
    n = len(dados_ordenados)

    # Calcular Q1 (25%) e Q3 (75%)
    q1_idx = n // 4
    q3_idx = 3 * n // 4

    q1 = dados_ordenados[q1_idx]
    q3 = dados_ordenados[q3_idx]
    iqr = q3 - q1

    limite_superior = q3 + (fator * iqr)
    limite_inferior = q1 - (fator * iqr)

    resultado = []
    for i, valor in enumerate(dados):
        eh_anomalia = valor > limite_superior or valor < limite_inferior
        resultado.append((i, valor, eh_anomalia))

    return resultado


def simulacao_monte_carlo_pi(amostras: int = 10000) -> dict:
    """
    Simulação de Monte Carlo simples para estimar o valor de π.
    Retorna dicionário com resultado e estatísticas.
    """
    pontos_dentro = 0

    for _ in range(amostras):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        distancia = math.sqrt(x*x + y*y)
        if distancia <= 1:
            pontos_dentro += 1

    pi_estimado = 4 * pontos_dentro / amostras
    erro = abs(pi_estimado - math.pi) / math.pi * 100

    return {
        "pi_estimado": pi_estimado,
        "pi_real": math.pi,
        "erro_percentual": erro,
        "pontos_dentro": pontos_dentro,
        "total_amostras": amostras,
        "precisao": f"{(100 - erro):.2f}%"
    }


def simular_investimento_juro_composto(capital_inicial: float,
                                     taxa_juros_anual: float,
                                     anos: int,
                                     simulacoes: int = 1000,
                                     volatilidade: float = 0.1) -> dict:
    """
    Simula crescimento de investimento com juros compostos usando Monte Carlo.
    Inclui variação aleatória na taxa de juros para simular volatilidade do mercado.
    """
    resultados_finais = []

    for _ in range(simulacoes):
        montante = capital_inicial
        for ano in range(anos):
            # Variação aleatória na taxa de juros (distribuição normal)
            taxa_variada = taxa_juros_anual + random.gauss(0, volatilidade)
            # Garantir que a taxa não seja negativa demais
            taxa_variada = max(-0.99, taxa_variada)  # Máximo -99% (perda total)
            montante *= (1 + taxa_variada)
        resultados_finais.append(montante)

    # Estatísticas
    media = statistics.mean(resultados_finais)
    mediana = statistics.median(resultados_finais)
    desvio_padrao = statistics.stdev(resultados_finais) if len(resultados_finais) >= 2 else 0.0
    percentil_5 = sorted(resultados_finais)[int(simulacoes * 0.05)]
    percentil_95 = sorted(resultados_finais)[int(simulacoes * 0.95)]

    return {
        "capital_inicial": capital_inicial,
        "taxa_juros_anual": taxa_juros_anual,
        "anos": anos,
        "simulacoes": simulacoes,
        "volatilidade": volatilidade,
        "resultado_medio": media,
        "resultado_mediano": mediana,
        "desvio_padrao": desvio_padrao,
        "percentil_5": percentil_5,
        "percentil_95": percentil_95,
        "probabilidade_perda": len([r for r in resultados_finais if r < capital_inicial]) / simulacoes * 100
    }


def analisar_sequencia_temporal(dados: List[float]) -> dict:
    """
    Analisa uma sequência temporal e retorna métricas descritivas.
    """
    if not dados:
        return {"erro": "Lista de dados vazia"}

    n = len(dados)
    media = statistics.mean(dados)
    mediana = statistics.median(dados)

    try:
        desvio_padrao = statistics.stdev(dados) if n >= 2 else 0.0
    except statistics.StatisticsError:
        desvio_padrao = 0.0

    minimo = min(dados)
    maximo = max(dados)
    amplitud = maximo - minimo

    # Tendência (comparando primeira e segunda metade)
    if n >= 4:
        metade = n // 2
        primeira_metade = dados[:metade]
        segunda_metade = dados[metade:2*metade] if 2*metade <= n else dados[metade:]

        if primeira_metade and segunda_metade:
            media_primeira = statistics.mean(primeira_metade)
            media_segunda = statistics.mean(segunda_metade)
            tendencia = "crescente" if media_segunda > media_primeira else "decrescente" if media_segunda < media_primeira else "estável"
            diferenca_percentual = ((media_segunda - media_primeira) / media_primeira * 100) if media_primeira != 0 else 0
        else:
            tendencia = "indeterminada"
            diferenca_percentual = 0.0
    else:
        tendencia = "insuficientes_dados"
        diferenca_percentual = 0.0

    # Detecção de sazonalidade muito básica (verificar padrões repetitivos)
    sazonalidade_detectada = False
    if n >= 6:
        # Verificar se há padrão a cada 2, 3 ou 4 períodos
        for periodo in [2, 3, 4]:
            if n >= periodo * 2:
                padroes = []
                for i in range(0, n - periodo, periodo):
                    if i + periodo < n:
                        padroes.append(dados[i:i+periodo])

                if len(padroes) >= 2:
                    # Verificar similaridade simples entre padrões consecutivos
                    similaridades = []
                    for j in range(len(padroes) - 1):
                        diff = sum(abs(a - b) for a, b in zip(padroes[j], padroes[j+1]))
                        similaridades.append(diff)

                    if similaridades:
                        media_similaridade = statistics.mean(similaridades)
                        if media_similaridade < (amplitud * 0.3):  # Limiar arbitrário
                            sazonalidade_detectada = True
                            break

    return {
        "tamanho_amostra": n,
        "media": media,
        "mediana": mediana,
        "desvio_padrao": desvio_padrao,
        "minimo": minimo,
        "maximo": maximo,
        "amplitud": amplitud,
        "tendencia": tendencia,
        "diferenca_percentual_media": diferenca_percentual,
        "sazonalidade_possivel": sazonalidade_detectada
    }


# Registro das funções no sistema de plugins
def register(api):
    """Registra todas as ferramentas de previsão temporal."""

    api.register_tool(
        name="prever_tendencia_linear",
        func=prever_tendencia_linear,
        description="Prevê valores futuros usando regressão linear simples.",
        parameters={
            "dados": {"type": "array", "items": {"type": "number"}, "description": "Lista de valores históricos"},
            "passos_futuros": {"type": "integer", "description": "Número de passos futuros para prever (padrão: 5)"}
        },
        required=["dados"]
    )

    api.register_tool(
        name="prever_media_movel",
        func=prever_media_movel,
        description="Prevê valores futuros usando média móvel simples.",
        parameters={
            "dados": {"type": "array", "items": {"type": "number"}, "description": "Lista de valores históricos"},
            "janela": {"type": "integer", "description": "Tamanho da janela para média móvel"},
            "passos_futuros": {"type": "integer", "description": "Número de passos futuros para prever (padrão: 5)"}
        },
        required=["dados", "janela"]
    )

    api.register_tool(
        name="detectar_anomalias",
        func=detectar_anomalias_desvio_padrao,
        description="Detecta anomalias em uma série de dados usando desvio padrão.",
        parameters={
            "dados": {"type": "array", "items": {"type": "number"}, "description": "Lista de valores para analisar"},
            "num_desvios": {"type": "number", "description": "Número de desvios padrão para considerar anomalia (padrão: 2.0)"}
        },
        required=["dados"]
    )

    api.register_tool(
        name="detectar_anomalias_iqr",
        func=detectar_anomalias_iqr,
        description="Detecta anomalias usando Interquartile Range (IQR).",
        parameters={
            "dados": {"type": "array", "items": {"type": "number"}, "description": "Lista de valores para analisar"},
            "fator": {"type": "number", "description": "Fator multiplicador do IQR (padrão: 1.5)"}
        },
        required=["dados"]
    )

    api.register_tool(
        name="simular_monte_carlo_pi",
        func=simulacao_monte_carlo_pi,
        description="Executa simulação de Monte Carlo para estimar o valor de π.",
        parameters={
            "amostras": {"type": "integer", "description": "Número de pontos aleatórios para usar na simulação (padrão: 10000)"}
        },
        required=[]
    )

    api.register_tool(
        name="simular_investimento",
        func=simular_investimento_juro_composto,
        description="Simula crescimento de investimento com juros compostos usando Monte Carlo.",
        parameters={
            "capital_inicial": {"type": "number", "description": "Valor inicial do investimento"},
            "taxa_juros_anual": {"type": "number", "description": "Taxa de juros anual esperada (ex: 0.07 para 7%)"},
            "anos": {"type": "integer", "description": "Número de anos para simular"},
            "simulacoes": {"type": "integer", "description": "Número de simulações para executar (padrão: 1000)"},
            "volatilidade": {"type": "number", "description": "Volatilidade da taxa de juros (padrão: 0.1 para 10%)"}
        },
        required=["capital_inicial", "taxa_juros_anual", "anos"]
    )

    api.register_tool(
        name="analisar_sequencia",
        func=analisar_sequencia_temporal,
        description="Analisa uma sequência temporal e retorna estatísticas descritivas.",
        parameters={
            "dados": {"type": "array", "items": {"type": "number"}, "description": "Lista de valores temporais para analisar"}
        },
        required=["dados"]
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Previsão temporal e análise de dados: médias móveis, regressão linear, detecção de anomalias, simulações Monte Carlo.",
        "tools": [
            "prever_tendencia_linear",
            "prever_media_movel",
            "detectar_anomalias",
            "detectar_anomalias_iqr",
            "simular_monte_carlo_pi",
            "simular_investimento",
            "analisar_sequencia"
        ]
    }
