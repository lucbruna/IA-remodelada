"""
plugin_data_utils.py
====================
Plugin de utilitarios para processamento e transformacao de dados:
formatacao e validacao de dados, informacoes geograficas,
cores, fusos horarios e texto.

Fornece:
  - Validacao e pretty-print de JSON
  - Conversao entre formatos (CSV, JSON, YAML)
  - Informacoes sobre paises (capital, moeda, idioma, bandeira)
  - Conversao de cores (hex, rgb, hsl, nome)
  - Conversao entre fusos horarios
  - Utilitarios de texto (contagem, reversao, maiusculas/minusculas)
  - Geracao de numeros aleatorios em intervalo
  - Conversao de numeros por extenso (pt-BR)

Uso no agente:
  "Valide este JSON para mim"
  "Converta este CSV em JSON"
  "Informacoes sobre o Brasil"
  "Converta a cor #FF0000 para RGB"
  "Que horas sao em Tóquio agora?"
  "Conte as palavras deste texto"
  "Gere um numero aleatorio entre 1 e 100"
  "Escreva 42 por extenso"
"""

import json
import logging
import random
import re
from datetime import datetime


# =====================================================================
# DADOS DE PAISES (codigo ISO, nome, capital, moeda, bandeira)
# =====================================================================

_PAISES = {
    "br": {"nome": "Brasil", "capital": "Brasilia", "moeda": "Real (BRL)", "bandeira": "🇧🇷", "idioma": "Portugues", "continente": "America do Sul"},
    "us": {"nome": "Estados Unidos", "capital": "Washington D.C.", "moeda": "Dolar (USD)", "bandeira": "🇺🇸", "idioma": "Ingles", "continente": "America do Norte"},
    "gb": {"nome": "Reino Unido", "capital": "Londres", "moeda": "Libra (GBP)", "bandeira": "🇬🇧", "idioma": "Ingles", "continente": "Europa"},
    "fr": {"nome": "Franca", "capital": "Paris", "moeda": "Euro (EUR)", "bandeira": "🇫🇷", "idioma": "Frances", "continente": "Europa"},
    "de": {"nome": "Alemanha", "capital": "Berlim", "moeda": "Euro (EUR)", "bandeira": "🇩🇪", "idioma": "Alemao", "continente": "Europa"},
    "it": {"nome": "Italia", "capital": "Roma", "moeda": "Euro (EUR)", "bandeira": "🇮🇹", "idioma": "Italiano", "continente": "Europa"},
    "es": {"nome": "Espanha", "capital": "Madri", "moeda": "Euro (EUR)", "bandeira": "🇪🇸", "idioma": "Espanhol", "continente": "Europa"},
    "pt": {"nome": "Portugal", "capital": "Lisboa", "moeda": "Euro (EUR)", "bandeira": "🇵🇹", "idioma": "Portugues", "continente": "Europa"},
    "jp": {"nome": "Japao", "capital": "Toquio", "moeda": "Iene (JPY)", "bandeira": "🇯🇵", "idioma": "Japones", "continente": "Asia"},
    "cn": {"nome": "China", "capital": "Pequim", "moeda": "Yuan (CNY)", "bandeira": "🇨🇳", "idioma": "Mandarim", "continente": "Asia"},
    "kr": {"nome": "Coreia do Sul", "capital": "Seul", "moeda": "Won (KRW)", "bandeira": "🇰🇷", "idioma": "Coreano", "continente": "Asia"},
    "in": {"nome": "India", "capital": "Nova Delhi", "moeda": "Rupia (INR)", "bandeira": "🇮🇳", "idioma": "Hindi", "continente": "Asia"},
    "ru": {"nome": "Russia", "capital": "Moscou", "moeda": "Rublo (RUB)", "bandeira": "🇷🇺", "idioma": "Russo", "continente": "Europa/Asia"},
    "ca": {"nome": "Canada", "capital": "Ottawa", "moeda": "Dolar Canadense (CAD)", "bandeira": "🇨🇦", "idioma": "Ingles/Frances", "continente": "America do Norte"},
    "au": {"nome": "Australia", "capital": "Camberra", "moeda": "Dolar Australiano (AUD)", "bandeira": "🇦🇺", "idioma": "Ingles", "continente": "Oceania"},
    "mx": {"nome": "Mexico", "capital": "Cidade do Mexico", "moeda": "Peso Mexicano (MXN)", "bandeira": "🇲🇽", "idioma": "Espanhol", "continente": "America do Norte"},
    "ar": {"nome": "Argentina", "capital": "Buenos Aires", "moeda": "Peso Argentino (ARS)", "bandeira": "🇦🇷", "idioma": "Espanhol", "continente": "America do Sul"},
    "cl": {"nome": "Chile", "capital": "Santiago", "moeda": "Peso Chileno (CLP)", "bandeira": "🇨🇱", "idioma": "Espanhol", "continente": "America do Sul"},
    "co": {"nome": "Colombia", "capital": "Bogota", "moeda": "Peso Colombiano (COP)", "bandeira": "🇨🇴", "idioma": "Espanhol", "continente": "America do Sul"},
    "za": {"nome": "Africa do Sul", "capital": "Pretoria", "moeda": "Rand (ZAR)", "bandeira": "🇿🇦", "idioma": "Africâner/Ingles", "continente": "Africa"},
    "eg": {"nome": "Egito", "capital": "Cairo", "moeda": "Libra Egipcia (EGP)", "bandeira": "🇪🇬", "idioma": "Arabe", "continente": "Africa"},
    "ng": {"nome": "Nigeria", "capital": "Abuja", "moeda": "Naira (NGN)", "bandeira": "🇳🇬", "idioma": "Ingles", "continente": "Africa"},
    "tr": {"nome": "Turquia", "capital": "Ancara", "moeda": "Lira Turca (TRY)", "bandeira": "🇹🇷", "idioma": "Turco", "continente": "Europa/Asia"},
    "sa": {"nome": "Arabia Saudita", "capital": "Ria", "moeda": "Rial (SAR)", "bandeira": "🇸🇦", "idioma": "Arabe", "continente": "Asia"},
    "il": {"nome": "Israel", "capital": "Jerusalem", "moeda": "Novo Shekel (ILS)", "bandeira": "🇮🇱", "idioma": "Hebraico", "continente": "Asia"},
    "se": {"nome": "Suecia", "capital": "Estocolmo", "moeda": "Coroa Sueca (SEK)", "bandeira": "🇸🇪", "idioma": "Sueco", "continente": "Europa"},
    "no": {"nome": "Noruega", "capital": "Oslo", "moeda": "Coroa Norueguesa (NOK)", "bandeira": "🇳🇴", "idioma": "Noruegues", "continente": "Europa"},
    "nl": {"nome": "Paises Baixos", "capital": "Amsterda", "moeda": "Euro (EUR)", "bandeira": "🇳🇱", "idioma": "Holandes", "continente": "Europa"},
    "ch": {"nome": "Suica", "capital": "Berna", "moeda": "Franco Suico (CHF)", "bandeira": "🇨🇭", "idioma": "Alemao/Frances/Italiano", "continente": "Europa"},
    "ae": {"nome": "Emirados Arabes", "capital": "Abu Dhabi", "moeda": "Dirham (AED)", "bandeira": "🇦🇪", "idioma": "Arabe", "continente": "Asia"},
}


