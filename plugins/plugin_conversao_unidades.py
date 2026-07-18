"""
plugin_conversao_unidades.py
=============================
Plugin de conversao entre unidades de medida: temperatura, comprimento,
peso/massa, volume, velocidade, area, tempo, pressao, energia, dados digitais.

Uso no agente:
  "Converta 25 graus Celsius para Fahrenheit"
  "Quanto e 1 metro em pes?"
  "Converta 5 kg para libras"
  "100 km/h em milhas por hora"
  "10 GB em MB"
"""

import logging


# =====================================================================
# DEFINICOES DE UNIDADES
# =====================================================================

_CATEGORIAS = {
    "temperatura": {
        "nome": "Temperatura",
        "icone": "🌡️",
        "unidades": ["celsius", "fahrenheit", "kelvin"],
    },
    "comprimento": {
        "nome": "Comprimento",
        "icone": "📏",
        "unidades": ["metro", "quilometro", "centimetro", "milimetro",
                     "micrometro", "nanometro", "milha", "jarda", "pe",
                     "polegada", "milha_nautica"],
    },
    "massa": {
        "nome": "Peso/Massa",
        "icone": "⚖️",
        "unidades": ["quilograma", "grama", "miligrama", "tonelada",
                     "libra", "onca", "pedra"],
    },
    "volume": {
        "nome": "Volume",
        "icone": "🧪",
        "unidades": ["litro", "mililitro", "metro_cubico",
                     "galao", "quartilho", "pinta", "xicara",
                     "colher_sopa", "colher_cha", "onca_liquida"],
    },
    "velocidade": {
        "nome": "Velocidade",
        "icone": "🚀",
        "unidades": ["km_h", "m_s", "mph", "nos", "velocidade_luz"],
    },
    "area": {
        "nome": "Area",
        "icone": "📐",
        "unidades": ["metro_quadrado", "quilometro_quadrado",
                     "hectare", "acre", "pe_quadrado", "jarda_quadrada"],
    },
    "tempo": {
        "nome": "Tempo",
        "icone": "⏱️",
        "unidades": ["segundo", "minuto", "hora", "dia", "semana", "mes", "ano"],
    },
    "pressao": {
        "nome": "Pressao",
        "icone": "💨",
        "unidades": ["pascal", "hectopascal", "kpa", "atm", "bar",
                     "mmhg", "psi", "torr"],
    },
    "energia": {
        "nome": "Energia",
        "icone": "⚡",
        "unidades": ["joule", "quilojoule", "caloria", "quilocaloria",
                     "watt_hora", "quilowatt_hora", "ev", "btu"],
    },
    "dados": {
        "nome": "Dados Digitais",
        "icone": "💾",
        "unidades": ["byte", "kilobyte", "megabyte", "gigabyte",
                     "terabyte", "petabyte", "bit", "kibibit", "mebibit"],
    },
}

# Mapeamento de alias e normalizacao de nomes
_ALIASES = {
    "c": "celsius", "f": "fahrenheit", "k": "kelvin",
    "m": "metro", "km": "quilometro", "cm": "centimetro", "mm": "milimetro",
    "um": "micrometro", "nm": "nanometro",
    "mi": "milha", "yd": "jarda", "ft": "pe", "in": "polegada",
    "kg": "quilograma", "g": "grama", "mg": "miligrama", "t": "tonelada",
    "lb": "libra", "oz": "onca", "st": "pedra",
    "l": "litro", "ml": "mililitro", "m3": "metro_cubico",
    "gal": "galao", "qt": "quartilho", "pt": "pinta",
    "cup": "xicara", "tbsp": "colher_sopa", "tsp": "colher_cha",
    "fl_oz": "onca_liquida",
    "kmh": "km_h", "km/h": "km_h", "ms": "m_s", "m/s": "m_s",
    "mph": "mph", "kn": "nos",
    "m2": "metro_quadrado", "km2": "quilometro_quadrado",
    "ha": "hectare", "ac": "acre",
    "s": "segundo", "min": "minuto", "h": "hora", "d": "dia",
    "sem": "semana", "mes": "mes", "a": "ano",
    "pa": "pascal", "hpa": "hectopascal", "kpa": "kpa",
    "atm": "atm", "bar": "bar", "mmhg": "mmhg",
    "j": "joule", "kj": "quilojoule", "cal": "caloria", "kcal": "quilocaloria",
    "wh": "watt_hora", "kwh": "quilowatt_hora",
    "b": "byte", "kb": "kilobyte", "mb": "megabyte", "gb": "gigabyte",
    "tb": "terabyte", "pb": "petabyte",
}


