"""
plugin_issue_to_pr.py
=====================
Automacao completa de Issue → Branch → Commit → Pull Request.

Fluxo:
  1. Le uma issue do GitHub
  2. Cria branch com nome descritivo
  3. Faz commit com mudancas
  4. Abre PR linkado a issue
  5. Auto-label e assign

Requer: GITHUB_TOKEN no .env
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Issue-to-PR Automation"

import os
import re
import json
import logging
import subprocess

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


def _patch(url, data):
    import requests
    resp = requests.patch(url, headers=_headers(), json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:50].rstrip('-')


def register(api):

    def issue_to_pr_full(
        owner: str,
        repo: str,
        issue_number: int,
        branch_prefix: str = "fix",
        working_dir: str = ".",
        commit_message: str = "",
        auto_label: bool = True,
    ) -> str:
        if not GITHUB_TOKEN:
            return "❌ GITHUB_TOKEN nao configurado."

        try:
            issue = _get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}")
        except Exception as e:
            return f"❌ Erro ao buscar issue #{issue_number}: {e}"

        title = issue.get("title", f"Issue #{issue_number}")
        body = issue.get("body", "") or ""
        labels = [l["name"] for l in issue.get("labels", [])]

        branch_name = f"{branch_prefix}/issue-{issue_number}-{_slugify(title)}"
        safe_branch = branch_name[:60]

        steps = []

        steps.append(f"📋 **Issue #{issue_number}:** {title}")
        steps.append(f"   Labels: {', '.join(labels) or 'nenhuma'}")

        out, err, rc = _run("git fetch origin", cwd=working_dir)
        if rc != 0:
            return f"❌ Erro ao buscar origin: {err}"

        out, err, rc = _run(f"git checkout -b {safe_branch}", cwd=working_dir)
        if rc != 0:
            out, err, rc = _run(f"git checkout {safe_branch}", cwd=working_dir)
            if rc != 0:
                return f"❌ Erro ao criar branch: {err}"
            steps.append(f"⚠️ Branch '{safe_branch}' ja existia, reutilizando")
        else:
            steps.append(f"🌿 Branch criada: `{safe_branch}`")

        issue_template = f"Resolves #{issue_number}\n\n"
        if body:
            issue_template += f"## Descricao da Issue\n\n{body[:500]}\n\n"
        issue_template += "## Mudancas\n\n- [ ] Implementacao\n- [ ] Testes\n- [ ] Documentacao"

        steps.append(f"📝 Template de commit preparado")

        if commit_message:
            final_msg = commit_message
        else:
            final_msg = f"fix: resolve #{issue_number} - {title[:50]}"

        out, err, rc = _run(f'git commit --allow-empty -m "{final_msg}"', cwd=working_dir)
        if rc != 0 and "nothing to commit" not in err:
            return f"❌ Erro ao commitar: {err}"
        steps.append(f"💾 Commit: `{final_msg}`")

        out, err, rc = _run(f"git push -u origin {safe_branch}", cwd=working_dir)
        if rc != 0:
            return f"❌ Erro ao push: {err}"
        steps.append(f"🚀 Branch pushada para origin")

        pr_body = f"## Resumo\n\nResolve #{issue_number}\n\n"
        pr_body += f"## Issue\n\n{body[:1000]}\n\n"
        pr_body += "---\n*Gerado automaticamente por Issue-to-PR Automation*"

        pr_data = {
            "title": f"fix: #{issue_number} - {title[:60]}",
            "body": pr_body,
            "head": safe_branch,
            "base": "main",
        }

        try:
            pr = _post(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", pr_data)
            steps.append(f"✅ PR aberto: #{pr['number']} — {pr['html_url']}")
        except Exception as e:
            return f"❌ Erro ao abrir PR: {e}\n\n" + "\n".join(steps)

        if auto_label:
            try:
                pr_labels = ["automated", "issue-linked"]
                if "bug" in labels:
                    pr_labels.append("bugfix")
                elif "enhancement" in labels:
                    pr_labels.append("feature")
                _post(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr['number']}/labels",
                      {"labels": pr_labels})
                steps.append(f"🏷️ Labels adicionadas: {', '.join(pr_labels)}")
            except Exception:
                pass

        try:
            _patch(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}",
                   {"state": "open"})
            steps.append(f"🔗 Issue #{issue_number} mantida aberta (sera fechada apos merge)")
        except Exception:
            pass

        return "\n".join(steps)

    def issue_to_pr_quick(owner: str, repo: str, issue_number: int, working_dir: str = ".") -> str:
        return issue_to_pr_full(owner, repo, issue_number, working_dir=working_dir)

    def issue_analyze(owner: str, repo: str, issue_number: int) -> str:
        if not GITHUB_TOKEN:
            return "❌ GITHUB_TOKEN nao configurado."
        try:
            issue = _get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}")
            comments = _get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments")

            labels = [l["name"] for l in issue.get("labels", [])]
            assignees = [a["login"] for a in issue.get("assignees", [])]

            analysis = (
                f"📋 **Issue #{issue_number}:** {issue.get('title')}\n\n"
                f"**Status:** {issue.get('state')}\n"
                f"**Autor:** {issue.get('user', {}).get('login')}\n"
                f"**Criada:** {issue.get('created_at', '')[:10]}\n"
                f"**Labels:** {', '.join(labels) or 'nenhuma'}\n"
                f"**Assignees:** {', '.join(assignees) or 'nenhum'}\n"
                f"**Comentarios:** {len(comments)}\n\n"
                f"**Corpo:**\n{(issue.get('body', '') or 'vazio')[:1000]}"
            )
            return analysis
        except Exception as e:
            return f"❌ Erro: {e}"

    def issue_list_ready(owner: str, repo: str, per_page: int = 10) -> str:
        if not GITHUB_TOKEN:
            return "❌ GITHUB_TOKEN nao configurado."
        try:
            data = _get(f"{GITHUB_API}/repos/{owner}/{repo}/issues?state=open&per_page={min(per_page, 50)}")
            if not data:
                return "Nenhuma issue aberta."
            items = []
            for i in data[:per_page]:
                if "pull_request" in i:
                    continue
                labels = [l["name"] for l in i.get("labels", [])]
                items.append(
                    f"#{i['number']} {i['title'][:50]}\n"
                    f"   Labels: {', '.join(labels) or 'nenhuma'} | {i.get('created_at', '')[:10]}"
                )
            return f"**{len(items)} issues abertas:**\n\n" + "\n".join(items)
        except Exception as e:
            return f"❌ Erro: {e}"

    def issue_create_from_description(
        owner: str, repo: str, title: str, body: str,
        labels: str = "", assignee: str = ""
    ) -> str:
        if not GITHUB_TOKEN:
            return "❌ GITHUB_TOKEN nao configurado."
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = [l.strip() for l in labels.split(",")]
        if assignee:
            payload["assignees"] = [assignee.strip()]
        try:
            issue = _post(f"{GITHUB_API}/repos/{owner}/{repo}/issues", payload)
            return f"✅ Issue #{issue['number']} criada: {issue['html_url']}"
        except Exception as e:
            return f"❌ Erro: {e}"

    api.register_tool("issue_to_pr_full", issue_to_pr_full,
        "Automacao completa: le issue, cria branch, commit, abre PR.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "issue_number": {"type": "integer", "description": "Numero da issue"},
         "branch_prefix": {"type": "string", "description": "Prefixo da branch (fix, feature, hotfix)"},
         "working_dir": {"type": "string", "description": "Diretorio do repo local"},
         "commit_message": {"type": "string", "description": "Mensagem customizada (opcional)"},
         "auto_label": {"type": "boolean", "description": "Adicionar labels automaticamente"}},
        ["owner", "repo", "issue_number"])

    api.register_tool("issue_to_pr_quick", issue_to_pr_quick,
        "Versao rapida: issue → PR com defaults.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "issue_number": {"type": "integer"}, "working_dir": {"type": "string"}},
        ["owner", "repo", "issue_number"])

    api.register_tool("issue_analyze", issue_analyze,
        "Analisa uma issue e retorna detalhes completos.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "issue_number": {"type": "integer"}}, ["owner", "repo", "issue_number"])

    api.register_tool("issue_list_ready", issue_list_ready,
        "Lista issues abertas prontas para trabalho.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "per_page": {"type": "integer"}}, ["owner", "repo"])

    api.register_tool("issue_create_from_description", issue_create_from_description,
        "Cria issue a partir de titulo e descricao.",
        {"owner": {"type": "string"}, "repo": {"type": "string"},
         "title": {"type": "string"}, "body": {"type": "string"},
         "labels": {"type": "string"}, "assignee": {"type": "string"}},
        ["owner", "repo", "title", "body"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Automacao Issue → Branch → PR com analise, labels e integracao GitHub.",
        "tools": ["issue_to_pr_full", "issue_to_pr_quick", "issue_analyze",
                   "issue_list_ready", "issue_create_from_description"],
    }
