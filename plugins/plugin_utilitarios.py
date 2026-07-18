"""
plugin_utilitarios.py
=====================
Plugin de utilidades: IMC, conversao de unidades e cambio em tempo real.

Ferramentas registradas:
  - calcular_imc(peso, altura) -> IMC + classificacao
  - converter_unidades(valor, de, para, tipo) -> conversao entre unidades
  - converter_moeda(valor, de, para) -> cambio real via exchangerate-api.com

wttr.in: https://github.com/chubin/wttr.in
"""

import json
import logging


# =====================================================================
# IMC
# =====================================================================

_TABELA_IMC = [
    (16.0, "Magreza grave", "🔴"),
    (17.0, "Magreza moderada", "🟠"),
    (18.5, "Magreza leve", "🟡"),
    (25.0, "Saudavel", "🟢"),
    (30.0, "Sobrepeso", "🟡"),
    (35.0, "Obesidade grau I", "🟠"),
    (40.0, "Obesidade grau II", "🔴"),
    (float("inf"), "Obesidade grau III", "⛔"),
]


def _classificar_imc(imc: float) -> tuple:
    """Retorna (classificacao, emoji) para o IMC."""
    for limite, classe, emoji in _TABELA_IMC:
        if imc < limite:
            return classe, emoji
    return "Desconhecido", "❓"


def _calcular_imc(peso: float, altura: float) -> str:
    """Calcula o IMC e retorna resultado detalhado."""
    if peso <= 0 or altura <= 0:
        return "❌ Peso e altura devem ser valores positivos."
    if altura > 3:
        return "❌ Altura parece estar em centimetros. Use metros (ex: 1.75)."

    imc = peso / (altura ** 2)
    imc_str = f"{imc:.1f}"
    classe, emoji = _classificar_imc(imc)

    # Calcula peso ideal (IMC 21.5 = meio do saudavel)
    peso_ideal_min = 18.5 * (altura ** 2)
    peso_ideal_max = 24.9 * (altura ** 2)
    peso_ideal_medio = 21.5 * (altura ** 2)

    linhas = [
        f"{emoji} **Seu IMC: {imc_str}**",
        f"  Classificacao: {classe}",
        f"",
        f"  📊 Peso ideal para sua altura:",
        f"     Minimo: {peso_ideal_min:.1f} kg",
        f"     Medio:  {peso_ideal_medio:.1f} kg",
        f"     Maximo: {peso_ideal_max:.1f} kg",
    ]

    if imc < 18.5:
        diff = peso_ideal_min - peso
        linhas.append(f"  💡 Voce esta {diff:.1f} kg abaixo do peso minimo ideal.")
    elif imc > 25:
        diff = peso - peso_ideal_max
        linhas.append(f"  💡 Voce esta {diff:.1f} kg acima do peso maximo ideal.")
    else:
        linhas.append(f"  ✅ Seu peso esta dentro da faixa saudavel!")

    linhas.append(f"")
    linhas.append(f"  ℹ Tabela: magreza < 18,5 | saudavel 18,5-24,9 | sobrepeso 25-29,9")

    return "\n".join(linhas)


# =====================================================================
# Conversao de Unidades
# =====================================================================