# =====================================================================
# FUNCOES DE CONVERSAO (para cada unidade -> valor base SI)
# =====================================================================

# Temperatura: base = Kelvin
def _temp_para_base(valor, unidade):
    if unidade == "celsius": return valor + 273.15
    if unidade == "fahrenheit": return (valor - 32) * 5/9 + 273.15
    if unidade == "kelvin": return valor

def _temp_da_base(valor, unidade):
    if unidade == "celsius": return round(valor - 273.15, 2)
    if unidade == "fahrenheit": return round((valor - 273.15) * 9/5 + 32, 2)
    if unidade == "kelvin": return valor

# Comprimento: base = metro
_CONV_COMPRIMENTO = {
    "metro": 1, "quilometro": 1000, "centimetro": 0.01, "milimetro": 0.001,
    "micrometro": 1e-6, "nanometro": 1e-9,
    "milha": 1609.344, "jarda": 0.9144, "pe": 0.3048, "polegada": 0.0254,
    "milha_nautica": 1852,
}

# Massa: base = quilograma
_CONV_MASSA = {
    "quilograma": 1, "grama": 0.001, "miligrama": 1e-6, "tonelada": 1000,
    "libra": 0.45359237, "onca": 0.0283495, "pedra": 6.35029,
}

# Volume: base = litro
_CONV_VOLUME = {
    "litro": 1, "mililitro": 0.001, "metro_cubico": 1000,
    "galao": 3.78541, "quartilho": 0.946353, "pinta": 0.473176,
    "xicara": 0.236588, "colher_sopa": 0.0147868, "colher_cha": 0.00492892,
    "onca_liquida": 0.0295735,
}

# Velocidade: base = m/s
_CONV_VELOCIDADE = {
    "m_s": 1, "km_h": 0.277778, "mph": 0.44704, "nos": 0.514444,
    "velocidade_luz": 299792458,
}

# Area: base = metro quadrado
_CONV_AREA = {
    "metro_quadrado": 1, "quilometro_quadrado": 1e6,
    "hectare": 10000, "acre": 4046.86,
    "pe_quadrado": 0.092903, "jarda_quadrada": 0.836127,
}

# Tempo: base = segundo
_CONV_TEMPO = {
    "segundo": 1, "minuto": 60, "hora": 3600, "dia": 86400,
    "semana": 604800, "mes": 2592000, "ano": 31536000,
}

# Pressao: base = pascal
_CONV_PRESSAO = {
    "pascal": 1, "hectopascal": 100, "kpa": 1000,
    "atm": 101325, "bar": 100000,
    "mmhg": 133.322, "psi": 6894.76, "torr": 133.322,
}

# Energia: base = joule
_CONV_ENERGIA = {
    "joule": 1, "quilojoule": 1000, "caloria": 4.184, "quilocaloria": 4184,
    "watt_hora": 3600, "quilowatt_hora": 3.6e6,
    "ev": 1.602e-19, "btu": 1055.06,
}

# Dados digitais: base = byte
_CONV_DADOS = {
    "bit": 0.125, "byte": 1,
    "kilobyte": 1000, "megabyte": 1e6, "gigabyte": 1e9,
    "terabyte": 1e12, "petabyte": 1e15,
    "kibibit": 128, "mebibit": 131072,
}

# Categoria -> (conversao para base, conversao da base)
_CONVERSORES = {
    "temperatura": (_temp_para_base, _temp_da_base),
    "comprimento": (_CONV_COMPRIMENTO, None),
    "massa": (_CONV_MASSA, None),
    "volume": (_CONV_VOLUME, None),
    "velocidade": (_CONV_VELOCIDADE, None),
    "area": (_CONV_AREA, None),
    "tempo": (_CONV_TEMPO, None),
    "pressao": (_CONV_PRESSAO, None),
    "energia": (_CONV_ENERGIA, None),
    "dados": (_CONV_DADOS, None),
}


