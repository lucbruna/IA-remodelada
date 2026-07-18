"""
plugin_web_scraper.py
=====================
Plugin de raspagem (web scraping) e extração de conteúdo de páginas web.
Permite extrair dados estruturados de HTML/XML, interpretar conteúdo e
coletar informações específicas de sites.

Recursos:
  - Extração de elementos HTML por seletores CSS ou XPath
  - Parsing de tabelas HTML para dados estruturados
  - Extraçăo de links, imagens e metadados
  - Suporte a autenticação básica e cookies
  - Tratamento de JavaScript limitado (via requests-html se disponível)
  - Extração de dados JSON-LD e microdados
  - Filtragem e limpeza de texto extraído
"""

import re
import json
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Any, Union
import time

__version__ = "1.0.0"
PLUGIN_NAME = "Web Scraper e Extração de Conteúdo"


def _check_bs4() -> bool:
    """Verifica se BeautifulSoup4 está disponível."""
    try:
        from bs4 import BeautifulSoup
        return True
    except ImportError:
        return False


def _check_lxml() -> bool:
    """Verifica se lxml está disponível (para parsing mais rápido)."""
    try:
        import lxml
        return True
    except ImportError:
        return False


def _check_requests_html() -> bool:
    """Verifica se requests-html está disponível (para JS rendering)."""
    try:
        from requests_html import HTMLSession
        return True
    except ImportError:
        return False


def extract_web_content(url: str,
                       selector_type: str = "css",
                       selector: str = "",
                       extract_type: str = "text",
                       attribute: str = "",
                       wait_time: int = 0,
                       headers: dict = None) -> str:
    """Extrai conteúdo específico de uma página web usando seletores.

    Args:
        url: URL da página para scrapar
        selector_type: Tipo de seletor ("css", "xpath", "regex")
        selector: Expressão de seletor para localizar elementos
        extract_type: Tipo de extração ("text", "html", "attribute", "links", "images", "tables")
        attribute: Nome do atributo para extrair (quando extract_type="attribute")
        wait_time: Tempo de espera em segundos para carregamento de JS (se disponível)
        headers: Headers HTTP personalizados

    Returns:
        Conteúdo extraído formatado ou mensagem de erro
    """
    try:
        import requests
    except ImportError:
        return "❌ Biblioteca 'requests' não disponível. Instale com: pip install requests"

    if not url.startswith(('http://', 'https://')):
        return "❌ URL inválida. Deve começar com http:// ou https://"

    # Headers padrão
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    if headers:
        default_headers.update(headers)

    try:
        # Usa requests-html se disponível para melhor suporte a JS
        if _check_requests_html() and wait_time > 0:
            from requests_html import HTMLSession
            session = HTMLSession()
            response = session.get(url, headers=default_headers, timeout=30)
            if wait_time > 0:
                response.html.render(timeout=wait_time * 1000)  # Converte para ms
            html_content = response.html.html
            session.close()
        else:
            response = requests.get(url, headers=default_headers, timeout=30)
            response.raise_for_status()
            html_content = response.text

        # Se não temos seletor, retorna informações básicas da página
        if not selector:
            return _get_basic_page_info(html_content, url)

        # Processa com BeautifulSoup se disponível
        if _check_bs4():
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml' if _check_lxml() else 'html.parser')
            return _extract_with_bs4(soup, selector_type, selector, extract_type, attribute, url)
        else:
            # Fallback para regex apenas (menos confiável)
            return _extract_with_regex(html_content, selector_type, selector, extract_type, attribute)

    except requests.exceptions.RequestException as e:
        return f"❌ Erro de rede ao acessar {url}: {str(e)}"
    except Exception as e:
        return f"❌ Erro durante extração: {str(e)}"


