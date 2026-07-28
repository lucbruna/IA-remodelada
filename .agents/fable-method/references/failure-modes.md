# Modos de Falha do Método Fable

Cada modo de falha mapeia para o passo do loop que o previne.

| # | Modo de Falha | Sintoma | Passo que Prevê |
|---|---|---|---|
| 1 | **Pular classificação** | Responde pergunta como se fosse tarefa, ou vice-versa | Passo 0 |
| 2 | **Falso "pronto"** | Entrega sem critério de verificação nomeado | Passo 1 |
| 3 | **Memorizar em vez de ler** | API signature inventada, caminho errado, config key incorreta | Passo 2 regra 2 |
| 4 | **Sequencializar trabalho paralelizável** | 5 web fetches em série quando poderiam ser 1 lote | Passo 2 regra 3 |
| 5 | **Ignorar intenção** | "Corrige" código que estava certo para fazer teste (errado) passar | Passo 2 regra 6, Passo 4 regra 1 |
| 6 | **Engolir surpresa** | Contradição código vs. spec vs. teste: escolhe um lado silenciosamente | Passo 2 regra 7 |
| 7 | **Hiper-venda** | Várias abordagens listadas, nenhuma comprometida | Passo 3 |
| 8 | **Ação não autorizada** | Deploy, push ou envio sem permissão do usuário | Passo 3 (portão de autorização) |
| 9 | **Fantasia** | Palpite apresentado como processo rigoroso | Portão de ajuste |
| 10 | **Reescrita em vez de edição** | Arquivo inteiro reescrito quando 2 linhas bastavam | Passo 4 regra 4 |
| 11 | **Destruição cega** | Arquivo deletado/sobrescrito sem ver o conteúdo primeiro | Passo 4 regra 6 |
| 12 | **Dependência sorrateira** | Nova biblioteca adicionada sem instrução do usuário | Passo 4 regra 8 |
| 13 | **Verificação de teatro** | "Testes passam" sem ter executado, diff não conferido | Passo 5 |
| 14 | **Caso único** | Bug corrigido em um lugar, mesmo padrão ignorado em outros | Passo 5 (checagem gêmea) |
| 15 | **Enterro de má notícia** | Falha enterrada no meio do relatório, conclusão otimista primeiro | Passo 6 |
| 16 | **Seguimento fantasma** | "Próximos passos" que não emergiram do trabalho real | Passo 6 |
| 17 | **Detrito** | Arquivos temporários, prints de debug, código comentado deixados | Passo 6 |
| 18 | **Ciclo infinito** | Mesma abordagem tentada 4+ vezes sem mudança de estratégia | Passo 5 (limite de 3 ciclos) |
