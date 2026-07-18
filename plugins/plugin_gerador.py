"""
plugin_gerador.py
=================
Plugin de geracao e transformacao de dados: senhas seguras,
identificadores unicos (UUID), hashing criptografico e checksums.

Fornece:
  - Senhas seguras com configuracao de complexidade
  - UUID v4 unico
  - Hashing de texto (MD5, SHA1, SHA256, SHA512)
  - Hashing de arquivo (SHA256, etc.)
  - Geracao de numeros aleatorios seguros

Uso no agente:
  "Gere uma senha forte de 16 caracteres"
  "Crie um UUID"
  "Calcule o MD5 deste texto"
  "Checksum SHA256 deste arquivo"
"""

import logging
import secrets
import string
import hashlib
import uuid
import os


def _gerar_senha(tamanho: int = 16, usar_maiusculas: bool = True,
                  usar_minusculas: bool = True, usar_numeros: bool = True,
                  usar_especiais: bool = True, evitar_ambiguos: bool = False) -> str:
    """Gera uma senha segura e aleatoria.

    Args:
        tamanho: Numero de caracteres (4-128)
        usar_maiusculas: Incluir A-Z
        usar_minusculas: Incluir a-z
        usar_numeros: Incluir 0-9
        usar_especiais: Incluir !@#$% etc.
        evitar_ambiguos: Evitar caracteres como Il1O0

    Returns:
        Senha gerada ou mensagem de erro
    """
    tamanho = max(4, min(128, tamanho))

    chars = ""
    if usar_minusculas:
        chars += string.ascii_lowercase
    if usar_maiusculas:
        chars += string.ascii_uppercase
    if usar_numeros:
        chars += string.digits
    if usar_especiais:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?/~"

    if not chars:
        return "❌ Selecione pelo menos um tipo de caractere."

    if evitar_ambiguos:
        for c in "Il1O0":
            chars = chars.replace(c, "")

    senha = "".join(secrets.choice(chars) for _ in range(tamanho))
    return senha


def _avaliar_senha(senha: str) -> str:
    """Avalia a forca de uma senha."""
    if not senha:
        return "❌ Informe uma senha para avaliar."

    comprimento = len(senha)
    categorias = 0
    if any(c.islower() for c in senha):
        categorias += 1
    if any(c.isupper() for c in senha):
        categorias += 1
    if any(c.isdigit() for c in senha):
        categorias += 1
    if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/~" for c in senha):
        categorias += 1

    # Entropia aproximada
    if comprimento >= 16 and categorias >= 4:
        nivel = "🔒 **Muito Forte**"
        estrelas = "★★★★★"
        dicas = ""
    elif comprimento >= 12 and categorias >= 3:
        nivel = "🔐 **Forte**"
        estrelas = "★★★★☆"
        dicas = ""
    elif comprimento >= 8 and categorias >= 2:
        nivel = "🔓 **Media**"
        estrelas = "★★★☆☆"
        dicas = "\n  💡 Dica: adicione mais tipos de caracteres e aumente para 12+ caracteres."
    else:
        nivel = "⚠️ **Fraca**"
        estrelas = "★★☆☆☆"
        dicas = "\n  💡 Dica: use 12+ caracteres com maiusculas, minusculas, numeros e simbolos."

    return (
        f"🔑 **AVALIACAO DE SENHA**\n\n"
        f"  Senha: `{senha}`\n"
        f"  Comprimento: {comprimento} caracteres\n"
        f"  Forca: {nivel} {estrelas}\n"
        f"  Categorias: {categorias}/4 tipos de caracteres{dicas}"
    )


def _gerar_uuid() -> str:
    """Gera um UUID v4."""
    return str(uuid.uuid4())


def _hash_texto(texto: str, algoritmo: str = "sha256") -> str:
    """Calcula o hash de um texto.

    Args:
        texto: Texto a ser hasheado
        algoritmo: Algoritmo (md5, sha1, sha256, sha512)

    Returns:
        Hash em hexadecimal
    """
    if not texto:
        return "❌ Informe um texto para calcular o hash."

    algoritmo = algoritmo.lower().strip()
    if algoritmo not in ("md5", "sha1", "sha256", "sha512"):
        return "❌ Algoritmo nao suportado. Use: md5, sha1, sha256, sha512."

    h = hashlib.new(algoritmo)
    h.update(texto.encode("utf-8"))
    return h.hexdigest()


