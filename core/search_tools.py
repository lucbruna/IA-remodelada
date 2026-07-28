from ._common import *
# =======================================================================
# REGISTRO DE FERRAMENTAS (usado pelo loop do agente)
# =======================================================================

def search_and_replace(file_path: str, old_text: str, new_text: str) -> str:
    """Busca e substitui texto em um arquivo. Similar a 'find and replace' em editores.

    Args:
        file_path: Caminho do arquivo a ser editado
        old_text: Texto exato a ser substituido
        new_text: Novo texto que substituira o antigo

    Returns:
        Mensagem de confirmacao ou erro
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return f"Texto nao encontrado em '{file_path}'."

        count = content.count(old_text)
        content = content.replace(old_text, new_text)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        palavra = "vez" if count == 1 else "vezes"
        return f"Substituido '{old_text}' por '{new_text}' em '{file_path}' ({count} {palavra})."
    except FileNotFoundError:
        return f"Arquivo nao encontrado: '{file_path}'"
    except Exception as e:
        return f"Erro ao substituir texto: {e}"


# =======================================================================
# NOVAS FERRAMENTAS TURBO: busca em conteudo, web, compressao, etc.
# =======================================================================

def grep_in_files(directory: str, pattern: str, include_ext: str = "") -> str:
    """Busca um texto dentro do conteudo de arquivos em um diretorio (recursivo).
    Similar ao grep do Linux. Opcional: filtrar por extensao (ex: '.py,.txt')."""
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        results = []
        exts = [e.strip().lower() for e in include_ext.split(",") if e.strip()] if include_ext else None
        for root, _, files in os.walk(directory):
            for f in files:
                if exts and not any(f.lower().endswith(e) for e in exts):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        for i, line in enumerate(fh, 1):
                            if compiled.search(line):
                                rel = os.path.relpath(path, directory)
                                results.append(f"{rel}:{i}: {line.rstrip()[:200]}")
                except Exception:
                    pass  # pula arquivos binarios ou sem permissao
        if not results:
            return "Nenhuma ocorrencia encontrada."
        total = len(results)
        if total > 100:
            results = results[:100]
            results.append(f"\n... e mais {total - 100} ocorrencias.")
        return "\n".join(results)
    except Exception as e:
        return f"Erro ao buscar conteudo: {e}"


def web_search(query: str, max_results: int = 5) -> str:
    """Busca na web usando DuckDuckGo (lite HTML). Nao precisa de API key."""
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        results = []
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            resp.text, re.DOTALL
        ):
            link = urllib.parse.unquote(match.group(1))
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            results.append(f"{title}\n  {link}")
            if len(results) >= max_results:
                break

        if not results:
            snippets = re.findall(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                resp.text, re.DOTALL
            )
            for s in snippets[:max_results]:
                results.append(re.sub(r"<[^>]+>", "", s).strip())

        if not results:
            return "Nenhum resultado encontrado. Tente uma busca mais especifica."

        return "\n---\n".join(results)
    except requests.Timeout:
        return "A busca na web excedeu o tempo limite. Tente novamente."
    except Exception as e:
        return f"Erro ao buscar na web: {e}"


def create_zip(source_path: str, output_path: str = "") -> str:
    """Compacta um arquivo ou pasta em um arquivo .zip."""
    try:
        if not output_path:
            base = os.path.basename(source_path.rstrip("/\\"))
            output_path = base + ".zip"
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(source_path):
                zf.write(source_path, os.path.basename(source_path))
            elif os.path.isdir(source_path):
                for root, _, files in os.walk(source_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        arcname = os.path.relpath(fp, os.path.dirname(source_path))
                        zf.write(fp, arcname)
            else:
                return f"Erro: caminho nao encontrado '{source_path}'."
        size = os.path.getsize(output_path)
        return f"Arquivo criado: {os.path.abspath(output_path)} ({size} bytes)"
    except Exception as e:
        return f"Erro ao criar zip: {e}"


def extract_zip(zip_path: str, output_dir: str = "") -> str:
    """Extrai um arquivo .zip para uma pasta."""
    try:
        if not output_dir:
            output_dir = os.path.splitext(os.path.basename(zip_path))[0]
        os.makedirs(output_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(output_dir)
        extracted = []
        for root, _, files in os.walk(output_dir):
            for f in files:
                extracted.append(os.path.relpath(os.path.join(root, f), output_dir))
        return f"Extraido para: {os.path.abspath(output_dir)}\nArquivos:\n" + "\n".join(extracted[:50])
    except Exception as e:
        return f"Erro ao extrair zip: {e}"


def search_conversation(query: str) -> str:
    """Busca texto dentro do historico de conversas salvo em disco."""
    try:
        history = _load_json(HISTORY_FILE, [])
        q = query.lower()
        results = []
        for i, m in enumerate(history):
            content = m.get("content", "")
            role = m.get("role", "unknown")
            if q in content.lower():
                preview = content[:200].replace("\n", " ")
                results.append(f"[{i}] {role}: {preview}...")
        if not results:
            return "Nenhuma mensagem encontrada com esse termo."
        return "\n".join(results)
    except Exception as e:
        return f"Erro ao buscar na conversa: {e}"


