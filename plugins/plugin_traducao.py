"""
plugin_traducao.py
==================
Plugin de traducao de textos usando MyMemory API (gratuita, sem API key).

Fornece:
  - Traducao entre dezenas de idiomas com deteccao automatica do idioma origem
  - Deteccao do idioma de um texto
  - Bandeiras e nomes completos dos idiomas

Uso no agente:
  "Traduza 'Hello world' para portugues"
  "Como se diz 'obrigado' em ingles?"
  "Detecte o idioma desta frase"

API: https://mymemory.translated.net/
"""

import json
import logging
import urllib.parse
import urllib.request
import urllib.error

# (nome, flag) — idiomas mais comuns
_IDIOMAS = {
    "en": ("Ingles", "🇬🇧"),
    "pt": ("Portugues", "🇧🇷"),
    "pt-br": ("Portugues BR", "🇧🇷"),
    "pt-pt": ("Portugues PT", "🇵🇹"),
    "es": ("Espanhol", "🇪🇸"),
    "fr": ("Frances", "🇫🇷"),
    "de": ("Alemao", "🇩🇪"),
    "it": ("Italiano", "🇮🇹"),
    "nl": ("Holandes", "🇳🇱"),
    "ru": ("Russo", "🇷🇺"),
    "ja": ("Japones", "🇯🇵"),
    "zh": ("Chines", "🇨🇳"),
    "zh-cn": ("Chines (Simplificado)", "🇨🇳"),
    "zh-tw": ("Chines (Tradicional)", "🇹🇼"),
    "ko": ("Coreano", "🇰🇷"),
    "ar": ("Arabe", "🇸🇦"),
    "hi": ("Hindi", "🇮🇳"),
    "bn": ("Bengali", "🇧🇩"),
    "tr": ("Turco", "🇹🇷"),
    "pl": ("Polones", "🇵🇱"),
    "sv": ("Sueco", "🇸🇪"),
    "no": ("Noruegues", "🇳🇴"),
    "da": ("Dinamarques", "🇩🇰"),
    "fi": ("Finlandes", "🇫🇮"),
    "cs": ("Tcheco", "🇨🇿"),
    "hu": ("Hungaro", "🇭🇺"),
    "ro": ("Romeno", "🇷🇴"),
    "el": ("Grego", "🇬🇷"),
    "he": ("Hebraico", "🇮🇱"),
    "th": ("Tailandes", "🇹🇭"),
    "vi": ("Vietnamita", "🇻🇳"),
    "id": ("Indonesio", "🇮🇩"),
    "ms": ("Malaio", "🇲🇾"),
    "sw": ("Swahili", "🇰🇪"),
    "tl": ("Filipino", "🇵🇭"),
    "uk": ("Ucraniano", "🇺🇦"),
    "ca": ("Catalan", "🇦🇩"),
    "cy": ("Gales", "🏴󠁧󠁢󠁷󠁬󠁳󠁿"),
    "ga": ("Irlandes", "🇮🇪"),
    "af": ("Africâner", "🇿🇦"),
    "sr": ("Servio", "🇷🇸"),
    "hr": ("Croata", "🇭🇷"),
    "sk": ("Eslovaco", "🇸🇰"),
    "sl": ("Esloveno", "🇸🇮"),
    "lt": ("Lituano", "🇱🇹"),
    "lv": ("Letao", "🇱🇻"),
    "et": ("Estonio", "🇪🇪"),
    "bg": ("Bulgaro", "🇧🇬"),
    "mk": ("Macedonio", "🇲🇰"),
    "sq": ("Albanes", "🇦🇱"),
    "hy": ("Armenio", "🇦🇲"),
    "ka": ("Georgiano", "🇬🇪"),
    "fa": ("Persa", "🇮🇷"),
    "ur": ("Urdu", "🇵🇰"),
    "ta": ("Tamil", "🇮🇳"),
    "te": ("Telugo", "🇮🇳"),
    "mr": ("Marati", "🇮🇳"),
    "gu": ("Gujarati", "🇮🇳"),
    "kn": ("Kannada", "🇮🇳"),
    "ml": ("Malaiala", "🇮🇳"),
    "si": ("Cingales", "🇱🇰"),
    "km": ("Khmer", "🇰🇭"),
    "lo": ("Lao", "🇱🇦"),
    "my": ("Birmanes", "🇲🇲"),
    "am": ("Amharico", "🇪🇹"),
    "ne": ("Nepales", "🇳🇵"),
    "mn": ("Mongol", "🇲🇳"),
}


def _info_idioma(codigo: str) -> tuple:
    """Retorna (nome, flag) para um codigo de idioma."""
    codigo = codigo.lower().strip()
    # Tenta match exato
    info = _IDIOMAS.get(codigo)
    if info:
        return info
    # Tenta match parcial (pt-br -> pt, zh-cn -> zh)
    codigo_base = codigo.split("-")[0] if "-" in codigo else codigo
    info = _IDIOMAS.get(codigo_base)
    if info:
        return info
    return (codigo.upper(), "🌐")


