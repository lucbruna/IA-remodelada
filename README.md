# IA Remodelada

Agente local inteligente com suporte a plugins, turbo mode, ensemble de modelos, e mais de 35 plugins para processamento de código, imagens, documentos, redes, backup e automação.

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.ai) com modelo `qwen2.5:1.5b` (ou superior)
- Git (para clonagem de repositórios)

## Instalação

```bash
pip install -r requirements.txt
ollama pull qwen2.5:1.5b
```

## Uso

```bash
python agente_cli.py      # Interface de linha de comando
python agente_gui.py      # Interface gráfica (Tkinter)
python agente_api_server.py  # Servidor REST API
python agente_dashboard.py   # Dashboard Rich
```

## Plugins

O sistema carrega automaticamente plugins do diretório `plugins/`. São mais de 35 plugins cobrindo:

- Download e scraping web
- Processamento de imagens (OCR, redimensionamento, filtros)
- Análise e geração de código
- Banco de dados SQLite
- Documentos (DOCX, XLSX, CSV)
- Visualização de dados (gráficos matplotlib)
- Segurança (hash, criptografia, varredura)
- Áudio (conversão, metadados)
- Rede (ping, DNS, port scan, WHOIS)
- Backup e restauração
- E muitos mais...

## Turbo Mode

O módulo `agente_turbo.py` adiciona inteligência avançada:
- Chain-of-thought reasoning
- Task decomposition
- Code review automático
- Error recovery
- Cache inteligente de ferramentas
- Smart context compression
