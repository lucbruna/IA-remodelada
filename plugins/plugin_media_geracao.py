"""
plugin_media_geracao.py
=======================
Plugin de geração de mídia — integra FLUX (imagem), ComfyUI (workflows)
e Wan Video (vídeo) no sistema de agentes.

REQUISITOS:
  - FLUX: pip install diffusers transformers torch accelerate
  - ComfyUI: ComfyUI rodando em http://localhost:8188
  - Wan Video: via diffusers ou ComfyUI workflow

Todas as funções falham graciosamente se o backend não estiver disponível.
"""

import os
import json
import uuid
import time
import base64
import io
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("plugin_media_geracao")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data", "media")
os.makedirs(DATA_DIR, exist_ok=True)

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════════════════
# BACKENDS DISPONÍVEIS
# ═══════════════════════════════════════════════════════════════════

def _check_flux() -> bool:
    """Verifica se FLUX (diffusers) está disponível."""
    try:
        import torch
        from diffusers import FluxPipeline
        return True
    except ImportError:
        return False


def _check_comfyui() -> bool:
    """Verifica se ComfyUI está rodando."""
    try:
        import requests
        resp = requests.get("http://127.0.0.1:8188/system_stats", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _check_wan() -> bool:
    """Verifica se Wan Video está disponível."""
    try:
        import torch
        from diffusers import WanPipeline
        return True
    except ImportError:
        return False


def _check_diffusers() -> bool:
    """Verifica se diffusers está instalado (para qualquer modelo)."""
    try:
        import diffusers
        return True
    except ImportError:
        return False


# ═══════════════════════════════════════════════════════════════════
# FLUX — Geração de Imagem via Diffusers
# ═══════════════════════════════════════════════════════════════════

def gerar_imagem_flux(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    guidance: float = 0.0,
    seed: Optional[int] = None,
    output_path: str = "",
) -> str:
    """
    Gera uma imagem usando FLUX.1 (via diffusers).
    
    Args:
        prompt: Descrição da imagem
        negative_prompt: O que evitar na imagem
        width: Largura (múltiplo de 16)
        height: Altura (múltiplo de 16)
        steps: Número de passos de inferência (4-50)
        guidance: Escala de guidance (0.0 = padrão FLUX)
        seed: Seed para reprodutibilidade (None = aleatório)
        output_path: Caminho para salvar (opcional)
    
    Returns:
        Mensagem de resultado ou erro
    """
    if not _check_flux():
        return (
            "❌ FLUX não disponível. Instale as dependências:\n"
            "  pip install diffusers transformers torch accelerate\n"
            "  Depois faça download: flux.1-schnell (via HuggingFace)"
        )

    try:
        import torch
        from diffusers import FluxPipeline

        if not output_path:
            nome = f"flux_{uuid.uuid4()[:8]}.png"
            output_path = os.path.join(DATA_DIR, nome)

        # Garante dimensões múltiplas de 16
        width = (width // 16) * 16
        height = (height // 16) * 16
        width = max(256, min(1536, width))
        height = max(256, min(1536, height))

        model_id = "black-forest-labs/FLUX.1-schnell"

        pipe = FluxPipeline.from_pretrained(
            model_id, torch_dtype=torch.bfloat16
        )
        pipe.enable_model_cpu_offload()

        generator = None
        if seed is not None:
            generator = torch.Generator().manual_seed(seed)

        image = pipe(
            prompt=prompt,
            guidance_scale=guidance,
            num_inference_steps=steps,
            width=width,
            height=height,
            generator=generator,
            max_sequence_length=256,
        ).images[0]

        image.save(output_path)
        file_size = os.path.getsize(output_path)

        return (
            f"✅ Imagem gerada com FLUX!\\n"
            f"📁 Arquivo: {os.path.basename(output_path)}\\n"
            f"📐 {width}×{height}px | {steps} passos\\n"
            f"💾 {file_size / 1024:.1f} KB\\n"
            f"📝 '{prompt[:80]}{'...' if len(prompt) > 80 else ''}'"
        )

    except Exception as e:
        return f"❌ Erro ao gerar imagem com FLUX: {e}"


# ═══════════════════════════════════════════════════════════════════
# ComfyUI — Workflows de Imagem/Vídeo
# ═══════════════════════════════════════════════════════════════════

def _comfyui_api(method: str, endpoint: str, data: dict = None) -> Optional[dict]:
    """Faz requisição à API do ComfyUI."""
    try:
        import requests
        url = f"http://127.0.0.1:8188{endpoint}"
        resp = requests.request(method, url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("ComfyUI API error: %s", e)
        return None


def _comfyui_upload_image(image_path: str) -> Optional[str]:
    """Faz upload de imagem para o ComfyUI."""
    try:
        import requests
        url = "http://127.0.0.1:8188/upload/image"
        with open(image_path, "rb") as f:
            resp = requests.post(url, files={"image": f}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("name")
    except Exception as e:
        logger.warning("ComfyUI upload error: %s", e)
        return None


def _comfyui_queue_prompt(workflow_json: dict) -> Optional[str]:
    """Envia workflow para fila do ComfyUI e retorna prompt_id."""
    try:
        import requests
        payload = {"prompt": workflow_json}
        resp = requests.post("http://127.0.0.1:8188/prompt", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("prompt_id")
    except Exception as e:
        logger.warning("ComfyUI queue error: %s", e)
        return None


def _comfyui_wait_for_result(prompt_id: str, timeout: int = 300) -> Optional[list]:
    """Aguarda processamento e retorna lista de imagens geradas."""
    try:
        import requests
        import websocket
    except ImportError:
        logger.warning("ComfyUI: websocket library not installed")
        return None

    client_id = str(uuid.uuid4())
    ws_url = f"ws://127.0.0.1:8188/ws?clientId={client_id}"

    try:
        ws = websocket.create_connection(ws_url, timeout=10)
        ws.settimeout(5)
        start = time.time()

        while time.time() - start < timeout:
            try:
                msg = ws.recv()
            except Exception:
                continue
            if not msg:
                continue

            data = json.loads(msg)
            msg_type = data.get("type", "")

            if msg_type == "progress":
                continue

            if data.get("data", {}).get("prompt_id") == prompt_id:
                status = data.get("data", {}).get("status", {})
                if status.get("completed") or status.get("status_str") == "success":
                    ws.close()
                    hist = requests.get(
                        f"http://127.0.0.1:8188/history/{prompt_id}",
                        timeout=10,
                    ).json()

                    outputs = []
                    if prompt_id in hist:
                        node_outputs = hist[prompt_id].get("outputs", {})
                        for node_id, node_data in node_outputs.items():
                            for img_data in node_data.get("images", []):
                                outputs.append({
                                    "filename": img_data["filename"],
                                    "subfolder": img_data.get("subfolder", ""),
                                    "type": img_data.get("type", "output"),
                                })
                    return outputs

        ws.close()
        return None

    except Exception as e:
        logger.warning("ComfyUI wait error: %s", e)
        return None


def _comfyui_download_image(filename: str, subfolder: str = "", tipo: str = "output") -> Optional[bytes]:
    """Baixa uma imagem do ComfyUI."""
    try:
        import requests
        params = {"filename": filename, "subfolder": subfolder, "type": tipo}
        resp = requests.get("http://127.0.0.1:8188/view", params=params, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning("ComfyUI download error: %s", e)
        return None


def gerar_comfyui(
    workflow_json: dict,
    output_name: str = "",
    wait_timeout: int = 300,
) -> str:
    """
    Executa um workflow no ComfyUI e retorna a imagem/vídeo gerado.
    
    Args:
        workflow_json: Workflow no formato API do ComfyUI
        output_name: Nome do arquivo de saída (opcional)
        wait_timeout: Tempo máximo de espera em segundos
    
    Returns:
        Mensagem de resultado ou erro
    """
    if not _check_comfyui():
        return "❌ ComfyUI não está rodando. Inicie em: http://127.0.0.1:8188"

    try:
        prompt_id = _comfyui_queue_prompt(workflow_json)
        if not prompt_id:
            return "❌ Erro ao enviar workflow para o ComfyUI"

        outputs = _comfyui_wait_for_result(prompt_id, timeout=wait_timeout)
        if not outputs:
            return "❌ Timeout ou erro ao processar workflow no ComfyUI"

        resultados = []
        for img_info in outputs:
            img_data = _comfyui_download_image(
                img_info["filename"],
                img_info.get("subfolder", ""),
                img_info.get("type", "output"),
            )
            if img_data:
                nome = output_name or f"comfyui_{uuid.uuid4()[:8]}_{img_info['filename']}"
                caminho = os.path.join(DATA_DIR, nome)
                with open(caminho, "wb") as f:
                    f.write(img_data)
                resultados.append(caminho)

        if resultados:
            return (
                f"✅ Workflow ComfyUI executado com sucesso!\\n"
                f"📁 {len(resultados)} arquivo(s) gerado(s):\\n"
                + "\\n".join(f"  • {os.path.basename(r)}" for r in resultados)
            )
        return "❌ Nenhum arquivo foi gerado pelo ComfyUI"

    except Exception as e:
        return f"❌ Erro no ComfyUI: {e}"


# ═══════════════════════════════════════════════════════════════════
# Wan Video — Geração de Vídeo via Diffusers
# ═══════════════════════════════════════════════════════════════════

def gerar_video_wan(
    prompt: str,
    negative_prompt: str = "",
    width: int = 576,
    height: int = 320,
    num_frames: int = 81,
    steps: int = 50,
    seed: Optional[int] = None,
    output_path: str = "",
) -> str:
    """
    Gera um vídeo usando Wan Video (via diffusers).
    
    Args:
        prompt: Descrição do vídeo
        negative_prompt: O que evitar
        width: Largura do vídeo
        height: Altura do vídeo
        num_frames: Número de frames (81 = ~3 segundos a 24fps)
        steps: Passos de inferência
        seed: Seed para reprodutibilidade
        output_path: Caminho para salvar (opcional)
    
    Returns:
        Mensagem de resultado ou erro
    """
    if not _check_wan():
        return (
            "❌ Wan Video não disponível. Instale as dependências:\\n"
            "  pip install diffusers transformers torch accelerate\\n"
            "  Modelo: https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
        )

    try:
        import torch
        from diffusers import WanPipeline
        from diffusers.utils import export_to_video

        if not output_path:
            nome = f"wan_{uuid.uuid4()[:8]}.mp4"
            output_path = os.path.join(DATA_DIR, nome)

        model_id = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"

        pipe = WanPipeline.from_pretrained(
            model_id, torch_dtype=torch.bfloat16
        )
        pipe.enable_model_cpu_offload()

        generator = None
        if seed is not None:
            generator = torch.Generator().manual_seed(seed)

        video = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=generator,
        ).frames[0]

        export_to_video(video, output_path, fps=24)
        file_size = os.path.getsize(output_path)

        duracao_seg = num_frames / 24
        return (
            f"✅ Vídeo gerado com Wan Video!\\n"
            f"📁 Arquivo: {os.path.basename(output_path)}\\n"
            f"🎬 {num_frames} frames | {duracao_seg:.1f}s | {width}×{height}\\n"
            f"💾 {file_size / (1024*1024):.1f} MB\\n"
            f"📝 '{prompt[:80]}{'...' if len(prompt) > 80 else ''}'"
        )

    except Exception as e:
        return f"❌ Erro ao gerar vídeo com Wan: {e}"


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTA UNIFICADA — Geração de Mídia
# ═══════════════════════════════════════════════════════════════════

def status_geracao() -> str:
    """Verifica quais backends de geração estão disponíveis."""
    status = [
        "╔════════════════════════════════════════╗",
        "║   🎨 STATUS — GERAÇÃO DE MÍDIA        ║",
        "╚════════════════════════════════════════╝",
        "",
    ]

    flux = _check_flux()
    comfy = _check_comfyui()
    wan = _check_wan()
    diff = _check_diffusers()

    status.append(f"📦 Diffusers:    {'✅' if diff else '❌'} (base para FLUX + Wan)")
    status.append(f"🎨 FLUX:         {'✅' if flux else '❌'} (imagem)")

    if not flux:
        status.append(f"   └ Instale: pip install diffusers transformers torch accelerate")

    status.append(f"🔧 ComfyUI:      {'✅' if comfy else '❌'} (workflows)")

    if comfy:
        status.append(f"   └ Rodando em http://127.0.0.1:8188")
    else:
        status.append(f"   └ Inicie o ComfyUI ou instale: pip install comfy-cli")

    status.append(f"🎬 Wan Video:    {'✅' if wan else '❌'} (vídeo)")

    if not wan:
        status.append(f"   └ Instale: pip install diffusers[torch]")

    status.append("")
    status.append("Comandos disponíveis:")
    status.append("  • gerar_imagem_flux(prompt) — imagem via FLUX")
    status.append("  • gerar_comfyui(workflow) — workflow no ComfyUI")
    status.append("  • gerar_video_wan(prompt) — vídeo via Wan")
    status.append("  • editar_imagem(...) — redimensionar, filtrar, converter")

    return "\\n".join(status)


# ═══════════════════════════════════════════════════════════════════
# REGISTRO
# ═══════════════════════════════════════════════════════════════════

def register(api):
    api.register_tool(
        name="gerar_imagem_flux",
        func=gerar_imagem_flux,
        description="Gera uma imagem usando FLUX.1 (modelo de IA de alta qualidade) via HuggingFace Diffusers. Use prompts descritivos em português ou inglês.",
        parameters={
            "prompt": {"type": "string", "description": "Descrição detalhada da imagem desejada"},
            "negative_prompt": {"type": "string", "description": "O que evitar na imagem (opcional)"},
            "width": {"type": "integer", "description": "Largura em pixels (múltiplo de 16, padrão: 1024)"},
            "height": {"type": "integer", "description": "Altura em pixels (múltiplo de 16, padrão: 1024)"},
            "steps": {"type": "integer", "description": "Passos de inferência (4-50, padrão: 4 para Schnell)"},
            "seed": {"type": "integer", "description": "Seed para reproduzir o mesmo resultado (opcional)"},
        },
        required=["prompt"],
    )

    api.register_tool(
        name="gerar_comfyui",
        func=gerar_comfyui,
        description="Executa um workflow JSON no ComfyUI (API). Use para workflows complexos de imagem, vídeo, upscale, ControlNet, etc. Precisa do ComfyUI rodando em http://localhost:8188.",
        parameters={
            "workflow_json": {"type": "any", "description": "Workflow no formato API do ComfyUI (objeto JSON)"},
            "output_name": {"type": "string", "description": "Nome do arquivo de saída (opcional)"},
            "wait_timeout": {"type": "integer", "description": "Tempo máximo de espera em segundos (padrão: 300)"},
        },
        required=["workflow_json"],
    )

    api.register_tool(
        name="gerar_video_wan",
        func=gerar_video_wan,
        description="Gera um vídeo curto usando Wan Video (via diffusers). Ideal para animações, clips e vídeos conceituais.",
        parameters={
            "prompt": {"type": "string", "description": "Descrição detalhada do vídeo desejado"},
            "negative_prompt": {"type": "string", "description": "O que evitar no vídeo (opcional)"},
            "width": {"type": "integer", "description": "Largura em pixels (padrão: 576)"},
            "height": {"type": "integer", "description": "Altura em pixels (padrão: 320)"},
            "num_frames": {"type": "integer", "description": "Número de frames (81 = ~3s, 161 = ~6s)"},
            "steps": {"type": "integer", "description": "Passos de inferência (padrão: 50)"},
            "seed": {"type": "integer", "description": "Seed para reproduzir o mesmo resultado (opcional)"},
        },
        required=["prompt"],
    )

    api.register_tool(
        name="status_geracao",
        func=status_geracao,
        description="Verifica quais backends de geração de mídia estão disponíveis (FLUX, ComfyUI, Wan Video) e lista os comandos disponíveis.",
        parameters={},
        required=[],
    )

    return {
        "name": "Geração de Mídia (FLUX + ComfyUI + Wan)",
        "version": __version__,
        "description": "Geração de imagens com FLUX, workflows com ComfyUI e vídeos com Wan Video — tudo local.",
        "tools": ["gerar_imagem_flux", "gerar_comfyui", "gerar_video_wan", "status_geracao"],
    }
