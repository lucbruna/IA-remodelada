"""
plugin_cambio.py
=================
Plugin de cotacao de moedas em TEMPO REAL usando a API gratuita
exchangerate-api.com (sem necessidade de API key).

Fornece:
  - Conversao entre quaisquer moedas (USD, BRL, EUR, GBP, JPY, etc.)
  - Listagem de taxas atuais para uma moeda base
  - Flags e nomes completos das moedas

Uso no agente:
  "Converta 100 dolares em reais"
  "Qual a cotacao do dolar hoje?"
  "Taxa do euro para libra"

API: https://www.exchangerate-api.com/
"""

import json
import logging
from datetime import datetime

# URL da API gratuita (base USD, sem API key)
_URL_CAMBIO = "https://api.exchangerate-api.com/v4/latest/USD"

# (nome, simbolo, flag)
_MOEDAS = {
    "USD": ("Dolar Americano", "US$", "🇺🇸"),
    "EUR": ("Euro", "€", "🇪🇺"),
    "GBP": ("Libra Esterlina", "£", "🇬🇧"),
    "JPY": ("Iene Japonês", "¥", "🇯🇵"),
    "BRL": ("Real Brasileiro", "R$", "🇧🇷"),
    "CAD": ("Dolar Canadense", "C$", "🇨🇦"),
    "AUD": ("Dolar Australiano", "A$", "🇦🇺"),
    "CHF": ("Franco Suico", "Fr", "🇨🇭"),
    "CNY": ("Yuan Chines", "¥", "🇨🇳"),
    "ARS": ("Peso Argentino", "$", "🇦🇷"),
    "MXN": ("Peso Mexicano", "$", "🇲🇽"),
    "INR": ("Rupia Indiana", "₹", "🇮🇳"),
    "KRW": ("Won Sul-Coreano", "₩", "🇰🇷"),
    "SEK": ("Coroa Sueca", "kr", "🇸🇪"),
    "NOK": ("Coroa Norueguesa", "kr", "🇳🇴"),
    "DKK": ("Coroa Dinamarquesa", "kr", "🇩🇰"),
    "NZD": ("Dolar Neozelandes", "NZ$", "🇳🇿"),
    "SGD": ("Dolar de Cingapura", "S$", "🇸🇬"),
    "HKD": ("Dolar de Hong Kong", "HK$", "🇭🇰"),
    "TRY": ("Lira Turca", "₺", "🇹🇷"),
    "RUB": ("Rublo Russo", "₽", "🇷🇺"),
    "ZAR": ("Rand Sul-Africano", "R", "🇿🇦"),
    "PLN": ("Zloty Polones", "zł", "🇵🇱"),
    "THB": ("Baht Tailandes", "฿", "🇹🇭"),
    "IDR": ("Rupia Indonésia", "Rp", "🇮🇩"),
    "HUF": ("Forint Hungaro", "Ft", "🇭🇺"),
    "CZK": ("Coroa Tcheca", "Kč", "🇨🇿"),
    "ILS": ("Novo Shekel Israelense", "₪", "🇮🇱"),
    "CLP": ("Peso Chileno", "$", "🇨🇱"),
    "PHP": ("Peso Filipino", "₱", "🇵🇭"),
    "AED": ("Dirham dos Emirados", "د.إ", "🇦🇪"),
    "SAR": ("Rial Saudita", "﷼", "🇸🇦"),
    "EGP": ("Libra Egipcia", "£", "🇪🇬"),
    "NGN": ("Naira Nigeriana", "₦", "🇳🇬"),
    "UAH": ("Hrivna Ucraniana", "₴", "🇺🇦"),
    "VND": ("Dong Vietnamita", "₫", "🇻🇳"),
    "MYR": ("Ringgit Malaio", "RM", "🇲🇾"),
    "TWD": ("Dolar Taiwanes", "NT$", "🇹🇼"),
    "PKR": ("Rupia Paquistanesa", "₨", "🇵🇰"),
    "COP": ("Peso Colombiano", "$", "🇨🇴"),
    "PEN": ("Sol Peruano", "S/", "🇵🇪"),
    "MAD": ("Dirham Marroquino", "د.م.", "🇲🇦"),
    "KWD": ("Dinar Kuwaitiano", "د.ك", "🇰🇼"),
    "QAR": ("Rial Catari", "﷼", "🇶🇦"),
    "OMR": ("Rial Omanense", "﷼", "🇴🇲"),
    "BHD": ("Dinar Bareinita", "د.ب", "🇧🇭"),
    "UYU": ("Peso Uruguaio", "$", "🇺🇾"),
    "BOB": ("Boliviano", "Bs", "🇧🇴"),
    "PYG": ("Guarani Paraguaio", "₲", "🇵🇾"),
    "CRC": ("Colon Costarriquenho", "₡", "🇨🇷"),
    "DOP": ("Peso Dominicano", "RD$", "🇩🇴"),
    "GTQ": ("Quetzal Guatemalteco", "Q", "🇬🇹"),
    "HNL": ("Lempira Hondurenha", "L", "🇭🇳"),
    "NIO": ("Cordoba Nicaraguense", "C$", "🇳🇮"),
    "PAB": ("Balboa Panamenho", "B/.", "🇵🇦"),
    "TTD": ("Dolar de Trinidad", "TT$", "🇹🇹"),
    "VES": ("Bolivar Venezuelano", "Bs.S", "🇻🇪"),
    "XOF": ("Franco CFA (BCEAO)", "Fr", "🏗️"),
    "XAF": ("Franco CFA (BEAC)", "Fr", "🏗️"),
    "CDF": ("Franco Congoles", "Fr", "🇨🇩"),
    "TND": ("Dinar Tunisiano", "د.ت", "🇹🇳"),
    "DZD": ("Dinar Argelino", "د.ج", "🇩🇿"),
    "AFN": ("Afegane Afegao", "؋", "🇦🇫"),
    "BDT": ("Taka Bangladeshi", "৳", "🇧🇩"),
    "LKR": ("Rupia Cingalesa", "Rs", "🇱🇰"),
    "MMK": ("Kyat Mianmarense", "K", "🇲🇲"),
    "KHR": ("Riel Cambojano", "៛", "🇰🇭"),
    "LAK": ("Kip Laosiano", "₭", "🇱🇦"),
    "MNT": ("Tugrik Mongol", "₮", "🇲🇳"),
    "NPR": ("Rupia Nepalesa", "₨", "🇳🇵"),
}

