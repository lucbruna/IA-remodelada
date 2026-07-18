"""
plugins/
=========
Pacote de plugins extensíveis para o Agente Local.

Cada arquivo .py nesta pasta pode definir um plugin que o agente
carrega automaticamente na inicializacao. Basta que o modulo
exporte uma funcao `register(api)`.

Exemplo minimo:
    def register(api):
        def minha_funcao(texto: str) -> str:
            return f"Plugin processou: {texto}"

        api.register_tool(
            name="minha_ferramenta",
            func=minha_funcao,
            description="Processa um texto qualquer",
            parameters={
                "texto": {"type": "string", "description": "Texto a processar"}
            },
            required=["texto"],
        )
"""

import os

PLUGINS_DIR = os.path.dirname(os.path.abspath(__file__))
