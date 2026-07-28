## Release v2.0.0 - Grande Atualizacao

Esta e a maior atualizacao do projeto IA Remodelada, com **189 arquivos alterados**, **43.000+ linhas adicionadas** e **50+ plugins novos**.

---

### Novidades Principais

#### Servidor API ChatGPT-like
- Streaming via Server-Sent Events (SSE)
- Upload de documentos
- Multi-conversas simultaneas
- Auth por API key + rate limiting
- Health check endpoint
- Auto-start do Ollama

#### Interface Web Responsiva
- `agente_web.html`: Interface completa estilo ChatGPT
- `agente_streamlit.py`: Interface Streamlit

#### 40+ Novos Plugins
- **Firecrawl**: Web scraping avancado
- **Mem0**: Camada de memoria universal
- **GitHub**: Repos, issues, PRs, busca de codigo
- **Playwright**: Browser automation
- **Brave Search**: Busca web via API
- **CrewAI**: Orquestracao multi-agente
- **Slack/Teams/Discord**: Notificacoes
- **Code Review**: Revisao rapida de codigo
- **Background Agents**: Agentes em background
- **Kanban**: Gestao visual de tarefas
- **Model Evals**: Comparacao de modelos
- **Diff Preview**: Preview de mudancas
- **Visual Debugger**: Breakpoints e step-through
- **Semantic Code Search**: Busca por significado
- **Auto Deploy**: Docker, Kubernetes, cloud
- **Prompt Hub**: Versionamento de prompts
- **A/B Testing**: Experimentos entre modelos
- **Multi-File Refactor**: Refatoracao coordenada
- **Project Config**: Configuracao customizada por projeto

#### Sandbox Docker
- Execucao isolada de codigo
- Resource limits (CPU, memoria)
- Configuracao por projeto

#### RAG (Retrieval-Augmented Generation)
- ChromaDB para busca semantica
- Qdrant como alternativa
- Indexacao de documentos
- Chunking automatico com overlap
- **Lazy initialization** para evitar bugs no Windows

#### Seguranca da API
- Autenticacao por API key
- Rate limiting por IP
- Headers X-API-Key ou Authorization Bearer

#### Docker
- Dockerfile para build da imagem
- docker-compose.yml para stack completa
- GitHub Actions para CI/CD (build + test + quality)

#### Metodos Fable
- `.agents/` com metodos Fable para agentes
- Skills: i-have-adhd formatting

#### Testes
- Testes unitarios e integracao (40+ testes)
- Security scan com bandit
- Syntax validation
- Flake8 lint

---

### Arquitetura

```
agente_core.py          # Facade de compatibilidade
agente_api_server.py    # Servidor REST API (FastAPI)
agente_cli.py           # Interface CLI
agente_gui.py           # Interface Tkinter
agente_streamlit.py     # Interface Streamlit
agente_turbo.py         # Modulo de inteligencia avancada
core/                   # Modulos core (30+ arquivos)
plugins/                # 72+ plugins
tests/                  # Testes unitarios e integracao
```

---

### Commits Incluidos

- `feat: grande atualizacao - ChatGPT-like API, web UI, plugins avancados, Docker, RAG, e 50+ plugins`
- `Dashboard turbinado: grafico pizza, timeline, categorias e ferramenta abrir_dashboard()`
- `Grande atualizacao: Llama 3.1, sub-agentes, memoria evolutiva, auto-init Ollama e dashboard`
- `first commit`

---

### Como Usar

```bash
# Instalacao
pip install -r requirements.txt
ollama pull qwen2.5:7b
ollama pull llava  # para visao

# Interfaces
python agente_cli.py          # CLI
python agente_gui.py          # GUI
python agente_streamlit.py    # Streamlit
python agente_api_server.py   # API Server
python agente_dashboard.py    # Dashboard
```

---

### Variaveis de Ambiente

Veja `.env.example` para todas as opcoes disponiveis. Principais:

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `AGENTE_MODEL` | `qwen2.5:7b` | Modelo principal |
| `AGENTE_VISION_MODEL` | `llava` | Modelo de visao |
| `AGENTE_API_KEY` | (vazio) | API key (vazio = sem auth) |
| `AGENTE_RATE_LIMIT` | `60` | Max req/min por IP |
| `FIRECRAWL_API_KEY` | (vazio) | API key do Firecrawl |
| `MEM0_API_KEY` | (vazio) | API key do Mem0 |
| `GITHUB_TOKEN` | (vazio) | GitHub PAT |
| `BRAVE_API_KEY` | (vazio) | Brave Search API key |

---

**Full Changelog**: https://github.com/lucbruna/IA-remodelada/commits/v2.0.0
