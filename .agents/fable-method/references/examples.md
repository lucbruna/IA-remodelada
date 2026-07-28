# Exemplos Trabalhados do Método Fable

## Exemplo 1: Trivial

**Usuário:** "Corrige o typo na linha 42 de core/llm.py: 'timeout' → 'timeout'."

**Portão de trivialidade:** Um arquivo, 1 linha, sem comportamento novo, sei exatamente o que mudar.

**Ação:** Editar a linha, reler o span, confirmar.

**Relatório:** "Typo corrigido em core/llm.py:42."

---

## Exemplo 2: Pergunta

**Usuário:** "Por que o servidor API está lento?"

**Passo 0:** Pergunta/avaliação. Não mudar nada.

**Passo 1:** Pronto = causa identificada com evidência observável.

**Passo 2:** 
- Orientar: ler agente_api_server.py, verificar rotas.
- Evidência: middleware de rate limiting faz sync I/O a cada requisição; sem cache; logger bloqueante.

**Passo 3:** Causa: logging síncrono + rate limit sem cache.

**Passo 6:** "O servidor faz I/O síncrono no logger e no rate limiter a cada requisição (`agente_api_server.py:200`, `middleware.py:45`). A correção seria logging assíncrono + cache de rate limit em memória. Quer que eu faça essa mudança?"

---

## Exemplo 3: Tarefa

**Usuário:** "Faz o teste de RAG passar."

**Passo 0:** Tarefa.

**Passo 1:** Pronto = `pytest tests/test_rag.py` passa verde.

**Passo 2:**
- Orientar: ler test_rag.py, código RAG.
- Ler test_rag.py — teste mocka retorno do ChromaDB mas o embedding real é `nomic-embed-text` que retorna 768 dims; o mock retorna 384 dims.
- Spec/docstring de `core/rag.py` diz "embeddings 768d".

**Passo 3:** Um problema: o mock no teste está desatualizado (384 vs 768).

**Passo 4 (portão de intenção):** INTENT: codigo RAG usa 768d; o teste mocka 384d; a docstring diz 768d. Corrigir o mock no teste, não o código.

**Passo 5:** `pytest tests/test_rag.py` passa.

**Passo 6:** "O teste de RAG mockava embeddings com 384 dimensões, mas o modelo real produz 768. Corrigido o mock no teste (`test_rag.py:25`). Teste passa."

---

## Exemplo 4: Plano-primeiro

**Usuário:** "Quero adicionar um novo plugin de análise de sentimentos."

**Passo 0:** Plano-primeiro (escopo ambíguo: qual API? thresholds? output?).

**Passo 1:** Pronto = plano que usuário aprova com verificação nomeada por passo.

**Passo 2:**
- Orientar: ler plugins existentes, ver padrão.
- Evidência: plugins seguem `PluginAPI` base class; cada plugin tem `__init__`, `execute`, `get_metadata`.

**Passo 3:** Plano recomendado: 1) criar plugin_analise_sentimentos.py seguindo padrão, 2) testar com frases conhecidas, 3) integrar no TOOLS_LIST.

**Entregar plano, PARE.**

---

## Exemplo 5: Surpresa

**Usuário:** "Corrige o bug no cálculo de desconto."

**Passo 2 evidência:** README.md diz "10% para compras acima de R$100". Código `calcula_desconto(150)` retorna 5%. Teste espera 10%.

**Surpresa:** Código implementa "5% acima de R$200, 10% acima de R$500" — contradiz README.

**Passo 2 regra 7:** Relatar a contradição. Perguntar qual lado o usuário quer seguir.

**Relatório:** "O README diz 10% acima de R$100, mas o código implementa uma tabela diferente (5% > R$200, 10% > R$500). O teste `test_desconto.py` espera 10% em R$150 (seguindo o README). Qual comportamento devo seguir — o README ou o código atual?"