# (nome, simbolo, tipo, fator_para_si)
# tipo define a categoria (length, mass, temp, volume, speed)
# fator_para_si e' o multiplicador para converter para a unidade base do SI
_UNIDADES = {
    # Temperatura (tratamento especial)
    "celsius": ("Celsius", "°C", "temp", None),
    "fahrenheit": ("Fahrenheit", "°F", "temp", None),
    "kelvin": ("Kelvin", "K", "temp", None),
    # Comprimento (para metros)
    "km": ("Quilometro", "km", "length", 1000.0),
    "m": ("Metro", "m", "length", 1.0),
    "cm": ("Centimetro", "cm", "length", 0.01),
    "mm": ("Milimetro", "mm", "length", 0.001),
    "milha": ("Milha", "mi", "length", 1609.34),
    "pes": ("Pe", "ft", "length", 0.3048),
    "polegada": ("Polegada", "in", "length", 0.0254),
    "jarda": ("Jarda", "yd", "length", 0.9144),
    # Massa (para kg)
    "kg": ("Quilograma", "kg", "mass", 1.0),
    "g": ("Grama", "g", "mass", 0.001),
    "mg": ("Miligrama", "mg", "mass", 0.000001),
    "libra": ("Libra", "lb", "mass", 0.453592),
    "onca": ("Onca", "oz", "mass", 0.0283495),
    "tonelada": ("Tonelada", "t", "mass", 1000.0),
    # Volume (para litros)
    "l": ("Litro", "L", "volume", 1.0),
    "ml": ("Mililitro", "mL", "volume", 0.001),
    "galao": ("Galao", "gal", "volume", 3.78541),
    "xicara": ("Xicara", "cup", "volume", 0.236588),
    # Velocidade (para km/h)
    "kmh": ("km/h", "km/h", "speed", 1.0),
    "mph": ("Milhas/h", "mph", "speed", 1.60934),
    "ms": ("m/s", "m/s", "speed", 3.6),
    "nos": ("Nos", "kn", "speed", 1.852),
}

_TIPOS_UNIDADE = {
    "temp": "🌡 Temperatura",
    "length": "📏 Comprimento",
    "mass": "⚖ Massa",
    "volume": "🧪 Volume",
    "speed": "💨 Velocidade",
}


def _converter_temperatura(valor: float, de: str, para: str) -> float:
    """Converte entre Celsius, Fahrenheit e Kelvin."""
    # Primeiro converte para Celsius
    de = de.lower()
    para = para.lower()
    if de == "celsius":
        celsius = valor
    elif de == "fahrenheit":
        celsius = (valor - 32) * 5 / 9
    elif de == "kelvin":
        celsius = valor - 273.15
    else:
        raise ValueError(f"Unidade de temperatura desconhecida: {de}")

    # Depois converte de Celsius para destino
    if para == "celsius":
        return celsius
    elif para == "fahrenheit":
        return celsius * 9 / 5 + 32
    elif para == "kelvin":
        return celsius + 273.15
    else:
        raise ValueError(f"Unidade de temperatura desconhecida: {para}")


def _converter_unidade(valor: float, de: str, para: str) -> str:
    """Converte entre unidades do mesmo tipo."""
    de_info = _UNIDADES.get(de.lower())
    para_info = _UNIDADES.get(para.lower())

    if not de_info:
        return f"❌ Unidade '{de}' nao reconhecida. Use: {', '.join(sorted(_UNIDADES.keys()))}"
    if not para_info:
        return f"❌ Unidade '{para}' nao reconhecida."

    if de_info[2] != para_info[2]:  # [2] = tipo
        tipo_de = _TIPOS_UNIDADE.get(de_info[2], de_info[2])
        tipo_para = _TIPOS_UNIDADE.get(para_info[2], para_info[2])
        return f"❌ Unidades incompativeis: {de_info[0]} ({tipo_de}) vs {para_info[0]} ({tipo_para})"

    # Tratamento especial para temperatura
    if de_info[2] == "temp":  # [2] = tipo, [3] = fator
        try:
            resultado = _converter_temperatura(valor, de.lower(), para.lower())
        except ValueError as e:
            return f"❌ {e}"
        nome_de, simb_de = de_info[0], de_info[1]
        nome_para, simb_para = para_info[0], para_info[1]
        return (
            f"🌡 **{valor} {simb_de}** = **{resultado:.2f} {simb_para}**\n"
            f"  {nome_de} → {nome_para}"
        )

    # Conversao por fator (fator_para_si: valor * fator_A / fator_B)
    fator = de_info[3] / para_info[3]
    resultado = valor * fator

    nome_de, simb_de = de_info[0], de_info[1]
    nome_para, simb_para = para_info[0], para_info[1]
    tipo = _TIPOS_UNIDADE.get(de_info[3], "")

    return (
        f"{tipo}\n"
        f"  **{valor} {simb_de}** = **{resultado:.4f} {simb_para}**\n"
        f"  {nome_de} → {nome_para}"
    )


