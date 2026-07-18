"""
plugin_noticias.py
==================
Plugin de noticias que busca manchetes atualizadas de fontes confiaveis
usando RSS feeds (sem API key necessaria).

Fornece:
  - Noticias do momento (principais manchetes)
  - Busca por topico ou palavra-chave
  - Suporta multiplas fontes: Google News, BBC, CNN, TechCrunch, etc.

Uso no agente:
  "Quais as principais noticias de hoje?"
  "Noticias sobre tecnologia"
  "Ultimas noticias do Brasil"
  "O que esta acontecendo no mundo?"
"""

import logging
import re
from datetime import datetime

# Fontes RSS organizadas por categoria
_FONTES = {
    "geral": [
        ("Google News (Brasil)", "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-BR"),
        ("Yahoo News", "https://rss.news.yahoo.com/rss/topstories"),
    ],
    "tecnologia": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Wired", "https://www.wired.com/feed/rss"),
        ("Hacker News", "https://hnrss.org/frontpage"),
    ],
    "ciencia": [
        ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml"),
        ("National Geographic", "https://www.nationalgeographic.com/feeds/latest/"),
    ],
    "negocios": [
        ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ],
    "mundo": [
        ("Reuters", "https://www.reutersagency.com/feed/"),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ],
}

# Todas as fontes em lista plana
_TODAS_FONTES = []
for categoria, fontes in _FONTES.items():
    _TODAS_FONTES.extend(fontes)


def _extrair_texto(elemento, caminho):
    """Extrai texto de um elemento XML de forma segura."""
    try:
        for tag in caminho.split("/"):
            if hasattr(elemento, "find"):
                elemento = elemento.find(tag)
                if elemento is None:
                    return ""
            else:
                return ""
        return (elemento.text or "").strip()
    except Exception:
        return ""


