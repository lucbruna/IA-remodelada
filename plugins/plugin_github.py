"""
plugin_github.py
=================
Integracao com GitHub API — gerencia repos, commits, PRs, issues.

Requer: GITHUB_TOKEN no .env (Personal Access Token)
"""

__version__ = "1.0.0"
PLUGIN_NAME = "GitHub Integration"

import os
import json
import logging

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"


def _headers():
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "IA-Remodelada"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _get(url):
    import requests
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(url, data):
    import requests
    resp = requests.post(url, headers=_headers(), json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def register(api):

    def github_status() -> str:
        if not GITHUB_TOKEN:
            return "❌ GITHUB_TOKEN nao configurado. Adicione no .env"
        try:
            user = _get(f"{GITHUB_API}/user")
            return (
                f"✅ GitHub conectado\n"
                f"   Usuario: {user.get('login')}\n"
                f"   Repos publicos: {user.get('public_repos')}\n"
                f"   Tipo: {user.get('type')}"
            )
        except Exception as e:
            return f"❌ Erro ao conectar: {e}"

    def github_list_repos(owner: str = "", per_page: int = 10) -> str:
        url = f"{GITHUB_API}/users/{owner}/repos" if owner else f"{GITHUB_API}/user/repos"
        data = _get(f"{url}?per_page={min(per_page, 50)}&sort=updated")
        if not data:
            return "Nenhum repositorio encontrado."
        repos = []
        for r in data[:per_page]:
            repos.append(
                f"• {r['full_name']} ({r.get('stargazers_count', 0)}★) "
                f"- {r.get('description', 'sem desc')[:60]}"
            )
        return "\n".join(repos)

    def github_get_repo(owner: str, repo: str) -> str:
        data = _get(f"{GITHUB_API}/repos/{owner}/{repo}")
        return (
            f"**{data['full_name']}**\n"
            f"Stars: {data.get('stargazers_count', 0)} | "
            f"Forks: {data.get('forks_count', 0)} | "
            f"Open Issues: {data.get('open_issues_count', 0)}\n"
            f"Descricao: {data.get('description', 'N/A')}\n"
            f"Linguagem: {data.get('language', 'N/A')}\n"
            f"URL: {data.get('html_url')}"
        )

    def github_list_issues(owner: str, repo: str, state: str = "open", per_page: int = 10) -> str:
        data = _get(f"{GITHUB_API}/repos/{owner}/{repo}/issues?state={state}&per_page={min(per_page, 30)}")
        if not data:
            return "Nenhuma issue encontrada."
        issues = []
        for i in data[:per_page]:
            labels = ", ".join(l["name"] for l in i.get("labels", []))
            issues.append(
                f"#{i['number']} [{i['state']}] {i['title'][:60]}\n"
                f"   Labels: {labels or 'nenhuma'} | {i.get('created_at', '')[:10]}"
            )
        return "\n".join(issues)

    def github_create_issue(owner: str, repo: str, title: str, body: str = "", labels: str = "") -> str:
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = [l.strip() for l in labels.split(",")]
        result = _post(f"{GITHUB_API}/repos/{owner}/{repo}/issues", payload)
        return f"✅ Issue #{result['number']} criada: {result['html_url']}"

    def github_list_prs(owner: str, repo: str, state: str = "open", per_page: int = 10) -> str:
        data = _get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls?state={state}&per_page={min(per_page, 30)}")
        if not data:
            return "Nenhum PR encontrado."
        prs = []
        for p in data[:per_page]:
            prs.append(
                f"#{p['number']} {p['title'][:60]}\n"
                f"   por {p['user']['login']} | {p.get('created_at', '')[:10]}"
            )
        return "\n".join(prs)

    def github_search_code(query: str, per_page: int = 10) -> str:
        data = _get(f"{GITHUB_API}/search/code?q={query}&per_page={min(per_page, 30)}")
        items = data.get("items", [])
        if not items:
            return "Nenhum resultado."
        results = []
        for item in items[:per_page]:
            results.append(
                f"• {item['repository']['full_name']}: {item['path']}\n"
                f"  {item.get('html_url', '')[:80]}"
            )
        return f"**{data.get('total_count', 0)} resultados:**\n\n" + "\n".join(results)

    def github_file_content(owner: str, repo: str, path: str, branch: str = "main") -> str:
        data = _get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}")
        if data.get("encoding") == "base64":
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            if len(content) > 8000:
                content = content[:8000] + "\n[...truncado...]"
            return f"**{path}** ({data.get('size', 0)} bytes):\n\n{content}"
        return str(data)

    api.register_tool("github_status", github_status,
        "Verifica conexao com GitHub (token, usuario).", {}, [])

    api.register_tool("github_list_repos", github_list_repos,
        "Lista repositorios de um usuario ou autenticado.",
        {"owner": {"type": "string", "description": "Owner (opcional, vazio = repos do usuario autenticado)"},
         "per_page": {"type": "integer", "description": "Max repos (opcional, padrao 10)"}}, [])

    api.register_tool("github_get_repo", github_get_repo,
        "Retorna detalhes de um repositorio.",
        {"owner": {"type": "string"}, "repo": {"type": "string"}}, ["owner", "repo"])

    api.register_tool("github_list_issues", github_list_issues,
        "Lista issues de um repositorio.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "state": {"type": "string", "description": "open, closed, all (opcional)"},
         "per_page": {"type": "integer"}}, ["owner", "repo"])

    api.register_tool("github_create_issue", github_create_issue,
        "Cria uma issue em um repositorio.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "title": {"type": "string", "description": "Titulo da issue"},
         "body": {"type": "string", "description": "Corpo da issue (opcional)"},
         "labels": {"type": "string", "description": "Labels separadas por virgula (opcional)"}}, ["owner", "repo", "title"])

    api.register_tool("github_list_prs", github_list_prs,
        "Lista pull requests de um repositorio.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "state": {"type": "string"}, "per_page": {"type": "integer"}}, ["owner", "repo"])

    api.register_tool("github_search_code", github_search_code,
        "Busca codigo no GitHub.",
        {"query": {"type": "string", "description": "Termo de busca"},
         "per_page": {"type": "integer"}}, ["query"])

    api.register_tool("github_file_content", github_file_content,
        "Le o conteudo de um arquivo de um repositorio.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "path": {"type": "string", "description": "Caminho do arquivo"},
         "branch": {"type": "string", "description": "Branch (opcional, padrao main)"}}, ["owner", "repo", "path"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Integracao GitHub: repos, issues, PRs, busca de codigo, leitura de arquivos.",
        "tools": ["github_status", "github_list_repos", "github_get_repo", "github_list_issues",
                   "github_create_issue", "github_list_prs", "github_search_code", "github_file_content"],
    }