def _normalizar_unidade(unidade: str) -> str:
    """Normaliza nome de unidade (alias -> nome padrao)."""
    u = unidade.lower().strip().replace("-", "_").replace(" ", "_")
    return _ALIASES.get(u, u)


def _encontrar_categoria(unidade: str) -> str:
    """Encontra a categoria de uma unidade."""
    for cat, info in _CATEGORIAS.items():
        if unidade in info["unidades"]:
            return cat
    return ""


def _converter(valor: float, de: str, para: str) -> str:
    """Converte um valor entre duas unidades.

    Args:
        valor: Valor numerico
        de: Unidade de origem
        para: Unidade de destino

    Returns:
        String com resultado ou mensagem de erro
    """
    de_norm = _normalizar_unidade(de)
    para_norm = _normalizar_unidade(para)

    if not de_norm or not para_norm:
        return "❌ Informe as unidades de origem e destino (ex: 'metro' 'pe')."

    cat_de = _encontrar_categoria(de_norm)
    cat_para = _encontrar_categoria(para_norm)

    if not cat_de:
        return f"❌ Unidade '{de}' nao reconhecida."
    if not cat_para:
        return f"❌ Unidade '{para}' nao reconhecida."
    if cat_de != cat_para:
        return f"❌ Unidades incompatíveis: '{de}' ({_CATEGORIAS[cat_de]['nome']}) e '{para}' ({_CATEGORIAS[cat_para]['nome']})"

    info = _CONVERSORES[cat_de]
    nome_cat = _CATEGORIAS[cat_de]["nome"]
    icone = _CATEGORIAS[cat_de]["icone"]

    if cat_de == "temperatura":
        # Usa funcoes especiais
        para_base = _temp_para_base(valor, de_norm)
        resultado = _temp_da_base(para_base, para_norm)
    else:
        tabela = info[0]
        fator_de = tabela.get(de_norm)
        fator_para = tabela.get(para_norm)

        if fator_de is None:
            return f"❌ Unidade '{de}' nao reconhecida."
        if fator_para is None:
            return f"❌ Unidade '{para}' nao reconhecida."

        # Converte para base e depois para destino
        valor_base = valor * fator_de
        resultado = valor_base / fator_para

    # Formata o resultado
    if isinstance(resultado, float):
        if abs(resultado) >= 10000:
            resultado_str = f"{resultado:,.2f}"
        elif abs(resultado) >= 1:
            resultado_str = f"{resultado:.4f}".rstrip("0").rstrip(".")
        elif abs(resultado) >= 0.001:
            resultado_str = f"{resultado:.6f}"
        else:
            resultado_str = f"{resultado:.2e}"
    else:
        resultado_str = str(resultado)

    # Formata valor de entrada
    valor_str = f"{valor:,.2f}" if isinstance(valor, float) else str(valor)

    # Taxas de conversao (evita divisao por zero)
    taxa_direta = resultado / valor if valor != 0 else 0
    taxa_inversa = valor / resultado if resultado != 0 else 0

    return (
        f"{icone} **CONVERSAO DE {nome_cat.upper()}**\n\n"
        f"  {valor_str} **{de_norm}**\n"
        f"  = **{resultado_str} {para_norm}**\n\n"
        f"  ℹ 1 {de_norm} = {taxa_direta:.6f} {para_norm}\n"
        f"  ℹ 1 {para_norm} = {taxa_inversa:.6f} {de_norm}"
    )


