"""
plugin_wttr_in.py
=================
Plugin de clima REAL usando a API gratuita wttr.in.

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

# Fallback para condicoes nao mapeadas
_EMOJI_FALLBACK = "🌡️"


def _processar_condicao(descricao_exata: str) -> tuple:
    """Retorna (emoji, traducao) para a descricao da API wttr.in.

    Usa lookup direto por chave exata (mais seguro que substring).
    Se nao encontrar, retorna fallback com a descricao original.
    """
    if descricao_exata in _CONDICOES:
        return _CONDICOES[descricao_exata]
    # Fallback: busca por substring (descricao aproximada)
    for chave, (emoji, traducao) in _CONDICOES.items():
        if chave.lower() in descricao_exata.lower():
            return (emoji, traducao)
    return (_EMOJI_FALLBACK, descricao_exata)


def _consultar_wttr_in(cidade: str) -> str:
    """Consulta o clima real na API wttr.in usando import lazy de requests.

    Usa o formato JSON (j1) que retorna dados completos:
    temperatura, sensacao, umidade, vento, visibilidade, etc.

    Args:
        cidade: Nome da cidade para consultar

    Returns:
        String formatada com os dados do clima
    """
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
            "User-Agent": "curl/7.68.0",  # wttr.in prefere User-Agent curl
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
        logging.error("Erro no plugin wttr.in para %s: %s", cidade, e)
        return f"❌ Erro inesperado ao consultar clima: {e}"

    # === Processa resposta ===
    corrente = dados.get("current_condition", [{}])[0]
    if not corrente:
        return f"Nao foi possivel obter o clima para '{cidade}'."

    # Dados principais
    temp = corrente.get("temp_C", "?")
    sensacao = corrente.get("FeelsLikeC", "?")
    umidade = corrente.get("humidity", "?")
    vento_kmh = corrente.get("windspeedKmph", "?")
    vento_dir = corrente.get("winddir16Point", "N/A")
    pressao = corrente.get("pressure", "?")
    visibilidade = corrente.get("visibility", "?")
    desc_ingles = corrente.get("weatherDesc", [{}])[0].get("value", "")
    indice_uv = corrente.get("uvIndex", "?")

    # Usa traducao da API se disponivel, senao usa mapping local
    desc_traduzida = corrente.get("lang_pt", [{}])[0].get("value", "")
    # Extrai emoji da descricao em ingles (sempre disponivel)
    emoji, desc_fallback = _processar_condicao(desc_ingles)
    # Usa traducao da API se disponivel e diferente do ingles
    if desc_traduzida and desc_traduzida != desc_ingles:
        desc_final = desc_traduzida
    else:
        desc_final = desc_fallback

    # Dados da cidade
    regiao = dados.get("nearest_area", [{}])[0]
    nome_cidade = regiao.get("areaName", [{}])[0].get("value", cidade.title())
    pais = regiao.get("country", [{}])[0].get("value", "")

    # Previsao do dia
    previsao = dados.get("weather", [{}])[0]
    max_temp = previsao.get("maxtempC", "?")
    min_temp = previsao.get("mintempC", "?")
    nascer_sol = previsao.get("astronomy", [{}])[0].get("sunrise", "?")
    por_sol = previsao.get("astronomy", [{}])[0].get("sunset", "?")

    # Formata a saida
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

    resultado.append(f"\n  📊 Fonte: wttr.in")

    return "\n".join(resultado)


def register(api):
    """Registra o plugin de clima real (wttr.in) no agente.

    Args:
        api: PluginAPI com metodo register_tool()
    """

    def clima_agora(cidade: str) -> str:
        """Retorna o clima atual de uma cidade usando dados reais do wttr.in.

        Args:
            cidade: Nome da cidade (ex: 'Sao Paulo', 'New York', 'Paris')

        Returns:
            Previsao detalhada do clima
        """
        return _consultar_wttr_in(cidade)

    api.register_tool(
        name="clima_agora",
        func=clima_agora,
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
        "version": "1.0.0",
        "description": "Clima real de qualquer cidade via wttr.in (sem API key)",
        "author": "Agente Local",
        "tools": ["clima_agora"],
    }