def _get_basic_page_info(html_content: str, url: str) -> str:
    """Extrai informações básicas da página quando nenhum seletor é especificado."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml' if _check_lxml() else 'html.parser')

        title = soup.find('title')
        title_text = title.get_text().strip() if title else "Sem título"

        # Meta description
        description = soup.find('meta', attrs={'name': 'description'})
        desc_text = description.get('content', '').strip() if description else ""

        # Contagem de elementos
        links = len(soup.find_all('a'))
        images = len(soup.find_all('img'))
        scripts = len(soup.find_all('script'))

        return (
            f"📄 INFORMAÇÕES DA PÁGINA: {url}\n"
            f"{'='*60}\n"
            f"Título: {title_text}\n"
            f"Descrição: {desc_text if desc_text else 'Não disponível'}\n"
            f"Links: {links} | Imagens: {images} | Scripts: {scripts}\n"
            f"Tamanho HTML: {len(html_content):,} caracteres\n\n"
            f"💡 Dica: Especifique um seletor CSS ou XPath para extrair conteúdo específico.\n"
            f"Exemplos de seletores: 'h1', '.article-content', '#main-table', 'tr'"
        )
    except Exception:
        # Se até o BeautifulSoup falhar, retorna info básica
        return (
            f"📄 Página acessada: {url}\n"
            f"Tamanho: {len(html_content):,} caracteres\n"
            f"⚠️  Para extração avançada, instale: pip install beautifulsoup4 lxml"
        )


def _extract_with_bs4(soup, selector_type: str, selector: str,
                     extract_type: str, attribute: str, base_url: str) -> str:
    """Extrai conteúdo usando BeautifulSoup."""
    try:
        elements = []

        if selector_type.lower() == "css":
            elements = soup.select(selector)
        elif selector_type.lower() == "xpath":
            # XPath não é suportado nativamente pelo BeautifulSoup
            # Para XPath completo, precisaríamos de lxml diretamente
            return "❌ Seletor XPath requer lxml diretamente. Use seletor CSS ou instale lxml para melhor suporte."
        else:
            return f"❌ Tipo de seletor não suportado: {selector_type}. Use 'css' ou 'xpath'."

        if not elements:
            return f"🔍 Nenhum elemento encontrado com o seletor: {selector}"

        # Processa com base no tipo de extração
        results = []

        if extract_type == "text":
            texts = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
            if texts:
                return "\n\n".join([f"• {text}" for text in texts[:20]])  # Limita a 20 resultados
            else:
                return "📝 Nenhum texto encontrado nos elementos selecionados."

        elif extract_type == "html":
            htmls = [str(elem) for elem in elements[:10]]  # Limita a 10 elementos
            return "\n\n---\n\n".join(htmls)

        elif extract_type == "attribute":
            if not attribute:
                return "❌ Para extração de atributo, especifique o nome do atributo."
            attrs = []
            for elem in elements:
                attr_value = elem.get(attribute)
                if attr_value is not None:
                    attrs.append(attr_value)
            if attrs:
                return "\n".join(attrs[:20])  # Limita a 20 resultados
            else:
                return f"🔧 Nenhum valor encontrado para o atributo '{attribute}'."

        elif extract_type == "links":
            links = []
            for elem in elements:
                if elem.name == 'a' and elem.get('href'):
                    href = urljoin(base_url, elem.get('href'))
                    text = elem.get_text(strip=True) or "[sem texto]"
                    links.append(f"{text}: {href}")
                # Também procura links em outros elementos com href
                elif elem.get('href'):
                    href = urljoin(base_url, elem.get('href'))
                    links.append(href)
            if links:
                return "\n".join(list(dict.fromkeys(links))[:20])  # Remove duplicatas, limita a 20
            else:
                return "🔗 Nenhum link encontrado nos elementos selecionados."

        elif extract_type == "images":
            images = []
            for elem in elements:
                if elem.name == 'img' and elem.get('src'):
                    src = urljoin(base_url, elem.get('src'))
                    alt = elem.get('alt', '[sem descrição]')
                    images.append(f"{alt}: {src}")
                # Também procura imagens em outros elementos com src ou background
                elif elem.get('src'):
                    src = urljoin(base_url, elem.get('src'))
                    images.append(src)
                elif elem.get('style'):
                    # Busca URLs de background-image no estilo
                    bg_matches = re.findall(r'url\(["\']?(.*?)["\']?\)', elem.get('style'))
                    for match in bg_matches:
                        images.append(urljoin(base_url, match))
            if images:
                return "\n".join(list(dict.fromkeys(images))[:20])  # Remove duplicatas, limita a 20
            else:
                return "🖼️ Nenhuma imagem encontrada nos elementos selecionados."

        elif extract_type == "tables":
            tables = []
            for elem in elements:
                if elem.name == 'table':
                    table_data = _html_table_to_text(elem)
                    if table_data.strip():
                        tables.append(table_data)
            if tables:
                return "\n\n---\n\n".join(tables[:5])  # Limita a 5 tabelas
            else:
                return "📊 Nenhuma tabela encontrada nos elementos selecionados."

        else:
            return f"❌ Tipo de extração não suportado: {extract_type}. Use: text, html, attribute, links, images, tables."

    except Exception as e:
        return f"❌ Erro durante processamento com BeautifulSoup: {str(e)}"


def _html_table_to_text(table_element) -> str:
    """Converte uma tabela HTML em texto formatado."""
    try:
        rows = []
        for tr in table_element.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cell_text = td.get_text(strip=True)
                cells.append(cell_text)
            if cells:
                rows.append(" | ".join(cells))

        if not rows:
            return ""

        # Cabeçalho
        result = []
        if rows:
            result.append(" | ".join(["---"] * len(rows[0].split(" | "))))
            result.insert(0, rows[0])
            result.extend(rows[1:])

        return "\n".join(result)
    except Exception:
        return "[Erro ao converter tabela]"


def _extract_with_regex(html_content: str, selector_type: str, selector: str,
                       extract_type: str, attribute: str) -> str:
    """Extração de fallback usando regex (menos confiável)."""
    if extract_type == "text":
        # Remove tags HTML e retorna texto limpo
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:1000] + ("..." if len(text) > 1000 else "")
    elif extract_type == "links":
        # Extrai links href
        links = re.findall(r'href=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        return "\n".join(list(dict.fromkeys(links))[:20])
    elif extract_type == "images":
        # Extrai fontes de imagens
        images = re.findall(r'src=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        img_links = [link for link in images if any(ext in link.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'])]
        return "\n".join(list(dict.fromkeys(img_links))[:20])
    else:
        return "⚠️ Extração avançada requer beautifulsoup4. Instale com: pip install beautifulsoup4 lxml"


def extract_structured_data(url: str, data_type: str = "json-ld") -> str:
    """Extrai dados estruturados de uma página (JSON-LD, microdados, RDFa).

    Args:
        url: URL da página para analisar
        data_type: Tipo de dados estruturados ("json-ld", "microdata", "rdfa", "opengraph", "all")

    Returns:
        Dados estruturados extraídos em formato JSON ou mensagem de erro
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        return f"❌ Bibliotecas necessárias não disponíveis. Instale com: pip install beautifulsoup4 lxml requests"

    if not url.startswith(('http://', 'https://')):
        return "❌ URL inválida. Deve começar com http:// ou https://"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml' if _check_lxml() else 'html.parser')

        results = {}

        if data_type in ["json-ld", "all"]:
            # Extrai JSON-LD
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            json_ld_data = []
            for script in json_ld_scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        json_ld_data.append(data)
                except json.JSONDecodeError:
                    continue
            if json_ld_data:
                results["json-ld"] = json_ld_data

        if data_type in ["microdata", "all"]:
            # Extrai microdados (itemprop, itemscope, itemtype)
            microdata = {}
            elements_with_itemscope = soup.find_all(itemscope=True)
            for elem in elements_with_itemscope:
                itemtype = elem.get('itemtype', 'sem tipo')
                props = {}
                for prop in elem.find_all(attrs={"itemprop": True}):
                    prop_name = prop.get('itemprop')
                    prop_value = prop.get_text(strip=True) or prop.get('content', '')
                    if prop_name:
                        props[prop_name] = prop_value
                if props:
                    microdata[itemtype] = props
            if microdata:
                results["microdata"] = microdata

        if data_type in ["opengraph", "all"]:
            # Extrai metadados Open Graph
            og_tags = {}
            for tag in soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
                prop = tag.get('property')
                content = tag.get('content', '')
                if prop and content:
                    og_tags[prop] = content
            if og_tags:
                results["opengraph"] = og_tags

        if data_type in ["rdfa", "all"]:
            # Extrai RDFa básico
            rdfa_data = {}
            # Propriedades comuns
            for prop in ['about', 'rel', 'rev', 'property', 'resource', 'datatype', 'typeof']:
                elements = soup.find_all(attrs={prop: True})
                if elements:
                    values = []
                    for elem in elements:
                        val = elem.get(prop)
                        if val:
                            values.append(val)
                    if values:
                        rdfa_data[prop] = list(dict.fromkeys(values))  # Remove duplicatas
            if rdfa_data:
                results["rdfa"] = rdfa_data

        if not results:
            return "📭 Nenhum dado estruturado encontrado na página."

        # Formata saída
        output = [f"📊 DADOS ESTRUTURADOS DE: {url}", "="*60]
        for data_type_key, data in results.items():
            output.append(f"\n🔹 {data_type_key.upper()}:")
            if isinstance(data, list):
                for i, item in enumerate(data[:3]):  # Limita a 3 itens por tipo
                    output.append(f"  {i+1}. {json.dumps(item, ensure_ascii=False, indent=2)[:200]}...")
                    if len(data) > 3:
                        output.append(f"     ... e mais {len(data)-3} itens")
            elif isinstance(data, dict):
                for key, value in list(data.items())[:5]:  # Limita a 5 pares chave-valor
                    if isinstance(value, dict) and len(str(value)) > 100:
                        output.append(f"  {key}: {str(value)[:100]}...")
                    else:
                        output.append(f"  {key}: {value}")
                if len(data) > 5:
                    output.append(f"     ... e mais {len(data)-5} campos")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Erro ao extrair dados estruturados: {str(e)}"


