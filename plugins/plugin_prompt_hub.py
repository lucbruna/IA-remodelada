"""
plugin_prompt_hub.py
====================
Versionamento e gestao de prompts — como Git para prompts.

Funcionalidades:
  - Criar, listar, versionar prompts
  - Tags (dev, staging, prod)
  - Diffs entre versoes
  - Deploy de prompts por ambiente
  - Historico de mudancas
  - Templates compartilhaveis
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Prompt Hub"

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "prompt_hub")
PROMPTS_DIR = os.path.join(DATA_DIR, "prompts")


def _ensure_dirs():
    os.makedirs(PROMPTS_DIR, exist_ok=True)


def _prompt_path(name: str) -> str:
    safe = name.replace("/", "_").replace("\\", "_").replace("..", "_")
    return os.path.join(PROMPTS_DIR, f"{safe}.json")


def _load_prompt(name: str) -> dict:
    path = _prompt_path(name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_prompt(name: str, data: dict):
    _ensure_dirs()
    with open(_prompt_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register(api):

    def prompt_create(name: str, content: str, description: str = "", tags: str = "") -> str:
        now = datetime.now().isoformat()
        data = {
            "name": name,
            "description": description,
            "current": content,
            "versions": [{"content": content, "timestamp": now, "message": "Initial version", "author": "user"}],
            "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
            "deployments": {},
            "created_at": now,
            "updated_at": now,
        }
        _save_prompt(name, data)
        return f"✅ Prompt '{name}' created (v1)"

    def prompt_update(name: str, content: str, message: str = "") -> str:
        data = _load_prompt(name)
        if not data:
            return f"❌ Prompt '{name}' not found. Use prompt_create first."
        data["versions"].append({
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "message": message or f"Update v{len(data['versions']) + 1}",
            "author": "user",
        })
        data["current"] = content
        data["updated_at"] = datetime.now().isoformat()
        _save_prompt(name, data)
        return f"✅ Prompt '{name}' updated (v{len(data['versions'])})"

    def prompt_get(name: str, version: int = 0) -> str:
        data = _load_prompt(name)
        if not data:
            return f"❌ Prompt '{name}' not found."
        if version == 0:
            content = data.get("current", "")
            v_num = len(data.get("versions", []))
            return f"**{name}** (v{v_num}):\n\n{content}"
        versions = data.get("versions", [])
        if version < 1 or version > len(versions):
            return f"❌ Version {version} not found (1-{len(versions)})"
        v = versions[version - 1]
        return f"**{name}** (v{version}):\nTimestamp: {v['timestamp']}\nMessage: {v['message']}\n\n{v['content']}"

    def prompt_list() -> str:
        _ensure_dirs()
        files = [f for f in os.listdir(PROMPTS_DIR) if f.endswith(".json")]
        if not files:
            return "No prompts in hub."
        lines = ["📋 **Prompt Hub:**\n"]
        for f in sorted(files):
            name = f.replace(".json", "")
            data = _load_prompt(name)
            versions = len(data.get("versions", []))
            tags = ", ".join(data.get("tags", []))
            lines.append(f"  • {name} (v{versions}) — {tags or 'no tags'}")
        return "\n".join(lines)

    def prompt_delete(name: str) -> str:
        path = _prompt_path(name)
        if os.path.exists(path):
            os.remove(path)
            return f"🗑️ Prompt '{name}' deleted."
        return f"❌ Prompt '{name}' not found."

    def prompt_diff(name: str, v1: int, v2: int) -> str:
        data = _load_prompt(name)
        if not data:
            return f"❌ Prompt '{name}' not found."
        versions = data.get("versions", [])
        if v1 < 1 or v1 > len(versions) or v2 < 1 or v2 > len(versions):
            return f"❌ Invalid versions (1-{len(versions)})"
        c1 = versions[v1 - 1]["content"]
        c2 = versions[v2 - 1]["content"]
        lines1 = c1.split("\n")
        lines2 = c2.split("\n")
        diff_lines = []
        max_len = max(len(lines1), len(lines2))
        for i in range(max_len):
            l1 = lines1[i] if i < len(lines1) else ""
            l2 = lines2[i] if i < len(lines2) else ""
            if l1 != l2:
                diff_lines.append(f"  - {l1}")
                diff_lines.append(f"  + {l2}")
        if not diff_lines:
            return "No differences found."
        return f"**Diff v{v1} → v{v2}:**\n" + "\n".join(diff_lines[:30])

    def prompt_deploy(name: str, environment: str) -> str:
        data = _load_prompt(name)
        if not data:
            return f"❌ Prompt '{name}' not found."
        data["deployments"][environment] = {
            "version": len(data["versions"]),
            "content": data["current"],
            "deployed_at": datetime.now().isoformat(),
        }
        _save_prompt(name, data)
        return f"✅ Prompt '{name}' deployed to '{environment}' (v{len(data['versions'])})"

    def prompt_get_deployed(environment: str) -> str:
        _ensure_dirs()
        results = []
        for f in os.listdir(PROMPTS_DIR):
            if not f.endswith(".json"):
                continue
            name = f.replace(".json", "")
            data = _load_prompt(name)
            dep = data.get("deployments", {}).get(environment)
            if dep:
                results.append(f"  • {name} — v{dep['version']} ({dep['deployed_at'][:10]})")
        if not results:
            return f"No prompts deployed to '{environment}'."
        return f"**Deployed to '{environment}':**\n" + "\n".join(results)

    def prompt_export(name: str) -> str:
        data = _load_prompt(name)
        if not data:
            return f"❌ Prompt '{name}' not found."
        return json.dumps(data, indent=2, ensure_ascii=False)

    def prompt_import(json_data: str) -> str:
        try:
            data = json.loads(json_data)
            name = data.get("name", "imported")
            _save_prompt(name, data)
            return f"✅ Prompt '{name}' imported ({len(data.get('versions', []))} versions)"
        except Exception as e:
            return f"❌ Import failed: {e}"

    def prompt_stats() -> str:
        _ensure_dirs()
        files = [f for f in os.listdir(PROMPTS_DIR) if f.endswith(".json")]
        total_versions = 0
        environments = set()
        for f in files:
            data = _load_prompt(f.replace(".json", ""))
            total_versions += len(data.get("versions", []))
            environments.update(data.get("deployments", {}).keys())
        return (
            f"📊 **Prompt Hub Stats:**\n"
            f"Total prompts: {len(files)}\n"
            f"Total versions: {total_versions}\n"
            f"Environments: {', '.join(environments) or 'none'}"
        )

    api.register_tool("prompt_create", prompt_create,
        "Create a new prompt in the hub.",
        {"name": {"type": "string"}, "content": {"type": "string"},
         "description": {"type": "string"}, "tags": {"type": "string"}}, ["name", "content"])

    api.register_tool("prompt_update", prompt_update,
        "Update prompt with new version.",
        {"name": {"type": "string"}, "content": {"type": "string"},
         "message": {"type": "string"}}, ["name", "content"])

    api.register_tool("prompt_get", prompt_get,
        "Get prompt content (current or specific version).",
        {"name": {"type": "string"}, "version": {"type": "integer"}}, ["name"])

    api.register_tool("prompt_list", prompt_list,
        "List all prompts in hub.", {}, [])

    api.register_tool("prompt_delete", prompt_delete,
        "Delete a prompt from hub.",
        {"name": {"type": "string"}}, ["name"])

    api.register_tool("prompt_diff", prompt_diff,
        "Show diff between two versions.",
        {"name": {"type": "string"}, "v1": {"type": "integer"},
         "v2": {"type": "integer"}}, ["name", "v1", "v2"])

    api.register_tool("prompt_deploy", prompt_deploy,
        "Deploy prompt to environment.",
        {"name": {"type": "string"}, "environment": {"type": "string"}}, ["name", "environment"])

    api.register_tool("prompt_get_deployed", prompt_get_deployed,
        "Get all prompts deployed to an environment.",
        {"environment": {"type": "string"}}, ["environment"])

    api.register_tool("prompt_export", prompt_export,
        "Export prompt as JSON.",
        {"name": {"type": "string"}}, ["name"])

    api.register_tool("prompt_import", prompt_import,
        "Import prompt from JSON.",
        {"json_data": {"type": "string"}}, ["json_data"])

    api.register_tool("prompt_stats", prompt_stats,
        "Get hub statistics.", {}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Prompt Hub: version control, tags, deploy, diff, import/export.",
        "tools": ["prompt_create", "prompt_update", "prompt_get", "prompt_list",
                   "prompt_delete", "prompt_diff", "prompt_deploy", "prompt_get_deployed",
                   "prompt_export", "prompt_import", "prompt_stats"],
    }