# Moedas mais comuns para exibicao rapida
_MOEDAS_PRINCIPAIS = ["USD", "BRL", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "ARS"]


def _info_moeda(codigo: str) -> tuple:
    """Retorna (nome, simbolo, flag) para uma moeda, ou fallback."""
    info = _MOEDAS.get(codigo)
    if info:
        return info
    return (codigo, "$", "💱")


def _consultar_taxas() -> dict:
    """Busca taxas de cambio da API exchangerate-api.com.

    Returns:
        dict com 'rates', 'date', 'base' ou dict de erro com 'erro'
    """
    try:
        import requests
    except ImportError:
        return {"erro": "⚠ Biblioteca 'requests' nao instalada.\nInstale com: pip install requests"}

    try:
        resp = requests.get(_URL_CAMBIO, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        logging.warning("Timeout ao consultar exchangerate-api")
        return {"erro": "⏱ Tempo esgotado ao consultar taxas de cambio."}
    except requests.exceptions.ConnectionError:
        logging.warning("Sem conexao ao consultar exchangerate-api")
        return {"erro": "🌐 Sem conexao com a internet para consultar cambio."}
    except json.JSONDecodeError:
        logging.warning("JSON invalido do exchangerate-api")
        return {"erro": "⚠ Resposta invalida do servidor de cambio."}
    except requests.exceptions.HTTPError as e:
        logging.warning("Erro HTTP no exchangerate-api: %s", e)
        return {"erro": f"❌ Erro HTTP ao consultar cambio: {e}"}
    except Exception as e:
        logging.error("Erro no plugin cambio: %s", e)
        return {"erro": f"❌ Erro inesperado ao consultar cambio: {e}"}


def _converter(valor: float, de: str, para: str) -> str:
    """Converte valor entre duas moedas."""
    de = de.upper().strip()
    para = para.upper().strip()

    if not de or not para:
        return "❌ Informe as moedas de origem e destino (ex: USD BRL)."

    dados = _consultar_taxas()
    if "erro" in dados:
        return dados["erro"]

    taxas = dados.get("rates", {})
    data_ref = dados.get("date", "hoje")

    if de not in taxas:
        sugestoes = [m for m in _MOEDAS_PRINCIPAIS if m in taxas]
        return f"❌ Moeda '{de}' nao reconhecida. Exemplos: {', '.join(sugestoes)}"
    if para not in taxas:
        return f"❌ Moeda '{para}' nao reconhecida."

    if de == para:
        nome, simb, bandeira = _info_moeda(de)
        return (
            f"{bandeira} **{valor:,.2f} {simb} ({de})**\n"
            f"  = **{valor:,.2f} {simb} ({para})**\n"
            f"  ℹ Mesma moeda — sem conversao necessaria."
        )

    # Converte via USD (base da API)
    taxa_origem = taxas[de]
    taxa_destino = taxas[para]
    taxa_direta = taxa_destino / taxa_origem
    resultado = valor * taxa_direta

    nome_de, simb_de, bandeira_de = _info_moeda(de)
    nome_para, simb_para, bandeira_para = _info_moeda(para)

    # Formata data
    try:
        dt = datetime.strptime(data_ref, "%Y-%m-%d")
        data_formatada = dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        data_formatada = str(data_ref)

    return (
        f"{bandeira_de} **{simb_de} {valor:,.2f}** {de} ({nome_de})\n"
        f"  = {bandeira_para} **{simb_para} {resultado:,.2f}** {para} ({nome_para})\n"
        f"\n"
        f"  📊 Taxa: **1 {de} = {taxa_direta:.6f} {para}**\n"
        f"  🔄 1 {para} = {1/taxa_direta:.6f} {de}\n"
        f"  📅 Data: {data_formatada}\n"
        f"  ℹ Fonte: exchangerate-api.com"
    )


def _listar_taxas(moeda_base: str = "USD") -> str:
    """Lista as principais taxas de cambio para uma moeda base."""
    moeda_base = moeda_base.upper().strip()

    dados = _consultar_taxas()
    if "erro" in dados:
        return dados["erro"]

    taxas = dados.get("rates", {})
    data_ref = dados.get("date", "hoje")

    if moeda_base not in taxas and moeda_base != "USD":
        return f"❌ Moeda '{moeda_base}' nao reconhecida."

    try:
        dt = datetime.strptime(data_ref, "%Y-%m-%d")
        data_formatada = dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        data_formatada = str(data_ref)

    nome_base, simb_base, bandeira_base = _info_moeda(moeda_base)
    valor_base_em_usd = taxas.get(moeda_base, 1.0) if moeda_base != "USD" else 1.0

    linhas = [
        f"{bandeira_base} **COTACOES — {nome_base} ({simb_base})**\n",
        f"  Base: {moeda_base}  |  Data: {data_formatada}\n",
    ]

    for codigo in _MOEDAS_PRINCIPAIS:
        if codigo == moeda_base:
            continue
        if codigo not in taxas:
            continue

        taxa = taxas[codigo] / valor_base_em_usd
        nome, simb, bandeira = _info_moeda(codigo)
        linhas.append(
            f"  {bandeira} **{codigo}** {nome:<20} {simb} **{taxa:,.6f}**"
        )

    # Se a moeda base nao for USD, mostra USD tambem
    if moeda_base != "USD" and "USD" in taxas:
        taxa_usd = 1.0 / valor_base_em_usd
        nome, simb, bandeira = _info_moeda("USD")
        linhas.append(f"  {bandeira} **USD** {nome:<20} {simb} **{taxa_usd:,.6f}**")

    linhas.append(f"\n  ℹ Fonte: exchangerate-api.com")
    return "\n".join(linhas)


def register(api):
    """Registra as ferramentas de cambio no agente."""

    # ---- Converter moeda ----
    def converter_moeda(valor: float, de: str, para: str) -> str:
        """Converte um valor entre duas moedas usando taxa de cambio atual.

        Args:
            valor: Valor numerico a ser convertido (ex: 100)
            de: Codigo ISO da moeda de origem (ex: USD, BRL, EUR)
            para: Codigo ISO da moeda de destino (ex: BRL, USD, EUR)

        Returns:
            Valor convertido com taxa de cambio e bandeiras
        """
        return _converter(valor, de, para)

    api.register_tool(
        name="cambio_moeda",
        func=converter_moeda,
        description=(
            "Converte valores entre moedas usando taxa de cambio ATUAL via API gratuita. "
            "Retorna o valor convertido, a taxa de cambio utilizada, "
            "bandeiras e nomes das moedas. "
            "Funciona com USD, BRL, EUR, GBP, JPY, CAD, AUD, CHF, CNY e 60+ moedas. "
            "Exemplos: '100 dolares em reais', '50 euros para libras', "
            "'1000 ienes em dolar'. "
            "Use quando o usuario perguntar sobre conversao de moeda, "
            "cambio, cotacao ou 'quanto vale X em Y'."
        ),
        parameters={
            "valor": {
                "type": "number",
                "description": "Valor a ser convertido (ex: 100.50)",
            },
            "de": {
                "type": "string",
                "description": "Codigo ISO da moeda de origem (ex: USD, BRL, EUR, GBP, JPY)",
            },
            "para": {
                "type": "string",
                "description": "Codigo ISO da moeda de destino (ex: BRL, USD, EUR, GBP)",
            },
        },
        required=["valor", "de", "para"],
    )

    # ---- Listar cotacoes ----
    def cotacoes_atuais(moeda_base: str = "USD") -> str:
        """Lista as principais taxas de cambio para uma moeda base.

        Args:
            moeda_base: Codigo ISO da moeda base (ex: USD, BRL, EUR). Padrao: USD.

        Returns:
            Tabela com as principais cotacoes
        """
        return _listar_taxas(moeda_base)

    api.register_tool(
        name="cotacoes_atuais",
        func=cotacoes_atuais,
        description=(
            "Lista as principais taxas de cambio para uma moeda base. "
            "Retorna uma tabela com as 10 moedas mais importantes "
            "(USD, BRL, EUR, GBP, JPY, CAD, AUD, CHF, CNY, ARS) "
            "com bandeiras, nomes completos e taxas atualizadas. "
            "Exemplos: 'cotacoes das principais moedas', "
            "'taxas do dolar hoje', 'cotacao do real'. "
            "Use quando o usuario pedir 'cotacoes', 'taxas de cambio', "
            "'como esta o dolar' ou 'lista de moedas'."
        ),
        parameters={
            "moeda_base": {
                "type": "string",
                "description": "Moeda base (opcional, padrao: USD). Ex: USD, BRL, EUR",
            },
        },
        required=[],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Cotacao de Moedas",
        "version": "1.0.0",
        "description": "Cambio em tempo real via exchangerate-api.com (60+ moedas, sem API key)",
        "author": "Agente Local",
        "tools": ["cambio_moeda", "cotacoes_atuais"],
    }