def _listar_unidades(categoria: str = "") -> str:
    """Lista as unidades disponiveis para conversao.

    Args:
        categoria: Categoria especifica ou vazio para todas

    Returns:
        String formatada com as unidades
    """
    if categoria:
        categoria = categoria.lower().strip()
        if categoria not in _CATEGORIAS:
            return f"❌ Categoria '{categoria}' nao encontrada. Categorias: {', '.join(_CATEGORIAS.keys())}"
        cats = {categoria: _CATEGORIAS[categoria]}
    else:
        cats = _CATEGORIAS

    linhas = ["📐 **UNIDADES DISPONIVEIS**\n"]
    for cat_id, info in cats.items():
        linhas.append(f"  {info['icone']} **{info['nome']}:**")
        for u in info["unidades"]:
            alias_encontrados = [a for a, n in _ALIASES.items() if n == u]
            alias_str = f" ({', '.join(alias_encontrados[:3])})" if alias_encontrados else ""
            linhas.append(f"    • `{u}`{alias_str}")
        linhas.append("")

    return "\n".join(linhas)


def register(api):
    """Registra as ferramentas de conversao no agente."""

    # ---- Converter unidade ----
    def converter_unidade(valor: float, de: str, para: str) -> str:
        """Converte um valor entre duas unidades de medida.

        Args:
            valor: Valor numerico a ser convertido
            de: Unidade de origem (ex: metro, kg, celsius, litro, km_h)
            para: Unidade de destino (ex: pe, libra, fahrenheit, galao, mph)

        Returns:
            Valor convertido com detalhes da conversao
        """
        return _converter(valor, de, para)

    api.register_tool(
        name="converter_unidade",
        func=converter_unidade,
        description=(
            "Converte valores entre unidades de medida: temperatura (celsius, fahrenheit, kelvin), "
            "comprimento (metro, km, cm, mm, milha, jarda, pe, polegada), "
            "peso/massa (kg, g, libra, onca, tonelada), "
            "volume (litro, galao, ml, metro cubico), "
            "velocidade (km/h, m/s, mph, nos), "
            "area (m2, km2, hectare, acre), "
            "tempo (segundo, minuto, hora, dia, mes, ano), "
            "pressao (pascal, atm, bar, psi, mmhg), "
            "energia (joule, caloria, kWh, BTU), "
            "dados digitais (byte, KB, MB, GB, TB). "
            "Exemplos: 'Converta 25 celsius para fahrenheit', "
            "'1 metro em pes', '5 kg em libras', "
            "'100 km/h em mph', '10 GB em MB'. "
            "Use quando o usuario pedir conversao entre unidades de medida."
        ),
        parameters={
            "valor": {
                "type": "number",
                "description": "Valor numerico a ser convertido",
            },
            "de": {
                "type": "string",
                "description": "Unidade de origem (ex: metro, celsius, kg, litro, km_h)",
            },
            "para": {
                "type": "string",
                "description": "Unidade de destino (ex: pe, fahrenheit, libra, galao)",
            },
        },
        required=["valor", "de", "para"],
    )

    # ---- Listar unidades ----
    def listar_unidades(categoria: str = "") -> str:
        """Lista as unidades de medida disponiveis para conversao.

        Args:
            categoria: Categoria para filtrar (temperatura, comprimento, massa, volume, velocidade, area, tempo, pressao, energia, dados)

        Returns:
            Lista de unidades com alias e icones
        """
        return _listar_unidades(categoria)

    api.register_tool(
        name="listar_unidades",
        func=listar_unidades,
        description=(
            "Lista todas as unidades de medida disponiveis para conversao, "
            "organizadas por categoria com alias e icones. "
            "Opcionalmente filtra por uma categoria especifica. "
            "Exemplos: 'Liste as unidades disponiveis', "
            "'Quais unidades de temperatura existem?', "
            "'Mostre as unidades de comprimento'. "
            "Use quando o usuario quiser saber quais unidades estao disponiveis."
        ),
        parameters={
            "categoria": {
                "type": "string",
                "description": "Categoria para filtrar (temperatura, comprimento, massa, volume, velocidade, area, tempo, pressao, energia, dados). Vazio = todas",
            },
        },
        required=[],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Conversao de Unidades",
        "version": "1.0.0",
        "description": "Converte entre 60+ unidades: temperatura, comprimento, massa, volume, velocidade, area, tempo, pressao, energia, dados",
        "author": "Agente Local",
        "tools": ["converter_unidade", "listar_unidades"],
    }
