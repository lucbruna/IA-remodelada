# Relatório de Análise e Evolução da IA Remodelada

## Visão Geral

**IA Remodelada** é um agente local de inteligência artificial com arquitetura modular,
suporte a plugins, turbo mode, ensemble de modelos, RAG e sandbox Docker. O sistema
usa Ollama como backend de LLM (modelo padrão `qwen2.5:7b`), com mais de 47 plugins
e 37 módulos core.

**Data da análise:** 22/07/2026

---

## 1. Arquitetura Atual

### 1.1 Estrutura de Diretórios

```
IA Remodelada/
├── agente_core.py          # Facade de compatibilidade (reexporta core/)
├── agente_turbo.py         # Módulo de inteligência turbo (cache, recovery, parallel)
├── agente_cli.py           # Interface CLI (terminal colorido)
├── agente_gui.py           # Interface GUI (Tkinter)
├── agente_api_server.py    # Servidor REST API (FastAPI, 2572 linhas)
├── agente_dashboard.py     # Dashboard Rich (terminal)
├── agente_streamlit.py     # Interface Streamlit
├── orquestrador_mestre.py  # CEO AI (planejar → arquitetar → executar → validar → revisar)
├── config.py               # Fonte única de configuração
├── core/                   # 37 módulos core (llm, memory, agent_loop, registry, etc.)
├── plugins/                # 47 plugins (rag, sandbox, memoria_evolutiva, etc.)
├── tests/                  # 10 arquivos de teste
├── docker-compose.yml      # Docker + Ollama + Open WebUI
└── Dockerfile              # Build multi-stage
```

### 1.2 Pipeline de Execução

```
Usuário → agente_cli/GUI/API → run_agent_turn() → agent_loop.py
    ↓
ensure_system_prompt() → semantic_cache_get() → smart_context_compress()
    ↓
_chat_with_retries() / _stream_chat() → ollama.chat()
    ↓
[tool_calls] → _execute_tool_call() → execute_with_recovery() → AVAILABLE_FUNCTIONS
    ↓
[hooks] → [prompt_guard] → [analytics] → [observability]
    ↓
save_conversation_history() → run_memory_pipeline() → hindsight_auto_learn()
```

### 1.3 Componentes Principais

| Componente | Descrição | Arquivo |
|---|---|---|
| **Config** | Modelo, visão, limites, paths | `config.py` |
| **LLM** | Chamadas ao Ollama com timeout e retries | `core/llm.py` |
| **Agent Loop** | Encadeamento de tool calls, limite de rounds | `core/agent_loop.py` |
| **Registry** | Registro de 170+ funções/ferramentas | `core/registry.py` |
| **Turbo** | Cache semântico, recovery, parallel, compressão | `agente_turbo.py` |
| **Memory Pipeline** | System prompt dinâmico, carregamento de plugins | `core/memory_pipeline.py` |
| **Autonomy** | Roteamento por intenção, contexto autônomo | `core/autonomy.py` |
| **Hindsight** | Memória duradoura estilo OMP | `core/hindsight.py` |
| **Prompt Guard** | Defesa contra prompt injection | `core/prompt_guard.py` |
| **Self Verify** | Loop adversarial (Fable 5) | `core/self_verify.py` |
| **Orquestrador** | CEO + sub-agentes especializados | `orquestrador_mestre.py` |

---

## 2. Pontos Fortes (Strengths)

### 2.1 Arquitetura Modular e Bem Organizada

- **Separação clara de responsabilidades:** `core/` (37 módulos) separado de `plugins/` (47 plugins)
- **Facade de compatibilidade:** `agente_core.py` reexporta tudo de `core/`, mantendo 100% de compatibilidade
- **Centralização de configuração:** `config.py` como fonte única de verdade para modelo, visão, limites
- **Carregamento automático de plugins:** Sistema `register(api)` simples e eficaz

### 2.2 Sistema de Plugins Extensível

- **47 plugins** cobrindo: RAG, sandbox, memória evolutiva, auto-evolução, código, imagens, áudio,
  redes, backup, segurança, banco de dados, documentos, scraping, MCP, Playwright, etc.
- **API de registro simples:** `api.register_tool(name, func, description, parameters)`
- **Carregamento dinâmico:** Plugins carregados automaticamente na inicialização

