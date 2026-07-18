"""
plugin_web_scraping.py
=======================
Web scraping avancado: parse de HTML, extracao de dados,
formularios, links, imagens e metadados de paginas.
"""

import os
import re
import json
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

__version__ = "1.0.0"
PLUGIN_NAME = "Web Scraping Avancado"


def register(api):
    def scrape_page(url: str, selector: str = "", extract: str = "text") -> str:
        """Extrai conteudo de uma pagina web. extract: text, html, links, images, metadata, all."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return "Instale: pip install requests beautifulsoup4"

        try:
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if extract == "links":
                links = []
                for a in soup.find_all("a", href=True):
                    href = urljoin(url, a["href"])
                    text = a.get_text(strip=True)[:80]
                    links.append(f"{text} -> {href}")
                return "\n".join(links[:200]) if links else "Nenhum link encontrado."

            if extract == "images":
                imgs = []
                for img in soup.find_all("img", src=True):
                    src = urljoin(url, img["src"])
                    alt = img.get("alt", "")[:60]
                    imgs.append(f"{alt} ({src})")
                return "\n".join(imgs[:100]) if imgs else "Nenhuma imagem encontrada."

            if extract == "metadata":
                meta = {}
                for m in soup.find_all("meta"):
                    if m.get("name"):
                        meta[m["name"]] = m.get("content", "")
                    if m.get("property"):
                        meta[m["property"]] = m.get("content", "")
                title = soup.title.string if soup.title else ""
                return f"Titulo: {title}\n" + "\n".join(f"{k}: {v}" for k, v in meta.items() if v)

            if extract == "all":
                title = soup.title.string if soup.title else "sem titulo"
                text = soup.get_text(separator="\n", strip=True)[:5000]
                links = len(soup.find_all("a", href=True))
                imgs = len(soup.find_all("img", src=True))
                return f"Titulo: {title}\nLinks: {links} | Imagens: {imgs}\n\n{text[:3000]}"

            if selector:
                elements = soup.select(selector)
                if not elements:
                    return f"Nenhum elemento encontrado com seletor '{selector}'."
                texts = []
                for el in elements[:50]:
                    texts.append(el.get_text(strip=True))
                return "\n---\n".join(texts)

            text = soup.get_text(separator="\n", strip=True)
            return text[:10000] if text else "Nenhum texto encontrado."
        except Exception as e:
            return f"Erro ao scraping {url}: {e}"

    def scrape_links(url: str, domain_only: bool = False) -> str:
        """Extrai todos os links de uma pagina, opcionalmente filtrando pelo mesmo dominio."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return "Instale: pip install requests beautifulsoup4"
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            parsed = urlparse(url)
            base_domain = parsed.netloc
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                if domain_only and urlparse(href).netloc != base_domain:
                    continue
                links.append(href)
            unique = sorted(set(links))
            return "\n".join(unique[:300]) if unique else "Nenhum link encontrado."
        except Exception as e:
            return f"Erro: {e}"

    def scrape_table(url: str, selector: str = "table") -> str:
        """Extrai tabela(s) de uma pagina HTML e retorna como texto tabular."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return "Instale: pip install requests beautifulsoup4"
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.select(selector)
            if not tables:
                return "Nenhuma tabela encontrada."
            results = []
            for i, table in enumerate(tables[:5]):
                rows = table.find_all("tr")
                table_data = []
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    table_data.append(" | ".join(cell.get_text(strip=True) for cell in cells))
                results.append(f"--- Tabela {i + 1} ---\n" + "\n".join(table_data))
            return "\n\n".join(results)
        except Exception as e:
            return f"Erro: {e}"

    def scrape_form(url: str) -> str:
        """Detecta e descreve formularios HTML de uma pagina."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return "Instale: pip install requests beautifulsoup4"
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            forms = soup.find_all("form")
            if not forms:
                return "Nenhum formulario encontrado."
            results = []
            for i, form in enumerate(forms[:10]):
                action = form.get("action", "")
                method = form.get("method", "get").upper()
                inputs = []
                for inp in form.find_all(["input", "select", "textarea"]):
                    name = inp.get("name", "")
                    typ = inp.get("type", "") if inp.name == "input" else inp.name
                    required = "required" if inp.get("required") else ""
                    inputs.append(f"  {name} ({typ}) {required}")
                results.append(
                    f"--- Form {i + 1} ---\n"
                    f"Action: {action}\nMethod: {method}\n"
                    f"Campos:\n" + "\n".join(inputs)
                )
            return "\n\n".join(results)
        except Exception as e:
            return f"Erro: {e}"

    def scrape_sitemap(url: str) -> str:
        """Extrai URLs de um sitemap.xml."""
        try:
            import requests
            import xml.etree.ElementTree as ET
        except ImportError:
            return "Instale requests: pip install requests"
        try:
            sitemap_url = url.rstrip("/") + "/sitemap.xml"
            resp = requests.get(sitemap_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = []
            for loc in root.findall(".//ns:loc", ns):
                urls.append(loc.text)
            if not urls:
                urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
            return "\n".join(urls[:500]) if urls else "Nenhuma URL encontrada no sitemap."
        except Exception as e:
            return f"Erro ao ler sitemap: {e}"

    def scrape_rss(url: str, max_items: int = 10) -> str:
        """Le e extrai items de um feed RSS/Atom."""
        try:
            import requests
            import xml.etree.ElementTree as ET
        except ImportError:
            return "Instale requests: pip install requests"
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = []
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")[:200]
                items.append(f"{title}\n  {link}\n  {desc}")
            if not items:
                for entry in root.findall(".//entry"):
                    title = entry.findtext("title", "")
                    link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                    link = link_el.get("href", "") if link_el is not None else ""
                    items.append(f"{title}\n  {link}")
            return "\n\n".join(items[:max_items]) if items else "Nenhum item encontrado."
        except Exception as e:
            return f"Erro ao ler RSS: {e}"

    api.register_tool("scrape_page", scrape_page,
        "Extrai conteudo de pagina web. Opcoes: text, html, links, images, metadata, all. Suporta seletor CSS.",
        {"url": {"type": "string", "description": "URL da pagina"}, "selector": {"type": "string", "description": "Seletor CSS (opcional)"}, "extract": {"type": "string", "description": "O que extrair: text, html, links, images, metadata, all (opcional)"}}, ["url"])

    api.register_tool("scrape_links", scrape_links,
        "Extrai todos os links de uma pagina. Opcional: filtrar pelo mesmo dominio.",
        {"url": {"type": "string", "description": "URL da pagina"}, "domain_only": {"type": "boolean", "description": "So links do mesmo dominio (opcional)"}}, ["url"])

    api.register_tool("scrape_table", scrape_table,
        "Extrai tabela(s) de pagina HTML e retorna como texto tabular.",
        {"url": {"type": "string", "description": "URL da pagina"}, "selector": {"type": "string", "description": "Seletor CSS da tabela (opcional)"}}, ["url"])

    api.register_tool("scrape_form", scrape_form,
        "Detecta e descreve formularios HTML de uma pagina (campos, action, method).",
        {"url": {"type": "string", "description": "URL da pagina"}}, ["url"])

    api.register_tool("scrape_sitemap", scrape_sitemap,
        "Extrai URLs de um sitemap.xml de um site.",
        {"url": {"type": "string", "description": "URL do site (ex: https://exemplo.com)"}}, ["url"])

    api.register_tool("scrape_rss", scrape_rss,
        "Le e extrai items de um feed RSS/Atom.",
        {"url": {"type": "string", "description": "URL do feed RSS/Atom"}, "max_items": {"type": "integer", "description": "Maximo de itens (opcional, padrao 10)"}}, ["url"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Web scraping avancado: parse HTML, links, tabelas, formularios, sitemaps, RSS",
        "tools": ["scrape_page", "scrape_links", "scrape_table", "scrape_form", "scrape_sitemap", "scrape_rss"],
    }
