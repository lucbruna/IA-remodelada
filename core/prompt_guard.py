from ._common import *
import re
import threading

# =======================================================================
# PROMPT GUARD - defesa contra prompt injection / tool poisoning
# -----------------------------------------------------------------------
# Adaptado do padrao advanced_security do projeto AGENTE_IA (OWASP 2026):
# detecta injecao direta (na entrada do usuario) e indireta (na saida de
# ferramentas/arquivos), sandbox escape e tentativas de vazamento de prompt.
# Pode ser plugado no inicio do turno e apos cada tool call para bloquear
# ou sinalizar ameacas. Silencioso em falhas.
# =======================================================================

_BLOCK_PATTERNS = [
    # EN patterns
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+",
    r"new\s+instructions",
    r"override\s+(all\s+)?safety",
    r"bypass\s+(all\s+)?security",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"do\s+not\s+blow\s+your\s+cover",
    r"undercover\s+mode",
    r"pretend\s+you\s+are",
    r"act\s+as\s+if",
    r"roleplay\s+as",
    r"simulate\s+being",
    r"from\s+now\s+on\s+you\s+are",
    r"disregard\s+(all\s+)?(previous|prior|earlier)",
    r"forget\s+(all\s+)?(previous|prior|earlier)\s+(instructions|rules|constraints)",
    r"new\s+role\s*:",
    r"system\s*prompt\s*override",
    r"developer\s+mode",
    r"jailbreak",
    r"\bdan\b.*mode",
    r"do\s+anything\s+now",
    # PT patterns
    r"ignore\s+(todas\s+)?(as\s+)?instru[cç][oõ]es\s+anteriores",
    r"ignore\s+as\s+instru[cç][oõ]es",
    r"voce\s+agora\s+e",
    r"voce\s+agora\s+e\s+um",
    r"nova\s+instru[cç][a\~o]",
    r"novas\s+instru[cç][oõ]es",
    r"ignore\s+regras",
    r"ignore\s+seguran[cç]a",
    r"ignore\s+todas\s+as\s+regras",
    r"seja\s+agora",
    r"a partir\s+de\s+agora\s+voce",
    r"esqueca\s+(todas\s+)?(as\s+)?instru[cç][oõ]es",
    r"n[a\~o]\s+sigas\s+as\s+regras",
    r"modo\s+desenvolvedor",
    r"modo\s+developer",
    r"modo\s+dan",
    r"modo\s+desbloqueado",
    r"fa[cç]\s+o\s+que\s+quiser",
]

_INJECTION_INDICATORS = [
    (r"ignore\s+all", "HIGH"),
    (r"you\s+are\s+now", "HIGH"),
    (r"new\s+instructions", "HIGH"),
    (r"system\s*:", "MEDIUM"),
    (r"human\s*:", "MEDIUM"),
    (r"assistant\s*:", "MEDIUM"),
    (r"<\|.*?\|>", "HIGH"),
    (r"\[INST\]", "HIGH"),
    (r"<<SYS>>", "HIGH"),
    (r"<\|im_start\|>", "HIGH"),
    (r"<\|im_end\|>", "HIGH"),
    (r"###\s+(System|Human|Assistant)\s*:", "HIGH"),
    (r"```\s*(system|human|assistant)", "HIGH"),
    (r"voce\s+agora", "HIGH"),
    (r"ignore\s+(as\s+)?regras", "HIGH"),
    (r"ignore\s+(as\s+)?instru", "HIGH"),
    (r"esqueca\s+tudo", "HIGH"),
    # Unicode confusables
    (r"[\u200b\u200c\u200d\ufeff]", "LOW"),
    # Base64 encoded instructions
    (r"[A-Za-z0-9+/]{40,}={0,2}", "LOW"),
]

_INDIRECT_PATTERNS = [
    (r"system\s*:\s*transfer", "CRITICAL"),
    (r"system\s*:\s*delete", "CRITICAL"),
    (r"system\s*:\s*execute", "CRITICAL"),
    (r"<script>", "HIGH"),
    (r"javascript:", "HIGH"),
    (r"data:text/html", "HIGH"),
    (r"eval\s*\(", "HIGH"),
    (r"exec\s*\(", "HIGH"),
    (r"__import__", "HIGH"),
    (r"subprocess", "MEDIUM"),
    (r"os\.system", "MEDIUM"),
]

_LEVEL_RANK = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _max(a, b):
    """Retorna o nivel de maior severidade entre a e b."""
    return a if _LEVEL_RANK.get(a, 0) >= _LEVEL_RANK.get(b, 0) else b


_guard_events = []
_guard_lock = threading.Lock()
MAX_INPUT_LENGTH = PROMPT_GUARD_MAX_INPUT


def prompt_guard_scan_input(text: str, source: str = "user") -> tuple:
    """Escaneia a entrada do usuario em busca de prompt injection.

    Retorna (nivel: str, ameacas: list). Bloqueia (HIGH/CRITICAL) quando
    padroes claros de injecao sao encontrados.
    """
    text = text or ""
    threats = []
    max_level = "NONE"
    if len(text) > MAX_INPUT_LENGTH:
        threats.append(f"Input excede tamanho maximo ({len(text)} > {MAX_INPUT_LENGTH})")
        max_level = _max(max_level, "MEDIUM")
    tl = text.lower()
    for p in _BLOCK_PATTERNS:
        if re.search(p, tl):
            threats.append(f"Padrao de injecao: {p}")
            max_level = _max(max_level, "HIGH")
    for p, lvl in _INJECTION_INDICATORS:
        if re.search(p, tl):
            threats.append(f"Indicador de injecao: {p}")
            max_level = _max(max_level, lvl)
    if threats:
        _record("injection_attempt", max_level, source, text[:500], threats)
    return max_level, threats


def prompt_guard_scan_tool_output(output: str, tool_name: str) -> tuple:
    """Escaneia a saida de uma ferramenta em busca de injecao indireta.

    Ferramentas que leem arquivos/web podem trazer conteudo malicioso que
    tenta comandar o agente. Retorna (nivel, ameacas).
    """
    output = output or ""
    threats = []
    max_level = "NONE"
    ol = output.lower()
    for p, lvl in _INDIRECT_PATTERNS:
        if re.search(p, ol):
            threats.append(f"Injecao indireta em {tool_name}: {p}")
            max_level = _max(max_level, lvl)
    if threats:
        _record("indirect_injection", max_level, tool_name, output[:500], threats)
    return max_level, threats


def prompt_guard_should_block(level: str) -> bool:
    """Retorna True se o nivel e alto o bastante para bloquear a acao."""
    return _LEVEL_RANK.get(level, 0) >= _LEVEL_RANK["HIGH"]


def prompt_guard_report() -> str:
    """Retorna um relatorio das ameacas detectadas nesta sessao."""
    with _guard_lock:
        if not _guard_events:
            return "Nenhuma ameaca de prompt injection detectada nesta sessao."
        linhas = [f"{e['ts']} [{e['level']}] {e['type']} de {e['source']}: "
                  f"{'; '.join(e['threats'][:3])}" for e in _guard_events[-20:]]
        return "Prompt Guard — ameacas detectadas:\n" + "\n".join(linhas)


def _record(etype, level, source, payload, threats):
    with _guard_lock:
        _guard_events.append({
            "ts": datetime.now().isoformat(), "type": etype, "level": level,
            "source": source, "payload": payload, "threats": threats,
        })