### 2.3 Inteligência Turbo Avançada

- **Cache semântico:** Embeddings via `nomic-embed-text`, similaridade cóseno, threshold 0.92
- **Recovery inteligente de erros:** Estratégias por tipo de erro (permissão, not found, timeout, encoding)
- **Execução paralela:** `ThreadPoolExecutor` para tool calls independentes
- **Decomposição de tarefas:** Templates por tipo (código, arquivos, análise, dados, web, imagem)
- **Compressão de contexto:** `smart_context_compress()` com agrupamento temático

### 2.4 Segurança e Observabilidade

- **Prompt Guard:** Detecção de prompt injection (entrada e saída de ferramentas), 4 níveis (NONE a CRITICAL)
- **Code Static Audit:** Análise estática de segurança (estilo bandit) - detecta eval/exec, subprocess, etc.
- **Resolve:** Ações destrutivas em modo preview (enqueue → apply/discard)
- **Sandbox Docker:** Execução isolada com limites de CPU, memória, processos, privilégios
- **Hooks configuráveis:** Eventos tool_call, tool_result, turn_start, turn_end, error, learn
- **Observabilidade:** Tracing via plugin_observabilidade, métricas de ferramentas

### 2.5 Memória e Aprendizado

- **Hindsight:** Memória duradoura estilo OMP (retain/recall/reflect/checkpoint/rewind)
- **Memória evolutiva:** Processamento automático de conversas, decay, grafo de conhecimento
- **Auto-evolução:** Otimização de parâmetros em runtime (NUM_CTX, TEMPERATURE, etc.)
- **Autonomia:** Roteamento por intenção (6 intents: código, brasil_mundo, pesquisa, criativo, arquivos, projeto)

### 2.6 Múltiplas Interfaces

- **CLI:** Terminal colorido, streaming, memória de conversas
- **GUI:** Tkinter com interface amigável
- **API REST:** FastAPI com Swagger UI, SSE streaming, upload de documentos
- **Dashboard:** Rich terminal com métricas em tempo real
- **Streamlit:** Interface web alternativa

### 2.7 Orquestração Avançada

- **Orquestrador Mestre:** CEO + Architect + sub-agentes especializados + Self-Reflection
- **Fluxo autônomo persistente:** Estados (planejado, executando, validando, corrigindo, etc.)
- **Sub-agentes isolados:** Git worktree próprio, maker + checker independentes
- **Self-verify:** Loop adversarial até aprovação ou esgotar max_rounds

### 2.8 Infraestrutura

- **Docker multi-stage:** Build otimizado, healthcheck, volumes persistentes
- **Docker Compose:** Ollama + API + Open WebUI
- **Testes:** 10 arquivos de teste (test_agente_core, test_plugins, test_async_api, etc.)

---

## 3. Pontos a Melhorar (Improvement Opportunities)

### 3.1 Testes e Qualidade

| Problema | Detalhe | Prioridade |
|---|---|---|
| **Cobertura de testes limitada** | Apenas 10 arquivos de teste, sem cobertura de integração completa | ALTA |
| **Falta de testes de carga** | Nenhum teste de performance ou carga para o agent loop | MÉDIA |
| **Testes de segurança insuficientes** | Prompt guard e code audit não têm testes dedicados | MÉDIA |
| **Falta de CI/CD** | Nenhum pipeline de CI automatizado (GitHub Actions, etc.) | ALTA |
| **Type hints parciais** | Muitos módulos usam `Any` ou falta type hints | BAIXA |

**Recomendações:**
- Adicionar pipeline GitHub Actions: lint → test → build → deploy
- Aumentar cobertura de testes para >80%
- Adicionar testes de integração para o agent loop completo
- Adicionar testes de carga com `locust` ou `k6`
- Adotar `mypy --strict` para type checking

### 3.2 Performance e Latência

| Problema | Detalho | Prioridade |
|---|---|---|
| **Ollama como único backend** | Não há fallback para outros provedores (OpenAI, Anthropic, etc.) | ALTA |
| **Latência de tool calls sequenciais** | Mesmo com parallel, tool calls dependentes são sequenciais | MÉDIA |
| **Cache semântico sem persistência eficiente** | JSON file, sem indexação, pode degradar com escala | MÉDIA |
| **Embedding model fixo** | `nomic-embed-text` hardcoded, sem fallback | BAIXA |
| **Sem otimização de prompts** | System prompt é grande (~360 linhas), pode ser otimizado | MÉDIA |

