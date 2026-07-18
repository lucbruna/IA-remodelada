"""
plugin_rede_avancada.py
=======================
Ferramentas de rede: ping, DNS lookup, whois, port scan simples,
HTTP requests, download de arquivos, verificacao de status HTTP.
"""

import os
import json
import socket
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Rede Avancada"


def register(api):
    def ping_host(host: str, contagem: int = 4) -> str:
        """Ping em um host (usando ping do sistema)."""
        import subprocess
        import platform
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            result = subprocess.run(
                ["ping", param, str(contagem), host],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout[:2000]
            return f"Falha no ping: {result.stderr[:500]}"
        except subprocess.TimeoutExpired:
            return f"Timeout ao pingar {host}"
        except Exception as e:
            return f"Erro: {e}"

    def dns_lookup(host: str, tipo: str = "A") -> str:
        """Consulta DNS: A, AAAA, MX, NS, TXT, CNAME."""
        try:
            tipo = tipo.upper()
            if tipo == "A":
                results = socket.getaddrinfo(host, 80, socket.AF_INET)
                ips = list(set(r[4][0] for r in results))
                return f"DNS A records for {host}:\n" + "\n".join(f"  {ip}" for ip in ips)
            elif tipo == "AAAA":
                results = socket.getaddrinfo(host, 80, socket.AF_INET6)
                ips = list(set(r[4][0] for r in results))
                return f"DNS AAAA records for {host}:\n" + "\n".join(f"  {ip}" for ip in ips)
            else:
                return f"Tipo {tipo} requer dns.resolver. Instale: pip install dnspython"
        except socket.gaierror as e:
            return f"Erro DNS: {e}"
        except Exception as e:
            return f"Erro: {e}"

    def dns_lookup_avancado(host: str, tipo: str = "A") -> str:
        """Consulta DNS avancada com dnspython: MX, NS, TXT, CNAME, SOA."""
        try:
            import dns.resolver
        except ImportError:
            return "Instale: pip install dnspython"
        try:
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(host, tipo)
            results = [f"DNS {tipo} records for {host}:"]
            for r in answers:
                results.append(f"  {r}")
            return "\n".join(results)
        except Exception as e:
            return f"Erro DNS: {e}"

    def port_scan(host: str, portas: str = "80,443,22,21,3306,5432,8080,8443") -> str:
        """Escaneia portas TCP. portas: separadas por virgula ou range (ex: 80-100)."""
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
        except ImportError:
            return "Erro no import."
        try:
            if "-" in portas:
                parts = portas.split("-")
                port_range = list(range(int(parts[0]), int(parts[1]) + 1))
            else:
                port_range = [int(p.strip()) for p in portas.split(",") if p.strip().isdigit()]

            abertas = []
            def _check(port):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                try:
                    result = s.connect_ex((host, port))
                    if result == 0:
                        svc = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
                               80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
                               3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis",
                               8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB"}.get(port, "")
                        return port, svc
                except Exception:
                    pass
                finally:
                    s.close()
                return None

            with ThreadPoolExecutor(max_workers=50) as pool:
                futures = {pool.submit(_check, p): p for p in port_range}
                for f in as_completed(futures):
                    result = f.result()
                    if result:
                        abertas.append(result)

            if not abertas:
                return f"Nenhuma porta aberta em {host} nas {len(port_range)} portas verificadas."
            abertas.sort()
            lines = [f"Portas abertas em {host} ({len(abertas)}/{len(port_range)}):"]
            for p, svc in abertas:
                svc_str = f" ({svc})" if svc else ""
                lines.append(f"  PORT {p}/TCP aberta{svc_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def http_check(url: str, timeout: int = 10) -> str:
        """Verifica status HTTP e headers de uma URL."""
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                headers = dict(resp.headers)
                return (
                    f"URL: {url}\n"
                    f"Status: {resp.status} {resp.reason}\n"
                    f"Tamanho: {headers.get('Content-Length', 'N/A')}\n"
                    f"Tipo: {headers.get('Content-Type', 'N/A')}\n"
                    f"Server: {headers.get('Server', 'N/A')}\n"
                    f"Ultima mod.: {headers.get('Last-Modified', 'N/A')}\n"
                    f"Cache: {headers.get('Cache-Control', 'N/A')}\n"
                )
        except Exception as e:
            return f"Erro ao acessar {url}: {e}"

    def download_arquivo(url: str, destino: str = "", timeout: int = 60) -> str:
        """Download de arquivo da internet."""
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            if not destino:
                nome = url.split("/")[-1].split("?")[0] or "download"
                destino = os.path.join(DATA_DIR, nome)
            parent = os.path.dirname(os.path.abspath(destino))
            if parent:
                os.makedirs(parent, exist_ok=True)
            urllib.request.urlretrieve(url, destino, context=ctx)
            size = os.path.getsize(destino)
            return f"Download concluido: {destino} ({size:,} bytes)"
        except Exception as e:
            return f"Erro no download: {e}"

    def whois(dominio: str) -> str:
        """Consulta WHOIS de dominio (via whois python)."""
        try:
            import whois as whois_module
        except ImportError:
            return "Instale: pip install whois"
        try:
            w = whois_module.whois(dominio)
            info = {
                "dominio": w.domain_name,
                "registrador": w.registrar,
                "criacao": str(w.creation_date),
                "expiracao": str(w.expiration_date),
                "ultima_atualizacao": str(w.updated_date),
                "dns": w.name_servers,
                "email": w.emails,
                "status": w.status,
                "org": w.org,
                "pais": w.country,
            }
            return json.dumps(info, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            return f"Erro WHOIS: {e}"

    api.register_tool("ping_host", ping_host,
        "Ping em host usando ping do sistema.",
        {"host": {"type": "string", "description": "Hostname ou IP"}, "contagem": {"type": "integer", "description": "Numero de pings (opcional)"}}, ["host"])

    api.register_tool("dns_lookup", dns_lookup,
        "Consulta DNS (A, AAAA). Para MX, NS, TXT use dns_lookup_avancado.",
        {"host": {"type": "string", "description": "Hostname"}, "tipo": {"type": "string", "description": "A ou AAAA (opcional)"}}, ["host"])

    api.register_tool("dns_lookup_avancado", dns_lookup_avancado,
        "Consulta DNS completa: MX, NS, TXT, CNAME, SOA (requer dnspython).",
        {"host": {"type": "string", "description": "Hostname"}, "tipo": {"type": "string", "description": "MX, NS, TXT, etc (opcional)"}}, ["host"])

    api.register_tool("port_scan", port_scan,
        "Escaneia portas TCP. Portas: '80,443,22' ou '1-1000'.",
        {"host": {"type": "string", "description": "Hostname ou IP"}, "portas": {"type": "string", "description": "Portas separadas por virgula ou range (opcional)"}}, ["host"])

    api.register_tool("http_check", http_check,
        "Verifica status HTTP e headers de uma URL.",
        {"url": {"type": "string", "description": "URL completa"}, "timeout": {"type": "integer", "description": "Timeout em segundos (opcional)"}}, ["url"])

    api.register_tool("download_arquivo", download_arquivo,
        "Download de arquivo da internet.",
        {"url": {"type": "string", "description": "URL do arquivo"}, "destino": {"type": "string", "description": "Caminho destino (opcional)"}, "timeout": {"type": "integer", "description": "Timeout (opcional)"}}, ["url"])

    api.register_tool("whois", whois,
        "Consulta WHOIS de dominio (requer pip install whois).",
        {"dominio": {"type": "string", "description": "Dominio (ex: google.com)"}}, ["dominio"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Rede: ping, DNS, port scan, HTTP check, download, WHOIS",
        "tools": ["ping_host", "dns_lookup", "dns_lookup_avancado", "port_scan", "http_check", "download_arquivo", "whois"],
    }
