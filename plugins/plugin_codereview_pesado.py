"""
plugin_codereview_pesado.py
===========================
Expoe codereview_pesado (core.codereview_heavy) como ferramenta carregavel.
Revisao de codigo PESADA: seguranca estatica (bandit-like) + revisao
semantica LLM + benchmark de performance + veredito unificado, numa so
chamada. Para codigo critico/nao-confiavel antes de producao.
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Code Review Pesado"


def register(api):
    try:
        from core.codereview_heavy import codereview_pesado
    except Exception as e:
        return {"name": PLUGIN_NAME, "version": __version__,
                "error": f"core.codereview_heavy indisponivel: {e}", "tools": []}
    api.register_tool(
        "codereview_pesado", codereview_pesado,
        "Revisao de codigo PESADA: auditoria estatica de seguranca (bandit-like) + "
        "revisao semantica LLM + benchmark de performance + veredito unificado. "
        "Use para codigo critico/nao-confiavel antes de producao.",
        {"code": "string", "linguagem": "string", "medir": "boolean"},
        ["code"],
    )
    return {"name": PLUGIN_NAME, "version": __version__,
            "description": "Code review pesado (seguranca + LLM + benchmark).",
            "tools": ["codereview_pesado"]}
