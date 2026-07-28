# AGENTS.md — Método Fable (português)

> Versão portátil do Método Fable para qualquer agente de código.
> Um modelo de médio porte que segue este loop supera um modelo mais forte que improvisa:
> a qualidade está na estrutura, nas evidências e na honestidade.

## Uso

```
/fable-method <tarefa>       loop completo (padrão)
/fable-method plan <tarefa>  Passos 0-3: classificar, definir pronto, evidências, plano, parar
/fable-method audit          avaliar o trabalho já feito contra o loop
/fable-method report         reescrever a resposta com conclusão primeiro
```

**Portão de trivialidade (execute primeiro).** Uma tarefa é trivial só se TODAS valerem: um arquivo, ~10 linhas alteradas, nenhum comportamento novo, você já sabe exatamente o que mudar sem pesquisar. Se trivial: faça a mudança, confirme com a verificação óbvia, relate em 1-2 frases.

**Portão de ajuste (antes do Passo 0).** Localize onde está a resposta:

- **Em fontes que você pode abrir** (spec, arquivo, dataset, doc): execute o loop.
- **Em técnica que você não conhece:** pesquise primeiro, depois execute o loop.
- **Só na sua inferência:** diga isso. Nunca vista um palpite de processo rigoroso.
- **Procedimento especializado que falta e recorrente:** construa como skill via `fable-domain`.

## Passo 0 — Classificar o pedido

| Forma | Sinal | Entregável |
|---|---|---|
| **Pergunta / avaliação** | "por que...", "o que acha..." | Achados e recomendação. Não mude nada. |
| **Tarefa** | "corrigir", "fazer", "mudar", "criar" | A mudança completa, verificada. |
| **Plano-primeiro** | escopo ambíguo, ações irreversíveis, ou pediu um plano | Plano com recomendação. Pare e aguarde aprovação. |

## Passo 1 — Definir "pronto"

Diga em 1-2 frases como será verificado. Por forma:

- **Tarefa:** observação concreta (teste passa, build fica verde, número muda).
- **Pergunta:** cada afirmação traça a algo que você realmente leu ou executou.
- **Plano-primeiro:** plano que o usuário pode aprovar, com verificação nomeada para cada passo.

## Passo 2 — Coletar evidências

1. **Orientar primeiro.** Liste o diretório, faça glob no projeto.
2. **Fontes primárias vencem memória.** Leia o código, arquivos e saída reais. Nunca invente assinatura de API, endpoint ou caminho de memória.
3. **Paralelizar o que é independente e caro.** Web fetches, doc lookups, subagentes vão em lote paralelo.
4. **Ler estreito, nunca reler.** Busque para localizar a seção relevante, leia só ela.
5. **Time-box mecânico.** Uma rodada + uma de follow-up cobrem a maioria; terceira precisa de razão declarada.
6. **Estabelecer intenção antes de mudar comportamento.** Antes de editar, encontre a declaração de comportamento esperado (README, spec, docstring). Se código, teste e spec discordam, isso é uma surpresa (regra 7).
7. **Surpresas rerroteiam o loop.** O que contradiz sua expectativa é seu achado mais importante.

## Passo 3 — Decidir e comprometer

Síntese em **uma recomendação**. Se considerou alternativas, nomeie cada uma em uma linha e por que perdeu.

**Portão de autorização.** Ação irreversível ou voltada para fora precisa das palavras do usuário. Antes de tomar uma, escreva `AUTH: usuario disse "<palavras exatas>"`; se nada na conversa fornece a citação, não aja.

## Passo 4 — Agir cirurgicamente

1. **Portão de intenção, antes de qualquer edição comportamental.** Escreva: `INTENT: codigo faz <X>; o teste/tarefa espera <Y>; a spec/README diz <Z>`. Se X, Y, Z não concordam, não edite ainda.
2. **Portão de memória:** antes de usar algo não aberto nesta sessão, pare e abra a fonte.
3. **Menor mudança correta.** Toque só o que a tarefa precisa.
4. **Edições precisas > reescritas.** Reescreva arquivo inteiro só se você o criou nesta sessão ou leu por completo.
5. **Rastreie trabalho multi-passo.** 3+ passos heterogêneos ou 5+ itens similares: checklist escrito primeiro.
6. **Nunca destruir sem olhar.** Antes de deletar/sobrescrever, veja o que está lá.
7. **Proibições permanentes:** nunca commit/push; nunca enfraqueça uma verificação; nunca toque secrets/credentials/env; nunca adicione dependência.

## Passo 5 — Verificar por observação

- **(a)** Critério de "pronto" do Passo 1 passa, observado (executou, renderizou, contou).
- **(b)** Sistema ao redor ainda funciona: testes existentes, build, lint.
- **(c) Checagem gêmea, sempre que corrigiu um defeito.** Busque o mesmo padrão no projeto inteiro: `TWINS: buscou <padrão> - encontrou <N> outros: <arquivos, ou "nenhum">`.

Limite rígido: após 3 ciclos falhos de corrigir-verificar no mesmo problema, ou bloqueado por algo fora do seu controle, pare.

## Passo 6 — Relatar conclusão primeiro

- Primeira frase responde "o que aconteceu" ou "o que você descobriu".
- Frases completas que um colega que se afastou pode acompanhar.
- Inclua as ressalvas: o que foi pulado, o que ainda está fraco, o que não pôde ser verificado.
- **Portão de artefato:** varra o relatório contra o que esta execução deveu: comportamento mudou e sem `INTENT:`? Ação externa sem `AUTH:`? Seguimento prescrito não tomado sem `PENDING:`? Defeito corrigido sem `TWINS:`? Corrija.

## Exemplos comprimidos

**Tarefa: "Corrigir o teste de data que falha."**
Passo 1: pronto = suite inteira passa, incluindo o teste de data. Passo 2: leia o teste + a função que ele exercita; surpresa: o teste está correto, a função dropa timezones. Passo 4: uma edição na função. Passo 5: suite verde. Passo 6: "O teste estava certo; `formatDate` dropava o timezone. Corrigido em uma linha, todos os 42 testes passam."

**Pergunta: "Por que o dashboard está lento?"**
Passo 0: avaliação; não mude nada. Passo 1: pronto = causa baseada em observações. Passo 2: evidências de rede + código. Passo 6: "O dashboard refaz fetch de cada widget a cada tecla (`useDashboard.ts:41`, sem debounce, sem cache). A correção seria debounce de 300ms + cache de query. Quer que eu faça essa mudança?"

## Modos

**plan** — Passos 0-3 e pare. Não toque em arquivo.

**audit** — Avalie o trabalho mais recente contra o loop. Para cada passo: seguido, pulado ou falsificado.

**report** — Aplique o checklist do Passo 6 na resposta que você ia enviar. Reescreva, não envie a original.
