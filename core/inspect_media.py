from ._common import *

# =======================================================================
# INSPECT MEDIA - ferramentas multimodais first-class (padrao OMP)
# -----------------------------------------------------------------------
# Reune generate_image, inspect_image (visao) e tts como ferramentas
# nativas do agente (nao so plugins). O agente pode gerar, analisar e
# falar midia diretamente, sem depender do carregamento de plugins.
# =======================================================================


def inspect_image(path: str, question: str = "Descreva esta imagem em detalhes.") -> str:
    """Analise visual (visao) de um arquivo de imagem local via modelo de visao.

    Use para OCR, descricao, contagem de elementos, ou responder perguntas
    especificas sobre a imagem. Requer VISION_MODEL configurado.
    """
    try:
        from .media import describe_image
        return describe_image(path, question)
    except Exception as e:
        return f"Erro ao analisar imagem: {e}"


def tts(text: str, voz_id: int = 0, velocidade: int = 180) -> str:
    """Fala o texto em VOZ ALTA (TTS local via pyttsx3) ou gera arquivo de audio.

    Se o pyttsx3 estiver disponivel, fala imediatamente. Caso contrario,
    usa salvar_audio para gerar um .wav. Retorna o caminho/cResultado.
    """
    try:
        from plugins.plugin_tts import salvar_audio, falar_texto
        try:
            return falar_texto(text)
        except Exception:
            return salvar_audio(text, voz_id=voz_id, velocidade=velocidade)
    except Exception as e:
        return f"Erro no TTS: {e}"
