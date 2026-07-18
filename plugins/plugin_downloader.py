"""
plugin_downloader.py
====================
Plugin de download de arquivos da internet. Permite baixar arquivos de qualquer URL
(e.g., GitHub, repositórios, documentação) e salvar no sistema de arquivos local com
indicadores de progresso e tratamento de erros.

Recursos:
  - Download de arquivos grandes com streaming (baixo uso de memória)
  - Barra de progresso com velocidade e ETA estimada
  - Extração automática de nome de arquivo da URL ou headers
  - Suporte a redirecionamentos HTTP
  - Tratamento de erros de rede e HTTP
  - Verificação de segurança básica para prevenir path traversal
"""

import os
import re
import hashlib
from datetime import datetime
from typing import Optional, Tuple
import mimetypes

__version__ = "1.0.0"
PLUGIN_NAME = "Downloader de Arquivos"


def _is_safe_path(path: str, base_path: str = None) -> bool:
    """Verifica se um caminho é seguro para prevenir path traversal attacks."""
    if base_path is None:
        base_path = os.getcwd()

    # Resolve o caminho absoluto
    try:
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_path)
        return abs_path.startswith(abs_base)
    except Exception:
        return False


def _extract_filename_from_url(url: str) -> Optional[str]:
    """Extrai nome de arquivo de uma URL quando possível."""
    # Remove query parameters e fragments
    clean_url = url.split('?')[0].split('#')[0]
    # Pega o último segmento do path
    filename = os.path.basename(clean_url)
    if filename and '.' in filename:  # Provavelmente tem extensão
        return filename
    return None


def _extract_filename_from_headers(headers: dict) -> Optional[str]:
    """Extrai nome de arquivo dos headers HTTP Content-Disposition."""
    content_disposition = headers.get('content-disposition') or headers.get('Content-Disposition')
    if content_disposition:
        # Procura por filename= ou filename*=
        filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
        if filename_match:
            return filename_match.group(2)
    return None


def download_file(url: str,
                 save_path: str = "",
                 show_progress: bool = True,
                 timeout: int = 30) -> str:
    """Baixa um arquivo de uma URL e salva no sistema de arquivos local.

    Args:
        url: URL do arquivo para baixar
        save_path: Caminho onde salvar o arquivo (se vazio, usa nome da URL ou diretório atual)
        show_progress: Se deve mostrar indicador de progresso durante o download
        timeout: Timeout em segundos para a requisição (padrão: 30)

    Returns:
        Mensagem de sucesso com detalhes do download ou mensagem de erro
    """
    try:
        import requests
    except ImportError:
        return "❌ Biblioteca 'requests' não disponível. Instale com: pip install requests"

    # Validação básica da URL
    if not url.startswith(('http://', 'https://')):
        return "❌ URL inválida. Deve começar com http:// ou https://"

    try:
        # Inicia a requisição com streaming para arquivos grandes
        response = requests.get(url, stream=True, timeout=timeout, allow_redirects=True)
        response.raise_for_status()  # Levanta exceção para códigos de erro HTTP

        # Determina o nome do arquivo e caminho de salvamento
        filename = None

        # 1. Tenta extrair dos headers
        filename = _extract_filename_from_headers(response.headers)

        # 2. Se não conseguiu, tenta da URL
        if not filename:
            filename = _extract_filename_from_url(url)

        # 3. Se ainda não tem nome, usa um nome genérico baseado em timestamp
        if not filename:
            # Tenta determinar extensão do content-type
            content_type = response.headers.get('content-type', '').split(';')[0].strip()
            extension = mimetypes.guess_extension(content_type) or '.bin'
            filename = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"

        # Determina o caminho completo de salvamento
        if not save_path:
            # Se nenhum caminho especificado, salva no diretório atual
            full_path = os.path.join(os.getcwd(), filename)
        elif os.path.isdir(save_path):
            # Se save_path é um diretório, coloca o arquivo dentro dele
            full_path = os.path.join(save_path, filename)
        else:
            # Se save_path parece ser um caminho completo de arquivo
            full_path = save_path
            # Se não tem diretório especificado, usa o diretório atual
            if not os.path.dirname(full_path):
                full_path = os.path.join(os.getcwd(), full_path)

        # Verifica segurança do caminho
        if not _is_safe_path(full_path):
            return f"❌ Caminho de salvamento inválido por motivos de segurança: {full_path}"

        # Garante que o diretório de destino existe
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Obtém o tamanho total se disponível nos headers
        total_size = int(response.headers.get('content-length', 0))

        # Inicia o download
        downloaded = 0
        chunk_size = 8192  # 8KB chunks
        start_time = datetime.now()

        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filtra chunks vazios
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Mostra progresso se solicitado e se soubermos o tamanho total
                    if show_progress and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        elapsed = (datetime.now() - start_time).total_seconds()
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        # Formata unidades
                        def format_bytes(bytes_val):
                            for unit in ['B', 'KB', 'MB', 'GB']:
                                if bytes_val < 1024.0:
                                    return f"{bytes_val:.1f} {unit}"
                                bytes_val /= 1024.0
                            return f"{bytes_val:.1f} TB"

                        speed_str = format_bytes(speed) + "/s"
                        downloaded_str = format_bytes(downloaded)
                        total_str = format_bytes(total_size)

                        # Calcula ETA
                        if speed > 0:
                            eta_seconds = (total_size - downloaded) / speed
                            eta_str = f"{int(eta_seconds//60)}:{int(eta_seconds%60):02d}" if eta_seconds >= 60 else f"{int(eta_seconds)}s"
                        else:
                            eta_str = "calculando..."

                        # Limpa a linha e mostra progresso (em um ambiente real, isso seria mais sofisticado)
                        # Para simplificação no console, vamos apenas atualizar periodicamente
                        if downloaded % (chunk_size * 100) == 0:  # A cada ~800KB
                            print(f"\r⬇️  Download: {percent:.1f}% ({downloaded_str}/{total_str}) "
                                  f"Velocidade: {speed_str} ETA: {eta_str}", end='', flush=True)

        # Limpa a linha de progresso se estava mostrando
        if show_progress and total_size > 0:
            print()  # Nova linha após o progresso

        # Calcula estatísticas finais
        elapsed_time = (datetime.now() - start_time).total_seconds()
        final_speed = downloaded / elapsed_time if elapsed_time > 0 else 0

        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.1f} TB"

        size_str = format_bytes(downloaded)
        speed_str = format_bytes(final_speed) + "/s"

        # Calcula hash MD5 para verificação de integridade (opcional)
        try:
            with open(full_path, 'rb') as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
            hash_str = file_hash.hexdigest()
        except Exception:
            hash_str = "não calculado"

        success_msg = (
            f"✅ Download concluído com sucesso!\n"
            f"📁 Arquivo salvo: {os.path.abspath(full_path)}\n"
            f"📊 Tamanho: {size_str}\n"
            f"⏱️  Tempo: {elapsed_time:.1f}s\n"
            f"🚀 Velocidade média: {speed_str}\n"
            f"🔗 URL: {url}\n"
            f"🔐 MD5: {hash_str}"
        )

        return success_msg

    except requests.exceptions.MissingSchema:
        return f"❌ URL inválida: {url}"
    except requests.exceptions.ConnectionError:
        return f"❌ Erro de conexão. Verifique sua internet e a URL: {url}"
    except requests.exceptions.Timeout:
        return f"❌ Timeout ao baixar de {url} (limite: {timeout}s)"
    except requests.exceptions.HTTPError as e:
        return f"❌ Erro HTTP {e.response.status_code}: {e.response.reason} para URL: {url}"
    except Exception as e:
        return f"❌ Erro inesperado durante download: {str(e)}"


