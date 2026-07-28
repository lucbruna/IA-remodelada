# IA Remodelada

Agente local inteligente com suporte a plugins, turbo mode, ensemble de modelos, RAG, sandbox Docker, e mais de 50 plugins para processamento de codigo, imagens, documentos, redes, backup e automacao.

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.ai) com modelo `qwen2.5:7b` (padrao, definido em `config.py`) e `llava` para visao
- Git (para clonagem de repositorios)
- Docker Desktop (necessario para execucao isolada em sandbox)

> O modelo padrao e centralizado em [`config.py`](config.py) e pode ser
> sobrescrito por variaveis de ambiente ou arquivo `.env` (veja
> `.env.example`). Nao altere o modelo diretamente nos modulos.

## Instalacao

```bash
pip install -r requirements.txt
ollama pull qwen2.5:7b
ollama pull llava  # para visao
```

## Uso

```bash
python agente_cli.py          # Interface de linha de comando
python agente_gui.py          # Interface grafica (Tkinter)
python agente_streamlit.py    # Interface Streamlit
python agente_api_server.py   # Servidor REST API (FastAPI)
python agente_dashboard.py    # Dashboard Rich
```

## Seguranca da API

O servidor API suporta autenticacao por API key e rate limiting:

```bash
# Configurar no .env:
AGENTE_API_KEY=sua_chave_secreta
AGENTE_RATE_LIMIT=60        # max requests/min por IP
AGENTE_RATE_LIMIT_WINDOW=60 # janela em segundos
```

Uso:
```bash
# Via header X-API-Key:
curl -H "X-API-Key: sua_chave" http://localhost:8000/chat -d '{"message":"Ola"}'

# Via Authorization Bearer:
curl -H "Authorization: Bearer sua_chave" http://localhost:8000/chat
```

Endpoints publicos (sem auth): `/`, `/docs`, `/redoc`, `/health`, `/system/status`