**Recomendações:**
- Adicionar backend abstrato com suporte a múltiplos provedores (Ollama, OpenAI, Anthropic, Gemini)
- Implementar rate limiting por usuário/IP na API
- Migrar cache semântico para ChromaDB/Qdrant com indexação
- Adicionar prompt optimization via A/B testing
- Implementar connection pooling para Ollama

### 3.3 Segurança

| Problema | Detalhe | Prioridade |
|---|---|---|
| **API sem autenticação** | `agente_api_server.py` não tem auth por padrão | ALTA |
| **Prompt guard básico** | Regex patterns, sem ML/anomaly detection | MÉDIA |
| **Sem rate limiting** | API vulnerável a abuse | MÉDIA |
| **Secrets em .env sem validação** | EMAIL_USER, EMAIL_PASS, master_password expostos | BAIXA |
| **Docker sem user não-root** | Container roda como root | BAIXA |

**Recomendações:**
- Adicionar JWT/OAuth2 authentication na API
- Adicionar rate limiting com `slowapi` ou `redis`
- Melhorar prompt guard com modelo de classificação
- Adicionar secrets validation e rotation
- Usar `USER` não-root no Dockerfile

### 3.4 Documentação

| Problema | Detalhe | Prioridade |
|---|---|---|
| **README básico** | Foca em instalação, não em arquitetura ou desenvolvimento | ALTA |
| **Sem docs de API** | Swagger UI existe mas não há documentação detalhada | ALTA |
| **Sem arquitetura docs** | Não há diagramas ou explicação de fluxos | MÉDIA |
| **Sem CONTRIBUTING.md** | Como contribuir não está documentado | MÉDIA |
| **Sem changelog** | Não há registro de mudanças por versão | BAIXA |

**Recomendações:**
- Criar `docs/` com: arquitetura, API reference, plugins guide, development guide
- Adicionar diagramas (Mermaid/PlantUML) de fluxos principais
- Criar `CONTRIBUTING.md` e `CHANGELOG.md`
- Documentar cada plugin com exemplos de uso

### 3.5 Manutenibilidade

| Problema | Detalhe | Prioridade |
|---|---|---|
| **System prompt monolítico** | 360 linhas em `memory_pipeline.py`, difícil de manter | MÉDIA |
| **Magic strings em vários módulos** | Nomes de funções, intents, etc. espalhados | MÉDIA |
| **Falta de logging estruturado** | Logs em texto, sem JSON/structured logging | BAIXA |
| **Hardcoded values** | Alguns valores hardcodados (ex: `nomic-embed-text`) | BAIXA |
| **Circular imports** | Alguns módulos importam de `agente_core` dentro de funções | BAIXA |

**Recomendações:**
- Modularizar system prompt em componentes (identity, tools, rules, turbo)
- Criar constants/enums para magic strings
- Adotar `structlog` para logging estruturado
- Centralizar magic values em `config.py`
- Resolver imports circulares com dependency injection

### 3.6 Experiência do Usuário

| Problema | Detalhe | Prioridade |
|---|---|---|
| **CLI sem autocomplete** | Não há autocompletar de comandos | BAIXA |
| **GUI básica (Tkinter)** | Interface simples, sem tema moderno | MÉDIA |
| **Dashboard sem gráficos interativos** | Rich terminal, mas sem visualização de dados | MÉDIA |
| **Sem notificações** | Não há sistema de notificações (push, email) | BAIXA |
| **API sem SDK** | Não há cliente SDK para integradores | MÉDIA |

**Recomendações:**
- Adicionar autocomplete com `argcomplete` no CLI
- Modernizar GUI com `customtkinter` ou migrar para `PyQt`/`Tauri`
- Adicionar gráficos interativos no dashboard
- Criar SDK Python/JS para a API
- Adicionar sistema de notificações

### 3.7 Escala e Produção