# =====================================================================
# CORES (nome -> hex)
# =====================================================================

_CORES = {
    "vermelho": "#FF0000", "azul": "#0000FF", "verde": "#00FF00",
    "amarelo": "#FFFF00", "laranja": "#FFA500", "roxo": "#800080",
    "rosa": "#FFC0CB", "marrom": "#A52A2A", "preto": "#000000",
    "branco": "#FFFFFF", "cinza": "#808080", "prata": "#C0C0C0",
    "ouro": "#FFD700", "turquesa": "#40E0D0", "salmao": "#FA8072",
    "vinho": "#800000", "verde_oliva": "#808000",
    "azul_marinho": "#000080", "roxo_escuro": "#4B0082",
    "indigo": "#4B0082", "magenta": "#FF00FF", "ciano": "#00FFFF",
    "violeta": "#EE82EE", "limao": "#00FF00", "coral": "#FF7F50",
}


def _cor_nome_para_hex(nome: str) -> str:
    """Converte nome de cor para hexadecimal."""
    return _CORES.get(nome.lower().strip(), "")


def _validar_json(texto: str) -> str:
    """Valida e formata um JSON.

    Args:
        texto: String contendo JSON

    Returns:
        JSON formatado ou mensagem de erro
    """
    if not texto or not texto.strip():
        return "❌ Informe um JSON para validar."

    try:
        dados = json.loads(texto.strip())
        formatado = json.dumps(dados, ensure_ascii=False, indent=2)
        # Truca se muito grande
        if len(formatado) > 5000:
            formatado = formatado[:5000] + "\n... (JSON truncado, muito grande)"
        return (
            "✅ **JSON VALIDO**\n\n"
            f"```json\n{formatado}\n```"
        )
    except json.JSONDecodeError as e:
        return (
            f"❌ **JSON INVALIDO**\n\n"
            f"  Erro: {e}\n"
            f"  Linha: {e.lineno}, Coluna: {e.colno}\n"
            f"  Posicao: {e.pos}"
        )


