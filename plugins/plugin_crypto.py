"""
plugin_crypto.py
===============
Plugin wrapper que expoe o modulo core.crypto_mod como ferramentas
carregaveis do agente. Criptografia ultra-moderna local: AES-256-GCM,
RSA-OAEP, ECC+ECDSA, Argon2id, HKDF e PQC (Kyber/Dilithium).

Requer: pip install cryptography  (e argon2-cffi / pqcrypto para os demais).
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Criptografia Ultra-Moderna"

# Mapeia o nome da ferramenta para (funcao, descricao, parametros, obrigatorios)
_TOOLS = [
    ("crypto_aes_encrypt", "Criptografa texto com AES-256-GCM (autenticado). Use password ou key_b64.",
     {"plaintext": "string", "password": "string", "key_b64": "string"}, ["plaintext"]),
    ("crypto_aes_decrypt", "Descriptografa token AES-GCM.",
     {"token": "string", "password": "string", "key_b64": "string"}, ["token"]),
    ("crypto_rsa_keygen", "Gera par de chaves RSA (2048/4096) e salva em disco.",
     {"bits": "integer"}, []),
    ("crypto_rsa_encrypt", "Criptografa com RSA-OAEP (SHA-256).",
     {"plaintext": "string", "pub_pem_path": "string"}, ["plaintext", "pub_pem_path"]),
    ("crypto_ec_keygen", "Gera par ECC (P-256/P-384/P-521).",
     {"curve": "string"}, []),
    ("crypto_ecdh_shared", "Deriva segredo compartilhado ECDH.",
     {"priv_pem_path": "string", "pub_pem_path": "string"}, ["priv_pem_path", "pub_pem_path"]),
    ("crypto_sign", "Assina mensagem com ECDSA (P-256)+SHA-256.",
     {"message": "string", "priv_pem_path": "string"}, ["message", "priv_pem_path"]),
    ("crypto_verify", "Verifica assinatura ECDSA (VALIDA/INVALIDA).",
     {"message": "string", "signature_b64": "string", "pub_pem_path": "string"},
     ["message", "signature_b64", "pub_pem_path"]),
    ("crypto_argon2", "Deriva hash de senha com Argon2id.",
     {"password": "string"}, ["password"]),
    ("crypto_argon2_verify", "Verifica hash Argon2id.",
     {"hash_str": "string", "password": "string"}, ["hash_str", "password"]),
    ("crypto_hkdf", "Deriva chave simetrica via HKDF-SHA256.",
     {"secret_b64": "string", "info": "string", "length": "integer"}, ["secret_b64"]),
    ("crypto_pqc_keygen", "Gera chaves pos-quantica Kyber/Dilithium (requer pqcrypto).",
     {"kind": "string"}, []),
    ("crypto_pqc_encapsulate", "Encapsula segredo com Kyber.",
     {"pub_pem_path": "string"}, ["pub_pem_path"]),
    ("crypto_pqc_decapsulate", "Decapsula segredo com Kyber.",
     {"priv_pem_path": "string", "ct_b64": "string"}, ["priv_pem_path", "ct_b64"]),
]


def register(api):
    try:
        from core import crypto_mod
    except Exception as e:
        return {"name": PLUGIN_NAME, "version": __version__,
                "error": f"core.crypto_mod indisponivel: {e}", "tools": []}
    tools_registradas = []
    for nome, desc, params, req in _TOOLS:
        fn = getattr(crypto_mod, nome, None)
        if fn is None:
            continue
        api.register_tool(nome, fn, desc, params, req)
        tools_registradas.append(nome)
    return {"name": PLUGIN_NAME, "version": __version__,
            "description": "Criptografia moderna local (AES-GCM, RSA, ECC, Argon2, PQC).",
            "tools": tools_registradas}
