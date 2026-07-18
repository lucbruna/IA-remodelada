"""
test_plugins.py
================
Testes unitarios para plugins com dependencias externas mockadas.

Uso:
    pytest test_plugins.py -v
    pytest test_plugins.py -v -k wttr
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch, MagicMock
import pytest


# =====================================================================
# Fixtures — dados simulados do wttr.in
# =====================================================================

@pytest.fixture
def resposta_wttr_sucesso() -> dict:
    """Resposta JSON simulada da API wttr.in para Sao Paulo."""
    return {
        "current_condition": [{
            "temp_C": "28",
            "FeelsLikeC": "27",
            "humidity": "65",
            "windspeedKmph": "15",
            "winddir16Point": "ESE",
            "pressure": "1015",
            "visibility": "10",
            "weatherDesc": [{"value": "Sunny"}],
            "uvIndex": "6",
            "lang_pt": [{"value": "Ensolarado"}],
        }],
        "nearest_area": [{
            "areaName": [{"value": "Sao Paulo"}],
            "country": [{"value": "Brazil"}],
        }],
        "weather": [{
            "maxtempC": "32",
            "mintempC": "20",
            "astronomy": [{"sunrise": "06:47 AM", "sunset": "05:31 PM"}],
        }],
    }


@pytest.fixture
def resposta_wttr_sem_traducao() -> dict:
    """Resposta sem traducao pt (usa fallback do mapping)."""
    return {
        "current_condition": [{
            "temp_C": "15",
            "FeelsLikeC": "13",
            "humidity": "80",
            "windspeedKmph": "25",
            "winddir16Point": "W",
            "pressure": "1020",
            "visibility": "8",
            "weatherDesc": [{"value": "Cloudy"}],
            "uvIndex": "2",
        }],
        "nearest_area": [{
            "areaName": [{"value": "London"}],
            "country": [{"value": "United Kingdom"}],
        }],
        "weather": [{
            "maxtempC": "18",
            "mintempC": "10",
            "astronomy": [{"sunrise": "07:30 AM", "sunset": "04:15 PM"}],
        }],
    }


# =====================================================================
# Tests: _processar_condicao
# =====================================================================

class TestProcessarCondicao:
    """Testa o mapeamento de condicoes climaticas (sem mock)."""

    def test_condicao_exata(self):
        """Descricao exata existente no mapping retorna (emoji, traducao)."""
        from plugins.plugin_wttr_in import _processar_condicao
        emoji, traducao = _processar_condicao("Sunny")
        assert "☀️" in emoji
        assert "Ensolarado" in traducao

    def test_condicao_exata_com_chaves_diferentes(self):
        """Outras condicoes exatas funcionam."""
        from plugins.plugin_wttr_in import _processar_condicao
        emoji, traducao = _processar_condicao("Thunderstorm")
        assert "⛈️" in emoji
        assert "Tempestade" in traducao

    def test_condicao_aproximada_substring(self):
        """Descricao aproximada via substring encontra match."""
        from plugins.plugin_wttr_in import _processar_condicao
        emoji, traducao = _processar_condicao("Light rain shower")
        assert "🌦️" in emoji

    def test_condicao_desconhecida_fallback(self):
        """Descricao sem match no mapping retorna fallback."""
        from plugins.plugin_wttr_in import _processar_condicao
        emoji, traducao = _processar_condicao("Alien weather")
        assert "🌡️" in emoji
        assert traducao == "Alien weather"

    def test_condicao_case_insensitive_substring(self):
        """Substring match ignora case."""
        from plugins.plugin_wttr_in import _processar_condicao
        emoji, traducao = _processar_condicao("heavy rain at times")
        assert "🌧️" in emoji


# =====================================================================
# Tests: _consultar_wttr_in (com requests mockado)
# =====================================================================

class TestConsultarWttrIn:
    """Testa a consulta a API wttr.in com requests mockado."""

    @patch("requests.get")
    def test_consulta_sucesso_com_traducao(self, mock_get, resposta_wttr_sucesso):
        """Consulta bem-sucedida com traducao pt retorna dados completos."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_wttr_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_wttr_in import _consultar_wttr_in
        resultado = _consultar_wttr_in("Sao Paulo")

        assert "Sao Paulo" in resultado
        assert "Brazil" in resultado
        assert "28" in resultado  # temperatura
        assert "32" in resultado  # max
        assert "20" in resultado  # min
        assert "65" in resultado  # umidade
        assert "Ensolarado" in resultado  # traducao pt
        assert "Fonte: wttr.in" in resultado

        # Verifica que a URL foi montada corretamente
        url_chamada = mock_get.call_args[0][0]
        assert "wttr.in/Sao Paulo?format=j1&lang=pt" in url_chamada

    @patch("requests.get")
    def test_consulta_sucesso_sem_traducao(self, mock_get, resposta_wttr_sem_traducao):
        """Sem traducao pt, usa fallback do mapping de condicoes."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_wttr_sem_traducao
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_wttr_in import _consultar_wttr_in
        resultado = _consultar_wttr_in("London")

        assert "London" in resultado
        assert "United Kingdom" in resultado
        assert "15" in resultado  # temperatura
        assert "Nublado" in resultado  # fallback do mapping
        assert "☁️" in resultado  # emoji do mapping

    @patch("requests.get")
    def test_timeout(self, mock_get):
        """Timeout na requisicao retorna mensagem amigavel."""
        from plugins.plugin_wttr_in import _consultar_wttr_in
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("simulated timeout")
        resultado = _consultar_wttr_in("Sao Paulo")

        assert "Tempo esgotado" in resultado

    @patch("requests.get")
    def test_conexao_recusada(self, mock_get):
        """Sem internet retorna mensagem amigavel."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("No internet")
        resultado = _consultar_wttr_in("Sao Paulo")

        assert "Sem conexao" in resultado

    @patch("requests.get")
    def test_cidade_nao_encontrada_404(self, mock_get):
        """HTTP 404 retorna mensagem especifica."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        from requests.exceptions import HTTPError
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = HTTPError("404 Not Found", response=mock_resp)
        mock_get.return_value = mock_resp

        resultado = _consultar_wttr_in("CidadeInexistenteXyz")

        assert "nao encontrada" in resultado.lower()

    @patch("requests.get")
    def test_json_invalido(self, mock_get):
        """Resposta com JSON invalido retorna mensagem."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        resultado = _consultar_wttr_in("Sao Paulo")

        assert "Resposta invalida" in resultado

    @patch("requests.get")
    def test_condicao_nao_mapeada(self, mock_get):
        """Condicao climatica desconhecida usa fallback de emoji."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        resposta_com_condicao_desconhecida = {
            "current_condition": [{
                "temp_C": "22",
                "FeelsLikeC": "20",
                "humidity": "70",
                "windspeedKmph": "10",
                "winddir16Point": "N",
                "pressure": "1010",
                "visibility": "9",
                "weatherDesc": [{"value": "Alien vortex"}],
                "uvIndex": "3",
            }],
            "nearest_area": [{
                "areaName": [{"value": "Test City"}],
                "country": [{"value": "Testland"}],
            }],
            "weather": [{
                "maxtempC": "25",
                "mintempC": "18",
                "astronomy": [{"sunrise": "06:00 AM", "sunset": "06:00 PM"}],
            }],
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_com_condicao_desconhecida
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        resultado = _consultar_wttr_in("Test City")

        assert "Alien vortex" in resultado  # descricao original mantida
        assert "🌡️" in resultado  # emoji fallback

    @patch("requests.get")
    def test_sem_astronomy(self, mock_get):
        """Resposta sem dados de astronomy nao quebra."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        resposta_sem_astro = {
            "current_condition": [{
                "temp_C": "25",
                "FeelsLikeC": "24",
                "humidity": "60",
                "windspeedKmph": "5",
                "winddir16Point": "S",
                "pressure": "1012",
                "visibility": "10",
                "weatherDesc": [{"value": "Clear"}],
                "uvIndex": "5",
                "lang_pt": [{"value": "Ceu limpo"}],
            }],
            "nearest_area": [{
                "areaName": [{"value": "Dubai"}],
                "country": [{"value": "UAE"}],
            }],
            "weather": [{
                "maxtempC": "30",
                "mintempC": "22",
                "astronomy": [{}],
            }],
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_sem_astro
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        resultado = _consultar_wttr_in("Dubai")

        assert "25" in resultado
        assert "nao" not in resultado[:50]  # nao deve ter erro

    def test_sem_requests(self):
        """Sem biblioteca requests instalada, retorna mensagem para instalar."""
        from plugins.plugin_wttr_in import _consultar_wttr_in

        # Simula ImportError no import requests
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named requests")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", mock_import):
            resultado = _consultar_wttr_in("Sao Paulo")
            assert "requests" in resultado
            assert "Instale" in resultado


