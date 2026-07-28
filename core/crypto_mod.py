from ._common import *
import os
import base64
import json

# =======================================================================
# CRYPTO MOD - criptografia ultra-moderna (estilo ferramentas de agente OMP)
# -----------------------------------------------------------------------
# Criptografia real de producao: AES-256-GCM (autenticada), RSA-OAEP,
# ECC (P-256/P-384), assinaturas ECDSA, derivacao Argon2id, HKDF, e
# criptografia pos-quantica (Kyber/ML-KEM e Dilithium) quando as libs
# estiverem instaladas. Tudo local, sem rede. Feito para tarefas pesadas
# de seguranca e codigo critico.
# =======================================================================

_CRYPTO_DIR = os.path.join(DATA_DIR, "memoria_evolutiva", "crypto")
os.makedirs(_CRYPTO_DIR, exist_ok=True)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")


def _u64(s: str) -> bytes:
    return base64.b64decode(s)


# ---------- AES-256-GCM ----------

def crypto_aes_encrypt(plaintext: str, password: str = "", key_b64: str = "") -> str:
    """Criptografa com AES-256-GCM (autenticado). Use password OU key_b64.

    Retorna JSON base64 com {iv, ct, tag, salt}. Seguro contra
    adulteracao (AEAD). Nunca use AES-ECB/CBC sem MAC.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        return "Instale: pip install cryptography"
    if not key_b64:
        if not password:
            return "Informe password ou key_b64."
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
        key = kdf.derive(password.encode())
    else:
        key = _u64(key_b64)
        salt = b""
    aes = AESGCM(key)
    iv = os.urandom(12)
    ct = aes.encrypt(iv, plaintext.encode(), None)
    blob = {"iv": _b64(iv), "ct": _b64(ct[:-16]), "tag": _b64(ct[-16:]), "salt": _b64(salt)}
    return "AES-GCM:" + _b64(json.dumps(blob).encode())


def crypto_aes_decrypt(token: str, password: str = "", key_b64: str = "") -> str:
    """Descriptografa um token gerado por crypto_aes_encrypt."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        return "Instale: pip install cryptography"
    if not token.startswith("AES-GCM:"):
        return "Token invalido (esperado AES-GCM:...)."
    blob = json.loads(_u64(token[len("AES-GCM:"):]).decode())
    iv, ct, tag, salt = _u64(blob["iv"]), _u64(blob["ct"]), _u64(blob["tag"]), _u64(blob["salt"])
    if not key_b64 and salt:
        if not password:
            return "Informe password."
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
        key = kdf.derive(password.encode())
    else:
        key = _u64(key_b64)
    aes = AESGCM(key)
    try:
        pt = aes.decrypt(iv, ct + tag, None)
        return pt.decode()
    except Exception as e:
        return f"Falha ao descriptografar (tag invalida?): {e}"


# ---------- RSA-OAEP ----------

def crypto_rsa_keygen(bits: int = 2048) -> str:
    """Gera par de chaves RSA (2048/4096) e salva em disco. Retorna paths."""
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        return "Instale: pip install cryptography"
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    priv = key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    p1 = os.path.join(_CRYPTO_DIR, f"rsa_{bits}_priv.pem")
    p2 = os.path.join(_CRYPTO_DIR, f"rsa_{bits}_pub.pem")
    open(p1, "wb").write(priv)
    open(p2, "wb").write(pub)
    return f"Chaves RSA-{bits} salvas:\n priv: {p1}\n pub: {p2}"


