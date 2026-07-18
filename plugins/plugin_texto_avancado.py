"""
plugin_texto_avancado.py
=========================
Processamento avancado de texto: templates, diff, transformacao,
analise de sentimentos (basica por palavras), contagem, formatacao,
extração de dados estruturados.
"""

import os
import json
import re
import difflib
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Texto Avancado"


def register(api):
    def diff_texto(texto_a: str, texto_b: str, contexto: int = 3) -> str:
        """Mostra diferencas entre dois textos (unified diff)."""
        lines_a = texto_a.splitlines(keepends=True)
        lines_b = texto_b.splitlines(keepends=True)
        diff = difflib.unified_diff(lines_a, lines_b, fromfile="A", tofile="B", n=contexto)
        result = "".join(diff)
        return result if result else "Textos identicos."

    def contar_palavras(texto: str, ignorar_stopwords: bool = False) -> str:
        """Contagem detalhada de palavras, caracteres, linhas, paragrafos, sentencas."""
        palavras = texto.split()
        stopwords = set()
        if ignorar_stopwords:
            stopwords = {"a", "o", "e", "de", "da", "do", "em", "para", "com", "um", "uma",
                         "os", "as", "no", "na", "se", "por", "que", "é", "são", "dos", "das"}
        palavras_filtradas = [p for p in palavras if p.lower().strip(".,!?;:()[]{}") not in stopwords]
        sentencas = re.split(r'[.!?]+', texto)
        sentencas = [s.strip() for s in sentencas if s.strip()]
        paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
        chars = len(texto)
        chars_sem_espaco = len(texto.replace(" ", "").replace("\n", "").replace("\t", ""))
        return (
            f"Estatisticas do texto:\n"
            f"  Palavras: {len(palavras)} ({len(palavras_filtradas)} sem stopwords)\n"
            f"  Caracteres: {chars} ({chars_sem_espaco} sem espacos)\n"
            f"  Linhas: {texto.count(chr(10))+1}\n"
            f"  Paragrafos: {len(paragrafos)}\n"
            f"  Sentencas: {len(sentencas)}\n"
            f"  Tamanho medio de palavra: {sum(len(p) for p in palavras)/len(palavras):.1f} chars" if palavras else "Texto vazio."
        )

    def extrair_dados(texto: str, padrao: str) -> str:
        """Extrai dados usando regex. padrao: regex com grupos de captura (). Retorna JSON."""
        try:
            matches = re.findall(padrao, texto, re.MULTILINE)
            if not matches:
                return "Nenhuma correspondencia encontrada."
            if isinstance(matches[0], tuple):
                result = [list(m) for m in matches]
            else:
                result = list(matches)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Erro no regex: {e}"

    def transformar_caso(texto: str, caso: str) -> str:
        """Transforma maiusculas/minusculas/titulo/invertido/alternado."""
        if caso == "maiusculo":
            return texto.upper()
        if caso == "minusculo":
            return texto.lower()
        if caso == "titulo":
            return texto.title()
        if caso == "invertido":
            return texto[::-1]
        if caso == "alternado":
            return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(texto))
        if caso == "capitalizado":
            return ". ".join(s.strip().capitalize() for s in re.split(r'(?<=[.?!])\s+', texto) if s.strip())
        return f"Caso invalido: {caso}. Use: maiusculo, minusculo, titulo, invertido, alternado, capitalizado."

    def listar_palavras_comuns(texto: str, limite: int = 10, ignorar_stopwords: bool = True) -> str:
        """Lista as palavras mais frequentes no texto."""
        stopwords = {"a", "o", "e", "de", "da", "do", "em", "para", "com", "um", "uma",
                     "os", "as", "no", "na", "se", "por", "que", "é", "são", "dos", "das",
                     "ao", "aos", "à", "às", "pelo", "pela", "pelos", "pelas",
                     "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
                     "aquele", "aquela", "aqueles", "aquelas", "isso", "isto", "aquilo"}
        palavras = re.findall(r'\b[a-zA-Záéíóúâêôãõçàèìòùäëïöüñ]+\b', texto.lower())
        if ignorar_stopwords:
            palavras = [p for p in palavras if p not in stopwords and len(p) > 1]
        from collections import Counter
        top = Counter(palavras).most_common(limite)
        if not top:
            return "Nenhuma palavra encontrada."
        lines = [f"Top {len(top)} palavras mais frequentes:"]
        for i, (palavra, count) in enumerate(top, 1):
            lines.append(f"  {i}. {palavra}: {count}x")
        return "\n".join(lines)

    def limpar_texto(texto: str, remover_espacos_extra: bool = True, remover_acentos: bool = False,
                     remover_pontuacao: bool = False, remover_numeros: bool = False) -> str:
        """Limpa e normaliza texto com varias opcoes."""
        result = texto
        if remover_acentos:
            import unicodedata
            result = unicodedata.normalize("NFKD", result).encode("ASCII", "ignore").decode("ASCII")
        if remover_pontuacao:
            result = re.sub(r'[.,!?;:()\[\]{}"\'\-/\\@#$%&*+=<>~^`|]', "", result)
        if remover_numeros:
            result = re.sub(r'\d+', "", result)
        if remover_espacos_extra:
            result = re.sub(r'\s+', " ", result).strip()
        return result

    def dividir_texto(texto: str, tamanho: int = 1000, sobrepor: int = 100) -> str:
        """Divide texto em chunks de tamanho X com sobreposicao."""
        if not texto:
            return "Texto vazio."
        chunks = []
        start = 0
        while start < len(texto):
            end = start + tamanho
            chunks.append(texto[start:end])
            start += tamanho - sobrepor
        result = f"Texto dividido em {len(chunks)} partes (tamanho={tamanho}, sobrepor={sobrepor}):\n\n"
        for i, chunk in enumerate(chunks, 1):
            result += f"--- Parte {i} ({len(chunk)} chars) ---\n{chunk}\n\n"
        return result

    api.register_tool("diff_texto", diff_texto,
        "Mostra diferencas entre dois textos no formato unified diff.",
        {"texto_a": {"type": "string", "description": "Primeiro texto"}, "texto_b": {"type": "string", "description": "Segundo texto"}, "contexto": {"type": "integer", "description": "Linhas de contexto (opcional)"}}, ["texto_a", "texto_b"])

    api.register_tool("contar_palavras", contar_palavras,
        "Contagem detalhada: palavras, chars, linhas, paragrafos, sentencas. Opcionalmente ignora stopwords.",
        {"texto": {"type": "string", "description": "Texto para analisar"}, "ignorar_stopwords": {"type": "boolean", "description": "Ignorar stopwords? (opcional)"}}, ["texto"])

    api.register_tool("extrair_dados", extrair_dados,
        "Extrai dados com regex. Use grupos de captura (). Retorna JSON.",
        {"texto": {"type": "string", "description": "Texto fonte"}, "padrao": {"type": "string", "description": "Regex com grupos de captura"}}, ["texto", "padrao"])

    api.register_tool("transformar_caso", transformar_caso,
        "Transforma maiusculas/minusculas/titulo/invertido/alternado/capitalizado.",
        {"texto": {"type": "string", "description": "Texto"}, "caso": {"type": "string", "description": "maiusculo, minusculo, titulo, invertido, alternado, capitalizado"}}, ["texto", "caso"])

    api.register_tool("listar_palavras_comuns", listar_palavras_comuns,
        "Lista palavras mais frequentes no texto, opcionalmente ignorando stopwords.",
        {"texto": {"type": "string", "description": "Texto"}, "limite": {"type": "integer", "description": "Numero maximo de palavras (opcional)"}, "ignorar_stopwords": {"type": "boolean", "description": "Ignorar stopwords? (opcional)"}}, ["texto"])

    api.register_tool("limpar_texto", limpar_texto,
        "Limpa texto: remove espacos extras, acentos, pontuacao, numeros.",
        {"texto": {"type": "string", "description": "Texto"}, "remover_espacos_extra": {"type": "boolean", "description": "Remover espacos extras? (opcional)"}, "remover_acentos": {"type": "boolean", "description": "Remover acentos? (opcional)"}, "remover_pontuacao": {"type": "boolean", "description": "Remover pontuacao? (opcional)"}, "remover_numeros": {"type": "boolean", "description": "Remover numeros? (opcional)"}}, ["texto"])

    api.register_tool("dividir_texto", dividir_texto,
        "Divide texto em chunks para processamento, com sobreposicao configuravel.",
        {"texto": {"type": "string", "description": "Texto"}, "tamanho": {"type": "integer", "description": "Tamanho de cada chunk (opcional)"}, "sobrepor": {"type": "integer", "description": "Sobreposicao entre chunks (opcional)"}}, ["texto"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Processamento avancado de texto: diff, estatisticas, regex, transformacao, limpeza, chunking",
        "tools": ["diff_texto", "contar_palavras", "extrair_dados", "transformar_caso", "listar_palavras_comuns", "limpar_texto", "dividir_texto"],
    }