# =====================================================================
# Tests: plugin_info e register
# =====================================================================

class TestPluginInfo:
    """Testa os metadados e registro do plugin."""

    def test_plugin_info_retorna_dict(self):
        """plugin_info retorna dict com metadados."""
        from plugins.plugin_wttr_in import plugin_info
        info = plugin_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "tools" in info
        assert "clima_agora" in info["tools"]

    def test_register_chama_api(self):
        """register() registra a ferramenta clima_agora via PluginAPI."""
        from plugins.plugin_wttr_in import register
        from agente_core import PluginAPI

        functions = {}
        tools_list = []
        api = PluginAPI(functions, tools_list)

        register(api)

        assert "clima_agora" in functions
        assert tools_list[0]["function"]["name"] == "clima_agora"


# =====================================================================
# Fixtures — dados simulados da exchangerate-api
# =====================================================================


@pytest.fixture
def resposta_cambio_sucesso() -> dict:
    """Resposta JSON simulada da API exchangerate-api.com (base USD)."""
    return {
        "base": "USD",
        "date": "2026-07-16",
        "rates": {
            "USD": 1,
            "BRL": 5.08,
            "EUR": 0.92,
            "GBP": 0.79,
            "JPY": 149.50,
            "CAD": 1.36,
            "AUD": 1.52,
            "CHF": 0.88,
            "CNY": 7.25,
            "ARS": 850.0,
            "KRW": 1320.0,
            "INR": 83.50,
            "MXN": 17.20,
        },
    }


