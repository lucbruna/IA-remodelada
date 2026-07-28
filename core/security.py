from ._common import *


def _derive_key(master_password: str) -> bytes:
    """Deriva uma chave AES de 32 bytes a partir da senha mestra."""
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", master_password.encode(), b"agente_salt_turbo", 100000, dklen=32)


def _encrypt(data: str, key: bytes) -> str:
    """Criptografa texto com AES-GCM."""
    from cryptography.fernet import Fernet
    import base64
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(data.encode()).decode()


def _decrypt(token: str, key: bytes) -> str:
    """Descriptografa texto com AES-GCM."""
    from cryptography.fernet import Fernet
    import base64
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.decrypt(token.encode()).decode()


def password_save(service: str, username: str, password: str, master_password: str) -> str:
    """Salva uma senha criptografada. Use uma senha mestra forte para proteger o cofre."""
    try:
        key = _derive_key(master_password)
        vault = {}
        if os.path.exists(PASSWORDS_FILE):
            try:
                with open(PASSWORDS_FILE, "r") as f:
                    encrypted = f.read()
                decrypted = _decrypt(encrypted, key)
                vault = json.loads(decrypted)
            except Exception:
                vault = {}
        vault[service] = {"username": username, "password": password}
        encrypted = _encrypt(json.dumps(vault, ensure_ascii=False), key)
        with open(PASSWORDS_FILE, "w") as f:
            f.write(encrypted)
        return f"Senha para '{service}' salva com seguranca."
    except ImportError:
        return "Instale: pip install cryptography"
    except Exception as e:
        return f"Erro ao salvar senha: {e}"


def password_get(service: str, master_password: str) -> str:
    """Recupera uma senha salva pelo nome do servico."""
    try:
        key = _derive_key(master_password)
        if not os.path.exists(PASSWORDS_FILE):
            return "Nenhuma senha salva ainda."
        with open(PASSWORDS_FILE, "r") as f:
            encrypted = f.read()
        decrypted = _decrypt(encrypted, key)
        vault = json.loads(decrypted)
        if service not in vault:
            return f"Servico '{service}' nao encontrado no cofre."
        entry = vault[service]
        return f"Servico: {service}\nUsuario: {entry['username']}\nSenha: {entry['password']}"
    except ImportError:
        return "Instale: pip install cryptography"
    except Exception as e:
        return f"Erro ao recuperar senha: {e} (senha mestra incorreta?)"


def password_list(master_password: str) -> str:
    """Lista todos os servicos salvos no cofre de senhas."""
    try:
        key = _derive_key(master_password)
        if not os.path.exists(PASSWORDS_FILE):
            return "Nenhuma senha salva ainda."
        with open(PASSWORDS_FILE, "r") as f:
            encrypted = f.read()
        decrypted = _decrypt(encrypted, key)
        vault = json.loads(decrypted)
        if not vault:
            return "Cofre vazio."
        return "Servicos no cofre:\n" + "\n".join(f"  {s}" for s in vault)
    except ImportError:
        return "Instale: pip install cryptography"
    except Exception:
        return "Erro ao listar (senha mestra incorreta?)."


# --- Code formatter ---
