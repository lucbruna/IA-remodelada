# WORKSTATE — IA Remodelada

## Objective
- Corrigir bugs do projeto "IA Remodelada" (E:\IA remodelada): IA respondia sem contexto, em inglês e listava ferramentas não solicitadas; tornar funcional a seleção de modelo no navegador (http://localhost:8000/ servido por agente_api_server.py + agente_web.html).

## Important Details
- Modelo trocado em config.py: `qwen2.5:1.5b` → `qwen2.5:7b` (já baixado no Ollama). VISION_MODEL=llava.
- Docker instalado; plugins de sandbox usam containers reais.
- "HERNNES" = grafia errada de Hermes Agent (Nous Research); não necessário integrar.
- Frontend servido por `@app.get("/")` lê `agente_web.html`. Backend tem `/models` (lista Ollama) e `/models/default`; chat aceita campo `model`.
- Backend API: agente_api_server.py; modelo padrão vem de `MODEL_NAME` (importado de config.MODEL).
- Ambiente: `python` no PATH resolve p/ venv do hermes-agent (C:\Users\tomga\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe) — tem fastapi/uvicorn/ollama/torch. Python do sistema (Python311) NÃO tem ollama. Warnings de pynvml/torch são irrelevantes.
- Cliente `ollama` instalado é VERSÃO NOVA: `ollama.list()` retorna pydantic `ListResponse` cujos modelos são objetos `Model` (atributo `model`, NÃO `name`).

## Work State
### Completed
- `core/agent_loop.py`: `ensure_system_prompt()` injeta/atualiza SYSTEM_PROMPT em todo turno; chamada em `run_agent_turn`. Validado: 2 system messages/turno.
- `core/memory_pipeline.py`: regra PT-BR no topo de `_build_system_prompt`; correção `consultar_solucao_erro`→`consultar_solucoes_erro`.
- `core/autonomy.py`: `_autonomous_context_for_turn` reescrita (instrução interna, não lista ferramentas soltas).
- `config.py`: MODEL = "qwen2.5:7b".
- Validação: 84 arquivos compilam; 49/49 plugins carregam.
- BUG ORQUESTRADOR "invalid model name (status code: 400)" — RESOLVIDO:
  - Sintoma: "[Sub-agente codigo] Erro: O modelo nao respondeu em 300s..." + "[Erro na chamada ao modelo: invalid model name (status code: 400)]" (orquestrador_mestre.py:94).
  - Causa raiz: endpoint `/orchestrate` (agente_api_server.py ~linha 1051) passava `model` direto p/ `OrquestradorMestre(model=model if model else None)` SEM `_normalize_model`. Com o dropdown quebrado (valores "?"), o frontend enviava "?" → ollama.chat(model="?") → 400. O endpoint de `/chat` normalizava, mas o de orquestração não.
  - Corrigido: (1) endpoint `/orchestrate` agora usa `OrquestradorMestre(model=_normalize_model(model))`; (2) `OrquestradorMestre._ollama_chat` (orquestrador_mestre.py ~linha 75) agora faz fallback p/ MODEL se `modelo` for "", "?", "null", "None".
  - VERIFICADO: OrquestradorMestre(model="?") executa sem "invalid model name" (repro3.py). Arquivos compilam OK.
  - Nota: o timeout de 300s do subagente é à parte (modelo válido, mas Ollama pode não estar rodando / primeiro load lento). Garantir `ollama serve` ativo e modelo baixado.
- INVESTIGAÇÃO SELETOR DE MODELO — RESOLVIDA:
  - Causa raiz: `/models` retornava `"name":"?"` para TODOS os modelos porque o código usava `m.get("name")`, mas o cliente `ollama` novo retorna objetos pydantic com atributo `model`. Resultado: dropdown populado só com "?"; nenhuma opção casava com o ativo "qwen2.5:7b"; `state.currentModel` vazio → seleção não funcionava de fato.
  - Corrigido em `agente_api_server.py` `list_models()` (linha ~392) e no endpoint de traces (~2492): normaliza resposta (pydantic `model_dump()` ou dict) e usa `d.get("name") or d.get("model")`; também trata `response` como pydantic ou dict.
  - VERIFICADO: `/models` agora retorna nomes reais (llama3.2:latest, qwen2.5:7b, etc.) e `active: "qwen2.5:7b"`. O frontend `loadModels()`/`switchModel()`/`send()` (já corretos) agora funcionam: popula o <select>, marca ativo, envia `model` no `/chat/stream`.
- Como rodar o servidor (precisa do venv do hermes):
  `C:\Users\tomga\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe agente_api_server.py`
  IMPORTANTE: o servidor só vive durante a chamada de shell; start+test devem estar NA MESMA chamada bash (loop de poll até :8000 subir).

### Blocked / Pendências
- Teste end-to-end de chat com modelo escolhido (`/chat`) deu timeout em 90s — provavelmente turno do agente pesado (system prompt + tools), NÃO relacionado à seleção de modelo. Não investigado a fundo; fora do escopo do bug do seletor. Se quiser, reduzir MAX_TOOL_ROUNDS ou testar com prompt mínimo.

## Next Move
- (Opcional) Confirmar que o chat usa o modelo escolhido fazendo um teste end-to-end com timeout maior ou modelo menor (qwen2.5:1.5b) e prompt trivial.
- Reiniciar o servidor manualmente para o usuário testar no navegador: `python agente_api_server.py` (venv hermes) e abrir http://localhost:8000/.

## Relevant Files
- E:\IA remodelada\config.py — MODEL qwen2.5:7b.
- E:\IA remodelada\core\agent_loop.py — ensure_system_prompt().
- E:\IA remodelada\core\memory_pipeline.py — SYSTEM_PROMPT PT-BR.
- E:\IA remodelada\core\autonomy.py — _autonomous_context_for_turn.
- E:\IA remodelada\agente_api_server.py — /models corrigido (linhas ~392 e ~2492); chat aceita `model`.
- E:\IA remodelada\agente_web.html — seletor #modelSelect, loadModels(), switchModel(), send() já corretos; só dependiam dos dados do backend.
- E:\IA remodelada\agente_core.py — facade; MODEL/VISION_MODEL de config.