def scrape_multiple_pages(urls: List[str],
                         selector_type: str = "css",
                         selector: str = "",
                         extract_type: str = "text",
                         delay: float = 1.0) -> str:
    """Faz scraping de múltiplas páginas com delay entre requisições.

    Args:
        urls: Lista de URLs para processar
        selector_type: Tipo de seletor ("css", "xpath")
        selector: Expressão de seletor para localizar elementos
        extract_type: Tipo de extração ("text", "html", "attribute", etc.)
        delay: Delay em segundos entre requisições (para ser respeitoso com servidores)

    Returns:
        Resultados consolidados do scraping de múltiplas páginas
    """
    if not urls:
        return "❌ Lista de vazia."

    results = []
    successful = 0
    failed = 0

    for i, url in enumerate(urls):
        try:
            result = extract_web_content(url, selector_type, selector, extract_type)
            if not result.startswith("❌"):
                results.append({
                    "url": url,
                    "status": "sucesso",
                    "data": result
                })
                successful += 1
            else:
                results.append({
                    "url": url,
                    "status": "falha",
                    "error": result
                })
                failed += 1
        except Exception as e:
            results.append({
                "url": url,
                "status": "erro",
                "error": str(e)
            })
            failed += 1

        # Delay entre requisições (exceto na última)
        if i < len(urls) - 1:
            time.sleep(delay)

    # Formata resultado
    output = [
        f"🌐 SCRAPING DE MÚLTIPLAS PÁGINAS ({len(urls)} URLs)",
        f"✅ Sucessos: {successful} | ❌ Falhas: {failed}",
        "="*60
    ]

    for result in results:
        if result["status"] == "sucesso":
            output.append(f"\n🔗 {result['url']}")
            output.append("-" * 40)
            # Limita o output para não ficar muito longo
            data_preview = result['data'][:300] + ("..." if len(result['data']) > 300 else "")
            output.append(data_preview)
        else:
            output.append(f"\n🔗 {result['url']}")
            output.append(f"❌ Erro: {result['error']}")

    return "\n".join(output)


