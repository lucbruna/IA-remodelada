# =============================================================================
# Makefile — IA Remodelada
# Comandos padronizados para desenvolvimento e execução.
# =============================================================================

PYTHON ?= python
PIP    ?= pip

.PHONY: help install install-dev test test-core lint run-cli run-gui run-api clean

help:  ## Exibe esta ajuda
	@echo "Comandos disponíveis:"
	@sed -n 's/^\([a-zA-Z0-9_-]*\):.*##\(.*\)/  \1  \2/p' $(MAKEFILE_LIST)

install:  ## Instala dependências básicas
	$(PIP) install -r requirements.txt

install-dev:  ## Instala dependências de desenvolvimento (testes, lint)
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-timeout pytest-asyncio flake8 bandit

test:  ## Roda todos os testes
	$(PYTHON) -m pytest tests/ -q

test-core:  ## Roda apenas os testes do núcleo
	$(PYTHON) -m pytest tests/test_agente_core.py -q

lint:  ## Verifica sintaxe (erros críticos) e estilo
	$(PYTHON) -m py_compile agente_core.py core/*.py agente_cli.py agente_gui.py agente_api_server.py agente_turbo.py orquestrador_mestre.py
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

run-cli:  ## Inicia o agente no terminal
	$(PYTHON) agente_cli.py

run-gui:  ## Inicia o agente com interface gráfica (Tkinter)
	$(PYTHON) agente_gui.py

run-api:  ## Inicia o servidor de API (http://localhost:8000)
	$(PYTHON) agente_api_server.py

clean:  ## Remove caches e artefatos de teste
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
	@echo "Limpeza concluída."
