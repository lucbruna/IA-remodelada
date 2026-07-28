from ._common import *
import requests
# =======================================================================


# =======================================================================
# DOWNLOAD E INSTALACAO (baixar arquivos, clonar repos, instalar pacotes)
# =======================================================================

def download_file(url: str, output_path: str = "") -> str:
    """
    Baixa QUALQUER arquivo da internet e salva no disco.
    
    Usa requests com streaming para baixar arquivos de QUALQUER origem:
    GitHub, sites, APIs, etc. Funciona com programas, instaladores,
    ZIPs, PDFs, imagens, videos, documentos, etc.
    
    Args:
        url: URL completa do arquivo (ex: https://github.com/user/repo/arquivo.zip)
        output_path: Caminho para salvar (opcional, usa nome do arquivo se vazio)
    
    Returns:
        Mensagem de confirmacao ou erro
    """
    try:
        import requests
        import hashlib
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"
    try:
        if not output_path:
            filename = url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = "download_" + hashlib.md5(url.encode()).hexdigest()[:8]
            output_path = os.path.join(".", filename)
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=120, stream=True)
        resp.raise_for_status()
        
        parent = os.path.dirname(os.path.abspath(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        size = os.path.getsize(output_path)
        size_str = f"{size:,} bytes"
        if size > 1024**2:
            size_str = f"{size/1024**2:.1f} MB"
        elif size > 1024:
            size_str = f"{size/1024:.1f} KB"
        
        return f"Download concluido: {os.path.abspath(output_path)} ({size_str})"
    except requests.Timeout:
        return "Timeout ao baixar. URL pode ser invalida ou conexao lenta."
    except requests.RequestException as e:
        return f"Erro ao baixar: {e}"
    except Exception as e:
        return f"Erro ao salvar: {e}"


def git_clone(url: str, output_dir: str = "") -> str:
    """
    Clona um repositorio Git (GitHub, GitLab, Bitbucket) para o computador.
    
    Git precisa estar instalado no sistema. Clona repos inteiros,
    ideais para baixar projetos, bibliotecas ou codigo-fonte.
    
    Args:
        url: URL do repositorio (ex: https://github.com/usuario/repo.git)
        output_dir: Pasta de destino (opcional)
    
    Returns:
        Mensagem de confirmacao ou erro
    """
    try:
        check = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        if check.returncode != 0:
            return "Git nao encontrado. Instale de: https://git-scm.com/downloads"
        
        cmd = ["git", "clone", url]
        if output_dir:
            cmd.append(output_dir)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return f"Repositorio clonado com sucesso."
        else:
            erro = result.stderr.strip()[:500]
            if "already exists" in erro:
                return f"Pasta ja existe. Use outro nome ou apague a existente."
            return f"Erro ao clonar: {erro}"
    except FileNotFoundError:
        return "Git nao encontrado. Instale de: https://git-scm.com/downloads"
    except subprocess.TimeoutExpired:
        return "Timeout ao clonar (5min). Repositorio pode ser muito grande."
    except Exception as e:
        return f"Erro ao clonar: {e}"


def pip_install(package: str) -> str:
    """
    Instala um pacote Python via pip.
    
    Args:
        package: Nome do pacote (ex: 'requests', 'numpy==1.24.0', 'pandas')
    
    Returns:
        Mensagem de confirmacao ou erro
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return f"Pacote instalado: {package}"
        else:
            erro = result.stderr.strip()[:500]
            return f"Erro ao instalar {package}: {erro}"
    except subprocess.TimeoutExpired:
        return f"Timeout ao instalar {package}."
    except Exception as e:
        return f"Erro ao instalar: {e}"


def extract_file(file_path: str, output_dir: str = "") -> str:
    """
    Extrai arquivos compactados (.zip, .tar.gz, .tgz, .tar).
    
    Args:
        file_path: Caminho do arquivo compactado
        output_dir: Pasta de destino (opcional)
    
    Returns:
        Mensagem de confirmacao
    """
    try:
        if not os.path.exists(file_path):
            return f"Arquivo nao encontrado: {file_path}"
        
        if not output_dir:
            output_dir = os.path.splitext(file_path)[0]
        
        os.makedirs(output_dir, exist_ok=True)
        
        name = file_path.lower()
        extracted = []
        
        if name.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(output_dir)
        elif name.endswith((".tar.gz", ".tgz")):
            import tarfile
            with tarfile.open(file_path, "r:gz") as tf:
                tf.extractall(output_dir)
        elif name.endswith(".tar"):
            import tarfile
            with tarfile.open(file_path, "r:") as tf:
                tf.extractall(output_dir)
        elif name.endswith(".tar.bz2"):
            import tarfile
            with tarfile.open(file_path, "r:bz2") as tf:
                tf.extractall(output_dir)
        else:
            return f"Formato nao suportado: {os.path.splitext(file_path)[1]}"
        
        # Lista arquivos extraidos
        for root, _, files in os.walk(output_dir):
            for f in files:
                extracted.append(os.path.relpath(os.path.join(root, f), output_dir))
        
        files_str = "\n".join(extracted[:50])
        if len(extracted) > 50:
            files_str += f"\n... e mais {len(extracted)-50} arquivos."
        
        return f"Extraido para: {os.path.abspath(output_dir)}\nArquivos:\n{files_str}"
    except Exception as e:
        return f"Erro ao extrair: {e}"



# --- Session manager (sessoes nomeadas) ---
SESSION_DIR = os.path.join(DATA_DIR, "sessoes")
os.makedirs(SESSION_DIR, exist_ok=True)


def _session_path(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip().lower())
    return os.path.join(SESSION_DIR, f"{safe}.json")


def session_save(name: str) -> str:
    """Salva a conversa atual com um nome para carregar depois."""
    try:
        history = _load_json(HISTORY_FILE, [])
        path = _session_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return f"Conversa salva como '{name}' ({len(history)} mensagens)."
    except Exception as e:
        return f"Erro ao salvar sessao: {e}"


def session_load(name: str) -> str:
    """Carrega uma conversa salva anteriormente pelo nome."""
    try:
        path = _session_path(name)
        if not os.path.exists(path):
            sessions = [f.replace(".json", "") for f in os.listdir(SESSION_DIR) if f.endswith(".json")]
            if not sessions:
                return "Nenhuma sessao salva encontrada."
            return f"Sessao '{name}' nao encontrada. Sessoes disponiveis: {', '.join(sessions)}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _save_json(HISTORY_FILE, data)
        return f"Sessao '{name}' carregada ({len(data)} mensagens). Use 'nova conversa' para aplicar."
    except Exception as e:
        return f"Erro ao carregar sessao: {e}"


def session_list() -> str:
    """Lista todas as sessoes de conversa salvas."""
    try:
        sessions = sorted([f.replace(".json", "") for f in os.listdir(SESSION_DIR) if f.endswith(".json")])
        if not sessions:
            return "Nenhuma sessao salva."
        return "Sessoes disponiveis:\n" + "\n".join(f"  {s}" for s in sessions)
    except Exception as e:
        return f"Erro ao listar sessoes: {e}"


# --- File diff ---