| Problema | Detalhe | Prioridade |
|---|---|---|
| **Sem load balancing** | API single-process, sem workers | MÉDIA |
| **Sem cache HTTP** | API não usa cache HTTP | BAIXA |
| **Sem monitoring** | Não há Prometheus/Grafana | MÉDIA |
| **Sem backup automático** | Dados não são backupados automaticamente | BAIXA |
| **Sem multi-tenancy** | Não há isolamento entre usuários | BAIXA |

**Recomendações:**
- Adicionar `gunicorn` com workers múltiplos
- Adicionar Prometheus metrics endpoint
- Implementar backup automático de `agente_data/`
- Adicionar multi-tenancy com tenant_id
- Adicionar health check mais detalhado

---

## 4. Roadmap de Evolução

### Fase 1: Fundamentos (Curto prazo - 1-2 meses)

| Item | Descrição | Esforço |
|---|---|---|
| **CI/CD Pipeline** | GitHub Actions: lint, test, build, publish | Médio |
| **API Authentication** | JWT auth + rate limiting | Médio |
| **Test Coverage** | Aumentar para >80%, testes de integração | Alto |
| **Type Hints** | `mypy --strict` em todos os módulos | Médio |
| **Documentation** | docs/ com arquitetura e API reference | Médio |

### Fase 2: Performance e Escala (Médio prazo - 2-4 meses)

| Item | Descrição | Esforço |
|---|---|---|
| **Multi-backend LLM** | Abstração com Ollama, OpenAI, Anthropic, Gemini | Alto |
| **Connection Pooling** | Pool de conexões para Ollama | Baixo |
| **Cache Migration** | Migrar para ChromaDB/Qdrant com indexação | Médio |
| **Load Balancing** | Gunicorn + workers múltiplos | Baixo |
| **Monitoring** | Prometheus metrics + Grafana dashboard | Médio |

### Fase 3: Experiência e Produção (Longo prazo - 4-6 meses)

| Item | Descrição | Esforço |
|---|---|---|
| **SDK** | Cliente Python e JS para API | Médio |
| **GUI Moderna** | Migrar de Tkinter para PyQt/Tauri | Alto |
| **Multi-tenancy** | Isolamento entre usuários | Médio |
| **Backup Automático** | Backup de dados com versionamento | Baixo |
| **Advanced Prompt Guard** | ML-based injection detection | Alto |

---

## 5. Métricas de Saúde Atuais

| Métrica | Valor | Target |
|---|---|---|
| **Módulos core** | 37 | - |
| **Plugins** | 47 | - |
| **Funções/ferramentas** | 170+ | - |
| **Linhas de código** | ~15,000 (core + plugins) | - |
| **Arquivos de teste** | 10 | 15+ |
| **Cobertura de testes** | ~40% (estimado) | >80% |
| **Type hints coverage** | ~60% (estimado) | >90% |
| **Documentação** | README básico | docs/ completo |
| **CI/CD** | Nenhum | GitHub Actions |
| **API auth** | Nenhum | JWT |
| **Rate limiting** | Nenhum | Implementar |

---

## 6. Conclusão

A **IA Remodelada** é um projeto extremamente bem arquitetado com uma base sólida
de agente local de IA. Os pontos fortes incluem:

1. **Arquitetura modular** impecável com separação clara de concerns
2. **Sistema de plugins** poderoso e extensível (47 plugins)
3. **Inteligência turbo** avançada (cache, recovery, parallel, compressão)
4. **Segurança abrangente** (prompt guard, code audit, sandbox, resolve)
5. **Múltiplas interfaces** (CLI, GUI, API, Dashboard, Streamlit)
6. **Orquestração avançada** (CEO, sub-agentes, self-verify, fluxo autônomo)

Os principais gargalos para produção são:

1. **Falta de CI/CD e testes** - risco de regressões
2. **API sem autenticação** - risco de segurança
3. **Ollama como único backend** - vendor lock-in
4. **Documentação limitada** - barreira para adoção

**Recomendação geral:** Priorizar CI/CD, autenticação de API e aumento de cobertura
de testes antes de escalar para produção. A arquitetura está pronta para crescimento,
mas precisa de mais robustez operacional.

---

*Relatório gerado por análise estática do código-fonte.*
*Arquivos analisados: 50+ arquivos Python, 4 arquivos de configuração, 10 arquivos de teste.*

---

## 7. Benchmark Comparativo: IA Remodelada vs ChatGPT/GPT