# =====================================================================
# Tests: _consultar_taxas (com requests mockado)
# =====================================================================


class TestConsultarTaxas:
    """Testa a consulta a exchangerate-api com requests mockado."""

    @patch("requests.get")
    def test_sucesso(self, mock_get, resposta_cambio_sucesso):
        """Consulta bem-sucedida retorna dict com rates, date, base."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _consultar_taxas
        dados = _consultar_taxas()

        assert "erro" not in dados
        assert dados["base"] == "USD"
        assert dados["date"] == "2026-07-16"
        assert dados["rates"]["BRL"] == 5.08
        assert dados["rates"]["EUR"] == 0.92
        assert len(dados["rates"]) == 13

        url_chamada = mock_get.call_args[0][0]
        assert "exchangerate-api.com" in url_chamada

    @patch("requests.get")
    def test_timeout(self, mock_get):
        """Timeout na requisicao retorna dict de erro."""
        from plugins.plugin_cambio import _consultar_taxas
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("simulated timeout")
        dados = _consultar_taxas()

        assert "erro" in dados
        assert "Tempo esgotado" in dados["erro"]

    @patch("requests.get")
    def test_conexao_recusada(self, mock_get):
        """Sem internet retorna dict de erro."""
        from plugins.plugin_cambio import _consultar_taxas
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("No internet")
        dados = _consultar_taxas()

        assert "erro" in dados
        assert "Sem conexao" in dados["erro"]

    @patch("requests.get")
    def test_json_invalido(self, mock_get):
        """Resposta com JSON invalido retorna dict de erro."""
        from plugins.plugin_cambio import _consultar_taxas

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        dados = _consultar_taxas()

        assert "erro" in dados
        assert "Resposta invalida" in dados["erro"]

    @patch("requests.get")
    def test_http_error(self, mock_get):
        """HTTP 500 retorna dict de erro."""
        from plugins.plugin_cambio import _consultar_taxas
        from requests.exceptions import HTTPError

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = HTTPError("500 Server Error", response=mock_resp)
        mock_get.return_value = mock_resp

        dados = _consultar_taxas()

        assert "erro" in dados
        assert "Erro HTTP" in dados["erro"]

    @patch("requests.get")
    def test_erro_generico(self, mock_get):
        """Exception generica retorna dict de erro."""
        from plugins.plugin_cambio import _consultar_taxas

        mock_get.side_effect = RuntimeError("Algo inesperado")
        dados = _consultar_taxas()

        assert "erro" in dados
        assert "inesperado" in dados["erro"]

    def test_sem_requests(self):
        """Sem biblioteca requests instalada, retorna mensagem para instalar."""
        from plugins.plugin_cambio import _consultar_taxas

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named requests")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", mock_import):
            dados = _consultar_taxas()
            assert "erro" in dados
            assert "requests" in dados["erro"]
            assert "Instale" in dados["erro"]


# =====================================================================
# Tests: _converter (com requests mockado)
# =====================================================================


class TestConverter:
    """Testa a funcao de conversao de moedas."""

    @patch("requests.get")
    def test_usd_para_brl(self, mock_get, resposta_cambio_sucesso):
        """Converte 100 USD para BRL com taxa correta."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _converter
        resultado = _converter(100, "USD", "BRL")

        assert "US$" in resultado  # simbolo USD
        assert "R$" in resultado  # simbolo BRL
        assert "508" in resultado.replace(",", "")  # 100 * 5.08 = 508
        assert "🇺🇸" in resultado  # flag USA
        assert "🇧🇷" in resultado  # flag Brasil
        assert "5.080000" in resultado  # taxa direta
        assert "16/07/2026" in resultado  # data formatada
        assert "exchangerate-api.com" in resultado

    @patch("requests.get")
    def test_eur_para_gbp(self, mock_get, resposta_cambio_sucesso):
        """Converte 50 EUR para GBP via taxa cruzada."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _converter
        # EUR -> GBP: taxa = GBP_rate / EUR_rate = 0.79 / 0.92 ≈ 0.858696
        # 50 * 0.858696 = 42.9348...
        resultado = _converter(50, "EUR", "GBP")

        assert "€" in resultado
        assert "£" in resultado
        # 50 EUR * (0.79/0.92) ≈ 42.93 GBP
        assert "42.93" in resultado  # 50 EUR * (0.79/0.92) = ~42.93 GBP

    @patch("requests.get")
    def test_mesma_moeda(self, mock_get, resposta_cambio_sucesso):
        """Converter USD para USD retorna sem conversao."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _converter
        resultado = _converter(100, "USD", "USD")

        assert "mesma moeda" in resultado.lower()
        assert "100" in resultado

    @patch("requests.get")
    def test_moeda_invalida_origem(self, mock_get, resposta_cambio_sucesso):
        """Moeda de origem invalida retorna mensagem de erro."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _converter
        resultado = _converter(100, "XYZ", "USD")

        assert "XYZ" in resultado
        assert "nao reconhecida" in resultado.lower()
        assert "USD" in resultado  # sugestoes

    @patch("requests.get")
    def test_moeda_invalida_destino(self, mock_get, resposta_cambio_sucesso):
        """Moeda de destino invalida retorna mensagem de erro."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _converter
        resultado = _converter(100, "USD", "XYZ")

        assert "XYZ" in resultado
        assert "nao reconhecida" in resultado.lower()

    def test_moeda_vazia(self):
        """Codigo de moeda vazio retorna mensagem informando."""
        from plugins.plugin_cambio import _converter
        resultado = _converter(100, "", "USD")

        assert "Informe" in resultado
        assert "moedas" in resultado.lower()

        resultado2 = _converter(100, "USD", "")
        assert "Informe" in resultado2

    @patch("requests.get")
    def test_erro_api_propagado(self, mock_get):
        """Erro da API e propagado para o usuario."""
        from plugins.plugin_cambio import _converter
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("simulated timeout")
        resultado = _converter(100, "USD", "BRL")

        assert "Tempo esgotado" in resultado