def download_github_file(repo_url: str,
                        file_path: str,
                        branch: str = "main",
                        save_path: str = "",
                        show_progress: bool = True) -> str:
    """Função especializada para baixar arquivos diretamente de repositórios GitHub.

    Converte uma URL de repositório GitHub padrão para a URL de arquivo raw.

    Args:
        repo_url: URL do repositório GitHub (ex: https://github.com/user/repo)
        file_path: Caminho do arquivo dentro do repositório
        branch: Branch ou tag a usar (padrão: main)
        save_path: Onde salvar o arquivo (opcional)
        show_progress: Se deve mostrar progresso

    Returns:
        Mensagem de resultado do download
    """
    # Normaliza a URL do repositório
    repo_url = repo_url.rstrip('/')
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]

    # Constrói a URL raw do GitHub
    # Formato: https://raw.githubusercontent.com/user/repo/branch/file_path
    if 'github.com' in repo_url:
        # Extrai user/repo da URL
        parts = repo_url.split('github.com/')
        if len(parts) == 2:
            user_repo = parts[1]
            raw_url = f"https://raw.githubusercontent.com/{user_repo}/{branch}/{file_path}"
            return download_file(raw_url, save_path, show_progress)

    # Se não for GitHub reconhecido, tenta download direto
    return download_file(repo_url, save_path, show_progress)


# Register all tools with the plugin system
def register(api):
    """Registra todas as ferramentas de download de arquivos."""
    api.register_tool(
        name="download_file_pro",
        func=download_file,
        description="Baixa um arquivo de qualquer URL com indicador de progresso, suporte a timeout, e verificacao de integridade.",
        parameters={
            "url": {"type": "string", "description": "URL do arquivo para baixar (http:// ou https://)"},
            "save_path": {"type": "string", "description": "Caminho onde salvar o arquivo (opcional)"},
            "show_progress": {"type": "boolean", "description": "Mostrar indicador de progresso (padrão: true)"},
            "timeout": {"type": "integer", "description": "Timeout em segundos para a requisição (padrão: 30)"}
        },
        required=["url"]
    )

    api.register_tool(
        name="download_github_file",
        func=download_github_file,
        description="Baixa um arquivo diretamente de um repositório GitHub (converte automaticamente para URL raw).",
        parameters={
            "repo_url": {"type": "string", "description": "URL do repositório GitHub (ex: https://github.com/user/repo)"},
            "file_path": {"type": "string", "description": "Caminho do arquivo dentro do repositório"},
            "branch": {"type": "string", "description": "Branch ou tag a usar (padrão: main)"},
            "save_path": {"type": "string", "description": "Onde salvar o arquivo (opcional)"},
            "show_progress": {"type": "boolean", "description": "Mostrar indicador de progresso (padrão: true)"}
        },
        required=["repo_url", "file_path"]
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Download de arquivos da internet com suporte a progresso, tratamento de erros e funcionalidade especializada para GitHub.",
        "tools": [
            "download_file_pro",
            "download_github_file"
        ],
    }