### 7.1 Comparação de Capacidades

| Capacidade | IA Remodelada | ChatGPT/GPT-4 | Gap |
|---|---|---|---|
| **Tamanho do Modelo** | qwen2.5:7b (7B params) | GPT-4 (1.8T params) | ⚠️ Muito menor |
| **Contexto** | 16K tokens (configurável) | 128K-1M tokens | ⚠️ 8-64x menor |
| **Web Browsing** | Plugins (DuckDuckGo, Playwright) | Integrado | ⚠️ Mais lento |
| **Code Interpreter** | run_python_code (local) | Integrado (sandbox) | ✅ Similar |
| **RAG/Local Files** | ChromaDB/Qdrant + OCR | Upload de arquivos | ✅ Vantagem local |
| **Sub-agentes** | Orquestrador + 10+ especialistas | Single agent | ✅ Vantagem |
| **Auto-verificação** | Self-verify (adversarial) | Manual | ✅ Vantagem |
| **Sandbox** | Docker isolado | Code interpreter sandbox | ✅ Vantagem |
| **Multi-modal** | llava (visão), TTS, geração imagem | Integrado | ⚠️ Mais básico |
| **Aprendizado** | Memória evolutiva + hindsight | Aprendizado contínuo | ⚠️ Mais limitado |
| **API Pública** | Local (FastAPI) | API paga | ✅ Gratuito/local |
| **Offline** | Totalmente offline | Requer internet | ✅ Vantagem |

### 7.2 Benchmark de Desenvolvimento (DevBench)

| Benchmark | IA Remodelada | ChatGPT/GPT-4 | Notas |
|---|---|---|---|
| **HumanEval** (Python) | ~30-40% (estimado) | ~67% (GPT-4) | Modelo menor limita |
| **MBPP** (Python básico) | ~40-50% (estimado) | ~75% (GPT-4) | Contexto limitado |
| **SWE-bench** (issues GitHub) | ~5-10% (estimado) | ~47% (GPT-4) | Falta de contexto |
| **DS-1000** (análise dados) | ~20-30% (estimado) | ~67% (GPT-4) | Plugins ajudam |
| **WebArena** (agente web) | ~15-25% (estimado) | ~55% (GPT-4) | Scraping limitado |
| **Full-stack dev** | ~25-35% (estimado) | ~60% (GPT-4) | Sub-agentes ajudam |

### 7.3 Nível de Maturidade

| Aspecto | Nível | Detalhe |
|---|---|---|
| **Arquitetura** | ⭐⭐⭐⭐⭐ | 5/5 - Modular, escalável, bem projetada |
| **Ferramentas** | ⭐⭐⭐⭐ | 4/5 - 170+ funções, mas sem web browsing integrado |
| **Segurança** | ⭐⭐⭐⭐ | 4/5 - Prompt guard, code audit, sandbox |
| **Experiência** | ⭐⭐⭐ | 3/5 - CLI/GUI/API, mas sem polish de ChatGPT |
| **Performance** | ⭐⭐ | 2/5 - Modelo pequeno (7B), contexto limitado |
| **Produção** | ⭐⭐ | 2/5 - Sem CI/CD, auth, rate limiting |
| **Documentação** | ⭐⭐ | 2/5 - README básico, sem docs detalhados |

### 7.4 O que falta para chegar perto do GPT

#### Gap 1: Tamanho e Qualidade do Modelo
- **Problema:** qwen2.5:7b tem 7B parâmetros vs 1.8T do GPT-4
- **Solução:** Suportar modelos maiores (qwen2.5:72b, llama3.1:70b) via Ollama ou
  integrar com API paga (OpenAI/Anthropic) como fallback
- **Esforço:** Médio

#### Gap 2: Contexto Limitado
- **Problema:** 16K tokens vs 128K do GPT-4
- **Solução:** Aumentar `AGENTE_NUM_CTX` para 32K-128K (dependendo do modelo),
  otimizar system prompt (atualmente 360 linhas), usar compressão mais agressiva
- **Esforço:** Baixo

#### Gap 3: Web Browsing Integrado
- **Problema:** Scraping via plugins é mais lento e menos confiável
- **Solução:** Integrar com serviço de busca web (SerpAPI, Brave Search) ou
  usar modelo com web browsing integrado
