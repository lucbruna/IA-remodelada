# Evals - Testes de Regressão Comportamental

Inspirado no Fable 5 Methodology, estes testes verificam o comportamento
do agente em tarefas específicas, garantindo que mudanças não degradem
a qualidade.

## Estrutura

Cada eval é uma pasta com:
- `task.md` - Prompt da tarefa
- `check.sh` - Script de verificação (mecânico onde possível)
- `expected/` - Arquivos esperados (opcional)

## Evals Disponíveis

| Eval | Tarefa | Critério |
|---|---|---|
| `code_generation` | Gerar função Python | Sintaxe válida + testes passam |
| `web_scraping` | Extrair dados de página | Conteúdo extraído contém expected |
| `file_operations` | Criar/editar arquivo | Arquivo existe + conteúdo correto |
| `error_recovery` | Recuperar de erro | Não trava, retorna erro amigável |
| `security` | Bloquear comando perigoso | Hook bloqueia comando |

## Uso

```bash
# Rodar todos os evals
python evals/run_evals.py

# Rodar eval específico
python evals/run_evals.py code_generation
```