def _hash_arquivo(caminho: str, algoritmo: str = "sha256") -> str:
    """Calcula o hash de um arquivo.

    Args:
        caminho: Caminho do arquivo
        algoritmo: Algoritmo (md5, sha1, sha256, sha512)

    Returns:
        Hash em hexadecimal ou mensagem de erro
    """
    if not os.path.exists(caminho):
        return f"❌ Arquivo nao encontrado: '{caminho}'"

    algoritmo = algoritmo.lower().strip()
    if algoritmo not in ("md5", "sha1", "sha256", "sha512"):
        return "❌ Algoritmo nao suportado. Use: md5, sha1, sha256, sha512."

    try:
        h = hashlib.new(algoritmo)
        with open(caminho, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"❌ Erro ao calcular hash do arquivo: {e}"


def register(api):
    """Registra as ferramentas de geracao no agente."""

    # ---- Gerar senha ----
    def gerar_senha(tamanho: int = 16, especiais: bool = True,
                     maiusculas: bool = True, numeros: bool = True,
                     evitar_ambiguos: bool = False) -> str:
        """Gera uma senha segura e aleatoria.

        Args:
            tamanho: Numero de caracteres (4-128, padrao: 16)
            especiais: Incluir caracteres especiais (!@#$ etc.)
            maiusculas: Incluir letras maiusculas (A-Z)
            numeros: Incluir numeros (0-9)
            evitar_ambiguos: Evitar caracteres ambiguos (Il1O0)

        Returns:
            Senha gerada aleatoriamente
        """
        return _gerar_senha(tamanho, maiusculas, True, numeros, especiais, evitar_ambiguos)

    api.register_tool(
        name="gerar_senha",
        func=gerar_senha,
        description=(
            "Gera senhas seguras e aleatorias com configuracao de complexidade. "
            "Permite escolher tamanho, uso de maiusculas, numeros e caracteres especiais. "
            "Exemplos: 'Gere uma senha de 20 caracteres', "
            "'Crie uma senha forte com simbolos', "
            "'Preciso de uma senha de 8 caracteres so numeros'. "
            "Use quando o usuario pedir para criar/gerar uma senha."
        ),
        parameters={
            "tamanho": {
                "type": "integer",
                "description": "Numero de caracteres (4-128). Padrao: 16",
            },
            "especiais": {
                "type": "boolean",
                "description": "Incluir caracteres especiais (!@#$ etc.). Padrao: true",
            },
            "maiusculas": {
                "type": "boolean",
                "description": "Incluir letras maiusculas. Padrao: true",
            },
            "numeros": {
                "type": "boolean",
                "description": "Incluir numeros. Padrao: true",
            },
            "evitar_ambiguos": {
                "type": "boolean",
                "description": "Evitar caracteres ambiguos (Il1O0). Padrao: false",
            },
        },
        required=[],
    )

    # ---- Avaliar senha ----
    def avaliar_senha(senha: str) -> str:
        """Avalia a forca de uma senha fornecida pelo usuario.

        Args:
            senha: Senha a ser avaliada

        Returns:
            Analise de forca com sugestoes de melhoria
        """
        return _avaliar_senha(senha)

    api.register_tool(
        name="avaliar_senha",
        func=avaliar_senha,
        description=(
            "Avalia a forca de uma senha fornecida pelo usuario. "
            "Analisa comprimento, variedade de caracteres e da uma nota "
            "(Fraca, Media, Forte, Muito Forte) com sugestoes de melhoria. "
            "Exemplo: 'avaliar_senha minhaSenha123'. "
            "Use quando o usuario quiser saber se uma senha e segura."
        ),
        parameters={
            "senha": {
                "type": "string",
                "description": "Senha a ser avaliada",
            },
        },
        required=["senha"],
    )

    # ---- Gerar UUID ----
    def gerar_uuid() -> str:
        """Gera um identificador unico universal (UUID v4)."""
        return _gerar_uuid()

    api.register_tool(
        name="gerar_uuid",
        func=gerar_uuid,
        description=(
            "Gera um UUID v4 (identificador unico universal) aleatorio. "
            "Util para criar IDs unicos, chaves de banco de dados, "
            "nomes de arquivo temporarios, etc. "
            "Exemplo: 'Gere um UUID para mim'. "
            "Use quando o usuario precisar de um identificador unico."
        ),
        parameters={},
        required=[],
    )

    # ---- Hash texto ----
    def hash_texto(texto: str, algoritmo: str = "sha256") -> str:
        """Calcula o hash criptografico de um texto.

        Args:
            texto: Texto a ser hasheado
            algoritmo: Algoritmo (md5, sha1, sha256, sha512). Padrao: sha256

        Returns:
            Hash em hexadecimal
        """
        return _hash_texto(texto, algoritmo)

    api.register_tool(
        name="hash_texto",
        func=hash_texto,
        description=(
            "Calcula o hash criptografico de um texto usando MD5, SHA1, SHA256 ou SHA512. "
            "Exemplos: 'Calcule o MD5 de hello', "
            "'Hash SHA256 deste texto', "
            "'Gere o SHA512 desta frase'. "
            "Use quando o usuario quiser calcular hash de um texto."
        ),
        parameters={
            "texto": {
                "type": "string",
                "description": "Texto para calcular o hash",
            },
            "algoritmo": {
                "type": "string",
                "description": "Algoritmo de hash (md5, sha1, sha256, sha512). Padrao: sha256",
            },
        },
        required=["texto"],
    )

    # ---- Hash arquivo ----
    def hash_arquivo(caminho: str, algoritmo: str = "sha256") -> str:
        """Calcula o hash criptografico de um arquivo.

        Args:
            caminho: Caminho do arquivo
            algoritmo: Algoritmo (md5, sha1, sha256, sha512). Padrao: sha256

        Returns:
            Hash em hexadecimal
        """
        return _hash_arquivo(caminho, algoritmo)

    api.register_tool(
        name="hash_arquivo",
        func=hash_arquivo,
        description=(
            "Calcula o hash SHA256 (ou outro algoritmo) de um arquivo. "
            "Util para verificar integridade de downloads, comparar arquivos, etc. "
            "Exemplos: 'Checksum SHA256 deste arquivo', "
            "'Calcule o MD5 do arquivo', "
            "'Verifique a integridade do download'. "
            "Use quando o usuario quiser verificar checksum de arquivo."
        ),
        parameters={
            "caminho": {
                "type": "string",
                "description": "Caminho do arquivo",
            },
            "algoritmo": {
                "type": "string",
                "description": "Algoritmo (md5, sha1, sha256, sha512). Padrao: sha256",
            },
        },
        required=["caminho"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Gerador e Hash",
        "version": "1.0.0",
        "description": "Senhas seguras, UUID, hashing MD5/SHA1/SHA256/SHA512, checksums",
        "author": "Agente Local",
        "tools": ["gerar_senha", "avaliar_senha", "gerar_uuid", "hash_texto", "hash_arquivo"],
    }
