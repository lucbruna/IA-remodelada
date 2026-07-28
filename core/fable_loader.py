import os
from config import BASE_DIR

FABLE_SKILLS = {
    "method": os.path.join(BASE_DIR, ".agents", "fable-method", "SKILL.md"),
    "loop": os.path.join(BASE_DIR, ".agents", "fable-loop", "SKILL.md"),
    "judge": os.path.join(BASE_DIR, ".agents", "fable-judge", "SKILL.md"),
    "domain": os.path.join(BASE_DIR, ".agents", "fable-domain", "SKILL.md"),
    "agents": os.path.join(BASE_DIR, "AGENTS.md"),
    "failure_modes": os.path.join(BASE_DIR, ".agents", "fable-method", "references", "failure-modes.md"),
    "examples": os.path.join(BASE_DIR, ".agents", "fable-method", "references", "examples.md"),
}

FABLE_ALIASES = {
    "metodo": "method",
    "method": "method",
    "loop": "loop",
    "juiz": "judge",
    "judge": "judge",
    "dominio": "domain",
    "domain": "domain",
    "agentes": "agents",
    "modos_falha": "failure_modes",
    "exemplos": "examples",
}

def fable_method_load(skill: str = "method") -> str:
    try:
        key = FABLE_ALIASES.get(skill.strip().lower(), skill.strip().lower())
        path = FABLE_SKILLS.get(key)
        if not path:
            disponiveis = ", ".join(sorted(set(FABLE_ALIASES.keys())))
            return f"Skill '{skill}' nao encontrada. Disponiveis: {disponiveis}"
        if not os.path.exists(path):
            return f"Arquivo nao encontrado: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"--- {key} ---\n{content}"
    except Exception as e:
        return f"Erro ao carregar skill Fable: {e}"
