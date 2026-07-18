"""
plugin_tts.py
=============
Plugin de Text-to-Speech (TTS) — transforma texto em voz usando pyttsx3.

Dependências:
  pip install pyttsx3

Recursos:
  - Falar texto em voz alta (com voz feminina/masculina)
  - Salvar áudio em arquivo .wav
  - Controlar velocidade e volume
  - Listar vozes disponíveis no sistema
"""

import logging
import os

__version__ = "1.0.0"
PLUGIN_NAME = "Text-to-Speech"


_TTS_ENGINE_CACHE = None

def _get_engine():
    """Retorna engine TTS (singleton com lazy initialization)."""
    global _TTS_ENGINE_CACHE
    if _TTS_ENGINE_CACHE is not None:
        return _TTS_ENGINE_CACHE
    try:
        import pyttsx3
        _TTS_ENGINE_CACHE = pyttsx3.init()
        return _TTS_ENGINE_CACHE
    except ImportError:
        return None
    except Exception as e:
        logging.warning("Erro ao iniciar TTS: %s", e)
        return None


def speak_text(texto: str, velocidade: int = 180, volume: float = 1.0,
               voz_id: int = 0) -> str:
    """Converte texto em voz e reproduz no alto-falante.

    Args:
        texto: Texto a ser falado
        velocidade: Velocidade da fala (50-300, padrao 180)
        volume: Volume (0.0 a 1.0, padrao 1.0)
        voz_id: Índice da voz (0 = primeira disponível, 1 = segunda, etc.)

    Returns:
        Mensagem de confirmação ou erro
    """
    engine = _get_engine()
    if engine is None:
        return "❌ pyttsx3 não está instalado. Execute: pip install pyttsx3"

    try:
        # Configura
        engine.setProperty("rate", max(50, min(300, velocidade)))
        engine.setProperty("volume", max(0.0, min(1.0, volume)))

        # Seleciona voz
        voices = engine.getProperty("voices")
        if voices and voz_id < len(voices):
            engine.setProperty("voice", voices[voz_id].id)

        engine.say(texto)
        engine.runAndWait()
        engine.stop()

        voz_usada = voices[voz_id].name if voices and voz_id < len(voices) else "padrão"
        return f"🔊 Falado ({len(texto)} caracteres, voz: {voz_usada})"
    except Exception as e:
        return f"❌ Erro ao falar: {e}"


def listar_vozes() -> str:
    """Lista as vozes TTS disponíveis no sistema.

    Returns:
        Lista formatada das vozes com índices e detalhes
    """
    engine = _get_engine()
    if engine is None:
        return "❌ pyttsx3 não está instalado. Execute: pip install pyttsx3"

    try:
        voices = engine.getProperty("voices")
        if not voices:
            return "Nenhuma voz TTS encontrada no sistema."
        
        linhas = ["--- Vozes TTS Disponíveis ---"]
        for i, v in enumerate(voices):
            nome = v.name or "sem nome"
            langs = v.languages or []
            gender = "feminina" if "female" in nome.lower() else "masculina"
            linhas.append(f"  [{i}] {nome} ({gender})")
        return "\n".join(linhas)
    except Exception as e:
        return f"❌ Erro ao listar vozes: {e}"


def salvar_audio(texto: str, arquivo: str = "", velocidade: int = 180,
                 volume: float = 1.0, voz_id: int = 0) -> str:
    """Salva o texto como arquivo de áudio .wav.

    Args:
        texto: Texto a ser convertido
        arquivo: Caminho do arquivo .wav (opcional)
        velocidade: Velocidade da fala (50-300)
        volume: Volume (0.0-1.0)
        voz_id: Índice da voz

    Returns:
        Mensagem de confirmação ou erro
    """
    engine = _get_engine()
    if engine is None:
        return "❌ pyttsx3 não está instalado. Execute: pip install pyttsx3"

    try:
        if not arquivo:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "agente_data"
            )
            os.makedirs(data_dir, exist_ok=True)
            arquivo = os.path.join(data_dir, f"audio_{timestamp}.wav")

        if not arquivo.endswith(".wav"):
            arquivo += ".wav"

        engine.setProperty("rate", max(50, min(300, velocidade)))
        engine.setProperty("volume", max(0.0, min(1.0, volume)))

        voices = engine.getProperty("voices")
        if voices and voz_id < len(voices):
            engine.setProperty("voice", voices[voz_id].id)

        engine.save_to_file(texto, arquivo)
        engine.runAndWait()
        engine.stop()

        tamanho = os.path.getsize(arquivo) if os.path.exists(arquivo) else 0
        return f"🔊 Áudio salvo: {os.path.abspath(arquivo)} ({tamanho} bytes)"
    except Exception as e:
        return f"❌ Erro ao salvar áudio: {e}"


def register(api):
    api.register_tool(
        name="falar_texto",
        func=speak_text,
        description=(
            "Converte texto em VOZ e reproduz no alto-falante do computador. "
            "Use quando o usuario pedir para 'falar', 'ler em voz alta', "
            "'dizer algo em audio', 'pronunciar'. Pode controlar velocidade e volume."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto a ser falado em voz alta"
            },
            "velocidade": {
                "type": "integer",
                "description": "Velocidade da fala (50=lento, 180=normal, 300=rapido)"
            },
            "volume": {
                "type": "number",
                "description": "Volume (0.0=silêncio a 1.0=máximo)"
            },
            "voz_id": {
                "type": "integer",
                "description": "Índice da voz (0=primeira disponível)"
            },
        },
        required=["texto"],
    )

    api.register_tool(
        name="listar_vozes_tts",
        func=listar_vozes,
        description=(
            "Lista as vozes de texto-para-fala (TTS) disponíveis no sistema. "
            "Útil antes de escolher uma voz específica para usar com falar_texto."
        ),
        parameters={},
        required=[],
    )

    api.register_tool(
        name="salvar_audio",
        func=salvar_audio,
        description=(
            "Converte texto em arquivo de áudio .wav e salva no disco. "
            "Use quando o usuario pedir para 'salvar como audio', 'gerar arquivo de voz'."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto a ser convertido em áudio"
            },
            "arquivo": {
                "type": "string",
                "description": "Caminho do arquivo .wav para salvar (opcional)"
            },
            "velocidade": {
                "type": "integer",
                "description": "Velocidade da fala (50-300)"
            },
            "volume": {
                "type": "number",
                "description": "Volume (0.0-1.0)"
            },
            "voz_id": {
                "type": "integer",
                "description": "Índice da voz"
            },
        },
        required=["texto"],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Texto-para-Voz: fala texto, salva áudio e lista vozes do sistema",
        "tools": ["falar_texto", "listar_vozes_tts", "salvar_audio"],
    }