## Endpoints Principais

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/chat` | POST | Envia mensagem e obtem resposta |
| `/chat/stream` | POST | Streaming via SSE |
| `/health` | GET | Health check para load balancers |
| `/models` | GET | Lista modelos Ollama disponiveis |
| `/conversations` | GET/POST | Gerencia conversas |
| `/memory` | GET/POST | Memoria de longo prazo |
| `/plugins` | GET | Lista plugins carregados |
| `/sandbox/*` | GET/POST | Sandbox Docker |
| `/metrics` | GET | Metricas Prometheus |
| `/traces` | GET | Traces de execucao |

## Plugins

O sistema carrega automaticamente plugins do diretorio `plugins/`. Sao mais de 70 plugins cobrindo:

- Download e scraping web
- Processamento de imagens (OCR, redimensionamento, filtros)
- Analise e geracao de codigo
- Banco de dados SQLite
- Documentos (DOCX, XLSX, CSV)
- Visualizacao de dados (graficos matplotlib)
- Seguranca (hash, criptografia, varredura)
- Audio (conversao, metadados)
- Rede (ping, DNS, port scan, WHOIS)
- Backup e restauracao
- Sandbox Docker (execucao isolada)
- RAG (busca semantica com ChromaDB)
- MCP (Model Context Protocol)
- Playwright (navegacao web)
- **Firecrawl** (web scraping avancado: busca, crawl, interacao com paginas)
- **Mem0** (camada de memoria universal: entity linking, temporal reasoning)
- **GitHub Integration** (repos, issues, PRs, busca de codigo)
- **Brave Search** (busca web via API)
- **CrewAI** (orquestracao multi-agente)
- **Slack/Teams/Discord Bot** (notificacoes e comandos)
- **Issue-to-PR Automation** (issue → branch → PR automatico)
- **AI Code Review** (revisao rapida de codigo)
- **Background Agents** (agentes em background com monitoramento)
- **Kanban Command Center** (gestao visual de tarefas)
- **Side-by-Side Model Evals** (comparacao de modelos)
- **Diff Preview System** (preview de mudancas antes de aplicar)
- **Visual Debugger** (breakpoints, step-through, variaveis)
- **Semantic Code Search** (busca por significado no codebase)
- **Auto Deploy** (Docker, Kubernetes, cloud deploy)
- **Prompt Hub** (versionamento de prompts)
- **A/B Testing** (experimentos entre modelos)
- **Multi-File Refactor** (refatoracao coordenada)
- **Project Config** (configuracao customizada por projeto)
- E muitos mais...

## Turbo Mode

O modulo `agente_turbo.py` adiciona inteligencia avancada:

- Chain-of-thought reasoning
- Task decomposition
- Code review automatico
- Error recovery
- Cache semantico de respostas
- Smart context compression
- Execucao paralela de tool calls

## Skills (Agentes de Formatacao)

O projeto inclui skills para formatacao de saida:

- **i-have-adhd**: Formatacao ADHD-friendly com bullets, emojis e estrutura visual clara

## Arquitetura

```
agente_core.py          # Facade de compatibilidade (reexporta core/)
agente_api_server.py    # Servidor REST API (FastAPI)
agente_cli.py           # Interface CLI
agente_gui.py           # Interface Tkinter
agente_streamlit.py     # Interface Streamlit
agente_turbo.py         # Modulo de inteligencia avancada

core/                   # Modulos core
  _common.py            # Imports e constantes compartilhadas
  agent_loop.py         # Loop principal do agente
  llm.py                # Comunicacao com Ollama
  memory.py             # Memoria persistente (JSON/SQLite)
  history_db.py         # Historico em SQLite (novo)
  compact.py            # Compactacao de contexto (tokens)
  prompt_guard.py       # Defesa contra prompt injection
  security.py           # Criptografia e cofre de senhas
  api_security.py       # Auth + rate limiting (novo)
  autonomy.py           # Roteamento inteligente
  hindsight.py          # Memoria duradoura
  hooks.py              # Sistema de eventos
  registry.py           # Registro de ferramentas
  memory_pipeline.py    # Pipeline de memoria evolutiva

plugins/                # 72+ plugins
  plugin_firecrawl.py   # Web scraping avancado (Firecrawl)
  plugin_mem0.py        # Memoria universal (Mem0)
  plugin_github.py      # GitHub API (repos, issues, PRs, busca)
  plugin_playwright.py  # Browser automation (Playwright)
  plugin_brave_search.py # Busca web via Brave Search API
  plugin_crewai.py      # Orquestracao multi-agente (CrewAI)
  plugin_slack.py       # Slack/Teams/Discord integration
  plugin_issue_to_pr.py # Issue → PR automation
  plugin_code_review.py # AI code review
  plugin_background_agents.py # Background agents
  plugin_kanban.py      # Command center Kanban
  plugin_model_evals.py # Side-by-side model evals
  plugin_diff_preview.py # Diff preview system
  plugin_debugger.py    # Visual debugger
  plugin_code_search.py # Semantic code search
  plugin_auto_deploy.py # Docker/K8s deploy
  plugin_prompt_hub.py  # Prompt versioning
  plugin_ab_testing.py  # A/B testing
  plugin_multi_file_refactor.py # Multi-file refactor
  plugin_project_config.py # Project config per project
tests/                  # Testes unitarios e integracao
```

## Qualidade

```bash
# Testes
python -m pytest tests/ -v

# Seguranca (prompt guard + API auth)
python -m pytest tests/test_security.py -v

# Integracao (SQLite + compact + agent loop)
python -m pytest tests/test_integration.py -v

# Lint
flake8 . --max-line-length=120

# Security scan
bandit -r core/ plugins/ -ll
```

## Variaveis de Ambiente

Veja `.env.example` para todas as opcoes disponiveis. Principais:

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `AGENTE_MODEL` | `qwen2.5:7b` | Modelo principal |
| `AGENTE_VISION_MODEL` | `llava` | Modelo de visao |
| `AGENTE_NUM_CTX` | `16384` | Tamanho do contexto |
| `AGENTE_TEMPERATURE` | `0.5` | Temperatura |
| `AGENTE_TIMEOUT` | `300` | Timeout do Ollama (s) |
| `AGENTE_MAX_TOOL_ROUNDS` | `15` | Max rounds de ferramentas |
| `AGENTE_API_KEY` | (vazio) | API key (vazio = sem auth) |
| `AGENTE_RATE_LIMIT` | `60` | Max req/min por IP |
| `AGENTE_HOST` | `0.0.0.0` | Host do servidor |
| `AGENTE_PORT` | `8000` | Porta do servidor |
| `FIRECRAWL_API_KEY` | (vazio) | API key do Firecrawl cloud |
| `FIRECRAWL_URL` | `https://api.firecrawl.dev` | URL do Firecrawl (self-hosted ou cloud) |
| `MEM0_API_KEY` | (vazio) | API key do Mem0 cloud |
| `MEM0_URL` | (vazio) | URL do Mem0 self-hosted |
| `MEM0_USER_ID` | `default_user` | ID padrao do usuario para memorias |
| `GITHUB_TOKEN` | (vazio) | GitHub Personal Access Token |
| `BRAVE_API_KEY` | (vazio) | Brave Search API key (2000 queries/mes gratis) |