# Register all tools
def register(api):
    """Registra todas as ferramentas de web scraping."""
    api.register_tool(
        name="extract_web_content",
        func=extract_web_content,
        description="Extrai conteúdo específico de páginas web usando seletores CSS/XPath.",
        parameters={
            "url": {"type": "string", "description": "URL da página para scrapar"},
            "selector_type": {"type": "string", "description": "Tipo de seletor: 'css' ou 'xpath' (padrão: 'css')"},
            "selector": {"type": "string", "description": "Expressão de seletor para localizar elementos (ex: 'h1', '.article-content', '#main-table')"},
            "extract_type": {"type": "string", "description": "Tipo de extração: 'text', 'html', 'attribute', 'links', 'images', 'tables' (padrão: 'text')"},
            "attribute": {"type": "string", "description": "Nome do atributo para extrair (quando extract_type='attribute')"},
            "wait_time": {"type": "integer", "description": "Tempo de espera em segundos para carregamento de JS (padrão: 0)"},
            "headers": {"type": "object", "description": "Headers HTTP personalizados (opcional)"}
        },
        required=["url"]
    )

    api.register_tool(
        name="extract_structured_data",
        func=extract_structured_data,
        description="Extrai dados estruturados de páginas web (JSON-LD, microdados, Open Graph, RDFa).",
        parameters={
            "url": {"type": "string", "description": "URL da página para analisar"},
            "data_type": {"type": "string", "description": "Tipo de dados: 'json-ld', 'microdata', 'rdfa', 'opengraph', 'all' (padrão: 'json-ld')"}
        },
        required=["url"]
    )

    api.register_tool(
        name="scrape_multiple_pages",
        func=scrape_multiple_pages,
        description="Faz scraping de múltiplas páginas com delay entre requisições para ser respeitoso com servidores.",
        parameters={
            "urls": {"type": "array", "items": {"type": "string"}, "description": "Lista de URLs para processar"},
            "selector_type": {"type": "string", "description": "Tipo de seletor: 'css' ou 'xpath' (padrão: 'css')"},
            "selector": {"type": "string", "description": "Expressão de seletor para localizar elementos"},
            "extract_type": {"type": "string", "description": "Tipo de extração: 'text', 'html', 'attribute', 'links', 'images', 'tables' (padrão: 'text')"},
            "delay": {"type": "number", "description": "Delay em segundos entre requisições (padrão: 1.0)"}
        },
        required=["urls"]
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Web scraper avançado para extração de conteúdo, dados estruturados e informações específicas de páginas web.",
        "tools": [
            "extract_web_content",
            "extract_structured_data",
            "scrape_multiple_pages"
        ],
    }