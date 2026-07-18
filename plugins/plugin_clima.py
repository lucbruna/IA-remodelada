"""
plugin_clima.py
================
Plugin de clima REAL usando a API gratuita wttr.in (substitui a versao
antiga com dados simulados).

Nao precisa de API key — consulta dados meteorologicos reais
de qualquer cidade do mundo via wttr.in.

Para testar, digite no agente:
  "Qual o clima em Sao Paulo agora?"
  "Como esta o tempo no Rio de Janeiro?"
  "Previsao para Lisboa"

wttr.in: https://github.com/chubin/wttr.in
"""

import json
import logging

# Mapeamento: descricao exata da API -> (emoji, traducao_pt)
_CONDICOES = {
    "Sunny": ("☀️", "Ensolarado"),
    "Clear": ("🌙", "Ceu limpo"),
    "Partly cloudy": ("⛅", "Parcialmente nublado"),
    "Cloudy": ("☁️", "Nublado"),
    "Overcast": ("☁️", "Encoberto"),
    "Mist": ("🌫️", "Nevoa"),
    "Fog": ("🌫️", "Nevoeiro"),
    "Light rain": ("🌦️", "Chuva fraca"),
    "Moderate rain": ("🌧️", "Chuva moderada"),
    "Heavy rain": ("🌧️", "Chuva forte"),
    "Light rain shower": ("🌦️", "Pancada de chuva fraca"),
    "Moderate or heavy rain shower": ("🌧️", "Pancada de chuva forte"),
    "Light snow": ("🌨️", "Neve fraca"),
    "Moderate snow": ("❄️", "Neve moderada"),
    "Heavy snow": ("❄️", "Neve forte"),
    "Thunderstorm": ("⛈️", "Tempestade"),
    "Light drizzle": ("🌦️", "Garoa"),
    "Patchy rain possible": ("🌦️", "Possibilidade de chuva"),
    "Patchy snow possible": ("🌨️", "Possibilidade de neve"),
    "Ice pellets": ("🧊", "Granizo pequeno"),
    "Hail": ("🌨️", "Granizo"),
    "Torrential rain shower": ("🌧️", "Chuva torrencial"),
    "Blizzard": ("❄️", "Nevasca"),
    "Fog patched": ("🌫️", "Nevoeiro parcial"),
    "Freezing fog": ("🌫️", "Nevoeiro congelante"),
}

_EMOJI_FALLBACK = "🌡️"


def _processar_condicao(descricao_exata: str) -> tuple:
    """Retorna (emoji, traducao) para a descricao da API wttr.in."""
    if descricao_exata in _CONDICOES:
        return _CONDICOES[descricao_exata]
    for chave, (emoji, traducao) in _CONDICOES.items():
        if chave.lower() in descricao_exata.lower():
            return (emoji, traducao)
    return (_EMOJI_FALLBACK, descricao_exata)