# =====================================================================
# Cambio (via API gratuita)
# =====================================================================

_MOEDAS_COMUNS = {
    "USD": "US$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "BRL": "R$", "CAD": "C$", "AUD": "A$", "CHF": "Fr",
    "CNY": "¥", "ARS": "$", "MXN": "$", "INR": "₹",
}

_URL_CAMBIO = "https://api.exchangerate-api.com/v4/latest/USD"


def _converter_moeda(valor: float, de: str, para: str) -> str:
    """Converte valor entre moedas usando taxa de cambio via exchangerate-api.com.

    Args:
        valor: Valor a ser convertido
        de: Codigo da moeda de origem (ex: USD, BRL, EUR)
        para: Codigo da moeda de destino (ex: BRL, USD, EUR)

    Returns:
        Resultado da conversao formatado
    """
    try:
        import requests
    except ImportError:
        return "⚠ Biblioteca 'requests' nao instalada.\nInstale com: pip install requests"

    de = de.upper().strip()
    para = para.upper().strip()

    if not de or not para:
        return "❌ Informe as moedas de origem e destino (ex: BRL USD)."

    if de == para:
        simbolo = _MOEDAS_COMUNS.get(de, "$")
        return f"{simbolo} {valor:.2f} {de} = {simbolo} {valor:.2f} {para} (mesma moeda)"

    try:
        resp = requests.get(_URL_CAMBIO, timeout=10)
        resp.raise_for_status()
        dados = resp.json()
    except requests.exceptions.Timeout:
        return "⏱ Tempo esgotado ao consultar taxas de cambio."
    except requests.exceptions.ConnectionError:
        return "🌐 Sem conexao com a internet para consultar cambio."
    except json.JSONDecodeError:
        return "⚠ Resposta invalida do servidor de cambio."
    except Exception as e:
        logging.error("Erro no cambio: %s", e)
        return f"❌ Erro ao consultar cambio: {e}"

    taxas = dados.get("rates", {})

    if de not in taxas:
        moedas = sorted(taxas.keys())[:20]
        return f"❌ Moeda '{de}' nao encontrada. Exemplos: {', '.join(moedas)}"
    if para not in taxas:
        return f"❌ Moeda '{para}' nao encontrada."

    # Converte: valor -> USD -> moeda destino
    taxa_origem = taxas[de]
    taxa_destino = taxas[para]
    valor_em_usd = valor / taxa_origem
    resultado = valor_em_usd * taxa_destino

    simb_de = _MOEDAS_COMUNS.get(de, "$")
    simb_para = _MOEDAS_COMUNS.get(para, "$")
    data_ref = dados.get("date", "hoje")

    return (
        f"💱 **{simb_de} {valor:,.2f} {de}** = **{simb_para} {resultado:,.2f} {para}**\n"
        f"  Taxa: 1 {de} = {taxa_destino / taxa_origem:.6f} {para}\n"
        f"  📅 Referencia: {data_ref}\n"
        f"  ℹ Fonte: exchangerate-api.com"
    )


# =====================================================================
# Registro
# =====================================================================

