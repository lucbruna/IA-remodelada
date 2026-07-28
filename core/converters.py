from ._common import *
def format_code(code: str, language: str = "python") -> str:
    """Formata/embeleza codigo fonte. Suporta: python, javascript, html, css, json."""
    try:
        if language == "python":
            import autopep8
            return autopep8.fix_code(code)
        elif language in ("javascript", "js"):
            import jsbeautifier
            return jsbeautifier.beautify(code)
        elif language == "html":
            import jsbeautifier
            return jsbeautifier.beautify(code)
        elif language == "css":
            import jsbeautifier
            return jsbeautifier.beautify(code)
        elif language == "json":
            parsed = json.loads(code)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        else:
            return f"Idioma '{language}' nao suportado. Use: python, javascript, html, css, json."
    except ImportError as e:
        lib = str(e).split("'")[1] if "'" in str(e) else "autopep8/jsbeautifier"
        return f"Instale: pip install {lib}"
    except json.JSONDecodeError as e:
        return f"JSON invalido: {e}"
    except Exception as e:
        return f"Erro ao formatar: {e}"


# --- QR Code generator ---
def qr_generate(text: str, output_path: str = "") -> str:
    """Gera um QR Code a partir de um texto ou URL e salva como imagem PNG."""
    try:
        import qrcode
        from PIL import Image
    except ImportError:
        return "Instale: pip install qrcode[pil]"
    try:
        if not output_path:
            safe = re.sub(r"[^a-zA-Z0-9]", "_", text[:20])
            output_path = os.path.join(DATA_DIR, f"qrcode_{safe}.png")
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        return f"QR Code salvo em: {os.path.abspath(output_path)}"
    except Exception as e:
        return f"Erro ao gerar QR Code: {e}"


# --- Markdown renderer ---
def markdown_to_html(markdown_text: str, output_path: str = "") -> str:
    """Converte texto Markdown para HTML. Opcional: salva em arquivo."""
    try:
        import markdown
    except ImportError:
        return "Instale: pip install markdown"
    try:
        html = markdown.markdown(
            markdown_text,
            extensions=["extra", "codehilite", "tables", "fenced_code"],
        )
        page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Markdown</title>
<style>
body {{ font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; }}
pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
</style></head><body>{html}</body></html>"""
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(page)
            return f"HTML salvo em: {os.path.abspath(output_path)}"
        return page
    except Exception as e:
        return f"Erro ao converter Markdown: {e}"


def markdown_file_to_html(file_path: str, output_path: str = "") -> str:
    """Le um arquivo Markdown e converte para HTML."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            md = f.read()
        return markdown_to_html(md, output_path)
    except FileNotFoundError:
        return f"Arquivo nao encontrado: {file_path}"
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


# --- Network tools ---
def network_ping(host: str, count: int = 4) -> str:
    """Pinga um host para verificar conectividade. Suporta IP ou dominio."""
    try:
        param = "-n" if sys.platform == "win32" else "-c"
        result = subprocess.run(
            ["ping", param, str(count), host],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output[:2000] or f"Ping para {host} concluido."
    except subprocess.TimeoutExpired:
        return f"Timeout ao pingar {host}."
    except FileNotFoundError:
        return "Ping nao disponivel neste sistema."
    except Exception as e:
        return f"Erro ao pingar: {e}"


def network_ports(host: str = "localhost", ports: str = "80,443,8080") -> str:
    """Verifica se portas especificas estao abertas em um host."""
    try:
        import socket
        port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        results = []
        for port in port_list:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            status = "ABERTA" if result == 0 else "fechada"
            results.append(f"  Porta {port}: {status}")
            sock.close()
        return f"Portas em {host}:\n" + "\n".join(results)
    except ImportError:
        return "Erro: socket nao disponivel."
    except Exception as e:
        return f"Erro ao verificar portas: {e}"


def network_myip() -> str:
    """Retorna o IP publico e local da maquina."""
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "indisponivel"
    try:
        import requests
        public_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        public_ip = "indisponivel (sem internet)"
    return f"IP Local: {local_ip}\nIP Publico: {public_ip}\nHostname: {hostname}"


