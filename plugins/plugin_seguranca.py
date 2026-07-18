"""
plugin_seguranca.py
===================
Criptografia, verificacao de integridade, hash, geracao de senhas
e varredura simples de seguranca em arquivos.
"""

import os
import json
import hashlib
import string
import random
import logging
import base64

__version__ = "1.0.0"
PLUGIN_NAME = "Seguranca e Criptografia"


def register(api):
    def gerar_hash(arquivo: str, algoritmo: str = "sha256") -> str:
        """Gera hash de arquivo. Algoritmos: md5, sha1, sha256, sha512."""
        alg = algoritmo.lower()
        if alg == "md5":
            h = hashlib.md5()
        elif alg == "sha1":
            h = hashlib.sha1()
        elif alg == "sha512":
            h = hashlib.sha512()
        else:
            h = hashlib.sha256()
        try:
            with open(arquivo, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return f"{algoritmo.upper()}({os.path.basename(arquivo)}): {h.hexdigest()}"
        except Exception as e:
            return f"Erro: {e}"

    def verificar_integridade(arquivo: str, hash_esperado: str, algoritmo: str = "sha256") -> str:
        """Verifica hash de arquivo contra valor esperado."""
        result = gerar_hash(arquivo, algoritmo)
        if result.startswith("Erro"):
            return result
        hash_real = result.split(": ")[-1].strip()
        if hash_real == hash_esperado.strip():
            return "OK: hash coincide."
        return f"DIFERENTE: esperado {hash_esperado}, obtido {hash_real}."

    def gerar_senha(tamanho: int = 16, maiusculas: bool = True, minusculas: bool = True,
                    numeros: bool = True, especiais: bool = True) -> str:
        """Gera senha aleatoria segura."""
        chars = ""
        if maiusculas:
            chars += string.ascii_uppercase
        if minusculas:
            chars += string.ascii_lowercase
        if numeros:
            chars += string.digits
        if especiais:
            chars += "!@#$%&*+-_=?"
        if not chars:
            chars = string.ascii_letters + string.digits
        password = "".join(random.SystemRandom().choice(chars) for _ in range(tamanho))
        return f"Senha gerada ({tamanho} chars): {password}"

    def criptografar_simples(texto: str, chave: str) -> str:
        """Criptografia simples XOR + Base64 (NAO seguro para dados reais)."""
        try:
            key_bytes = chave.encode()
            text_bytes = texto.encode()
            result = bytes(text_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(text_bytes)))
            encoded = base64.b64encode(result).decode()
            return encoded
        except Exception as e:
            return f"Erro: {e}"

    def descriptografar_simples(codigo: str, chave: str) -> str:
        """Descriptografa texto cifrado com criptografar_simples."""
        try:
            key_bytes = chave.encode()
            decoded = base64.b64decode(codigo)
            result = bytes(decoded[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(decoded)))
            return result.decode("utf-8")
        except Exception as e:
            return f"Erro: {e} - chave incorreta ou dados invalidos."

    def varre_variaveis(path: str = ".") -> str:
        """Varre arquivos em busca de possiveis chaves/senhas hard-coded."""
        padroes = [
            "api_key", "api-key", "apikey", "secret", "password", "senha",
            "token", "credentials", "aws_", "sk-", "pk-", "-----BEGIN",
        ]
        encontrados = []
        total = 0
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith((".", "_", "venv", "node_modules", "__pycache__"))]
            for fname in files:
                if fname.endswith((".py", ".js", ".ts", ".json", ".yml", ".yaml", ".env", ".ini", ".cfg", ".conf")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                lower = line.lower().strip()
                                for padrao in padroes:
                                    if padrao in lower and not lower.strip().startswith(("#", "//", "/*")):
                                        encontrados.append(f"  {fpath}:{i} -> {line.strip()[:100]}")
                                        break
                        total += 1
                    except Exception:
                        pass
        if not encontrados:
            return f"Varredura concluida: {total} arquivos verificados, nenhum padrao suspeito encontrado."
        report = f"Varredura: {total} arquivos, {len(encontrados)} ocorrencias suspeitas:\n"
        report += "\n".join(encontrados[:30])
        if len(encontrados) > 30:
            report += f"\n... e mais {len(encontrados)-30} ocorrencias."
        return report

    def verificar_ssl(hostname: str, porta: int = 443) -> str:
        """Verifica certificado SSL de um host."""
        import socket
        import ssl
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, porta), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        return f"{hostname}: certificado nao disponivel."
                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    expires = cert.get("notAfter", "N/A")
                    return (
                        f"SSL {hostname}:{porta}\n"
                        f"  Sujeito: {subject.get('commonName', 'N/A')}\n"
                        f"  Emissor: {issuer.get('commonName', 'N/A')}\n"
                        f"  Expira: {expires}\n"
                        f"  SANs: {', '.join(cert.get('subjectAltName', []))}"
                    )
        except Exception as e:
            return f"Erro SSL em {hostname}:{porta}: {e}"

    api.register_tool("gerar_hash", gerar_hash,
        "Gera hash de arquivo (md5, sha1, sha256, sha512).",
        {"arquivo": {"type": "string", "description": "Caminho do arquivo"}, "algoritmo": {"type": "string", "description": "Algoritmo: md5, sha1, sha256, sha512 (opcional)"}}, ["arquivo"])

    api.register_tool("verificar_integridade", verificar_integridade,
        "Verifica hash de arquivo contra valor esperado.",
        {"arquivo": {"type": "string", "description": "Caminho do arquivo"}, "hash_esperado": {"type": "string", "description": "Hash esperado"}, "algoritmo": {"type": "string", "description": "Algoritmo (opcional)"}}, ["arquivo", "hash_esperado"])

    api.register_tool("gerar_senha", gerar_senha,
        "Gera senha aleatoria segura com opcoes de caracteres.",
        {"tamanho": {"type": "integer", "description": "Tamanho (opcional, padrao 16)"}, "maiusculas": {"type": "boolean", "description": "Incluir maiusculas (opcional)"}, "minusculas": {"type": "boolean", "description": "Incluir minusculas (opcional)"}, "numeros": {"type": "boolean", "description": "Incluir numeros (opcional)"}, "especiais": {"type": "boolean", "description": "Incluir especiais (opcional)"}}, [])

    api.register_tool("criptografar_simples", criptografar_simples,
        "Criptografia XOR+Base64. NAO usar para dados sensiveis.",
        {"texto": {"type": "string", "description": "Texto a criptografar"}, "chave": {"type": "string", "description": "Chave secreta"}}, ["texto", "chave"])

    api.register_tool("descriptografar_simples", descriptografar_simples,
        "Descriptografa texto cifrado com criptografar_simples.",
        {"codigo": {"type": "string", "description": "Texto cifrado"}, "chave": {"type": "string", "description": "Chave secreta"}}, ["codigo", "chave"])

    api.register_tool("varre_variaveis", varre_variaveis,
        "Varre arquivos em busca de chaves/senhas hard-coded.",
        {"path": {"type": "string", "description": "Diretorio para varredura (opcional)"}}, [])

    api.register_tool("verificar_ssl", verificar_ssl,
        "Verifica certificado SSL de um host.",
        {"hostname": {"type": "string", "description": "Hostname"}, "porta": {"type": "integer", "description": "Porta (opcional, padrao 443)"}}, ["hostname"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Criptografia, hash, integridade, senhas, varredura de seguranca, SSL",
        "tools": ["gerar_hash", "verificar_integridade", "gerar_senha", "criptografar_simples", "descriptografar_simples", "varre_variaveis", "verificar_ssl"],
    }