def _formatar_clima(cidade: str) -> str:
    """Consulta o clima REAL de uma cidade via wttr.in."""
    try:
        import requests
    except ImportError:
        return (
            "⚠ Biblioteca 'requests' nao instalada.\n"
            "Instale com: pip install requests"
        )

    try:
        url = f"https://wttr.in/{cidade}?format=j1&lang=pt"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "curl/7.68.0",
        })
        resp.raise_for_status()
        dados = resp.json()

    except requests.exceptions.Timeout:
        logging.warning("Timeout ao consultar wttr.in para: %s", cidade)
        return "⏱ Tempo esgotado ao consultar o clima. Verifique sua internet."
    except requests.exceptions.ConnectionError:
        logging.warning("Sem conexao ao consultar wttr.in para: %s", cidade)
        return (
            "🌐 Sem conexao com a internet.\n"
            "Nao foi possivel acessar o wttr.in para consultar o clima."
        )
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return f"🌍 Cidade '{cidade}' nao encontrada. Verifique o nome."
        logging.warning("Erro HTTP no wttr.in para %s: %s", cidade, e)
        return f"❌ Erro HTTP ao consultar clima: {e}"
    except json.JSONDecodeError:
        logging.warning("JSON invalido do wttr.in para: %s", cidade)
        return "⚠ Resposta invalida do servidor de clima. Tente novamente."
    except Exception as e:
        logging.error("Erro no plugin clima para %s: %s", cidade, e)
        return f"❌ Erro inesperado ao consultar clima: {e}"

    # Processa dados
    corrente = dados.get("current_condition", [{}])[0]
    if not corrente:
        return f"Nao foi possivel obter o clima para '{cidade}'."

    temp = corrente.get("temp_C", "?")
    sensacao = corrente.get("FeelsLikeC", "?")
    umidade = corrente.get("humidity", "?")
    vento_kmh = corrente.get("windspeedKmph", "?")
    vento_dir = corrente.get("winddir16Point", "N/A")
    pressao = corrente.get("pressure", "?")
    visibilidade = corrente.get("visibility", "?")
    desc_ingles = corrente.get("weatherDesc", [{}])[0].get("value", "")
    indice_uv = corrente.get("uvIndex", "?")

    desc_traduzida = corrente.get("lang_pt", [{}])[0].get("value", "")
    emoji, desc_fallback = _processar_condicao(desc_ingles)
    desc_final = desc_traduzida if (desc_traduzida and desc_traduzida != desc_ingles) else desc_fallback

    regiao = dados.get("nearest_area", [{}])[0]
    nome_cidade = regiao.get("areaName", [{}])[0].get("value", cidade.title())
    pais = regiao.get("country", [{}])[0].get("value", "")

    previsao = dados.get("weather", [{}])[0]
    max_temp = previsao.get("maxtempC", "?")
    min_temp = previsao.get("mintempC", "?")
    nascer_sol = previsao.get("astronomy", [{}])[0].get("sunrise", "?")
    por_sol = previsao.get("astronomy", [{}])[0].get("sunset", "?")

    resultado = [
        f"{emoji} **{nome_cidade}** — {pais}\n",
        f"  🌡 Temperatura: {temp}°C (max {max_temp}°C / min {min_temp}°C)",
        f"  🤔 Sensacao termica: {sensacao}°C",
        f"  ☁ Condicao: {desc_final}",
        f"  💧 Umidade: {umidade}%",
        f"  💨 Vento: {vento_kmh} km/h ({vento_dir})",
        f"  🔆 Indice UV: {indice_uv}",
        f"  👁 Visibilidade: {visibilidade} km",
        f"  🌀 Pressao: {pressao} hPa",
    ]

    if nascer_sol != "?" or por_sol != "?":
        resultado.append(f"  🌅 Sol: {nascer_sol} / {por_sol}")

    resultado.append("\n  📊 Fonte: wttr.in")

    return "\n".join(resultado)


def register(api):
    """Registra o plugin de clima REAL (wttr.in) no agente.

    Mantem o mesmo nome de ferramenta 'consultar_clima' para
    compatibilidade com versoes anteriores.

    Args:
        api: PluginAPI com metodo register_tool()
    """

    def consultar_clima(cidade: str) -> str:
        """Retorna o clima ATUAL e REAL de uma cidade via wttr.in.

        Args:
            cidade: Nome da cidade (ex: 'Sao Paulo', 'New York')

        Returns:
            Dados completos do clima formatados
        """
        return _formatar_clima(cidade)

    api.register_tool(
        name="consultar_clima",
        func=consultar_clima,
        description=(
            "Retorna o clima ATUAL e REAL de uma cidade usando a API wttr.in. "
            "Fornece temperatura, sensacao termica, umidade, vento, "
            "visibilidade, pressao e indice UV. Use quando o usuario perguntar "
            "sobre o tempo, clima, temperatura ou condicoes meteorologicas "
            "de alguma cidade do mundo."
        ),
        parameters={
            "cidade": {
                "type": "string",
                "description": (
                    "Nome da cidade para consultar. "
                    "Exemplos: 'Sao Paulo', 'Rio de Janeiro', 'London', 'Paris'"
                ),
            }
        },
        required=["cidade"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Clima Real (wttr.in)",
        "version": "2.0.0",
        "description": "Clima real de qualquer cidade via wttr.in (sem API key)",
        "author": "Agente Local",
        "tools": ["consultar_clima"],
    }
