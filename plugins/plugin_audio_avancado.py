"""
plugin_audio_avancado.py
========================
Manipulacao de audio: reproducao basica (console beep), geracao de tons,
metadados, conversao de formatos (com ffmpeg), silencios,
audio transcription helper.
"""

import os
import json
import math
import struct
import wave
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Audio Avancado"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data", "audio")
os.makedirs(DATA_DIR, exist_ok=True)


def register(api):
    def _has_ffmpeg():
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def gerar_tom(frequencia: float = 440.0, duracao: float = 1.0, volume: float = 0.5,
                  formato: str = "wav", samplerate: int = 44100, salvar: str = "") -> str:
        """Gera arquivo de audio com tom senoidal."""
        try:
            import numpy as np
        except ImportError:
            return "Instale: pip install numpy"
        try:
            n_samples = int(samplerate * duracao)
            t = np.linspace(0, duracao, n_samples, False)
            tone = np.sin(frequencia * 2 * np.pi * t) * volume
            tone = np.clip(tone, -1.0, 1.0)
            path = salvar or os.path.join(DATA_DIR, f"tom_{frequencia:.0f}hz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{formato}")
            if formato == "wav":
                tone_int = np.int16(tone * 32767)
                with wave.open(path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(samplerate)
                    wf.writeframes(tone_int.tobytes())
            else:
                # fallback wav
                path = path.replace(f".{formato}", ".wav")
                tone_int = np.int16(tone * 32767)
                with wave.open(path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(samplerate)
                    wf.writeframes(tone_int.tobytes())
            return f"Tom {frequencia}Hz gerado: {path} ({duracao:.1f}s)"
        except Exception as e:
            return f"Erro: {e}"

    def info_audio(caminho: str) -> str:
        """Obtem metadados de arquivo de audio."""
        try:
            import mutagen
        except ImportError:
            return "Instale: pip install mutagen"
        try:
            audio = mutagen.File(caminho)
            if audio is None:
                return "Formato nao reconhecido pelo mutagen."
            info = {
                "arquivo": os.path.basename(caminho),
                "tamanho": f"{os.path.getsize(caminho):,} bytes",
                "formato": type(audio).__name__,
                "duracao": f"{audio.info.length:.2f}s",
                "bitrate": f"{getattr(audio.info, 'bitrate', 0)//1000} kbps" if hasattr(audio.info, 'bitrate') else "N/A",
                "samplerate": f"{getattr(audio.info, 'sample_rate', 'N/A')} Hz",
                "canais": getattr(audio.info, 'channels', 'N/A'),
            }
            if hasattr(audio, "tags") and audio.tags:
                for k, v in audio.tags.items():
                    info[k] = str(v[0]) if isinstance(v, list) else str(v)
            return json.dumps(info, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Erro: {e}"

    def converter_audio(origem: str, destino: str) -> str:
        """Converte formato de audio usando ffmpeg. Ex: .mp3 -> .wav, .wav -> .ogg."""
        if not _has_ffmpeg():
            return "ffmpeg nao encontrado. Instale ffmpeg e adicione ao PATH."
        try:
            import subprocess
            parent = os.path.dirname(os.path.abspath(destino))
            if parent:
                os.makedirs(parent, exist_ok=True)
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", origem, destino],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                size = os.path.getsize(destino)
                return f"Convertido: {origem} -> {destino} ({size:,} bytes)"
            return f"Erro ffmpeg: {result.stderr[:500]}"
        except Exception as e:
            return f"Erro: {e}"

    def concatenar_audio(arquivos: str, destino: str) -> str:
        """Concatena varios arquivos de audio. arquivos: JSON array de caminhos."""
        if not _has_ffmpeg():
            return "ffmpeg nao encontrado."
        try:
            files = json.loads(arquivos) if isinstance(arquivos, str) else arquivos
            parent = os.path.dirname(os.path.abspath(destino))
            if parent:
                os.makedirs(parent, exist_ok=True)
            import subprocess
            # cria lista tmp
            lista_path = os.path.join(DATA_DIR, "_concat_list.txt")
            with open(lista_path, "w", encoding="utf-8") as f:
                for fp in files:
                    f.write(f"file '{os.path.abspath(fp)}'\n")
            result = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_path, "-c", "copy", destino],
                capture_output=True, text=True, timeout=120
            )
            os.remove(lista_path)
            if result.returncode == 0:
                size = os.path.getsize(destino)
                return f"Audios concatenados: {destino} ({size:,} bytes)"
            return f"Erro: {result.stderr[:500]}"
        except Exception as e:
            return f"Erro: {e}"

    def silenciar_audio(origem: str, destino: str, inicio: float = 0.0, fim: float = 0.0) -> str:
        """Remove silencio no inicio/fim do audio usando ffmpeg."""
        if not _has_ffmpeg():
            return "ffmpeg nao encontrado."
        try:
            import subprocess
            parent = os.path.dirname(os.path.abspath(destino))
            if parent:
                os.makedirs(parent, exist_ok=True)
            filtro = []
            if inicio > 0:
                filtro.append(f"silenceremove=start_periods=1:start_silence={inicio}:start_threshold=-50dB")
            if fim > 0:
                filtro.append(f"silenceremove=stop_periods=1:stop_silence={fim}:stop_threshold=-50dB")
            filtro_str = ",".join(filtro) if filtro else "anull"
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", origem, "-af", filtro_str, destino],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                size = os.path.getsize(destino)
                return f"Silencio removido: {destino} ({size:,} bytes)"
            return f"Erro: {result.stderr[:500]}"
        except Exception as e:
            return f"Erro: {e}"

    api.register_tool("gerar_tom", gerar_tom,
        "Gera tom senoidal em WAV. frequencia em Hz, duracao em segundos.",
        {"frequencia": {"type": "number", "description": "Frequencia em Hz (opcional)"}, "duracao": {"type": "number", "description": "Duracao em segundos (opcional)"}, "volume": {"type": "number", "description": "Volume 0-1 (opcional)"}, "formato": {"type": "string", "description": "Formato: wav (opcional)"}, "samplerate": {"type": "integer", "description": "Sample rate (opcional)"}, "salvar": {"type": "string", "description": "Caminho (opcional)"}}, [])

    api.register_tool("info_audio", info_audio,
        "Obtem metadados de arquivo de audio (mutagen).",
        {"caminho": {"type": "string", "description": "Caminho do arquivo"}}, ["caminho"])

    api.register_tool("converter_audio", converter_audio,
        "Converte formato de audio com ffmpeg (ex: .mp3 -> .wav).",
        {"origem": {"type": "string", "description": "Arquivo de origem"}, "destino": {"type": "string", "description": "Arquivo de destino"}}, ["origem", "destino"])

    api.register_tool("concatenar_audio", concatenar_audio,
        "Concatena varios audios em um unico arquivo usando ffmpeg.",
        {"arquivos": {"type": "string", "description": "JSON array de caminhos"}, "destino": {"type": "string", "description": "Arquivo de saida"}}, ["arquivos", "destino"])

    api.register_tool("silenciar_audio", silenciar_audio,
        "Remove silencio no inicio/fim do audio com ffmpeg.",
        {"origem": {"type": "string", "description": "Arquivo de origem"}, "destino": {"type": "string", "description": "Arquivo de destino"}, "inicio": {"type": "number", "description": "Tolerancia silencio inicio (opcional)"}, "fim": {"type": "number", "description": "Tolerancia silencio fim (opcional)"}}, ["origem", "destino"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Geracao de tons, metadados, conversao, concatenacao de audio (numpy + ffmpeg)",
        "tools": ["gerar_tom", "info_audio", "converter_audio", "concatenar_audio", "silenciar_audio"],
    }
