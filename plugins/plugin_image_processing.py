"""
plugin_image_processing.py
=========================
Plugin de processamento avançado de imagens. Fornece ferramentas para geração e descrição básicas, incluindo:
- Transformações geométricas (redimensionamento, rotação, corte)
- Filtros e ajustes de cor
- Conversão de formatos
- Extração de metadados (EXIF)
- Criação de miniaturas
- Overposição de texto e marca d'água
- Comparação de imagens
"""

import os
import io
import base64
from datetime import datetime
from typing import Tuple, List, Optional, Union
import hashlib

__version__ = "1.0.0"
PLUGIN_NAME = "Processamento Avançado de Imagens"


def _check_pil() -> bool:
    """Verifica se a biblioteca PIL/Pillow está disponível."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ExifTags
        return True
    except ImportError:
        return False


def _check_opencv() -> bool:
    """Verifica se a biblioteca OpenCV está disponível."""
    try:
        import cv2
        import numpy as np
        return True
    except ImportError:
        return False


def get_image_info(image_path: str) -> str:
    """Obtém informações detalhadas sobre uma imagem, incluindo metadados EXIF.

    Args:
        image_path: Caminho para o arquivo de imagem

    Returns:
        Informações formatadas da imagem
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image, ExifTags
        import json

        with Image.open(image_path) as img:
            info = []
            info.append(f"🖼️  INFORMAÇÕES DA IMAGEM: {os.path.basename(image_path)}")
            info.append("=" * 50)
            info.append(f"Formato: {img.format}")
            info.append(f"Modo: {img.mode}")
            info.append(f"Dimensões: {img.size[0]} x {img.size[1]} pixels")
            info.append(f"Largura: {img.size[0]} px")
            info.append(f"Altura: {img.size[1]} px")
            info.append(f"Total de pixels: {img.size[0] * img.size[1]:,}")

            # File size
            file_size = os.path.getsize(image_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            info.append(f"Tamanho do arquivo: {size_str}")

            # Calculate aspect ratio
            width, height = img.size
            if height > 0:
                aspect_ratio = width / height
                # Simplify ratio
                if abs(aspect_ratio - 1.0) < 0.01:
                    aspect_str = "1:1 (quadrada)"
                elif abs(aspect_ratio - 1.333) < 0.01:
                    aspect_str = "4:3"
                elif abs(aspect_ratio - 1.778) < 0.01:
                    aspect_str = "16:9"
                elif abs(aspect_ratio - 2.39) < 0.01:
                    aspect_str = "21:9 (cinema)"
                else:
                    aspect_str = f"{aspect_ratio:.2f}:1"
                info.append(f"Proporção: {aspect_str}")

            # EXIF data
            try:
                exif_data = img._getexif()
                if exif_data:
                    info.append("")
                    info.append("📋 METADADOS EXIF:")
                    for tag_id, value in exif_data.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        # Skip binary data
                        if isinstance(value, bytes):
                            continue
                        info.append(f"  {tag}: {value}")
                else:
                    info.append("")
                    info.append("📋 Nenhum dado EXIF encontrado.")
            except AttributeError:
                info.append("")
                info.append("📋 Metadados EXIF não disponíveis para este formato.")

            # Color mode info
            mode_descriptions = {
                '1': '1-bit pixels, black and white',
                'L': '8-bit pixels, black and white',
                'P': '8-bit pixels, mapped to palette',
                'RGB': '3x8-bit pixels, true color',
                'RGBA': '4x8-bit pixels, true color with transparency',
                'CMYK': '4x8-bit pixels, color separation',
                'YCbCr': '3x8-bit pixels, color video format',
                'LAB': '3x8-bit pixels, Lab color space',
                'HSV': '3x8-bit pixels, Hue, Saturation, Value color space'
            }
            if img.mode in mode_descriptions:
                info.append("")
                info.append(f"🎨 Modo de cor: {img.mode} ({mode_descriptions[img.mode]})")

            # Check if image has transparency
            if 'transparency' in img.info or img.mode in ('RGBA', 'LA', 'PA'):
                info.append("")
                info.append("🔳 Transparência: Sim")
            else:
                info.append("")
                info.append("🔲 Transparência: Não")

            return "\n".join(info)

    except Exception as e:
        return f"❌ Erro ao analisar imagem: {str(e)}"


def resize_image(image_path: str, width: int = None, height: int = None,
                scale: float = None, maintain_aspect: bool = True,
                output_path: str = None) -> str:
    """Redimensiona uma imagem com várias opções.

    Args:
        image_path: Caminho para a imagem de entrada
        width: Largura desejada em pixels
        height: Altura desejada em pixels
        scale: Fator de escala (ex: 0.5 para metade do tamanho)
        maintain_aspect: Se deve manter a proporção original
        output_path: Caminho para salvar a imagem redimensionada (se None, sobrescreve original)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image

        with Image.open(image_path) as img:
            original_width, original_height = img.size

            # Calculate new dimensions
            if scale is not None:
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
            elif width is not None and height is not None:
                if maintain_aspect:
                    # Calculate based on maintaining aspect ratio
                    ratio_w = width / original_width
                    ratio_h = height / original_height
                    ratio = min(ratio_w, ratio_h) if maintain_aspect else max(ratio_w, ratio_h)
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                else:
                    new_width = width
                    new_height = height
            elif width is not None:
                if maintain_aspect:
                    new_height = int(original_height * (width / original_width))
                    new_width = width
                else:
                    new_width = width
                    new_height = original_height
            elif height is not None:
                if maintain_aspect:
                    new_width = int(original_width * (height / original_height))
                    new_height = height
                else:
                    new_width = original_width
                    new_height = height
            else:
                return "❌ Especifique pelo menos uma dimensão (width, height ou scale)"

            # Ensure minimum dimensions
            new_width = max(1, new_width)
            new_height = max(1, new_height)

            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Determine output path
            if output_path is None:
                output_path = image_path

            # Save image
            # Determine format from extension or original
            if output_path.lower().endswith(('.jpg', '.jpeg')):
                format_to_save = 'JPEG'
                # Ensure RGB mode for JPEG
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', resized_img.size, (255, 255, 255))
                    rgb_img.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode in ('RGBA', 'LA') else None)
                    resized_img = rgb_img
            elif output_path.lower().endswith('.png'):
                format_to_save = 'PNG'
            elif output_path.lower().endswith('.bmp'):
                format_to_save = 'BMP'
            elif output_path.lower().endswith('.tiff'):
                format_to_save = 'TIFF'
            else:
                # Use original format
                format_to_save = img.format if img.format else 'PNG'
                if not output_path.lower().endswith(f'.{format_to_save.lower()}'):
                    output_path = f"{os.path.splitext(output_path)[0]}.{format_to_save.lower()}"

            resized_img.save(output_path, format_to_save, optimize=True)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            action = "sobrescrita" if output_path == image_path else "salva"
            return (
                f"✅ Imagem redimensionada e {action} com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"📐 Dimensões: {original_width}×{original_height} → {new_width}×{new_height}\n"
                f"📏 Escala: {new_width/original_width:.2f}x largura, {new_height/original_height:.2f}x altura\n"
                f"💾 Tamanho: {size_str}"
            )

    except Exception as e:
        return f"❌ Erro ao redimensionar imagem: {str(e)}"


def rotate_image(image_path: str, angle: float, expand: bool = True,
                resample: int = 3, output_path: str = None) -> str:
    """Rota uma imagem por um ângulo especificado.

    Args:
        image_path: Caminho para a imagem de entrada
        angle: Ângulo de rotação em graus (positivo = horário)
        expand: Se deve expandir a imagem para acomodar toda a rotação
        resample: Filtro de reamostragem (0=NEAREST, 1=BOX, 2=BILINEAR, 3=HAMMING, 4=BICUBIC, 5=LANCZOS)
        output_path: Caminho para salvar a imagem rotacionada (se None, sobrescreve original)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Rotate image
            rotated_img = img.rotate(-angle, expand=expand, resample=resample, fillcolor=(255, 255, 255))

            # Determine output path
            if output_path is None:
                output_path = image_path

            # Save image (preserve format when possible)
            if output_path is None or output_path == image_path:
                # Save with original format
                img_format = img.format if img.format else 'PNG'
                rotated_img.save(output_path, img_format)
            else:
                # Determine format from extension
                ext = os.path.splitext(output_path)[1].lower()
                format_map = {
                    '.jpg': 'JPEG', '.jpeg': 'JPEG',
                    '.png': 'PNG',
                    '.bmp': 'BMP',
                    '.tiff': 'TIFF', '.tif': 'TIFF',
                    '.gif': 'GIF',
                    '.webp': 'WEBP'
                }
                fmt = format_map.get(ext, 'PNG')
                # Handle special cases
                if fmt == 'JPEG' and rotated_img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for JPEG
                    rgb_img = Image.new('RGB', rotated_img.size, (255, 255, 255))
                    rgb_img.paste(rotated_img, mask=rotated_img.split()[-1] if rotated_img.mode in ('RGBA', 'LA') else None)
                    rotated_img = rgb_img
                rotated_img.save(output_path, fmt)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            action = "sobrescrita" if output_path == image_path else "salva"
            return (
                f"✅ Imagem rotacionada e {action} com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"🔄 Rotação: {angle}° (sentido horário)\n"
                f"📐 Dimensões: {img.size[0]}×{img.size[1]} → {rotated_img.size[0]}×{rotated_img.size[1]}\n"
                f"💾 Tamanho: {size_str}"
            )

    except Exception as e:
        return f"❌ Erro ao rotacionar imagem: {str(e)}"


def apply_filter(image_path: str, filter_type: str, intensity: float = 1.0,
                output_path: str = None) -> str:
    """Aplica vários filtros a uma imagem.

    Args:
        image_path: Caminho para a imagem de entrada
        filter_type: Tipo de filtro ('blur', 'sharpen', 'edge_enhance', 'emboss',
                    'smooth', 'detail', 'gaussian_blur', 'unsharp_mask',
                    'color_balance', 'brightness', 'contrast', 'saturation')
        intensity: Intensidade do efeito (0.0 a 2.0, onde 1.0 é normal)
        output_path: Caminho para salvar a imagem filtrada (se None, sobrescreve original)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image, ImageFilter, ImageEnhance

        with Image.open(image_path) as img:
            original_img = img.copy()
            filtered_img = img.copy()

            # Apply filter based on type
            if filter_type == 'blur':
                filtered_img = filtered_img.filter(ImageFilter.BLUR)
            elif filter_type == 'gaussian_blur':
                radius = int(2 * intensity)  # Scale intensity to reasonable radius
                radius = max(1, radius)
                filtered_img = filtered_img.filter(ImageFilter.GaussianBlur(radius=radius))
            elif filter_type == 'sharpen':
                filtered_img = filtered_img.filter(ImageFilter.SHARPEN)
                # Enhance sharpening effect
                if intensity != 1.0:
                    enhancer = ImageEnhance.Sharpness(filtered_img)
                    filtered_img = enhancer.enhance(intensity)
            elif filter_type == 'edge_enhance':
                filtered_img = filtered_img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            elif filter_type == 'emboss':
                filtered_img = filtered_img.filter(ImageFilter.EMBOSS)
            elif filter_type == 'smooth':
                filtered_img = filtered_img.filter(ImageFilter.SMOOTH_MORE)
            elif filter_type == 'detail':
                filtered_img = filtered_img.filter(ImageFilter.DETAIL)
            elif filter_type == 'unsharp_mask':
                radius = int(2 * intensity)
                radius = max(1, radius)
                percent = int(150 * intensity)
                percent = max(0, min(500, percent))
                threshold = 3
                filtered_img = filtered_img.filter(
                    ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
                )
            elif filter_type == 'brightness':
                enhancer = ImageEnhance.Brightness(filtered_img)
                filtered_img = enhancer.enhance(intensity)
            elif filter_type == 'contrast':
                enhancer = ImageEnhance.Contrast(filtered_img)
                filtered_img = enhancer.enhance(intensity)
            elif filter_type == 'saturation':
                enhancer = ImageEnhance.Color(filtered_img)
                filtered_img = enhancer.enhance(intensity)
            elif filter_type == 'color_balance':
                # Simple color balance adjustment
                if img.mode != 'RGB':
                    if img.mode == 'RGBA':
                        r, g, b, a = img.split()
                        rgb_img = Image.merge('RGB', (r, g, b))
                    else:
                        rgb_img = img.convert('RGB')
                else:
                    rgb_img = img.copy()

                r, g, b = rgb_img.split()
                # Adjust color channels based on intensity (simplified)
                r_factor = 1.0 + (intensity - 1.0) * 0.5  # Center around 1.0
                g_factor = 1.0
                b_factor = 1.0 - (intensity - 1.0) * 0.5  # Opposite direction

                r_enhancer = ImageEnhance.Brightness(r)
                g_enhancer = ImageEnhance.Brightness(g)
                b_enhancer = ImageEnhance.Brightness(b)

                r = r_enhancer.enhance(r_factor)
                g = g_enhancer.enhance(g_factor)
                b = b_enhancer.enhance(b_factor)

                filtered_img = Image.merge('RGB', (r, g, b))
                # Preserve alpha if original had it
                if img.mode == 'RGBA':
                    filtered_img = Image.merge('RGBA', (*filtered_img.split(), a))
            else:
                return f"❌ Tipo de filtro não suportado: {filter_type}. Tipos disponíveis: blur, gaussian_blur, sharpen, edge_enhance, emboss, smooth, detail, unsharp_mask, brightness, contrast, saturation, color_balance"

            # Determine output path
            if output_path is None:
                output_path = image_path

            # Save image (handle format conversion if needed)
            if output_path is None or output_path == image_path:
                # Save with original format
                img_format = img.format if img.format else 'PNG'
                filtered_img.save(output_path, img_format)
            else:
                # Determine format from extension
                ext = os.path.splitext(output_path)[1].lower()
                format_map = {
                    '.jpg': 'JPEG', '.jpeg': 'JPEG',
                    '.png': 'PNG',
                    '.bmp': 'BMP',
                    '.tiff': 'TIFF', '.tif': 'TIFF',
                    '.gif': 'GIF',
                    '.webp': 'WEBP'
                }
                fmt = format_map.get(ext, 'PNG')
                # Handle special cases
                if fmt == 'JPEG' and filtered_img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for JPEG
                    rgb_img = Image.new('RGB', filtered_img.size, (255, 255, 255))
                    rgb_img.paste(filtered_img, mask=filtered_img.split()[-1] if filtered_img.mode in ('RGBA', 'LA') else None)
                    filtered_img = rgb_img
                filtered_img.save(output_path, fmt)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            action = "sobrescrita" if output_path == image_path else "salva"
            filter_names = {
                'blur': 'Desfoque',
                'gaussian_blur': 'Desfoque Gaussiano',
                'sharpen': 'Nitidez',
                'edge_enhance': 'Realce de Bordas',
                'emboss': 'Relevo',
                'smooth': 'Suavização',
                'detail': 'Detalhe',
                'unsharp_mask': 'Máscara Não Nítida',
                'brightness': 'Brilho',
                'contrast': 'Contraste',
                'saturation': 'Saturação',
                'color_balance': 'Equilíbrio de Cores'
            }
            filter_name = filter_names.get(filter_type, filter_type)

            return (
                f"✅ Filtro '{filter_name}' aplicado e imagem {action} com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"🎚️ Intensidade: {intensity}\n"
                f"💾 Tamanho: {size_str}"
            )

    except Exception as e:
        return f"❌ Erro ao aplicar filtro: {str(e)}"


def convert_image_format(image_path: str, output_path: str = None,
                        format: str = None, quality: int = 85) -> str:
    """Converte uma imagem para um formato diferente.

    Args:
        image_path: Caminho para a imagem de entrada
        output_path: Caminho para salvar a imagem convertida (se None, usa mesmo nome com nova extensão)
        format: Formato de destino ('JPEG', 'PNG', 'BMP', 'TIFF', 'GIF', 'WEBP')
        quality: Qualidade para formatos com perda (1-100, padrão: 85)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Determine output format
            if format is None:
                if output_path:
                    ext = os.path.splitext(output_path)[1].upper()
                    if ext.startswith('.'):
                        ext = ext[1:]
                    format = ext if ext else 'PNG'
                else:
                    format = img.format if img.format else 'PNG'

            format = format.upper()
            format_map = {
                'JPG': 'JPEG',
                'JPEG': 'JPEG',
                'PNG': 'PNG',
                'BMP': 'BMP',
                'TIFF': 'TIFF',
                'TIF': 'TIFF',
                'GIF': 'GIF',
                'WEBP': 'WEBP'
            }
            save_format = format_map.get(format, 'PNG')

            # Determine output path
            if output_path is None:
                base_name = os.path.splitext(image_path)[0]
                extension_map = {
                    'JPEG': '.jpg',
                    'PNG': '.png',
                    'BMP': '.bmp',
                    'TIFF': '.tiff',
                    'GIF': '.gif',
                    'WEBP': '.webp'
                }
                extension = extension_map.get(save_format, '.png')
                output_path = f"{base_name}{extension}"

            # Handle special conversions
            img_to_save = img.copy()
            if save_format == 'JPEG' and img_to_save.mode in ('RGBA', 'LA', 'P'):
                # JPEG doesn't support transparency, composite on white background
                rgb_img = Image.new('RGB', img_to_save.size, (255, 255, 255))
                if img_to_save.mode == 'P':
                    img_to_save = img_to_save.convert('RGBA')
                if img_to_save.mode in ('RGBA', 'LA'):
                    rgb_img.paste(img_to_save, mask=img_to_save.split()[-1])
                else:
                    rgb_img.paste(img_to_save)
                img_to_save = rgb_img
            elif save_format in ['PNG', 'TIFF', 'WEBP', 'GIF']:
                # These formats support various modes, but ensure compatibility
                if img_to_save.mode == 'P' and 'transparency' in img.info:
                    # Convert palette with transparency to RGBA for better preservation
                    img_to_save = img_to_save.convert('RGBA')

            # Save image
            save_kwargs = {}
            if save_format == 'JPEG':
                save_kwargs['quality'] = max(1, min(100, quality))
                save_kwargs['optimize'] = True
            elif save_format == 'PNG':
                save_kwargs['optimize'] = True
            elif save_format == 'WEBP':
                save_kwargs['quality'] = max(1, min(100, quality))

            img_to_save.save(output_path, save_format, **save_kwargs)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            return (
                f"✅ Imagem convertida com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"🔄 Formato: {img.format if img.format else 'desconhecido'} → {save_format}\n"
                f"📐 Dimensões: {img.size[0]}×{img.size[1]} mantidas\n"
                f"💾 Tamanho: {size_str}"
                + (f" (qualidade: {quality}%)" if save_format in ['JPEG', 'WEBP'] else "")
            )

    except Exception as e:
        return f"❌ Erro ao converter formato de imagem: {str(e)}"


def create_thumbnail(image_path: str, size: Union[int, Tuple[int, int]] = (128, 128),
                    output_path: str = None, crop_to_fit: bool = False) -> str:
    """Cria uma miniatura (thumbnail) de uma imagem.

    Args:
        image_path: Caminho para a imagem de entrada
        size: Tamanho da miniatura (int para quadrado, ou tuple (width, height))
        output_path: Caminho para salvar a miniatura (se None, adiciona '_thumb' ao nome)
        crop_to_fit: Se deve cortar a imagem para exatamente caber no tamanho (sem distorção)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Determine thumbnail size
            if isinstance(size, int):
                thumb_size = (size, size)
            else:
                thumb_size = size

            # Create thumbnail
            if crop_to_fit:
                # Crop to fit exactly (may crop parts of image)
                thumb_img = ImageOps.fit(img, thumb_size, Image.Resampling.LANCZOS)
            else:
                # Fit within bounds (preserves aspect ratio, may have empty space)
                thumb_img = img.copy()
                thumb_img.thumbnail(thumb_size, Image.Resampling.LANCZOS)

            # Determine output path
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                ext = os.path.splitext(image_path)[1]
                directory = os.path.dirname(image_path)
                output_path = os.path.join(directory, f"{base_name}_thumb{ext}")

            # Save thumbnail
            # Preserve format when possible
            if output_path.lower().endswith(('.jpg', '.jpeg')):
                format_to_save = 'JPEG'
                # Ensure RGB for JPEG
                if thumb_img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', thumb_img.size, (255, 255, 255))
                    rgb_img.paste(thumb_img, mask=thumb_img.split()[-1] if thumb_img.mode in ('RGBA', 'LA') else None)
                    thumb_img = rgb_img
            elif output_path.lower().endswith('.png'):
                format_to_save = 'PNG'
            elif output_path.lower().endswith('.bmp'):
                format_to_save = 'BMP'
            elif output_path.lower().endswith(('.tiff', '.tif')):
                format_to_save = 'TIFF'
            else:
                format_to_save = img.format if img.format else 'PNG'

            thumb_img.save(output_path, format_to_save, optimize=True)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            return (
                f"✅ Miniatura criada com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"📐 Tamanho original: {img.size[0]}×{img.size[1]} → miniatura: {thumb_img.size[0]}×{thumb_img.size[1]}\n"
                f"✂️ Corte ajustado: {'Sim' if crop_to_fit else 'Não'}\n"
                f"💾 Tamanho: {size_str}"
            )

    except Exception as e:
        return f"❌ Erro ao criar miniatura: {str(e)}"


def overlay_text(image_path: str, text: str, position: str = "bottom-right",
                font_size: int = 20, font_color: str = "white",
                background_color: str = None, opacity: float = 0.7,
                padding: int = 10, output_path: str = None) -> str:
    """Sobrepõe texto em uma imagem (útil para legendas ou marca d'água).

    Args:
        image_path: Caminho para a imagem de entrada
        text: Texto para sobrepor
        position: Posição do texto ('top-left', 'top-center', 'top-right',
                 'center-left', 'center', 'center-right',
                 'bottom-left', 'bottom-center', 'bottom-right')
        font_size: Tamanho da fonte em pixels
        font_color: Cor do texto (nome ou hexadecimal #RRGGBB)
        background_color: Cor de fundo do texto (None para transparente)
        opacity: Opacidade do texto/fundo (0.0 a 1.0)
        padding: Espaçamento interno em pixels
        output_path: Caminho para salvar a imagem com texto (se None, sobrescreve original)

    Returns:
        Mensagem de sucesso ou erro
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image_path):
        return f"❌ Arquivo não encontrado: {image_path}"

    try:
        from PIL import Image, ImageDraw, ImageFont
        import webcolors

        with Image.open(image_path) as img:
            # Ensure image is in RGBA mode for transparency support
            if img.mode != 'RGBA':
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGBA')

            # Create a transparent overlay for text
            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            # Try to load a font, fall back to default
            try:
                # Try common system fonts
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "/System/Library/Fonts/Helvetica.ttc",  # macOS
                    "C:/Windows/Fonts/arial.ttf",  # Windows
                    "arial.ttf"  # Fallback
                ]
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except IOError:
                        continue
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # Get text size
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Calculate position
            margin = padding
            x, y = 0, 0
            if position == "top-left":
                x = margin
                y = margin
            elif position == "top-center":
                x = (img.width - text_width) // 2
                y = margin
            elif position == "top-right":
                x = img.width - text_width - margin
                y = margin
            elif position == "center-left":
                x = margin
                y = (img.height - text_height) // 2
            elif position == "center":
                x = (img.width - text_width) // 2
                y = (img.height - text_height) // 2
            elif position == "center-right":
                x = img.width - text_width - margin
                y = (img.height - text_height) // 2
            elif position == "bottom-left":
                x = margin
                y = img.height - text_height - margin
            elif position == "bottom-center":
                x = (img.width - text_width) // 2
                y = img.height - text_height - margin
            elif position == "bottom-right":
                x = img.width - text_width - margin
                y = img.height - text_height - margin
            else:
                # Default to bottom-right
                x = img.width - text_width - margin
                y = img.height - text_height - margin

            # Parse colors
            try:
                if font_color.startswith('#'):
                    font_rgb = webcolors.hex_to_rgb(font_color)
                else:
                    font_rgb = webcolors.name_to_rgb(font_color)
            except ValueError:
                # Fallback to white
                font_rgb = (255, 255, 255)

            if background_color:
                try:
                    if background_color.startswith('#'):
                        bg_rgb = webcolors.hex_to_rgb(background_color)
                    else:
                        bg_rgb = webcolors.name_to_rgb(background_color)
                except ValueError:
                    # Fallback to black with opacity
                    bg_rgb = (0, 0, 0)
            else:
                bg_rgb = (0, 0, 0)  # Default black background

            # Apply opacity
            font_rgba = (*font_rgb, int(255 * opacity))
            bg_rgba = (*bg_rgb, int(255 * opacity)) if background_color else (0, 0, 0, 0)

            # Draw background if specified
            if background_color:
                # Add padding to background
                bg_x0 = x - padding//2
                bg_y0 = y - padding//2
                bg_x1 = x + text_width + padding//2
                bg_y1 = y + text_height + padding//2
                draw.rectangle([bg_x0, bg_y0, bg_x1, bg_y1], fill=bg_rgba)

            # Draw text
            draw.text((x, y), text, font=font, fill=font_rgba)

            # Composite the text layer onto the image
            result = Image.alpha_composite(img, txt_layer)

            # Determine output path
            if output_path is None:
                output_path = image_path

            # Convert back to original mode if needed for saving
            if output_path == image_path and img.mode != 'RGBA':
                # Need to convert back to original format for saving
                if img.mode == 'RGB':
                    result = result.convert('RGB')
                elif img.mode == 'L':
                    result = result.convert('L')
                else:
                    # Try to convert back, fallback to RGB
                    try:
                        result = result.convert(img.mode)
                    except ValueError:
                        result = result.convert('RGB')

            # Save image
            if output_path == image_path:
                # Save with original format
                img_format = img.format if img.format else 'PNG'
                # Handle format-specific conversions
                if img_format == 'JPEG' and result.mode == 'RGBA':
                    # JPEG doesn't support alpha, composite on white
                    rgb_bg = Image.new('RGB', result.size, (255, 255, 255))
                    rgb_bg.paste(result, mask=result.split()[-1])  # Use alpha channel as mask
                    result = rgb_bg
                result.save(output_path, img_format)
            else:
                # Determine format from extension
                ext = os.path.splitext(output_path)[1].lower()
                format_map = {
                    '.jpg': 'JPEG', '.jpeg': 'JPEG',
                    '.png': 'PNG',
                    '.bmp': 'BMP',
                    '.tiff': 'TIFF', '.tif': 'TIFF',
                    '.gif': 'GIF',
                    '.webp': 'WEBP'
                }
                fmt = format_map.get(ext, 'PNG')
                # Handle special cases
                if fmt == 'JPEG' and result.mode == 'RGBA':
                    # JPEG doesn't support alpha, composite on white
                    rgb_bg = Image.new('RGB', result.size, (255, 255, 255))
                    rgb_bg.paste(result, mask=result.split()[-1])  # Use alpha channel as mask
                    result = rgb_bg
                result.save(output_path, fmt)

            # Format file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            action = "sobrescrita" if output_path == image_path else "salva"
            return (
                f"✅ Texto sobreposto e imagem {action} com sucesso!\n"
                f"📁 Arquivo: {os.path.basename(output_path)}\n"
                f"📝 Texto: '{text}'\n"
                f"📍 Posição: {position}\n"
                f"🔤 Fonte: {font_size}px, {font_color}\n"
                f"🎨 Fundo: {background_color or 'transparente'}\n"
                f"💧 Opacidade: {opacity}\n"
                f"💾 Tamanho: {size_str}"
            )

    except Exception as e:
        return f"❌ Erro ao sobrepor texto na imagem: {str(e)}"


def compare_images(image1_path: str, image2_path: str,
                  method: str = "pixel_diff", threshold: int = 10) -> str:
    """Compara duas imagens e mostra as diferenças.

    Args:
        image1_path: Caminho para a primeira imagem
        image2_path: Caminho para a segunda imagem
        method: Método de comparação ('pixel_diff', 'histogram', 'structural')
        threshold: Limite de diferença para considerar pixels diferentes (0-255)

    Returns:
        Resultado da comparação
    """
    if not _check_pil():
        return "❌ Biblioteca PIL/Pillow não disponível. Instale com: pip install pillow"

    if not os.path.exists(image1_path):
        return f"❌ Primeira imagem não encontrada: {image1_path}"

    if not os.path.exists(image2_path):
        return f"❌ Segunda imagem não encontrada: {image2_path}"

    try:
        from PIL import Image, ImageChops, ImageStat
        import math

        with Image.open(image1_path) as img1, Image.open(image2_path) as img2:
            # Convert to same mode if needed
            if img1.mode != img2.mode:
                # Convert both to RGB for comparison
                if img1.mode in ('RGBA', 'LA', 'P') and 'transparency' in img1.info:
                    img1 = img1.convert('RGBA')
                else:
                    img1 = img1.convert('RGB')

                if img2.mode in ('RGBA', 'LA', 'P') and 'transparency' in img2.info:
                    img2 = img2.convert('RGBA')
                else:
                    img2 = img2.convert('RGB')

            # Ensure same size
            if img1.size != img2.size:
                # Resize second image to match first
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

            if method == "pixel_diff":
                # Pixel-by-pixel difference
                diff = ImageChops.difference(img1, img2)

                # Convert to grayscale for easier analysis
                if diff.mode != 'L':
                    diff_gray = diff.convert('L')
                else:
                    diff_gray = diff

                # Get statistics
                stat = ImageStat.Stat(diff_gray)
                mean_diff = stat.mean[0]
                std_dev = stat.stddev[0]

                # Count pixels above threshold
                # Create binary image where pixels above threshold are white
                threshold_img = diff_gray.point(lambda p: 255 if p > threshold else 0)
                threshold_stat = ImageStat.Stat(threshold_img)
                white_pixels = threshold_stat.sum[0]
                total_pixels = img1.width * img1.height
                percent_different = (white_pixels / 255) / total_pixels * 100 if total_pixels > 0 else 0

                identical = mean_diff == 0 and std_dev == 0

                if identical:
                    return (
                        "✅ IMAGENS IDÊNTICAS\n"
                        f"📁 Imagem 1: {os.path.basename(image1_path)}\n"
                        f"📁 Imagem 2: {os.path.basename(image2_path)}\n"
                        f"📐 Dimensões: {img1.width}×{img1.height}\n"
                        f"🎯 Diferença média: {mean_diff:.2f}/255\n"
                        f"📊 Desvio padrão: {std_dev:.2f}/255\n"
                        f"📈 Pixels diferentes: 0/{total_pixels} (0.00%)"
                    )
                else:
                    # Format numbers nicely
                    if mean_diff < 1:
                        mean_str = f"{mean_diff:.3f}"
                    else:
                        mean_str = f"{mean_diff:.1f}"

                    if std_dev < 1:
                        std_str = f"{std_dev:.3f}"
                    else:
                        std_str = f"{std_dev:.1f}"

                    # Format percentage
                    if percent_different < 0.01:
                        percent_str = f"{percent_different:.4f}%"
                    elif percent_different < 1:
                        percent_str = f"{percent_different:.2f}%"
                    else:
                        percent_str = f"{percent_different:.1f}%"

                    return (
                        "🔍 COMPARAÇÃO DE IMAGENS (DIFERENÇA DE PIXEL)\n"
                        f"📁 Imagem 1: {os.path.basename(image1_path)}\n"
                        f"📁 Imagem 2: {os.path.basename(image2_path)}\n"
                        f"📐 Dimensões: {img1.width}×{img1.height}\n"
                        f"🎯 Diferença média: {mean_str}/255\n"
                        f"📊 Desvio padrão: {std_str}/255\n"
                        f"📈 Pixels diferentes: {int(white_pixels/255):,}/{total_pixels:,} ({percent_str})\n"
                        f"🎚️ Limiar usado: {threshold}/255\n"
                        f"{'✅ Imagens são muito similares' if percent_different < 1 else '⚠️ Diferença significativa detectada'}"
                    )

            elif method == "histogram":
                # Compare histograms
                hist1 = img1.histogram()
                hist2 = img2.histogram()

                # Calculate correlation or distance
                # Using Euclidean distance for simplicity
                squared_diff = sum((a - b) ** 2 for a, b in zip(hist1, hist2))
                euclidean_distance = math.sqrt(squared_diff)

                # Normalize by max possible distance
                max_possible = math.sqrt(len(hist1) * (255 ** 2))
                similarity = 1 - (euclidean_distance / max_possible) if max_possible > 0 else 1

                return (
                    "🔍 COMPARAÇÃO DE IMAGENS (HISTOGRAMA)\n"
                    f"📁 Imagem 1: {os.path.basename(image1_path)}\n"
                    f"📁 Imagem 2: {os.path.basename(image2_path)}\n"
                    f"📐 Dimensões: {img1.width}×{img1.height}\n"
                    f"📊 Similaridade de histograma: {similarity:.4f} ({similarity*100:.2f}%)\n"
                    f"📏 Distância Euclidiana: {euclidean_distance:.2f}\n"
                    f"{'✅ Histogramas muito similares' if similarity > 0.95 else '⚠️ Diferença significativa nos histogramas'}"
                )

            else:
                return f"❌ Método de comparação não suportado: {method}. Métodos disponíveis: pixel_diff, histogram"

    except Exception as e:
        return f"❌ Erro ao comparar imagens: {str(e)}"


# Register all tools
def register(api):
    """Registra todas as ferramentas de processamento avançado de imagens."""
    api.register_tool(
        name="get_image_info",
        func=get_image_info,
        description="Obtém informações detalhadas sobre uma imagem, incluindo dimensões, formato, tamanho e metadados EXIF.",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
        },
        required=["image_path"],
    )

    api.register_tool(
        name="resize_image",
        func=resize_image,
        description="Redimensiona uma imagem com opções para manter proporção, escala específica ou dimensões exatas.",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "width": {"type": "integer", "description": "Largura desejada em pixels (opcional)"},
            "height": {"type": "integer", "description": "Altura desejada em pixels (opcional)"},
            "scale": {"type": "number", "description": "Fator de escala (ex: 0.5 para metade do tamanho)"},
            "maintain_aspect": {"type": "boolean", "description": "Manter proporção original (padrão: true)"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem redimensionada (opcional)"},
        },
        required=["image_path"],
    )

    api.register_tool(
        name="rotate_image",
        func=rotate_image,
        description="Rota uma imagem por um ângulo especificado em graus.",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "angle": {"type": "number", "description": "Ângulo de rotação em graus (positivo = horário)"},
            "expand": {"type": "boolean", "description": "Expandir imagem para acomodar rotação completa (padrão: true)"},
            "resample": {"type": "integer", "description": "Filtro de reamostragem (0-5, padrão: 3=LANCZOS)"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem rotacionada (opcional)"},
        },
        required=["image_path", "angle"],
    )

    api.register_tool(
        name="apply_filter",
        func=apply_filter,
        description="Aplica vários filtros a uma imagem (desfoque, nitidez, brilho, contraste, etc.).",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "filter_type": {"type": "string", "description": "Tipo de filtro: blur, gaussian_blur, sharpen, edge_enhance, emboss, smooth, detail, unsharp_mask, brightness, contrast, saturation, color_balance"},
            "intensity": {"type": "number", "description": "Intensidade do efeito (0.0 a 2.0, padrão: 1.0)"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem filtrada (opcional)"},
        },
        required=["image_path", "filter_type"],
    )

    api.register_tool(
        name="convert_image_format",
        func=convert_image_format,
        description="Converte uma imagem para um formato diferente (JPEG, PNG, BMP, TIFF, GIF, WEBP).",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem convertida (opcional)"},
            "format": {"type": "string", "description": "Formato de destino: JPEG, PNG, BMP, TIFF, GIF, WEBP"},
            "quality": {"type": "integer", "description": "Qualidade para formatos com perda (1-100, padrão: 85)"},
        },
        required=["image_path"],
    )

    api.register_tool(
        name="create_thumbnail",
        func=create_thumbnail,
        description="Cria uma miniatura (thumbnail) de uma imagem com opções de corte ajustado.",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "size": {"type": "any", "description": "Tamanho da miniatura: inteiro para quadrado ou tupla (largura, altura)"},
            "output_path": {"type": "string", "description": "Caminho para salvar a miniatura (opcional)"},
            "crop_to_fit": {"type": "boolean", "description": "Cortar imagem para exatamente caber no tamanho (padrão: false)"},
        },
        required=["image_path"],
    )

    api.register_tool(
        name="overlay_text",
        func=overlay_text,
        description="Sobrepõe texto em uma imagem (útil para legendas, marca d'água ou anotações).",
        parameters={
            "image_path": {"type": "string", "description": "Caminho para o arquivo de imagem"},
            "text": {"type": "string", "description": "Texto para sobrepor na imagem"},
            "position": {"type": "string", "description": "Posição do texto: top-left, top-center, top-right, center-left, center, center-right, bottom-left, bottom-center, bottom-right (padrão: bottom-right)"},
            "font_size": {"type": "integer", "description": "Tamanho da fonte em pixels (padrão: 20)"},
            "font_color": {"type": "string", "description": "Cor do texto (nome ou hexadecimal #RRGGBB, padrão: white)"},
            "background_color": {"type": "string", "description": "Cor de fundo do texto (opcional, padrão: none para transparente)"},
            "opacity": {"type": "number", "description": "Opacidade do texto/fundo (0.0 a 1.0, padrão: 0.7)"},
            "padding": {"type": "integer", "description": "Espaçamento interno em pixels (padrão: 10)"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem com texto (opcional)"},
        },
        required=["image_path", "text"],
    )

    api.register_tool(
        name="compare_images",
        func=compare_images,
        description="Compara duas imagens e mostra as diferenças usando vários métodos.",
        parameters={
            "image1_path": {"type": "string", "description": "Caminho para a primeira imagem"},
            "image2_path": {"type": "string", "description": "Caminho para a segunda imagem"},
            "method": {"type": "string", "description": "Método de comparação: pixel_diff, histogram (padrão: pixel_diff)"},
            "threshold": {"type": "integer", "description": "Limite de diferença para pixels diferentes (0-255, padrão: 10)"},
        },
        required=["image1_path", "image2_path"],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Processamento avançado de imagens com redimensionamento, rotação, filtros, conversão de formatos, miniaturas, sobreposição de texto e comparação",
        "tools": [
            "get_image_info", "resize_image", "rotate_image", "apply_filter",
            "convert_image_format", "create_thumbnail", "overlay_text", "compare_images"
        ],
    }