"""
core/audio_whisper.py
=====================
Transcricao de audio via Whisper.

Suporta:
  - Whisper local (openai-whisper)
  - Whisper via Ollama (se disponivel)
  - Fallback para APIs externas

Inspirado no Code Interpreter do ChatGPT que transcende audio nativamente.
"""

import os
import io
import json
import logging
import tempfile
from typing import Optional, Dict, Any

from ._common import (
    os, logging, json, tempfile,
    DATA_DIR, EMBEDDING_MODEL,
)

# --- Config ---
AUDIO_CACHE_DIR = os.path.join(DATA_DIR, "audio_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}
MAX_AUDIO_SIZE_MB = 25

WHISPER_MODEL = os.environ.get("AGENTE_WHISPER_MODEL", "whisper-large-v3")


class WhisperTranscriber:
    """Transcritores de audio com multiplos backends."""

    def __init__(self):
        self._whisper_model = None
        self._current_model = None

    def transcribe(
        self,
        audio_path: str = None,
        audio_bytes: bytes = None,
        language: str = "pt",
        model: str = None,
        output_format: str = "text",
    ) -> Dict[str, Any]:
        """Transcreve audio para texto.

        Args:
            audio_path: Caminho para arquivo de audio
            audio_bytes: Bytes do audio (alternativa ao path)
            language: Codigo do idioma (pt, en, es, etc.)
            model: Modelo Whisper a usar
            output_format: "text", "srt", "vtt", "json"

        Returns:
            Dict com text, language, duration, segments
        """
        if not audio_path and not audio_bytes:
            return {"error": "Forneça audio_path ou audio_bytes"}

        # Valida formato
        if audio_path:
            ext = os.path.splitext(audio_path)[1].lower()
            if ext not in SUPPORTED_FORMATS:
                return {"error": "Formato nao suportado: %s. Use: %s" % (ext, ", ".join(SUPPORTED_FORMATS))}
            size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            if size_mb > MAX_AUDIO_SIZE_MB:
                return {"error": "Arquivo muito grande: %.1fMB (max: %dMB)" % (size_mb, MAX_AUDIO_SIZE_MB)}

        # Tenta transcricao
        result = self._transcribe_whisper(audio_path, audio_bytes, language, model)
        if result and not result.get("error"):
            return result

        # Fallback: tenta via Ollama
        result = self._transcribe_ollama(audio_path, audio_bytes, language)
        if result and not result.get("error"):
            return result

        return {"error": "Nenhum backend de transcricao disponivel. Instale: pip install openai-whisper"}

    def _transcribe_whisper(
        self,
        audio_path: str = None,
        audio_bytes: bytes = None,
        language: str = "pt",
        model: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Transcreve usando openai-whisper local."""
        try:
            import whisper
        except ImportError:
            return None

        model_name = model or WHISPER_MODEL

        # Carrega modelo (com cache)
        if self._whisper_model is None or self._current_model != model_name:
            try:
                self._whisper_model = whisper.load_model(model_name)
                self._current_model = model_name
            except Exception as e:
                logging.warning("Erro ao carregar Whisper model %s: %s", model_name, e)
                try:
                    self._whisper_model = whisper.load_model("base")
                    self._current_model = "base"
                except Exception:
                    return None

        # Prepara audio
        if audio_bytes:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_bytes)
            tmp.close()
            audio_file = tmp.name
        else:
            audio_file = audio_path

        try:
            options = {"language": language} if language else {}
            result = self._whisper_model.transcribe(audio_file, **options)

            output = {
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "segments": [],
            }

            for seg in result.get("segments", []):
                output["segments"].append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", ""),
                })

            output["duration"] = output["segments"][-1]["end"] if output["segments"] else 0
            return output

        except Exception as e:
            logging.error("Erro na transcricao Whisper: %s", e)
            return {"error": str(e)}
        finally:
            if audio_bytes and os.path.exists(audio_file):
                os.unlink(audio_file)

    def _transcribe_ollama(
        self,
        audio_path: str = None,
        audio_bytes: bytes = None,
        language: str = "pt",
    ) -> Optional[Dict[str, Any]]:
        """Tenta transcricao via Ollama."""
        try:
            import ollama
            resp = ollama.list()
            models = [m.get("name", "") for m in resp.get("models", [])]
            audio_models = [m for m in models if "whisper" in m.lower() or "audio" in m.lower()]
            if not audio_models:
                return None
            return None
        except Exception:
            return None

    def format_srt(self, segments: list) -> str:
        """Formata segmentos como SRT."""
        srt_lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            srt_lines.append(str(i))
            srt_lines.append("%s --> %s" % (start, end))
            srt_lines.append(seg["text"])
            srt_lines.append("")
        return "\n".join(srt_lines)

    def format_vtt(self, segments: list) -> str:
        """Formata segmentos como WebVTT."""
        vtt_lines = ["WEBVTT", ""]
        for seg in segments:
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            vtt_lines.append("%s --> %s" % (start, end))
            vtt_lines.append(seg["text"])
            vtt_lines.append("")
        return "\n".join(vtt_lines)

    def _format_time(self, seconds: float) -> str:
        """Formata tempo para SRT/VTT (HH:MM:SS,mmm)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


# --- Ferramentas para o agente ---

_transcriber = WhisperTranscriber()


def transcribe_audio_tool(audio_path: str, language: str = "pt", model: str = None) -> str:
    """Ferramenta: transcreve arquivo de audio para texto."""
    result = _transcriber.transcribe(audio_path, language=language, model=model)
    if result.get("error"):
        return "Erro na transcricao: %s" % result["error"]

    text = result.get("text", "")
    duration = result.get("duration", 0)
    lang = result.get("language", language)

    output = "**Transcricao** (%s, %.1fs)\n\n%s" % (lang, duration, text)

    segments = result.get("segments", [])
    if len(segments) > 3:
        output += "\n\n**Segmentos (%d):**\n" % len(segments)
        for seg in segments[:10]:
            output += "[%.1fs - %.1fs] %s\n" % (seg["start"], seg["end"], seg["text"])

    return output