- **Esforço:** Médio

#### Gap 4: Treinamento e Fine-tuning
- **Problema:** GPT-4 foi treinado com milhões de exemplos de código
- **Solução:** Fine-tuning local com `plugin_fine_tuning.py` usando dados de
  HumanEval/MBPP, ou usar modelo pré-treinado maior
- **Esforço:** Alto

#### Gap 5: Experiência de Usuário
- **Problema:** Interface menos polida que ChatGPT
- **Solução:** Modernizar GUI, adicionar tema escuro, animações, feedback visual
- **Esforço:** Médio

#### Gap 6: Produção e Escala
- **Problema:** Sem CI/CD, auth, rate limiting
- **Solução:** Ver seção 3.1 e 3.3 do relatório
- **Esforço:** Médio

### 7.5 Estratégia para Fechar o Gap

| Fase | Objetivo | Timeline | Esforço |
|---|---|---|---|
| **Fase A** | Suportar modelos maiores (32B+) | 1-2 meses | Médio |
| **Fase B** | Aumentar contexto para 64K-128K | 2-4 semanas | Baixo |
| **Fase C** | Web browsing integrado (SerpAPI) | 1 mês | Médio |
| **Fase D** | Fine-tuning com dados de código | 2-3 meses | Alto |
| **Fase E** | Modernizar UX/UI | 2-3 meses | Médio |
| **Fase F** | CI/CD + Auth + Rate Limiting | 1-2 meses | Médio |

### 7.6 Conclusão do Benchmark

A **IA Remodelada** tem uma **arquitetura superior** em termos de modularidade,
segurança e recursos avançados (sub-agentes, self-verify, sandbox). No entanto,
o **gargalo principal é o modelo de linguagem** (qwen2.5:7b vs GPT-4).

**O potencial está lá:** com um modelo maior (32B+), contexto ampliado (64K+),
web browsing integrado e fine-tuning, a IA Remodelada pode chegar a **70-80% da
capacidade do GPT-4** em tarefas de desenvolvimento, mantendo vantagens em
privacidade, custo e controle local.

**Diferenciais únicos que o GPT não tem:**
1. Sub-agentes especializados com git worktree isolado
2. Self-verificação adversarial (loop Fable 5)
3. Sandbox Docker com limites de recursos
4. Memória duradoura estilo OMP (hindsight)
5. Auto-evolução de parâmetros em runtime
6. 100% offline e gratuito

---

## 8. Integração de Conceitos do Fable 5, ChatGPT e Claude

### 8.1 Análise dos Projetos de Referência

#### Fable 5 (Claude Fable 5)

**Origem:** Metodologia auto-documentada pelo Claude Fable 5 para transferir seu modo de trabalho para modelos menos avançados.

**Arquitetura de 4 camadas de enforcement:**
```
HOOK (script) → AGENT (subagente) → CONTEXT (prose) → EVAL (teste)
```

**Componentes principais:**
- **Hooks:** Scripts determinísticos (shell/Python) que bloqueiam ações perigosas
- **Agents:** Sub-agentes com contratos estritos (builder, qa-verifier, code-reviewer, research-scout)
- **Skills:** Procedimentos on-demand carregáveis (26 skills)
- **Evals:** Testes de regressão comportamental
- **RunContext:** Estado serializável, checkpointado a cada passo

**Conceitos-chave:**
- "Rules decay; enforce what you can" — enfatizar enforcement sobre prose
- "Verify, don't trust" — sub-agente independente nunca viu o reasoning
- "Plan ≠ History" — plano estruturado fora da conversa
- "Accumulating replan" — passos concluídos preservados

#### ChatGPT (OpenAI)

**Componentes relevantes:**
- **Web Browsing Plugin:** Bing Search API, GET requests only, robots.txt, rate limiting, user-agent `ChatGPT-User`
- **Code Interpreter:** Python sandbox firewalled, resource limits, ephemeral disk, sessão persistente
- **Plugin System:** OpenAPI spec + manifest, documentação para modelos e humanos

**Arquitetura:**
```
Plugin API (OpenAPI) → Manifest → Model Context → Tool Invocation
```

**Segurança:**
- Sandboxed execution environment
- Strict network controls (no internet from code)
- Resource limits por sessão
- Isolated service (browsing separado da infraestrutura)

