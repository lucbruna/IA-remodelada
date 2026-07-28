"""
plugin_project_config.py
========================
Configuracao por projeto — .cursorrules equivalent.

Funcionalidades:
  - Definir instrucoes customizadas por projeto
  - Configuracoes de estilo, convencoes, patterns
  - Carregar automaticamente ao iniciar sessao
  - Validar codigo contra regras do projeto
  - Exportar/importar configuracoes
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Project Config"

import os
import json
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE = ".ia_project_config.json"
CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "project_configs")


def _find_project_root() -> str:
    current = os.getcwd()
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, CONFIG_FILE)):
            return current
        if os.path.exists(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    return os.getcwd()


def _load_config(project_root: str = "") -> dict:
    root = project_root or _find_project_root()
    config_path = os.path.join(root, CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_config(config: dict, project_root: str = ""):
    root = project_root or _find_project_root()
    config_path = os.path.join(root, CONFIG_FILE)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def register(api):

    def project_config_init(project_name: str = "", root_dir: str = "") -> str:
        root = root_dir or _find_project_root()
        existing = _load_config(root)
        if existing:
            return f"⚠️ Config already exists at {root}. Use project_config_update to modify."
        config = {
            "project_name": project_name or os.path.basename(root),
            "language": "python",
            "style": {
                "indent": 4,
                "line_length": 120,
                "naming_convention": "snake_case",
                "docstring_style": "google",
            },
            "instructions": [
                "Write clean, readable code",
                "Add docstrings to all public functions",
                "Use type hints where possible",
                "Follow PEP 8 style guide",
            ],
            "forbidden_patterns": [
                "eval()",
                "exec()",
                "os.system()",
                "shell=True",
            ],
            "required_patterns": [
                "def .* -> ",  # return type hints
            ],
            "ignore_files": [
                "*.pyc",
                "__pycache__",
                ".git",
                "node_modules",
            ],
            "custom_rules": {},
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        _save_config(config, root)
        return f"✅ Project config created at {root}"

    def project_config_get(root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No project config found. Use project_config_init first."
        lines = [
            f"📋 **Project Config: {config.get('project_name', 'unnamed')}**",
            f"Language: {config.get('language', '?')}",
            f"\n**Style:**",
            f"  Indent: {config.get('style', {}).get('indent', 4)}",
            f"  Line length: {config.get('style', {}).get('line_length', 120)}",
            f"  Naming: {config.get('style', {}).get('naming_convention', '?')}",
            f"\n**Instructions:**",
        ]
        for inst in config.get("instructions", []):
            lines.append(f"  • {inst}")
        forbidden = config.get("forbidden_patterns", [])
        if forbidden:
            lines.append(f"\n**Forbidden:** {', '.join(forbidden)}")
        return "\n".join(lines)

    def project_config_update(key: str, value: str, root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No config found. Use project_config_init first."
        keys = key.split(".")
        target = config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        try:
            target[keys[-1]] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            target[keys[-1]] = value
        _save_config(config, root_dir)
        return f"✅ Updated '{key}' = {value}"

    def project_config_add_instruction(instruction: str, root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No config found. Use project_config_init first."
        if "instructions" not in config:
            config["instructions"] = []
        config["instructions"].append(instruction)
        _save_config(config, root_dir)
        return f"✅ Instruction added: {instruction}"

    def project_config_add_forbidden(pattern: str, root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No config found. Use project_config_init first."
        if "forbidden_patterns" not in config:
            config["forbidden_patterns"] = []
        if pattern not in config["forbidden_patterns"]:
            config["forbidden_patterns"].append(pattern)
        _save_config(config, root_dir)
        return f"✅ Forbidden pattern added: {pattern}"

    def project_config_validate(file_path: str, root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No config found."
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        issues = []
        for pattern in config.get("forbidden_patterns", []):
            import re
            matches = re.findall(pattern, content)
            if matches:
                issues.append(f"  ⚠️ Forbidden pattern found: {pattern} ({len(matches)} times)")
        for pattern in config.get("required_patterns", []):
            import re
            if not re.search(pattern, content):
                issues.append(f"  ⚠️ Missing required pattern: {pattern}")
        line_length = config.get("style", {}).get("line_length", 120)
        for i, line in enumerate(content.split("\n"), 1):
            if len(line) > line_length:
                issues.append(f"  ⚠️ Line {i} exceeds {line_length} chars ({len(line)})")
                if len(issues) > 10:
                    issues.append("  ... (truncated)")
                    break
        if not issues:
            return f"✅ {file_path} passes all project rules."
        return f"**Issues in {file_path}:**\n" + "\n".join(issues)

    def project_config_export(root_dir: str = "") -> str:
        config = _load_config(root_dir)
        if not config:
            return "No config found."
        return json.dumps(config, indent=2, ensure_ascii=False)

    def project_config_import(json_data: str, root_dir: str = "") -> str:
        try:
            config = json.loads(json_data)
            _save_config(config, root_dir)
            return f"✅ Config imported for project: {config.get('project_name', '?')}"
        except Exception as e:
            return f"❌ Import failed: {e}"

    def project_config_list_all() -> str:
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        files = [f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")]
        if not files:
            return "No saved project configs."
        lines = ["📋 **Saved Project Configs:**\n"]
        for f in sorted(files):
            name = f.replace(".json", "")
            lines.append(f"  • {name}")
        return "\n".join(lines)

    def project_config_load_template(template: str, root_dir: str = "") -> str:
        templates = {
            "python": {
                "language": "python",
                "style": {"indent": 4, "line_length": 88, "naming_convention": "snake_case", "docstring_style": "google"},
                "instructions": ["Follow PEP 8", "Use black formatter", "Add type hints", "Use f-strings"],
                "forbidden_patterns": ["eval()", "exec()", "os.system()", "shell=True"],
                "required_patterns": ["def .* -> "],
            },
            "javascript": {
                "language": "javascript",
                "style": {"indent": 2, "line_length": 100, "naming_convention": "camelCase"},
                "instructions": ["Use ESLint rules", "Prefer const", "Use template literals", "Add JSDoc"],
                "forbidden_patterns": ["eval(", "with("],
                "required_patterns": [],
            },
            "typescript": {
                "language": "typescript",
                "style": {"indent": 2, "line_length": 100, "naming_convention": "camelCase"},
                "instructions": ["Use strict mode", "Prefer interfaces", "Use readonly", "Add return types"],
                "forbidden_patterns": ["eval(", "any"],
                "required_patterns": [": (string|number|boolean|void|Promise)"],
            },
        }
        if template not in templates:
            return f"❌ Template '{template}' not found. Options: {', '.join(templates.keys())}"
        config = templates[template].copy()
        config["project_name"] = os.path.basename(_find_project_root())
        _save_config(config, root_dir)
        return f"✅ Template '{template}' applied."

    api.register_tool("project_config_init", project_config_init,
        "Initialize project config.",
        {"project_name": {"type": "string"}, "root_dir": {"type": "string"}}, [])

    api.register_tool("project_config_get", project_config_get,
        "Get current project config.",
        {"root_dir": {"type": "string"}}, [])

    api.register_tool("project_config_update", project_config_update,
        "Update a config value (dot notation).",
        {"key": {"type": "string"}, "value": {"type": "string"},
         "root_dir": {"type": "string"}}, ["key", "value"])

    api.register_tool("project_config_add_instruction", project_config_add_instruction,
        "Add custom instruction.",
        {"instruction": {"type": "string"}, "root_dir": {"type": "string"}}, ["instruction"])

    api.register_tool("project_config_add_forbidden", project_config_add_forbidden,
        "Add forbidden pattern.",
        {"pattern": {"type": "string"}, "root_dir": {"type": "string"}}, ["pattern"])

    api.register_tool("project_config_validate", project_config_validate,
        "Validate file against project rules.",
        {"file_path": {"type": "string"}, "root_dir": {"type": "string"}}, ["file_path"])

    api.register_tool("project_config_export", project_config_export,
        "Export config as JSON.",
        {"root_dir": {"type": "string"}}, [])

    api.register_tool("project_config_import", project_config_import,
        "Import config from JSON.",
        {"json_data": {"type": "string"}, "root_dir": {"type": "string"}}, ["json_data"])

    api.register_tool("project_config_list_all", project_config_list_all,
        "List all saved project configs.", {}, [])

    api.register_tool("project_config_load_template", project_config_load_template,
        "Load a config template (python, javascript, typescript).",
        {"template": {"type": "string"}, "root_dir": {"type": "string"}}, ["template"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Project config: custom instructions, style rules, forbidden patterns, validation.",
        "tools": ["project_config_init", "project_config_get", "project_config_update",
                   "project_config_add_instruction", "project_config_add_forbidden",
                   "project_config_validate", "project_config_export", "project_config_import",
                   "project_config_list_all", "project_config_load_template"],
    }