def _requisicao_mymemory(url: str) -> dict:
    """Faz requisicao GET para MyMemory.

    Returns:
        Dict com resposta ou dict com chave 'erro'
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgenteLocal/1.0)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        reason = str(e.reason) if hasattr(e, 'reason') else str(e)
        logging.warning("Erro de conexao MyMemory: %s", reason)
        return {"erro": f"🌐 Sem conexao com a internet.\n{reason}"}
    except urllib.error.HTTPError as e:
        logging.warning("Erro HTTP MyMemory: %s", e)
        if e.code == 429:
            return {"erro": "⏳ Limite de requisicoes diarias excedido (1000/dia).\nTente novamente amanha ou reduza o tamanho do texto."}
        return {"erro": f"❌ Erro HTTP ao consultar servico de traducao: {e.code}"}
    except json.JSONDecodeError:
        logging.warning("JSON invalido do MyMemory")
        return {"erro": "⚠ Resposta invalida do servidor de traducao."}
    except Exception as e:
        logging.error("Erro no plugin traducao: %s", e)
        return {"erro": f"❌ Erro inesperado: {e}"}


def _detectar_idioma_local(texto: str) -> str:
    """Detecta o idioma de um texto usando langdetect (se disponivel).

    Returns:
        Codigo ISO do idioma (ex: 'en', 'pt', 'es'), ou string vazia se falhar
    """
    try:
        from langdetect import detect, DetectorFactory
        # Garante resultados deterministicos
        DetectorFactory.seed = 0
        return detect(texto.strip()[:500])
    except ImportError:
        return ""
    except Exception:
        return ""


def _traduzir(texto: str, fonte: str = "auto", alvo: str = "pt") -> str:
    """Traduz um texto entre idiomas usando MyMemory.

    Args:
        texto: Texto a ser traduzido
        fonte: Codigo ISO do idioma de origem (padrao: 'auto')
        alvo: Codigo ISO do idioma de destino (padrao: 'pt')

    Returns:
        String com traducao e metadados
    """
    if not texto or not texto.strip():
        return "❌ Informe o texto a ser traduzido."

    alvo = alvo.lower().strip()
    if not alvo:
        return "❌ Informe o idioma de destino (ex: 'pt', 'en', 'es')."

    if fonte.lower().strip() == alvo:
        return "❌ Os idiomas de origem e destino sao os mesmos."

    # Detecta o idioma de origem se for "auto"
    fonte_real = fonte.lower().strip()
    fonte_detectada = ""
    if fonte_real == "auto":
        codigo_detectado = _detectar_idioma_local(texto)
        if codigo_detectado:
            fonte_real = codigo_detectado
            fonte_detectada = codigo_detectado
        else:
            # Fallback: ingles
            fonte_real = "en"
            fonte_detectada = ""

    # Monta URL MyMemory: langpair=source|target
    langpair = f"{fonte_real}|{alvo}"
    q_encoded = urllib.parse.quote(texto.strip()[:500])  # MyMemory limita a 500 chars
    url = f"https://api.mymemory.translated.net/get?q={q_encoded}&langpair={langpair}"

    dados = _requisicao_mymemory(url)
    if "erro" in dados:
        return dados["erro"]

    status = dados.get("responseStatus", 0)
    if status != 200:
        erro_msg = dados.get("responseDetails", f"Status {status}")
        return f"❌ Erro na traducao: {erro_msg}"

    response_data = dados.get("responseData", {})
    texto_traduzido = response_data.get("translatedText", "")
    if not texto_traduzido:
        return "⚠ O servico retornou uma traducao vazia."

    # Label de origem
    if fonte_detectada:
        nome_fonte, flag_fonte = _info_idioma(fonte_detectada)
        label_origem = f"🔍 {flag_fonte} {nome_fonte} (detectado: {fonte_detectada})"
    elif fonte.lower().strip() == "auto":
        label_origem = "🔍 Ingles (assumido — instale 'pip install langdetect' para deteccao)"
    else:
        nome_fonte, flag_fonte = _info_idioma(fonte)
        label_origem = f"{flag_fonte} {nome_fonte} ({fonte})"

    nome_alvo, flag_alvo = _info_idioma(alvo)

    # Qualidade da traducao
    match_pct = response_data.get("match", 0)
    if isinstance(match_pct, (int, float)):
        match_pct = match_pct * 100 if match_pct < 1 else match_pct
    else:
        match_pct = 0

    # Cota
    quota = dados.get("quotaFinished", False)
    quota_aviso = "\n\n⚠ Cota diaria esgotada — traducao pode ser limitada." if quota else ""

    return (
        f"🔤 **TRADUCAO**\n\n"
        f"  {label_origem}\n"
        f"  ➡ {flag_alvo} **{nome_alvo}** ({alvo})\n\n"
        f"  📝 **Original:**\n"
        f"  \"{texto.strip()}\"\n\n"
        f"  ✅ **Traducao:**\n"
        f"  \"{texto_traduzido}\"\n\n"
        f"  📊 Qualidade: {match_pct:.0f}%{quota_aviso}\n"
        f"  ℹ Fonte: MyMemory (mymemory.translated.net)"
    )


def _detectar(texto: str) -> str:
    """Detecta o idioma de um texto usando langdetect.

    Args:
        texto: Texto a ser analisado

    Returns:
        String com idioma detectado e confianca
    """
    if not texto or not texto.strip():
        return "❌ Informe o texto para detectar o idioma."

    try:
        from langdetect import detect, detect_langs, DetectorFactory, LangDetectException
        DetectorFactory.seed = 0

        texto_curto = texto.strip()[:500]
        codigo = detect(texto_curto)
        idiomas_detectados = detect_langs(texto_curto)

        if idiomas_detectados:
            principal = idiomas_detectados[0]
            confianca = principal.prob * 100
        else:
            confianca = 0.0

    except ImportError:
        return (
            "⚠ Biblioteca 'langdetect' nao disponivel.\n"
            "Instale com: pip install langdetect\n\n"
            "Enquanto isso, especifique o idioma de origem manualmente (ex: 'en', 'pt', 'es')."
        )
    except LangDetectException as e:
        return f"⚠ Nao foi possivel detectar o idioma: {e}"
    except Exception as e:
        return f"❌ Erro ao detectar idioma: {e}"

    nome, flag = _info_idioma(codigo)
    nivel = "Alta" if confianca >= 90 else ("Media" if confianca >= 60 else "Baixa")
    barra = _barra_confianca(confianca)

    return (
        f"🔍 **DETECCAO DE IDIOMA**\n\n"
        f"  {flag} **{nome}** ({codigo})\n"
        f"  📊 Confianca: {confianca:.0f}% ({nivel})\n"
        f"  {barra}\n\n"
        f"  📝 Texto: \"{texto.strip()[:200]}\"{'...' if len(texto.strip()) > 200 else ''}\n\n"
        f"  ℹ Fonte: langdetect (Google Language Detection)"
    )


def _barra_confianca(pct: float) -> str:
    """Gera uma barra visual de confianca."""
    blocos_cheios = max(0, min(10, int(pct / 10)))
    blocos = "█" * blocos_cheios + "░" * (10 - blocos_cheios)
    return f"  [{blocos}]"


def register(api):
    """Registra as ferramentas de traducao no agente."""

    # ---- Traduzir texto ----
    def traduzir_texto(texto: str, para: str, de: str = "auto") -> str:
        """Traduz um texto entre idiomas.

        Args:
            texto: Texto a ser traduzido
            para: Codigo ISO do idioma de destino (ex: pt, en, es, fr, de, it, ja, zh)
            de: Codigo ISO do idioma de origem (opcional, padrao 'auto' para deteccao)

        Returns:
            Texto traduzido com informacoes dos idiomas
        """
        return _traduzir(texto, de, para)

    api.register_tool(
        name="traduzir_texto",
        func=traduzir_texto,
        description=(
            "Traduz textos entre 70+ idiomas usando a API gratuita MyMemory. "
            "Deteccao automatica do idioma de origem (use 'auto' ou omita 'de'). "
            "Retorna o texto traduzido com bandeiras e nomes dos idiomas. "
            "Idiomas suportados: portugues (pt), ingles (en), espanhol (es), "
            "frances (fr), alemao (de), italiano (it), japones (ja), chines (zh), "
            "coreano (ko), arabe (ar), russo (ru), e muitos outros. "
            "Exemplos: 'Traduza Hello world para portugues', "
            "'Como se diz obrigado em ingles?', "
            "'Traduza este texto para o espanhol'. "
            "Use quando o usuario pedir traducao de texto entre idiomas."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto a ser traduzido",
            },
            "para": {
                "type": "string",
                "description": "Codigo ISO do idioma de destino (ex: pt, en, es, fr, de, it, ja, zh)",
            },
            "de": {
                "type": "string",
                "description": "Codigo ISO do idioma de origem (opcional, padrao: 'auto')",
            },
        },
        required=["texto", "para"],
    )

    # ---- Detectar idioma ----
    def detectar_idioma(texto: str) -> str:
        """Detecta o idioma de um texto.

        Args:
            texto: Texto a ser analisado

        Returns:
            Idioma detectado com nivel de confianca
        """
        return _detectar(texto)

    api.register_tool(
        name="detectar_idioma",
        func=detectar_idioma,
        description=(
            "Detecta o idioma de um texto usando a API MyMemory. "
            "Retorna o nome do idioma, codigo ISO, bandeira e nivel de confianca. "
            "Exemplos: 'Detecte o idioma desta frase', "
            "'Que idioma e este texto?'. "
            "Use quando o usuario perguntar 'que idioma e este' ou "
            "'detecte o idioma' de um texto."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto para detectar o idioma",
            },
        },
        required=["texto"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Traducao de Textos",
        "version": "1.0.0",
        "description": "Traducao entre 70+ idiomas via MyMemory API (gratuita, sem API key)",
        "author": "Agente Local",
        "tools": ["traduzir_texto", "detectar_idioma"],
    }