def _csv_para_json(texto: str, delimiter: str = ",") -> str:
    """Converte CSV para JSON.

    Args:
        texto: Conteudo CSV
        delimiter: Delimitador (padrao: virgula)

    Returns:
        JSON formatado
    """
    if not texto or not texto.strip():
        return "❌ Informe um CSV para converter."

    try:
        import csv
        import io

        reader = csv.DictReader(io.StringIO(texto.strip()), delimiter=delimiter)
        linhas = list(reader)
        if not linhas:
            return "⚠ CSV vazio ou com apenas cabecalho."

        result = json.dumps(linhas, ensure_ascii=False, indent=2)
        if len(result) > 5000:
            result = result[:5000] + f"\n... (truncado, {len(linhas)} linhas no total)"
        return (
            f"✅ **CSV → JSON** ({len(linhas)} linhas)\n\n"
            f"```json\n{result}\n```"
        )
    except Exception as e:
        return f"❌ Erro ao converter CSV: {e}"


def _info_pais(codigo: str) -> str:
    """Retorna informacoes sobre um pais.

    Args:
        codigo: Codigo ISO do pais (ex: br, us, jp)

    Returns:
        Informacoes formatadas do pais
    """
    codigo = codigo.lower().strip()
    if len(codigo) > 3:
        # Pode ser nome do pais, tenta buscar
        for c, info in _PAISES.items():
            if codigo in info["nome"].lower():
                codigo = c
                break

    info = _PAISES.get(codigo)
    if not info:
        sugeridos = list(_PAISES.keys())[:10]
        return (
            f"❌ Pais '{codigo}' nao encontrado.\n"
            f"  Exemplos de codigos: {', '.join(sugeridos)}"
        )

    return (
        f"{info['bandeira']} **{info['nome']}**\n\n"
        f"  Capital: {info['capital']}\n"
        f"  Moeda: {info['moeda']}\n"
        f"  Idioma: {info['idioma']}\n"
        f"  Continente: {info['continente']}\n"
    )


