from ._common import *

# =======================================================================
# HOOKS - eventos configuraveis (padrao 'hooks' do oh-my-pi)
# -----------------------------------------------------------------------
# Permite registrar callbacks em pontos do ciclo do agente (tool_call,
# session_start, turn_end, error). Integra com observabilidade e qualquer
# plugin. Hooks sao funcoes (evento, contexto) -> None silenciosas.
# =======================================================================

_HOOKS = {}  # evento -> lista de funcoes


def hook_register(event: str, fn) -> str:
    """Registra uma funcao como hook para um evento.

    Eventos: 'tool_call', 'tool_result', 'turn_start', 'turn_end',
    'error', 'learn'. A funcao recebe (evento, contexto_dict).
    """
    event = (event or "").strip()
    if not event:
        return "Informe o evento."
    _HOOKS.setdefault(event, []).append(fn)
    return f"Hook registrado para '{event}' ({len(_HOOKS[event])} no total)."


def hook_emit(event: str, context: dict = None) -> None:
    """Dispara todos os hooks de um evento. Silencioso em falhas."""
    for fn in _HOOKS.get(event, []):
        try:
            fn(event, context or {})
        except Exception as e:
            logging.warning("hook '%s' falhou: %s", event, e)


def hook_list() -> list:
    """Retorna os eventos registrados e quantos hooks cada um tem."""
    return [{"event": e, "count": len(fns)} for e, fns in _HOOKS.items()]


# Hook padrao: alimenta a observabilidade sempre que uma ferramenta roda.
def _observabilidade_hook(event: str, ctx: dict) -> None:
    try:
        from plugins.plugin_observabilidade import registrar_trace
        nome = ctx.get("name", event)
        sucesso = ctx.get("success", True)
        dur = ctx.get("duration_ms", 0)
        detalhes = str(ctx.get("detail", ""))[:500]
        registrar_trace("hook:" + event, nome, sucesso, dur, detalhes)
    except Exception:
        pass


# Registrado automaticamente ao importar o modulo.
hook_register("tool_call", _observabilidade_hook)
hook_register("error", _observabilidade_hook)
