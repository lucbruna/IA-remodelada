---
name: fable-loop
description: Workflow orquestrado de ponta a ponta que executa uma tarefa como o Fable executava sessões. Subagentes de evidência em paralelo, um plano comprometido, execução cirúrgica com portão de intenção, agentes de verificação adversarial, relatório honesto conclusão-primeiro. Use para tarefas multi-passo não triviais quando o usuário disser "/fable-loop" ou "execute o loop fable".
trigger: /fable-loop
---

# O Loop Fable

Esta skill orquestra o fable-method: leia o SKILL.md primeiro; suas regras governam cada estágio. O método diz O QUE verificar; este loop diz QUEM faz o trabalho: o que roda na thread principal, o que é delegado a subagentes, e o que é atacado antes da entrega.

**Portão primeiro.** Trivial pelo portão de trivialidade do método: apenas faça, verifique com a verificação óbvia, relate em 2 frases. Sem estágios, sem subagentes. Tudo mais executa os quatro estágios abaixo em ordem.

## Estágio 1 — PLAN (primeiro bookend)

1. Aplique os Passos 0-3 do método: classificar, definir pronto com verificação nomeada, declarar suposições.
2. **Fan-out de evidências.** Dispare os coletores de evidência como subagentes paralelos em UMA mensagem, nunca sequencial:
   - questões de código: um agente Explore por área distinta;
   - questões de biblioteca ou fato: agente de pesquisa que busca docs atuais ou web;
   - cada subagente retorna achados destilados com citações.
   Um lote + um lote de follow-up é o orçamento; terceiro precisa de razão declarada.
3. **Produza o artefato do plano** neste formato: classificação; definição de pronto + verificação; evidências encontradas (citadas); UMA abordagem recomendada (alternativas descartadas em uma linha cada); o escopo (arquivos exatos que o trabalho tocará); riscos e suposições; e o checklist de execução.
4. **Portão de decisão.** Tarefa em forma de tarefa e reversível: prossiga ao Estágio 2 sem perguntar. Forma plano-primeiro (escopo ambíguo, ações irreversíveis, ou usuário pediu plano): apresente o artefato do plano e PARE para aprovação.

## Estágio 2 — EXECUTAR

1. Trabalhe o checklist na **thread principal** (use ferramenta todo se disponível; marque itens ao completar). Decidir e editar ficam na thread principal; apenas busca e verificação delegam.
2. Toda edição segue Passo 4 do método: portão de intenção antes de mudanças comportamentais, portão de memória antes de primeiro uso de algo não aberto, menor mudança correta, edições precisas, nunca destruir sem olhar.
3. Itens mecânicos independentes (mesma mudança em muitos arquivos, geração isolada de arquivos) podem delegar a subagentes paralelos, em uma mensagem, com isolamento de worktree se puderem tocar os mesmos arquivos.
4. Uma surpresa no meio da execução rerroteia conforme Passo 2 regra 7: diga, depois atualize o plano ou volte ao Estágio 1. Nunca force o plano através de uma surpresa.
5. Ignorância no meio de item é pausa, não palpite: no momento em que uma edição carregaria um fato de memória (assinatura, chave, figura), pare aquele item, dispare um subagente de pesquisa conforme portão de memória do método, e retome quando retornar.
6. Itens de checklist voltados para fora obedecem ao portão de autorização do método: sem autorização do usuário citada, sem ação; o item se converte em próximo passo proposto no relatório.

## Estágio 3 — VERIFICAR (adversarialmente)

1. Execute a verificação nomeada você mesmo, ambas as metades: o critério de pronto observado (executou, renderizou, contou), e o sistema ao redor ainda saudável (build, testes, lint para área tocada).
2. **Para mudanças consequentes, dispare atacantes.** 1-3 subagentes paralelos, cada um instruído a REFUTAR o trabalho de uma lente distinta, por exemplo: "Leia este diff e prove que a mudança está errada ou incompleta", "Exerça o comportamento alterado em runtime e encontre entrada que quebre", "Verifique esta afirmação contra a spec/docs e encontre contradição", "Compare o conjunto completo de mudanças contra o escopo declarado do plano e prove que algo fora do escopo mudou". Lentes distintas vencem revisores idênticos.
3. Um achado que sobrevive à sua própria verificação volta ao Estágio 2 como trabalho novo. Limite rígido conforme método: 3 ciclos falhos de corrigir-verificar no mesmo problema, ou qualquer bloqueador fora do seu controle, significa parar e devolver com a saída e sua hipótese.

## Estágio 4 — AUDITAR e RELATAR (segundo bookend)

1. Auto-auditoria conforme modo audit do fable-method: para cada passo do método, seguido, pulado ou falsificado. Corrija o que uma passada pode corrigir (geralmente afirmação não verificada: verifique agora ou re-rotule como ressalva).
2. Entregue conforme Passo 6 do método: conclusão na primeira frase, evidência de verificação mostrada, ressalvas honestas, seguimentos só se emergiram do trabalho. Sem nomes de estágio ou números de passo no relatório; as linhas INTENT e AUTH são os únicos artefatos do método que um relatório pode conter.

## Quando NÃO usar este loop

- Tarefas triviais (o portão cuida delas).
- Perguntas puras sem trabalho multi-passo: fable-method simples cobre.
- Dentro de fase GSD já orquestrada: GSD é dono dos estágios lá; aplique regras do fable-method dentro delas em vez de aninhar loops.

## Economia de modelo

O loop é agnóstico de modelo. Subagentes de evidência e atacante são amigáveis a modelos baratos; mantenha a thread principal (decidir, editar) no modelo mais forte disponível, e dê aos atacantes esforço maior que aos coletores quando houver escolha.