def _limpar_html(texto: str) -> str:
    """Remove tags HTML basicas de um texto."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = texto.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    texto = texto.replace("&quot;", '"').replace("&#39;", "'")
    return texto.strip()


def _buscar_rss(url: str, limite: int = 5) -> list:
    """Busca noticias de um feed RSS.

    Args:
        url: URL do feed RSS
        limite: Numero maximo de itens

    Returns:
        Lista de dicts com 'titulo', 'link', 'fonte', 'data' ou lista vazia
    """
    try:
        import feedparser
        feed = feedparser.parse(url)
        itens = []
        for entry in feed.entries[:limite]:
            titulo = _limpar_html(entry.get("title", ""))
            link = entry.get("link", "")
            data = entry.get("published", entry.get("updated", ""))
            desc = _limpar_html(entry.get("summary", entry.get("description", "")))
            itens.append({
                "titulo": titulo,
                "link": link,
                "fonte": feed.feed.get("title", url) if hasattr(feed, "feed") else url,
                "data": data,
                "descricao": desc[:200] if desc else "",
            })
        return itens
    except ImportError:
        # Fallback: usa requests + xml.etree.ElementTree
        try:
            import requests
            import xml.etree.ElementTree as ET
        except ImportError:
            return []

        try:
            resp = requests.get(url, timeout=10,
                                headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            # Namespace comum em RSS
            ns = {"": "http://www.w3.org/2005/Atom"}
            itens = []

            # Tenta Atom first, depois RSS
            entries = root.findall(".//entry", ns) or root.findall(".//item")
            titulo_feed = root.findtext("title", "") or root.findtext("channel/title", "")

            for entry in entries[:limite]:
                titulo = entry.findtext("title", "")
                link_el = entry.find("link")
                link = ""
                if link_el is not None:
                    link = link_el.get("href", link_el.text or "")
                pub = entry.findtext("published", entry.findtext("pubDate", ""))
                desc = entry.findtext("summary", entry.findtext("description", ""))
                itens.append({
                    "titulo": _limpar_html(titulo),
                    "link": link,
                    "fonte": _limpar_html(titulo_feed) or url,
                    "data": pub,
                    "descricao": _limpar_html(desc)[:200] if desc else "",
                })
            return itens
        except Exception as e:
            logging.warning("Erro ao buscar RSS %s: %s", url, e)
            return []


def _formatar_noticias(itens: list, categoria: str = "") -> str:
    """Formata lista de noticias em texto bonito."""
    if not itens:
        return ""

    cabecalho = f"📰 **NOTICIAS{' — ' + categoria.upper() if categoria else ''}**\n"
    linhas = [cabecalho]

    for i, item in enumerate(itens, 1):
        titulo = item.get("titulo", "Sem titulo")
        fonte = item.get("fonte", "Desconhecida")
        data = item.get("data", "")
        link = item.get("link", "")
        desc = item.get("descricao", "")

        # Formata data relativa se possivel
        data_str = ""
        if data:
            try:
                from dateutil.parser import parse as parse_date
                dt = parse_date(data)
                agora = datetime.now()
                diff = agora - dt
                if diff.days == 0:
                    horas = int(diff.seconds / 3600)
                    data_str = f"ha {horas}h" if horas > 0 else "agora"
                elif diff.days == 1:
                    data_str = "ontem"
                elif diff.days < 7:
                    data_str = f"ha {diff.dias}dias"
                else:
                    data_str = dt.strftime("%d/%m")
            except Exception:
                data_str = data[:16]

        linha = f"\n  **{i}. {titulo}**"
        if data_str:
            linha += f"\n     🕐 {data_str}"
        linha += f"\n     📰 {fonte}"
        if desc:
            # Pega so o inicio da descricao
            desc_curta = desc[:150]
            linha += f"\n     💬 {desc_curta}"
        if link:
            linha += f"\n     🔗 `{link}`"
        linhas.append(linha)

    return "\n".join(linhas)


def _noticias_do_momento(categoria: str = "geral", quantidade: int = 5) -> str:
    """Busca as principais noticias de uma categoria.

    Args:
        categoria: Categoria (geral, tecnologia, ciencia, negocios, mundo)
        quantidade: Numero de noticias por fonte (max 10)

    Returns:
        String formatada com as noticias
    """
    quantidade = min(quantidade, 10)
    categoria = categoria.lower().strip()

    if categoria in _FONTES:
        fontes = _FONTES[categoria]
    else:
        # Busca em todas as categorias
        todas = [f for fonte_list in _FONTES.values() for f in fonte_list]
        fontes = todas[:3]

    todas_noticias = []
    for nome_fonte, url in fontes:
        itens = _buscar_rss(url, limite=quantidade)
        todas_noticias.extend(itens)
        if len(todas_noticias) >= quantidade * 2:
            break

    if not todas_noticias:
        return "⚠ Nao foi possivel buscar noticias no momento.\nVerifique sua conexao com a internet."

    # Limita ao total
    todas_noticias = todas_noticias[:quantidade * 2]

    # Remove duplicatas aproximadas (mesmo titulo)
    vistos = set()
    noticias_unicas = []
    for item in todas_noticias:
        chave = item.get("titulo", "").lower()[:60]
        if chave and chave not in vistos:
            vistos.add(chave)
            noticias_unicas.append(item)

    return _formatar_noticias(noticias_unicas[:quantidade], categoria if categoria in _FONTES else "todas")


def _buscar_noticias(termo: str, quantidade: int = 5) -> str:
    """Busca noticias por palavra-chave.

    Args:
        termo: Palavra-chave ou topico para buscar
        quantidade: Numero de resultados

    Returns:
        String formatada com noticias encontradas
    """
    if not termo or not termo.strip():
        return "❌ Informe um termo para buscar (ex: 'inteligencia artificial', 'eleicoes')."

    termo = termo.strip()
    quantidade = min(quantidade, 10)

    try:
        import requests
    except ImportError:
        return "⚠ Instale a lib 'requests' primeiro: pip install requests"

    try:
        # Usa Google News RSS search
        from urllib.parse import quote
        url = f"https://news.google.com/rss/search?q={quote(termo)}&hl=pt-BR&gl=BR"
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        try:
            import feedparser
            feed = feedparser.parse(resp.content)
            itens = []
            for entry in feed.entries[:quantidade]:
                titulo = _limpar_html(entry.get("title", ""))
                link = entry.get("link", "")
                fonte = _limpar_html(entry.get("source", {}).get("title", ""))
                data = entry.get("published", "")
                itens.append({
                    "titulo": titulo,
                    "link": link,
                    "fonte": fonte or "Google News",
                    "data": data,
                    "descricao": "",
                })
        except ImportError:
            # Fallback XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            itens = []
            for item in root.findall(".//item")[:quantidade]:
                titulo = item.findtext("title", "")
                link = item.findtext("link", "")
                fonte_el = item.find("source")
                fonte = fonte_el.text if fonte_el is not None else ""
                data = item.findtext("pubDate", "")
                itens.append({
                    "titulo": _limpar_html(titulo),
                    "link": link,
                    "fonte": fonte or "Google News",
                    "data": data,
                    "descricao": "",
                })

        if not itens:
            return f"🔍 Nenhuma noticia encontrada para '{termo}'. Tente termos diferentes."

        return _formatar_noticias(itens, f'busca: "{termo}"')

    except requests.exceptions.Timeout:
        return "⏱ Tempo esgotado ao buscar noticias."
    except requests.exceptions.ConnectionError:
        return "🌐 Sem conexao com a internet."
    except Exception as e:
        return f"❌ Erro ao buscar noticias: {e}"


def register(api):
    """Registra as ferramentas de noticias no agente."""

    # ---- Noticias do momento ----
    def noticias_do_momento(categoria: str = "geral", quantidade: int = 5) -> str:
        """Busca as principais noticias do momento.

        Args:
            categoria: Categoria (geral, tecnologia, ciencia, negocios, mundo)
            quantidade: Quantidade de noticias (max 10)

        Returns:
            Lista de noticias com titulo, fonte e link
        """
        return _noticias_do_momento(categoria, quantidade)

    api.register_tool(
        name="noticias_do_momento",
        func=noticias_do_momento,
        description=(
            "Busca as principais noticias do momento de fontes confiaveis via RSS. "
            "Categorias: 'geral' (padrao), 'tecnologia', 'ciencia', 'negocios', 'mundo'. "
            "Retorna titulo, fonte, data relativa e link de cada noticia. "
            "Exemplos: 'Quais as noticias de hoje?', "
            "'O que esta acontecendo na tecnologia?', "
            "'Ultimas noticias do mundo'. "
            "Use quando o usuario perguntar sobre noticias, atualidades, "
            "ultimas novidades ou o que esta acontecendo."
        ),
        parameters={
            "categoria": {
                "type": "string",
                "description": "Categoria das noticias (geral, tecnologia, ciencia, negocios, mundo). Padrao: geral",
            },
            "quantidade": {
                "type": "integer",
                "description": "Quantidade de noticias para retornar (max 10). Padrao: 5",
            },
        },
        required=[],
    )

    # ---- Buscar noticias ----
    def buscar_noticias(termo: str, quantidade: int = 5) -> str:
        """Busca noticias sobre um topico especifico.

        Args:
            termo: Palavra-chave ou topico para buscar
            quantidade: Quantidade de resultados (max 10)

        Returns:
            Noticias encontradas sobre o tema
        """
        return _buscar_noticias(termo, quantidade)

    api.register_tool(
        name="buscar_noticias",
        func=buscar_noticias,
        description=(
            "Busca noticias sobre um topico ou palavra-chave especifica usando Google News RSS. "
            "Retorna as manchetes mais recentes com fonte e link. "
            "Exemplos: 'Noticias sobre inteligencia artificial', "
            "'O que esta acontecendo com a economia?', "
            "'Noticias sobre o Brasil'. "
            "Use quando o usuario perguntar sobre um topico especifico "
            "e quiser noticias atualizadas sobre ele."
        ),
        parameters={
            "termo": {
                "type": "string",
                "description": "Termo ou topico para buscar noticias (ex: 'inteligencia artificial', 'eleicoes')",
            },
            "quantidade": {
                "type": "integer",
                "description": "Quantidade de resultados (max 10). Padrao: 5",
            },
        },
        required=["termo"],
    )

    return plugin_info()


def plugin_info() -> dict:
    """Retorna metadados do plugin."""
    return {
        "name": "Noticias",
        "version": "1.0.0",
        "description": "Noticias do momento via RSS (Google News, TechCrunch, BBC, Reuters, etc.)",
        "author": "Agente Local",
        "tools": ["noticias_do_momento", "buscar_noticias"],
    }