def crypto_rsa_encrypt(plaintext: str, pub_pem_path: str) -> str:
    """Criptografa com RSA-OAEP (SHA-256). Para troca de chaves/pequenos dados."""
    try:
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization
    except ImportError:
        return "Instale: pip install cryptography"
    try:
        pub = serialization.load_pem_public_key(open(pub_pem_path, "rb").read())
        ct = pub.encrypt(plaintext.encode(), padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        return "RSA:" + _b64(ct)
    except Exception as e:
        return f"Erro RSA: {e}"


# ---------- ECC + assinatura ECDSA ----------

def crypto_ec_keygen(curve: str = "secp256r1") -> str:
    """Gera par ECC (P-256/P-384/P-521) para troca de chaves e assinaturas."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        return "Instale: pip install cryptography"
    name = {"secp256r1": ec.SECP256R1(), "secp384r1": ec.SECP384R1(),
            "secp521r1": ec.SECP521R1()}.get(curve, ec.SECP256R1())
    key = ec.generate_private_key(name)
    priv = key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    p1 = os.path.join(_CRYPTO_DIR, f"ec_{curve}_priv.pem")
    p2 = os.path.join(_CRYPTO_DIR, f"ec_{curve}_pub.pem")
    open(p1, "wb").write(priv)
    open(p2, "wb").write(pub)
    return f"Chaves ECC-{curve} salvas:\n priv: {p1}\n pub: {p2}"


def crypto_ecdh_shared(priv_pem_path: str, pub_pem_path: str) -> str:
    """Deriva segredo compartilhado ECDH (usado para acordo de chave)."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        return "Instale: pip install cryptography"
    try:
        priv = serialization.load_pem_private_key(open(priv_pem_path, "rb").read(), password=None)
        pub = serialization.load_pem_public_key(open(pub_pem_path, "rb").read())
        secret = priv.exchange(ec.ECDH(), pub)
        return _b64(secret)
    except Exception as e:
        return f"Erro ECDH: {e}"


def crypto_sign(message: str, priv_pem_path: str) -> str:
    """Assina uma mensagem com ECDSA (P-256) + SHA-256. Prova autenticidade."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
    except ImportError:
        return "Instale: pip install cryptography"
    try:
        priv = serialization.load_pem_private_key(open(priv_pem_path, "rb").read(), password=None)
        sig = priv.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        return "SIG:" + _b64(sig)
    except Exception as e:
        return f"Erro ao assinar: {e}"


def crypto_verify(message: str, signature_b64: str, pub_pem_path: str) -> str:
    """Verifica assinatura ECDSA. Retorna OK ou erro."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
    except ImportError:
        return "Instale: pip install cryptography"
    try:
        pub = serialization.load_pem_public_key(open(pub_pem_path, "rb").read())
        sig_raw = signature_b64[len("SIG:"):] if signature_b64.startswith("SIG:") else signature_b64
        pub.verify(_u64(sig_raw), message.encode(), ec.ECDSA(hashes.SHA256()))
        return "ASSINATURA VALIDA"
    except Exception as e:
        return f"ASSINATURA INVALIDA: {e}"


# ---------- Argon2id (derivacao de senha) ----------

def crypto_argon2(password: str) -> str:
    """Deriva hash de senha com Argon2id (resistente a GPU/ASIC)."""
    try:
        import argon2
    except ImportError:
        return "Instale: pip install argon2-cffi"
    try:
        ph = argon2.PasswordHasher()
        return "ARGON2:" + ph.hash(password)
    except Exception as e:
        return f"Erro Argon2: {e}"


def crypto_argon2_verify(hash_str: str, password: str) -> str:
    """Verifica um hash Argon2id. Retorna OK ou erro."""
    try:
        import argon2
    except ImportError:
        return "Instale: pip install argon2-cffi"
    try:
        ph = argon2.PasswordHasher()
        h = hash_str[len("ARGON2:"):] if hash_str.startswith("ARGON2:") else hash_str
        ph.verify(h, password)
        return "SENHA CONFERE"
    except Exception as e:
        return f"SENHA NAO CONFERE: {e}"


# ---------- HKDF (derivacao de chave a partir de segredo) ----------

def crypto_hkdf(secret_b64: str, info: str = "agente", length: int = 32) -> str:
    """Deriva uma chave simetrica de um segredo compartilhado (HKDF-SHA256)."""
    try:
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        return "Instale: pip install cryptography"
    try:
        hkdf = HKDF(algorithm=hashes.SHA256(), length=length, info=info.encode(), salt=None)
        key = hkdf.derive(_u64(secret_b64))
        return _b64(key)
    except Exception as e:
        return f"Erro HKDF: {e}"


# ---------- CRIPTOGRAFIA POS-QUANTICA (PQC) ----------

def crypto_pqc_keygen(kind: str = "kyber") -> str:
    """Gera chaves pos-quantica (ML-KEM/Kyber para encapsulamento,
    Dilithium para assinatura) se a lib 'pqcrypto' estiver instalada.

    Requer: pip install pqcrypto. Sem PQC, use ECC/AES-GCM acima.
    """
    try:
        if kind == "kyber":
            import pqcrypto.kem.kyber512 as kem
            pk, sk = kem.generate_keypair()
            suffix = "kyber"
        else:
            import pqcrypto.sign.dilithium2 as sig
            pk, sk = sig.generate_keypair()
            suffix = "dilithium"
    except ImportError:
        return ("Lib PQC nao instalada. Instale: pip install pqcrypto "
                "(ou oqs/liboqs-python). Sem PQC, use ECC/AES-GCM acima.")
    except Exception as e:
        return f"Erro PQC: {e}"
    p1 = os.path.join(_CRYPTO_DIR, f"pqc_{suffix}_pub.bin")
    p2 = os.path.join(_CRYPTO_DIR, f"pqc_{suffix}_priv.bin")
    open(p1, "wb").write(pk)
    open(p2, "wb").write(sk)
    return f"Par PQC ({suffix}) gerado:\n pub: {p1}\n priv: {p2}"


def crypto_pqc_encapsulate(pub_pem_path: str) -> str:
    """Encapsula segredo com Kyber (retorna ciphertext + segredo derivado)."""
    try:
        import pqcrypto.kem.kyber512 as kem
        ct, ss = kem.encrypt(open(pub_pem_path, "rb").read())
        return "PQC-ENC:" + _b64(ct) + "|" + _b64(ss)
    except ImportError:
        return "Instale: pip install pqcrypto"
    except Exception as e:
        return f"Erro PQC encaps: {e}"


def crypto_pqc_decapsulate(priv_pem_path: str, ct_b64: str) -> str:
    """Decapsula segredo com Kyber."""
    try:
        import pqcrypto.kem.kyber512 as kem
        ss = kem.decrypt(_u64(ct_b64), open(priv_pem_path, "rb").read())
        return _b64(ss)
    except ImportError:
        return "Instale: pip install pqcrypto"
    except Exception as e:
        return f"Erro PQC decaps: {e}"