# =====================================================================
# Tests: _listar_taxas (com requests mockado)
# =====================================================================


class TestListarTaxas:
    """Testa a listagem de taxas de cambio."""

    @patch("requests.get")
    def test_listar_usd(self, mock_get, resposta_cambio_sucesso):
        """Lista as 10 principais moedas com base USD."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _listar_taxas
        resultado = _listar_taxas("USD")

        assert "COTACOES" in resultado
        assert "Dolar Americano" in resultado
        assert "16/07/2026" in resultado
        assert "🇧🇷" in resultado and "BRL" in resultado
        assert "🇪🇺" in resultado and "EUR" in resultado
        assert "exchangerate-api.com" in resultado
        # Nao deve incluir USD na lista (base = USD)
        assert "**USD**" not in resultado.split("COTACOES")[1]

    @patch("requests.get")
    def test_listar_brl(self, mock_get, resposta_cambio_sucesso):
        """Lista as moedas com base BRL (moeda nao-USD)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _listar_taxas
        resultado = _listar_taxas("BRL")

        assert "Real Brasileiro" in resultado
        assert "Real Brasileiro" in resultado  # cabecalho
        assert "16/07/2026" in resultado
        # USD deve aparecer como item na lista (base = BRL)
        assert "**USD**" in resultado.split("COTACOES")[1]
        # BRL nao deve aparecer como item (e a base)
        assert "**BRL**" not in resultado.split("COTACOES")[1]

    @patch("requests.get")
    def test_moeda_invalida(self, mock_get, resposta_cambio_sucesso):
        """Moeda base invalida retorna mensagem de erro."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resposta_cambio_sucesso
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from plugins.plugin_cambio import _listar_taxas
        resultado = _listar_taxas("XYZ")

        assert "XYZ" in resultado
        assert "nao reconhecida" in resultado.lower()

    @patch("requests.get")
    def test_erro_api_propagado(self, mock_get):
        """Erro da API e propagado na listagem."""
        from plugins.plugin_cambio import _listar_taxas
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("No internet")
        resultado = _listar_taxas("USD")

        assert "Sem conexao" in resultado


# =====================================================================
# Tests: plugin_info e register do plugin_cambio
# =====================================================================


class TestPluginInfoCambio:
    """Testa os metadados e registro do plugin de cambio."""

    def test_plugin_info_retorna_dict(self):
        """plugin_info retorna dict com metadados corretos."""
        from plugins.plugin_cambio import plugin_info
        info = plugin_info()
        assert isinstance(info, dict)
        assert info["name"] == "Cotacao de Moedas"
        assert info["version"] == "1.0.0"
        assert "cambio_moeda" in info["tools"]
        assert "cotacoes_atuais" in info["tools"]

    def test_register_chama_api(self):
        """register() registra cambio_moeda e cotacoes_atuais via PluginAPI."""
        from plugins.plugin_cambio import register
        from agente_core import PluginAPI

        functions = {}
        tools_list = []
        api = PluginAPI(functions, tools_list)

        register(api)

        assert "cambio_moeda" in functions
        assert "cotacoes_atuais" in functions
        assert tools_list[0]["function"]["name"] == "cambio_moeda"
        assert tools_list[1]["function"]["name"] == "cotacoes_atuais"
