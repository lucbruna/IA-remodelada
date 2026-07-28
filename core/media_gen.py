from ._common import *
import requests
import smtplib
import whisper
def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    sd_url: str = "http://127.0.0.1:7860",
) -> str:
    """Gera uma imagem usando Stable Diffusion WebUI API. O servidor SD deve estar rodando."""
    try:
        import requests
        import base64
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"

    try:
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "save_images": False,
            "send_images": True,
        }
        resp = requests.post(
            f"{sd_url}/sdapi/v1/txt2img",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("images", [])
        if not images:
            return "SD nao retornou imagens."

        output_dir = os.path.join(DATA_DIR, "imagens_geradas")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = []
        for i, img_b64 in enumerate(images):
            img_data = base64.b64decode(img_b64)
            fname = f"sd_{timestamp}_{i}.png"
            fpath = os.path.join(output_dir, fname)
            with open(fpath, "wb") as f:
                f.write(img_data)
            paths.append(fpath)

        return f"Imagem(ns) gerada(s):\n" + "\n".join(paths)
    except requests.ConnectionError:
        return (f"SD WebUI nao encontrado em {sd_url}. "
                "Certifique-se de rodar o Stable Diffusion com --api (ex: webui.bat --api)")
    except Exception as e:
        return f"Erro ao gerar imagem: {e}"


# --- Voice input via Whisper ---
def transcribe_audio(audio_path: str) -> str:
    """Transcreve audio para texto usando Whisper (modelo local). Suporta: .mp3, .wav, .m4a, .ogg."""
    try:
        import whisper
    except ImportError:
        return "Instale: pip install openai-whisper"
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language="pt")
        text = result["text"].strip()
        return text or "Nenhum texto detectado no audio."
    except Exception as e:
        return f"Erro ao transcrever audio: {e}"


def record_and_transcribe(duration: int = 5) -> str:
    """Grava audio do microfone por N segundos e transcreve com Whisper."""
    try:
        import whisper
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        return "Instale: pip install openai-whisper sounddevice soundfile"
    try:
        sample_rate = 16000
        print(f"Gravando por {duration}s... (fale agora)")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        temp_path = os.path.join(DATA_DIR, "_temp_audio.wav")
        sf.write(temp_path, recording, sample_rate)
        model = whisper.load_model("base")
        result = model.transcribe(temp_path, language="pt")
        os.remove(temp_path)
        return result["text"].strip() or "(silencio detectado)"
    except Exception as e:
        return f"Erro ao gravar/transcrever: {e}"


# --- Email (SMTP) ---
def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    username: str = "",
    password: str = "",
) -> str:
    """Envia um email via SMTP. Para Gmail, use 'smtp.gmail.com:587' com senha de app."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
    except ImportError:
        return "Erro: smtplib nao disponivel."

    if not username or not password:
        return ("Configuracao de email necessaria. Use as variaveis "
                "EMAIL_USER e EMAIL_PASS ou passe username/password.")

    try:
        msg = MIMEMultipart()
        msg["From"] = username
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        return f"Email enviado para {to} com assunto '{subject}'."
    except smtplib.SMTPAuthenticationError:
        return "Erro de autenticacao. Para Gmail, use uma senha de app (nao a senha normal)."
    except Exception as e:
        return f"Erro ao enviar email: {e}"


# --- MCP Client (Model Context Protocol simplificado) ---
def mcp_call(server_url: str, tool_name: str, arguments: str = "{}") -> str:
    """Chama uma ferramenta em um servidor MCP (Model Context Protocol).
    MCP permite conectar o agente a servicos externos padronizados.
    Ex: 'http://localhost:8000/mcp' com tool_name='list_files' e arguments='{"path": "."}"""
    # Tenta usar o plugin MCP primeiro (mais completo)
    try:
        from plugins.plugin_mcp import mcp_chamar
    except ImportError:
        pass  # plugin nao disponivel, usa fallback
    else:
        try:
            return mcp_chamar(server_url, tool_name, arguments)
        except Exception as e:
            return f"Erro no plugin MCP: {e}"
    # Fallback: implementacao inline
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": json.loads(arguments),
            },
            "id": 1,
        }
        resp = requests.post(server_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return f"Erro MCP: {data['error']}"
        result = data.get("result", {})
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return "\n".join(texts) if texts else json.dumps(result, indent=2)
    except requests.ConnectionError:
        return f"Servidor MCP nao encontrado em {server_url}. Verifique se o servidor esta rodando."
    except Exception as e:
        return f"Erro na chamada MCP: {e}"


def mcp_list_tools(server_url: str) -> str:
    """Lista as ferramentas disponiveis em um servidor MCP."""
    # Tenta usar o plugin MCP primeiro (mais completo)
    try:
        from plugins.plugin_mcp import mcp_listar_ferramentas
    except ImportError:
        pass  # plugin nao disponivel, usa fallback
    else:
        try:
            return mcp_listar_ferramentas(server_url)
        except Exception as e:
            return f"Erro no plugin MCP: {e}"
    # Fallback: implementacao inline
    try:
        import requests
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        }
        resp = requests.post(server_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        tools = data.get("result", {}).get("tools", [])
        if not tools:
            return "Nenhuma ferramenta registrada no servidor MCP."
        lines = [f"  {t['name']}: {t.get('description', '')}" for t in tools]
        return "Ferramentas MCP disponiveis:\n" + "\n".join(lines)
    except requests.ConnectionError:
        return f"Servidor MCP nao encontrado em {server_url}."
    except Exception as e:
        return f"Erro ao listar ferramentas MCP: {e}"