def register(api):
    """Registra as ferramentas de utilitarios no agente."""

    # ---- IMC ----
    def calcular_imc(peso: float, altura: float) -> str:
        """Calcula o IMC (Indice de Massa Corporal) e retorna classificacao.

        Args:
            peso: Peso em quilogramas (ex: 70.5)
            altura: Altura em metros (ex: 1.75)

        Returns:
            IMC calculado com classificacao e peso ideal
        """
        return _calcular_imc(peso, altura)

    api.register_tool(
        name="calcular_imc",
        func=calcular_imc,
        description=(
            "Calcula o IMC (Indice de Massa Corporal) a partir de peso e altura. "
            "Retorna o valor do IMC, classificacao (magreza, saudavel, sobrepeso, "
            "obesidade), faixa de peso ideal e recomendacoes. "
            "Use quando o usuario perguntar sobre IMC, peso ideal, ou classificacao de peso."
        ),
        parameters={
            "peso": {
                "type": "number",
                "description": "Peso em quilogramas (ex: 70.5)",
            },
            "altura": {
                "type": "number",
                "description": "Altura em metros (ex: 1.75)",
            },
        },
        required=["peso", "altura"],
    )

    # ---- Conversao de Unidades ----
    def converter_unidades(valor: float, de: str, para: str) -> str:
        """Converte entre unidades de medida (comprimento, massa, volume, velocidade, temperatura).

        Args:
            valor: Valor numerico a ser convertido
            de: Unidade de origem (ex: 'km', 'kg', 'celsius', 'l', 'kmh')
            para: Unidade de destino (ex: 'milha', 'libra', 'fahrenheit', 'galao', 'mph')

        Returns:
            Resultado da conversao formatado
        """
        return _converter_unidade(valor, de, para)

    api.register_tool(
        name="converter_unidades",
        func=converter_unidades,
        description=(
            "Converte valores entre unidades de medida. "
            "Suporta: comprimento (km, m, cm, mm, milha, pes, polegada, jarda), "
            "massa (kg, g, mg, libra, onca, tonelada), "
            "volume (L, mL, galao, xicara), "
            "velocidade (km/h, mph, m/s, nos), "
            "temperatura (celsius, fahrenheit, kelvin). "
            "Exemplos: '10 km em milhas', '100°F em Celsius', '5 kg em libras'."
        ),
        parameters={
            "valor": {
                "type": "number",
                "description": "Valor numerico a ser convertido",
            },
            "de": {
                "type": "string",
                "description": "Unidade de origem: km, m, cm, mm, milha, pes, polegada, jarda, kg, g, mg, libra, onca, tonelada, L, mL, galao, xicara, celsius, fahrenheit, kelvin, kmh, mph, ms, nos",
            },
            "para": {
                "type": "string",
                "description": "Unidade de destino (mesmas opcoes)",
            },
        },
        required=["valor", "de", "para"],
    )

    # ---- Cambio ----
    def converter_moeda(valor: float, de: str, para: str) -> str:
        """Converte valor entre moedas usando taxa de cambio atual via API.

        Args:
            valor: Valor a ser convertido
            de: Codigo da moeda de origem (ex: USD, BRL, EUR, GBP, JPY)
            para: Codigo da moeda de destino (ex: BRL, USD, EUR)

        Returns:
            Valor convertido com taxa de cambio
        """
        return _converter_moeda(valor, de, para)

    api.register_tool(
        name="converter_moeda",
        func=converter_moeda,
        description=(
            "Converte valores entre moedas usando taxa de cambio atual via API gratuita. "
            "Moedas suportadas: USD, BRL, EUR, GBP, JPY, CAD, AUD, CHF, CNY, ARS, MXN, INR "
            "e muitas outras. "
            "Exemplos: '100 dolares em reais', '50 euros em libras', '1000 JPY em USD'."
            "Use quando o usuario perguntar sobre conversao de moeda, cambio ou cotacao."
        ),
        parameters={
            "valor": {
                "type": "number",
                "description": "Valor a ser convertido (ex: 100)",
            },
            "de": {
                "type": "string",
                "description": "Codigo ISO da moeda de origem (ex: USD, BRL, EUR, GBP)",
            },
            "para": {
                "type": "string",
                "description": "Codigo ISO da moeda de destino (ex: BRL, USD, EUR)",
            },
        },
        required=["valor", "de", "para"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Utilitarios",
        "version": "1.0.0",
        "description": "IMC, conversao de unidades e cambio em tempo real",
        "author": "Agente Local",
        "tools": ["calcular_imc", "converter_unidades", "converter_moeda"],
    }