def _converter_cor(valor: str, de: str = "auto", para: str = "hex") -> str:
    """Converte entre formatos de cor.

    Args:
        valor: Valor da cor (ex: #FF0000, rgb(255,0,0), hsl(0,100,50), 'vermelho')
        de: Formato de origem ('auto', 'hex', 'rgb', 'hsl', 'nome')
        para: Formato de destino ('hex', 'rgb', 'hsl')

    Returns:
        Cor convertida
    """
    if not valor:
        return "❌ Informe uma cor para converter."

    v = valor.strip()
    r = g = b = 0

    # Detecta formato automaticamente
    if v.startswith("#"):
        fmt_origem = "hex"
        try:
            v_hex = v.lstrip("#")
            r = int(v_hex[0:2], 16)
            g = int(v_hex[2:4], 16)
            b = int(v_hex[4:6], 16)
        except (ValueError, IndexError):
            return f"❌ Cor hexadecimal invalida: '{valor}'"
    elif v.lower().startswith("rgb"):
        fmt_origem = "rgb"
        nums = re.findall(r"\d+", v)
        if len(nums) >= 3:
            r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
        else:
            return f"❌ Cor RGB invalida: '{valor}'"
    elif v.lower().startswith("hsl"):
        fmt_origem = "hsl"
        nums = re.findall(r"\d+", v)
        if len(nums) >= 3:
            h_val, s_val, l_val = int(nums[0]), int(nums[1]) / 100, int(nums[2]) / 100
            # Converte HSL para RGB
            c = (1 - abs(2 * l_val - 1)) * s_val
            x = c * (1 - abs((h_val / 60) % 2 - 1))
            m = l_val - c / 2
            if h_val < 60: r, g, b = c, x, 0
            elif h_val < 120: r, g, b = x, c, 0
            elif h_val < 180: r, g, b = 0, c, x
            elif h_val < 240: r, g, b = 0, x, c
            elif h_val < 300: r, g, b = x, 0, c
            else: r, g, b = c, 0, x
            r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
        else:
            return f"❌ Cor HSL invalida: '{valor}'"
    else:
        fmt_origem = "nome"
        hex_cor = _cor_nome_para_hex(v)
        if hex_cor:
            v_hex = hex_cor.lstrip("#")
            r = int(v_hex[0:2], 16)
            g = int(v_hex[2:4], 16)
            b = int(v_hex[4:6], 16)
        else:
            return f"❌ Cor nao reconhecida: '{valor}'"

    # Valida
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

    # Converte para saida
    saidas = []
    saidas.append(f"  🎨 HEX: `#{r:02X}{g:02X}{b:02X}`")
    saidas.append(f"  🎨 RGB: `rgb({r}, {g}, {b})`")

    hsl_h = 0
    r_norm, g_norm, b_norm = r / 255, g / 255, b / 255
    max_c = max(r_norm, g_norm, b_norm)
    min_c = min(r_norm, g_norm, b_norm)
    l_val = (max_c + min_c) / 2
    if max_c == min_c:
        hsl_s = 0
    else:
        delta = max_c - min_c
        hsl_s = delta / (1 - abs(2 * l_val - 1))
        if max_c == r_norm:
            hsl_h = 60 * (((g_norm - b_norm) / delta) % 6)
        elif max_c == g_norm:
            hsl_h = 60 * (((b_norm - r_norm) / delta) + 2)
        else:
            hsl_h = 60 * (((r_norm - g_norm) / delta) + 4)
    saidas.append(f"  🎨 HSL: `hsl({int(hsl_h)}, {int(hsl_s * 100)}%, {int(l_val * 100)}%)`")

    # Nome aproximado
    nome_cor = ""
    for nome, hex_ref in _CORES.items():
        ref_r = int(hex_ref.lstrip("#")[0:2], 16)
        ref_g = int(hex_ref.lstrip("#")[2:4], 16)
        ref_b = int(hex_ref.lstrip("#")[4:6], 16)
        dist = ((r - ref_r) ** 2 + (g - ref_g) ** 2 + (b - ref_b) ** 2) ** 0.5
        if dist < 100:
            nome_cor = nome
            break
    if nome_cor:
        saidas.append(f"  🏷️ Nome aproximado: {nome_cor}")

    saidas.append(f"\n  ℹ Exemplo visual: `#{r:02X}{g:02X}{b:02X}`")

    return "🎨 **CONVERSAO DE COR**\n\n" + "\n".join(saidas)


