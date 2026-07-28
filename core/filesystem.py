from ._common import *
# =======================================================================
# ARQUIVOS E PASTAS
# =======================================================================

def create_folder(path: str) -> str:
    """Cria uma pasta (e subpastas necessarias)."""
    try:
        os.makedirs(path, exist_ok=True)
        return f"Pasta criada em: {os.path.abspath(path)}"
    except Exception as e:
        return f"Erro ao criar pasta: {e}"


def write_file(path: str, content: str) -> str:
    """Cria ou sobrescreve um arquivo de texto."""
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Arquivo salvo em: {os.path.abspath(path)}"
    except Exception as e:
        return f"Erro ao escrever arquivo: {e}"


def append_file(path: str, content: str) -> str:
    """Adiciona texto ao final de um arquivo existente."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Conteudo adicionado em: {os.path.abspath(path)}"
    except Exception as e:
        return f"Erro ao adicionar ao arquivo: {e}"


def read_file(path: str) -> str:
    """Le o conteudo de um arquivo de texto."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


def list_files(path: str = ".") -> str:
    """Lista arquivos e pastas dentro de um diretorio."""
    try:
        items = os.listdir(path)
        return "\n".join(items) if items else "A pasta esta vazia."
    except Exception as e:
        return f"Erro ao listar pasta: {e}"


def search_files(directory: str, name_pattern: str) -> str:
    """Busca arquivos cujo nome contenha um texto, dentro de um diretorio (recursivo)."""
    try:
        matches = []
        for root, _, files in os.walk(directory):
            for f in files:
                if name_pattern.lower() in f.lower():
                    matches.append(os.path.join(root, f))
        return "\n".join(matches) if matches else "Nenhum arquivo encontrado."
    except Exception as e:
        return f"Erro ao buscar arquivos: {e}"


def get_file_info(path: str) -> str:
    """Retorna tamanho, data de modificacao e tipo de um arquivo ou pasta."""
    try:
        if not os.path.exists(path):
            return "Caminho nao existe."
        is_dir = os.path.isdir(path)
        size = os.path.getsize(path) if not is_dir else "-"
        modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d/%m/%Y %H:%M:%S")
        tipo = "pasta" if is_dir else "arquivo"
        return f"Tipo: {tipo}\nTamanho: {size} bytes\nUltima modificacao: {modified}"
    except Exception as e:
        return f"Erro ao obter informacoes: {e}"


def move_file(source: str, destination: str) -> str:
    """Move ou renomeia um arquivo ou pasta."""
    try:
        shutil.move(source, destination)
        return f"Movido de '{source}' para '{destination}'"
    except Exception as e:
        return f"Erro ao mover: {e}"


def copy_file(source: str, destination: str) -> str:
    """Copia um arquivo ou pasta para outro local."""
    try:
        if os.path.isdir(source):
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        return f"Copiado de '{source}' para '{destination}'"
    except Exception as e:
        return f"Erro ao copiar: {e}"


def delete_path(path: str, confirm: bool = False) -> str:
    """Apaga um arquivo ou pasta. Acao IRREVERSIVEL - exige confirm=true."""
    if not confirm:
        return (
            f"Acao cancelada por seguranca. Para realmente apagar '{path}', "
            "confirme explicitamente (confirm=true)."
        )
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"'{path}' apagado com sucesso."
    except Exception as e:
        return f"Erro ao apagar: {e}"


