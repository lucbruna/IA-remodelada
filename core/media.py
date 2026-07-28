from ._common import *
# =======================================================================
# DOCUMENTOS: PDF e IMAGEM
# =======================================================================

def read_pdf(path: str, max_chars: int = 5000) -> str:
    """Extrai e retorna o texto de um arquivo PDF."""
    try:
        import PyPDF2
    except ImportError:
        return "Instale a lib primeiro: pip install PyPDF2"
    try:
        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts).strip()
        if not text:
            return "Nao foi possivel extrair texto (o PDF pode ser so imagens escaneadas)."
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...conteudo truncado...]"
        return text
    except Exception as e:
        return f"Erro ao ler PDF: {e}"


def read_image_text(path: str) -> str:
    """Extrai texto de uma imagem via OCR (funciona bem com prints, documentos escaneados)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "Instale as libs primeiro: pip install pillow pytesseract (e o programa Tesseract-OCR no sistema)"
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="por+eng").strip()
        return text or "Nenhum texto encontrado na imagem."
    except Exception as e:
        return f"Erro ao ler imagem: {e}"


def describe_image(path: str, question: str = "Descreva esta imagem em detalhes.") -> str:
    """Usa um modelo de visao (ex: llava) para descrever ou responder perguntas sobre uma imagem."""
    try:
        import ollama
        from agente_core import _call_ollama_with_timeout
        response = _call_ollama_with_timeout(
            ollama.chat,
            model=VISION_MODEL,
            messages=[{"role": "user", "content": question, "images": [path]}],
            options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        )
        return response["message"]["content"]
    except ImportError:
        return "Instale a lib 'ollama' primeiro: pip install ollama"
    except TimeoutError as e:
        return f"Timeout ao descrever imagem: o modelo de visao nao respondeu a tempo. Verifique se o Ollama esta rodando."
    except Exception as e:
        return (
            f"Erro ao descrever imagem: {e}\n"
            f"(certifique-se de ter baixado um modelo com visao: ollama pull {VISION_MODEL})"
        )