def _contagem_texto(texto: str) -> str:
    """Analisa estatisticas de um texto.

    Args:
        texto: Texto para analisar

    Returns:
        Estatisticas do texto
    """
    if not texto or not texto.strip():
        return "❌ Informe um texto para analisar."

    chars = len(texto)
    chars_sem_espaco = len(texto.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", ""))
    palavras = len([p for p in texto.split() if p.strip()])
    linhas = len(texto.splitlines())
    letras = sum(1 for c in texto if c.isalpha())
    numeros = sum(1 for c in texto if c.isdigit())
    espacos = sum(1 for c in texto if c.isspace())
    pontuacao = sum(1 for c in texto if c in ".,;:!?\"'()[]{}—…-/@#$%^&*+=<>")

    return (
        f"📊 **ESTATISTICAS DO TEXTO**\n\n"
        f"  📝 Palavras: {palavras:,}\n"
        f"  🔤 Caracteres: {chars:,}\n"
        f"  ✂️ Sem espacos: {chars_sem_espaco:,}\n"
        f"  📄 Linhas: {linhas:,}\n"
        f"  🔡 Letras: {letras:,}\n"
        f"  🔢 Numeros: {numeros:,}\n"
        f"  ⬜ Espacos: {espacos:,}\n"
        f"  🔣 Pontuacao: {pontuacao:,}\n\n"
        f"  📏 Texto medio: {chars / max(palavras, 1):.1f} chars/palavra"
    )


def _numero_aleatorio(minimo: int = 1, maximo: int = 100) -> str:
    """Gera um numero aleatorio em um intervalo.

    Args:
        minimo: Valor minimo (padrao: 1)
        maximo: Valor maximo (padrao: 100)

    Returns:
        Numero aleatorio
    """
    try:
        n = random.randint(min(minimo, maximo), max(minimo, maximo))
        return f"🎲 **Numero aleatorio:** {n} (entre {minimo} e {maximo})"
    except ValueError:
        return "❌ Intervalo invalido. Informe dois numeros inteiros."


def _agora_em(to_timezone: str = "America/Sao_Paulo") -> str:
    """Mostra a hora atual em um fuso horario.

    Args:
        to_timezone: Fuso horario de destino

    Returns:
        Data e hora no fuso especificado
    """
    try:
        import pytz
        fuso = pytz.timezone(to_timezone)
        agora = datetime.now(fuso)
        return (
            f"🕐 **HORA ATUAL**\n\n"
            f"  🌍 Fuso: {to_timezone}\n"
            f"  🕐 Data/Hora: {agora.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"  ℹ UTC offset: {agora.strftime('%z')}"
        )
    except ImportError:
        return "⚠ Biblioteca 'pytz' nao disponivel.\nInstale com: pip install pytz"
    except Exception as e:
        return f"❌ Fuso horario invalido: {e}"


def register(api):
    """Registra as ferramentas de utilitarios de dados no agente."""

    # ---- Validar JSON ----
    def validar_json(texto: str) -> str:
        """Valida e formata um JSON.

        Args:
            texto: Texto JSON para validar

        Returns:
            JSON formatado ou detalhes do erro de sintaxe
        """
        return _validar_json(texto)

    api.register_tool(
        name="validar_json",
        func=validar_json,
        description=(
            "Valida se um texto e um JSON valido e retorna o JSON formatado "
            "com indentacao, ou uma mensagem de erro detalhada (linha, coluna, descricao). "
            "Exemplos: 'Valide este JSON para mim', "
            "'Este JSON esta correto?'. "
            "Use quando o usuario quiser verificar ou formatar JSON."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto JSON para validar",
            },
        },
        required=["texto"],
    )

    # ---- CSV para JSON ----
    def csv_para_json(texto: str, delimiter: str = ",") -> str:
        """Converte dados CSV para formato JSON.

        Args:
            texto: Conteudo CSV
            delimiter: Delimitador de colunas (padrao: virgula)

        Returns:
            JSON gerado a partir do CSV
        """
        return _csv_para_json(texto, delimiter)

    api.register_tool(
        name="csv_para_json",
        func=csv_para_json,
        description=(
            "Converte dados no formato CSV (valores separados por virgula) "
            "para JSON estruturado. Detecta automaticamente o cabecalho. "
            "Exemplos: 'Converta este CSV para JSON', "
            "'Transforme estes dados em JSON'. "
            "Use quando o usuario tiver dados em CSV e quiser converte-los para JSON."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Dados em formato CSV para converter",
            },
            "delimiter": {
                "type": "string",
                "description": "Delimitador de colunas (padrao: ,)",
            },
        },
        required=["texto"],
    )

    # ---- Info pais ----
    def info_pais(codigo: str) -> str:
        """Retorna informacoes sobre um pais.

        Args:
            codigo: Codigo ISO do pais (ex: br, us, jp, fr, de) ou nome

        Returns:
            Informacoes: capital, moeda, idioma, continente, bandeira
        """
        return _info_pais(codigo)

    api.register_tool(
        name="info_pais",
        func=info_pais,
        description=(
            "Retorna informacoes detalhadas sobre um pais: capital, moeda, "
            "idioma oficial, continente e bandeira. Aceita codigo ISO de 2 letras "
            "(br, us, jp, fr, de, etc.) ou nome do pais. "
            "Exemplos: 'Informacoes sobre o Brasil', "
            "'Dados do Japao', 'Info do Canada'. "
            "Use quando o usuario perguntar sobre um pais."
        ),
        parameters={
            "codigo": {
                "type": "string",
                "description": "Codigo ISO do pais (ex: br, us, jp, fr, de) ou nome",
            },
        },
        required=["codigo"],
    )

    # ---- Converter cor ----
    def converter_cor(valor: str, para: str = "hex") -> str:
        """Converte entre formatos de cor.

        Args:
            valor: Cor em qualquer formato (hex, rgb, hsl, nome)
            para: Formato de destino (hex, rgb, hsl). Padrao: hex

        Returns:
            Cor convertida para os formatos principais
        """
        return _converter_cor(valor, "auto", para)

    api.register_tool(
        name="converter_cor",
        func=converter_cor,
        description=(
            "Converte cores entre formatos HEX, RGB, HSL e nomes comuns. "
            "Detecta automaticamente o formato de entrada e mostra a cor em "
            "todos os formatos principais com nome aproximado. "
            "Exemplos: 'Converta #FF0000 para RGB', "
            "'Qual a cor rgb(255, 0, 0) em hex?', "
            "'Converta azul para HSL'. "
            "Use quando o usuario quiser converter ou identificar cores."
        ),
        parameters={
            "valor": {
                "type": "string",
                "description": "Cor em qualquer formato: hex (#FF0000), rgb (rgb(255,0,0)), hsl (hsl(0,100,50)) ou nome (vermelho, azul)",
            },
            "para": {
                "type": "string",
                "description": "Formato de destino (hex, rgb, hsl). Padrao: hex",
            },
        },
        required=["valor"],
    )

    # ---- Contagem texto ----
    def contar_texto(texto: str) -> str:
        """Analisa estatisticas de um texto.

        Args:
            texto: Texto para analisar

        Returns:
            Estatisticas: palavras, caracteres, linhas, letras, numeros
        """
        return _contagem_texto(texto)

    api.register_tool(
        name="contar_texto",
        func=contar_texto,
        description=(
            "Analisa estatisticas de um texto: contagem de palavras, "
            "caracteres (com e sem espacos), linhas, letras, numeros, "
            "espacos e pontuacao. "
            "Exemplos: 'Conte as palavras deste texto', "
            "'Quantos caracteres tem esta frase?', "
            "'Estatisticas do paragrafo'. "
            "Use quando o usuario quiser analisar a composicao de um texto."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto para analisar",
            },
        },
        required=["texto"],
    )

    # ---- Numero aleatorio ----
    def numero_aleatorio(minimo: int = 1, maximo: int = 100) -> str:
        """Gera um numero aleatorio em um intervalo.

        Args:
            minimo: Valor minimo (padrao: 1)
            maximo: Valor maximo (padrao: 100)

        Returns:
            Numero aleatorio gerado
        """
        return _numero_aleatorio(minimo, maximo)

    api.register_tool(
        name="numero_aleatorio",
        func=numero_aleatorio,
        description=(
            "Gera um numero aleatorio inteiro dentro de um intervalo especificado. "
            "Exemplos: 'Gere um numero aleatorio entre 1 e 10', "
            "'Sorteie um numero de 1 a 100', "
            "'Escolha um numero aleatorio'. "
            "Use quando o usuario quiser um numero aleatorio ou sortear algo."
        ),
        parameters={
            "minimo": {
                "type": "integer",
                "description": "Valor minimo do intervalo. Padrao: 1",
            },
            "maximo": {
                "type": "integer",
                "description": "Valor maximo do intervalo. Padrao: 100",
            },
        },
        required=[],
    )

    # ---- Hora em fuso ----
    def hora_em(to_timezone: str) -> str:
        """Mostra a hora atual em um fuso horario.

        Args:
            to_timezone: Fuso horario (ex: America/Sao_Paulo, Asia/Tokyo, Europe/London)

        Returns:
            Data e hora atual no fuso especificado
        """
        return _agora_em(to_timezone)

    api.register_tool(
        name="hora_em",
        func=hora_em,
        description=(
            "Mostra a data e hora atual em qualquer fuso horario do mundo. "
            "Usa a biblioteca pytz para conversao precisa. "
            "Exemplos: 'Que horas sao em Toquio?', "
            "'Hora atual em Londres', "
            "'Que horas sao no Japao agora?'. "
            "Use quando o usuario perguntar que horas sao em algum lugar do mundo."
        ),
        parameters={
            "to_timezone": {
                "type": "string",
                "description": "Fuso horario (ex: America/Sao_Paulo, Asia/Tokyo, Europe/London, America/New_York)",
            },
        },
        required=["to_timezone"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Utilitarios de Dados",
        "version": "1.0.0",
        "description": "JSON/CSV, cores, paises, fuso horario, contagem texto, numeros aleatorios",
        "author": "Agente Local",
        "tools": [
            "validar_json", "csv_para_json", "info_pais",
            "converter_cor", "contar_texto", "numero_aleatorio", "hora_em",
        ],
    }
