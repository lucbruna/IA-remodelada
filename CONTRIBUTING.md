# Contribuindo para IA Remodelada

Obrigado por contribuir! Este guia explica como configurar o ambiente e submeter mudancas.

## Setup de Desenvolvimento

```bash
# 1. Clone o repositorio
git clone <repo-url>
cd IA-remodelada

# 2. Crie ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instale dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # se existir

# 4. Instale Ollama e modelos
ollama pull qwen2.5:7b
ollama pull llava

# 5. Copie .env.example para .env
cp .env.example .env

# 6. Rode os testes
python -m pytest tests/ -v
```

## Estrutura do Projeto

```
core/           # Modulos core (logica principal)
plugins/        # Plugins (carregados automaticamente)
tests/          # Testes
agente_*.py     # Interfaces (CLI, GUI, API, etc)
config.py       # Configuracao centralizada
```

## Regras de Codigo

1. **Python 3.11+** — use features modernas (match, type hints, walrus operator)
2. **Sem comentarios obvios** — o codigo deve falar por si
3. **Docstrings** — toda funcao publica deve ter docstring curta
4. **Imports explicitos** — evite `from X import *` em novos codigos
5. **Tratamento de erros** — nunca use `except Exception: pass` silencioso; logge o erro
6. **Testes** — toda funcao nova deve ter ao menos 1 teste

## Criando um Plugin

Plugins ficam em `plugins/` e sao carregados automaticamente:

```python
# plugins/plugin_exemplo.py

def minha_ferramenta(parametro: str) -> str:
    """Description curta (aparece no system prompt)."""
    return f"Resultado: {parametro}"

# Registra no carregamento automatico
TOOLS = [{
    "type": "function",
    "function": {
        "name": "minha_ferramenta",
        "description": "Description curta da ferramenta",
        "parameters": {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Descricao do parametro"
                }
            },
            "required": ["parametro"]
        }
    }
}]

FUNCTIONS = {"minha_ferramenta": minha_ferramenta}
```

## Submetendo Mudancas

1. Crie uma branch (`git checkout -b feature/nome`)
2. Faca suas alteracoes
3. Rode os testes (`pytest tests/ -v`)
4. Commit com mensagem descritiva
5. Abra um Pull Request

### Formato de Commit

```
tipo(modulo): descricao curta

- detalhe 1
- detalhe 2
```

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Areas de Melhoria

Priorizadas por impacto:

1. **Seguranca** — prompt guard, sandbox, auth
2. **Testes** — cobertura > 80%
3. **Performance** — cache, async, compactacao
4. **Documentacao** — API docs, guias
5. **UX** — CLI autocomplete, feedback

## Duvidas?

Abra uma issue com a tag `question`.