#### Claude Computer Use (Anthropic)

**Componentes:**
- **Computer Use Tool:** screenshot, mouse, keyboard, scroll, drag
- **Browser Automation:** Playwright MCP (DOM-aware, accessibility tree)
- **Agent Loop:** screenshot → reason → act → repeat
- **Reference Implementation:** Docker container com Xvfb, Firefox, agent loop

**Arquitetura:**
```
Claude API → Tool Request → Harness executes → Screenshot → Claude
```

**Vantagens do Browser Automation (Playwright MCP):**
- Element-based targeting (ref) vs pixel coordinates
- DOM-aware (não precisa de visão)
- Mais rápido e determinístico que computer use
- Structured output para scripts

### 8.2 Arquivos/Conceitos a Inserir no Projeto

#### A. Web Browsing (Prioridade ALTA)

**Do Claude Browser Automation (Playwright MCP):**

| Conceito | Como implementar | Esforço |
|---|---|---|
| **DOM-aware browser tool** | Criar `core/browser_tool.py` com Playwright integrado | Médio |
| **Element ref targeting** | JavaScript utilities para gerar refs (como no demo) | Médio |
| **Coordinate scaling** | Escalar coords de 1456x819 → 1920x1080 | Baixo |
| **Form manipulation** | `form_input(ref, value)` direto no DOM | Baixo |
| **Page text extraction** | `get_page_text()` com filtro interativo | Baixo |

**Do ChatGPT Web Browsing:**
- **Bing Search API** como backend de busca (via SerpAPI ou Bing direto)
- **GET requests only** para segurança
- **Robots.txt** checking
- **Rate limiting** por IP
- **User-agent** configurável

**Implementação sugerida:**
```python
# core/browser_tool.py
class BrowserTool:
    def navigate(self, url: str) -> str
    def read_page(self, text: str = "interactive") -> dict
    def left_click(self, ref: str = None, coordinate: list = None) -> str
    def form_input(self, ref: str, value: str) -> str
    def get_page_text(self) -> str
    def find(self, text: str) -> list
    def screenshot(self, region: list = None) -> str
    def execute_js(self, code: str) -> str
```

**Arquivos a criar:**
- `core/browser_tool.py` — Browser automation com Playwright
- `plugins/plugin_browser_mcp.py` — MCP server para browser
- `core/web_search.py` — Busca via Bing/SerpAPI (upgrade do DuckDuckGo atual)

#### B. Fine-tuning (Prioridade MÉDIA)

**Do Fable 5 Methodology:**

| Conceito | Como implementar | Esforço |
|---|---|---|
| **Verification catalog** | Catálogo de "smallest failing check" por tipo de tarefa | Médio |
| **Decomposition patterns** | Padrões de decomposição por domínio | Médio |
| **Preflight sweep** | Verificação pré-completa (preflight.sh) | Baixo |
| **Adversarial review** | Sub-agente que procura por "fake progress" | Médio |

**Do ChatGPT Code Interpreter:**
- **Persistent session** — sessão Python mantida entre chamadas
- **Ephemeral disk** — workspace temporário por conversa
- **Resource limits** — CPU, memória, tempo limitados
- **File upload/download** — upload de arquivos para workspace

**Do Claude Computer Use:**
- **Self-verification** — verificar contra especificação
- **Evidence-based** — provas reais, não apenas claims
- **Exit check** — verificação final contra critérios de sucesso

**Implementação sugerida:**
```python
# core/fine_tuning.py
class FineTuningPipeline:
    def prepare_dataset(self, source: str = "humaneval") -> str
    def train(self, dataset: str, model: str, epochs: int = 3) -> str
    def evaluate(self, model: str, benchmark: str) -> dict
    def deploy(self, model: str) -> str
```

**Arquivos a criar:**
- `core/verification_catalog.py` — Catálogo de verificações mínimas
- `core/fine_tuning.py` — Pipeline de fine-tuning local
- `plugins/plugin_fine_tuning.py` — Upgrade do plugin existente
- `evals/` — Diretório de testes de regressão (inspirado em Fable 5)

#### C. Produção (Prioridade ALTA)

**Do Fable 5 Hooks:**

