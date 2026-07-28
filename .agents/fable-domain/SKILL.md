---
name: fable-domain
description: Discute um domínio com o usuário, pesquisa em fontes reais, e gera um bundle de skill confiável para ele — um workflow passo-a-passo com flowchart, um adaptador de domínio, uma fixture de armadilha, e um smoke eval. Use quando o usuário disser "/fable-domain <setor>", "crie uma skill para <domínio>", ou "adicione um domínio ao método fable".
trigger: /fable-domain
---

# fable-domain

O fable-method vem com adaptadores de domínio que traduzem seu loop para os substantivos de um setor. Esta skill cria um novo e entrega ao usuário um **workflow utilizável passo-a-passo com um flowchart**, para que um modelo menor possa abordar aquele domínio como o Fable abordaria.

## O que produz (o bundle; todos os quatro, ou não está pronto)

1. **Workflow de domínio com flowchart.** A abordagem passo-a-passo para este domínio, destilada da discussão e pesquisa, mais um mermaid flowchart.
2. **O adaptador**, conforme `references/domains/TEMPLATE.md`.
3. **A fixture de armadilha**, um diretório no formato `eval/scenarios/` cujo GROUND-TRUTH.md define a tarefa, a armadilha (a fraude central do setor), limites de pontuação e comportamento ideal.
4. **Um smoke eval**, 1-2 execuções controle-vs-adaptador, julgadas por diff e execução, rotuladas smoke-grade.

## Estágio 1: Discutir

Fazer uma skill é um ato deliberado e acompanhado, então começa com uma conversa. Pergunte adaptativamente: qual é o caso de uso real e quem o executa; como é "bom" neste domínio e como um profissional saberia; quais fontes e autoridades o usuário confia; o que a skill nunca deve fazer; o que exatamente deve produzir. Pare quando você puder declarar as evidências, autoridade e modos de falha do domínio de volta ao usuário e eles concordarem.

**Linhas vermelhas (recusa dura).** Se o domínio requer licenciamento profissional ou uma resposta errada causa dano físico, legal ou financeiro, NÃO gere um checklist. Isso cobre: diagnóstico e tratamento médico/clínico, aconselhamento jurídico, aconselhamento financeiro específico de compra/venda/alocação, saúde mental e engenharia de segurança crítica.

**Parada de escopo.** Se o setor solicitado não pode preencher o template com substantivos genuinamente diferentes do padrão de codificação (sua evidência são arquivos e tracebacks, sua autoridade é a spec, suas fraudes são os modos de falha do próprio método), pare aqui e diga que o método já cobre; nenhum adaptador é gerado.

## Estágio 2: Pesquisar

Baseado na discussão, pesquisa web vinculada, buscada agora: o que profissionais tratam como evidência, quem são as autoridades reais, os regulamentos e políticas atuais que vinculam o domínio, e seus modos de falha documentados. Toda afirmação que nomeia um regulamento, política, limite ou prática ganha um link e data de acesso na seção Sources. Sem acesso web significa nenhum bundle confiável: diga e pare.

## Estágio 3: Gerar o bundle

1. **Orientar e ler TODOS os adaptadores existentes.**
2. **Escopar o setor.** Uma frase de "aplica-se quando" e uma frase de limite nomeando o adaptador mais próximo ou o padrão de codificação.
3. **Escrever o workflow e seu flowchart.**
4. **Escrever o adaptador** conforme TEMPLATE.md.
5. **Vincular toda superfície de roteamento.** O parágrafo de adaptador no SKILL.md do método, o router nos flowcharts, a lista de adaptadores no README, a lista de setores do fable-judge.
6. **Construir a fixture de armadilha.** Pequena, de decisão única, minutos para executar.

## Estágio 4: Verificar, smoke-eval, relatar

1. **Verificar mecanicamente.** Execute o script de verificação do repositório; corrija o que falha.
2. **Smoke eval.** Execute a fixture nua vs. com o bundle. Uma semente é smoke test, não benchmark; rotule como tal.
3. **Julgar o bundle.** Antes de entregar, execute uma passagem fable-judge sobre as próprias afirmações do bundle: cada fonte nomeada realmente buscada, a armadilha verificada em todos os três estados, toda superfície de roteamento realmente vinculada.
4. **Relatar conclusão primeiro.** O inventário do bundle, o que foi verificado e como, as fontes buscadas, e a linha de dívida honesta.