| Hook | Evento | O que fazer | Esforço |
|---|---|---|---|
| `pre-tool-guard.py` | PreToolUse (Bash) | Bloquear comandos destrutivos | Baixo |
| `close-guard.py` | Stop | Verificar critérios de sucesso | Médio |
| `spawn-guard.py` | PreToolUse (Agent) | Gate em spawns de sub-agentes | Médio |
| `session-end.py` | SessionEnd | Cleanup de recursos | Baixo |

**Do ChatGPT Plugin System:**
- **OpenAPI spec** para documentação de plugins
- **Manifest** com metadados
- **Isolated service** para segurança

**Do Claude Computer Use:**
- **Agent loop** robusto com retry
- **Cost management** — limites de steps
- **Safety classifiers** — detecção de comportamento perigoso

**Implementação sugerida:**
```python
# core/hooks_production.py
class ProductionHooks:
    def pre_tool_guard(self, command: str) -> bool  # Bloqueia rm -rf, etc.
    def close_guard(self, task_result: str) -> bool  # Verifica critérios
    def spawn_guard(self, prompt: str) -> bool  # Gate em spawns
    def session_end(self) -> None  # Cleanup
    def rate_limit(self, user_id: str) -> bool  # Rate limiting
```

**Arquivos a criar:**
- `core/hooks_production.py` — Hooks de produção (inspirado Fable 5)
- `core/rate_limiter.py` — Rate limiting por usuário/IP
- `core/auth.py` — JWT authentication
- `core/cost_manager.py` — Gerenciamento de custos/tokens
- `evals/` — Diretório de testes comportamentais

### 8.3 Plano de Implementação por Fase

#### Fase 1: Web Browsing (2-3 meses)

| Semana | Tarefa | Esforço |
|---|---|---|
| 1-2 | Integrar Playwright MCP como plugin | Médio |
| 3-4 | Criar `core/browser_tool.py` com DOM-aware | Médio |
| 5-6 | Upgrade `web_search` para Bing/SerpAPI | Baixo |
| 7-8 | Testes e documentação | Médio |

**Arquivos:**
- `core/browser_tool.py` (novo)
- `plugins/plugin_browser_mcp.py` (novo)
- `core/web_search.py` (upgrade)
- `tests/test_browser_tool.py` (novo)

#### Fase 2: Fine-tuning e Verificação (2-3 meses)

| Semana | Tarefa | Esforço |
|---|---|---|
| 1-2 | Criar `evals/` com testes de regressão | Médio |
| 3-4 | Implementar verification catalog | Médio |
| 5-6 | Pipeline de fine-tuning local | Alto |
| 7-8 | Adversarial review sub-agent | Médio |

**Arquivos:**
- `evals/` (novo diretório)
- `core/verification_catalog.py` (novo)
- `core/fine_tuning.py` (novo)
- `plugins/plugin_fine_tuning.py` (upgrade)

#### Fase 3: Produção e Segurança (2 meses)

| Semana | Tarefa | Esforço |
|---|---|---|
| 1-2 | Hooks de produção (Fable 5) | Médio |
| 3-4 | Auth JWT + Rate Limiting | Médio |
| 5-6 | Cost manager + Safety | Médio |
| 7-8 | CI/CD + Testes | Médio |

**Arquivos:**
- `core/hooks_production.py` (novo)
- `core/auth.py` (novo)
- `core/rate_limiter.py` (novo)
- `core/cost_manager.py` (novo)
- `.github/workflows/ci.yml` (novo)

### 8.4 Conclusão

A **IA Remodelada** já possui uma base sólida com conceitos avançados de agentes (orquestrador, sub-agentes, self-verify). A integração de conceitos do **Fable 5**, **ChatGPT** e **Claude** pode elevar o projeto a um nível de produção enterprise:

1. **Web Browsing:** Playwright MCP + Bing Search API = browsing confiável e rápido
2. **Fine-tuning:** Pipeline local + verification catalog = melhor qualidade de código
3. **Produção:** Hooks + Auth + Rate Limiting = pronto para produção

**O diferencial único que emergiria:** Um agente local que combina a **arquitetura modular** da IA Remodelada, a **metodologia de enforcement** do Fable 5, o **browser automation DOM-aware** do Claude, e o **sandbox** do ChatGPT Code Interpreter — tudo 100% offline e gratuito.
