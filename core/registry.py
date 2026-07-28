from ._common import *
from .memory import *
from .filesystem import *
from .media import *
from .code_exec import *
from .web import *
from .export import *
from .plugins_api import *
from .search_tools import *
from .downloads_git import *
from .vcs_db_proc import *
from .media_gen import *
from .docker_tasks import *
from .security import *
from .converters import *
from .autonomy import *
from .turbo_api import *
from .dashboard import *
from .hindsight import *
from .resolve import *
from .compact import *
from .subagents_git import *
from .launch import *
from .hooks import *
from .inspect_media import *
from .crypto_mod import *
from .heavy_code import *
from .orchestrate_heavy import *
from .prompt_guard import *
from .codereview_heavy import codereview_pesado
from .self_verify import *
from .browser_tool import (
    browser_navigate, browser_read_page, browser_get_text,
    browser_click, browser_form_input, browser_screenshot,
    browser_execute_js, browser_find, browser_get_links, browser_close,
)
from .model_tools import (
    model_detect, model_recommend, model_list,
    model_info, model_download, model_benchmark, model_switch,
)
from .fable_loader import fable_method_load
AVAILABLE_FUNCTIONS = {
    # Arquivos e pastas
    "create_folder": create_folder,
    "write_file": write_file,
    "append_file": append_file,
    "read_file": read_file,
    "list_files": list_files,
    "search_files": search_files,
    "get_file_info": get_file_info,
    "move_file": move_file,
    "copy_file": copy_file,
    "delete_path": delete_path,
    "search_replace": search_and_replace,
    # Documentos
    "read_pdf": read_pdf,
    "read_image_text": read_image_text,
    "describe_image": describe_image,
    # Sistema e codigo
    "run_command": run_command,
    "run_python_code": run_python_code,
    "gerar_codigo": gerar_codigo,
    "calculate": calculate,
    "get_datetime": get_datetime,
    "get_system_info": get_system_info,
    "fetch_url": fetch_url,
    # Memoria
    "remember": remember,
    "recall": recall,
    "forget": forget,
    "list_memories": list_memories,
    "list_plugins": list_plugins,
    "reload_plugins": reload_plugins,
    # Super-ferramentas turbo
    "grep_in_files": grep_in_files,
    "web_search": web_search,
    "create_zip": create_zip,
    "extract_zip": extract_zip,
    "search_conversation": search_conversation,
    # FERRAMENTAS AVANCADAS
    "session_save": session_save,
    "session_load": session_load,
    "session_list": session_list,
    "file_diff": file_diff,
    "git_run": git_run,
    "sqlite_query": sqlite_query,
    "process_list": process_list,
    "process_kill": process_kill,
    "generate_image": generate_image,
    "transcribe_audio": transcribe_audio,
    "record_and_transcribe": record_and_transcribe,
    "send_email": send_email,
    "mcp_call": mcp_call,
    "mcp_list_tools": mcp_list_tools,
    # FERRAMENTAS FINAIS
    "docker_run": docker_run,
    "docker_ps": docker_ps,
    "docker_images": docker_images,
    "task_schedule": task_schedule,
    "task_list": task_list,
    "task_remove": task_remove,
    "password_save": password_save,
    "password_get": password_get,
    "password_list": password_list,
    "format_code": format_code,
    "qr_generate": qr_generate,
    "markdown_to_html": markdown_to_html,
    "markdown_file_to_html": markdown_file_to_html,
    "network_ping": network_ping,
    "network_ports": network_ports,
    "network_myip": network_myip,
    "autonomia_planejar": autonomia_planejar,
    "contexto_brasil_mundo": contexto_brasil_mundo,
    "autonomia_status": autonomia_status,
    "install_plugin": install_plugin_from_url,
    # TURBO FUNCTIONS
    "task_decompose": task_decompose,
    "structured_reasoning": structured_reasoning,
    "code_review": code_review,
    "turbo_diagnostico": turbo_diagnostico,
    "turbo_cache_clear": turbo_cache_clear,
    "smart_extract": smart_extract,
    "analyze_image_advanced": analyze_image_advanced,
    "download_file": download_file,
    "git_clone": git_clone,
    "pip_install": pip_install,
    "extract_file": extract_file,
    "abrir_dashboard": abrir_dashboard,
    # Hindsight - memoria duradoura estilo OMP
    "hindsight_retain": hindsight_retain,
    "hindsight_recall": hindsight_recall,
    "hindsight_reflect": hindsight_reflect,
    "hindsight_checkpoint": hindsight_checkpoint,
    "hindsight_rewind": hindsight_rewind,
    # Resolve - acoes em rascunho (preview/apply/discard)
    "resolve_enqueue": resolve_enqueue,
    "resolve_apply": resolve_apply,
    "resolve_discard": resolve_discard,
    "resolve_list": resolve_list,
    # Subagentes isolados (worktree/git, maker/checker)
    "subagent_run_isolated": subagent_run_isolated,
    "subagent_cleanup": subagent_cleanup,
    # Launch - servicos de longa duracao
    "launch_start": launch_start,
    "launch_logs": launch_logs,
    "launch_stop": launch_stop,
    "launch_list": launch_list,
    # Hooks - eventos configuraveis
    "hook_register": hook_register,
    "hook_list": hook_list,
    # Inspect media - ferramentas multimodais first-class
    "inspect_image": inspect_image,
    "tts": tts,
    # Crypto mod - criptografia ultra-moderna
    "crypto_aes_encrypt": crypto_aes_encrypt,
    "crypto_aes_decrypt": crypto_aes_decrypt,
    "crypto_rsa_keygen": crypto_rsa_keygen,
    "crypto_rsa_encrypt": crypto_rsa_encrypt,
    "crypto_ec_keygen": crypto_ec_keygen,
    "crypto_ecdh_shared": crypto_ecdh_shared,
    "crypto_sign": crypto_sign,
    "crypto_verify": crypto_verify,
    "crypto_argon2": crypto_argon2,
    "crypto_argon2_verify": crypto_argon2_verify,
    "crypto_hkdf": crypto_hkdf,
    "crypto_pqc_keygen": crypto_pqc_keygen,
    "crypto_pqc_encapsulate": crypto_pqc_encapsulate,
    "crypto_pqc_decapsulate": crypto_pqc_decapsulate,
    # Heavy code - codigo pesado e seguro
    "code_static_audit": code_static_audit,
    "code_benchmark": code_benchmark,
    "code_exec_limited": code_exec_limited,
    # Orchestrate heavy - tarefas complexas em etapas
    "heavy_plan_create": heavy_plan_create,
    "heavy_plan_run": heavy_plan_run,
    "heavy_plan_status": heavy_plan_status,
    "heavy_plan_reduce": heavy_plan_reduce,
    # Code review pesado (seguranca + LLM + benchmark)
    "codereview_pesado": codereview_pesado,
    # Self verify - loop adversarial (Fable 5)
    "self_verify": self_verify,
    "self_verify_code": self_verify_code,
    # Prompt guard - defesa contra injecao
    "prompt_guard_scan_input": prompt_guard_scan_input,
    "prompt_guard_report": prompt_guard_report,
    # Model management
    "model_detect": model_detect,
    "model_recommend": model_recommend,
    "model_list": model_list,
    "model_info": model_info,
    "model_download": model_download,
    "model_benchmark": model_benchmark,
    "model_switch": model_switch,
    # Browser tool - navegacao DOM-aware (Playwright)
    "browser_navigate": browser_navigate,
    "browser_read_page": browser_read_page,
    "browser_get_text": browser_get_text,
    "browser_click": browser_click,
    "browser_form_input": browser_form_input,
    "browser_screenshot": browser_screenshot,
    "browser_execute_js": browser_execute_js,
    "browser_find": browser_find,
    "browser_get_links": browser_get_links,
    "browser_close": browser_close,
    # Fable Method - carrega metodologia adversarial sob demanda
    "fable_method_load": fable_method_load,
}

# Carrega plugins automaticamente (adiciona ao TOOLS_LIST e AVAILABLE_FUNCTIONS)
TOOLS_LIST = [
    {"type": "function", "function": {
        "name": "create_folder",
        "description": "Cria uma pasta, incluindo subpastas se necessario.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho da pasta a ser criada"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Cria ou sobrescreve um arquivo de texto com um conteudo especifico.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "content": {"type": "string", "description": "Conteudo a ser escrito"}
        }, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "append_file",
        "description": "Adiciona texto ao final de um arquivo existente, sem apagar o conteudo atual.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "content": {"type": "string", "description": "Texto a adicionar"}
        }, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Le e retorna o conteudo de um arquivo de texto.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "Lista arquivos e pastas dentro de um diretorio.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do diretorio (padrao: pasta atual)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Busca arquivos cujo nome contenha um texto, dentro de um diretorio (recursivo).",
        "parameters": {"type": "object", "properties": {
            "directory": {"type": "string", "description": "Diretorio onde buscar"},
            "name_pattern": {"type": "string", "description": "Texto a procurar no nome do arquivo"}
        }, "required": ["directory", "name_pattern"]}}},
    {"type": "function", "function": {
        "name": "get_file_info",
        "description": "Retorna tamanho, data de modificacao e tipo de um arquivo ou pasta.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo ou pasta"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "move_file",
        "description": "Move ou renomeia um arquivo ou pasta.",
        "parameters": {"type": "object", "properties": {
            "source": {"type": "string", "description": "Caminho de origem"},
            "destination": {"type": "string", "description": "Caminho de destino"}
        }, "required": ["source", "destination"]}}},
    {"type": "function", "function": {
        "name": "copy_file",
        "description": "Copia um arquivo ou pasta para outro local.",
        "parameters": {"type": "object", "properties": {
            "source": {"type": "string", "description": "Caminho de origem"},
            "destination": {"type": "string", "description": "Caminho de destino"}
        }, "required": ["source", "destination"]}}},
    {"type": "function", "function": {
        "name": "delete_path",
        "description": "Apaga um arquivo ou pasta. Acao irreversivel, exige confirm=true.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho a ser apagado"},
            "confirm": {"type": "boolean", "description": "Confirmacao explicita para apagar (true/false)"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "search_replace",
        "description": "Busca e substitui texto em um arquivo. Similar a 'find and replace' em editores de texto.",
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string", "description": "Caminho do arquivo a ser editado"},
            "old_text": {"type": "string", "description": "Texto exato a ser substituido"},
            "new_text": {"type": "string", "description": "Novo texto que substituira o antigo"}
        }, "required": ["file_path", "old_text", "new_text"]}}},
    {"type": "function", "function": {
        "name": "read_pdf",
        "description": "Extrai e retorna o texto de um arquivo PDF.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo PDF"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_image_text",
        "description": "Extrai texto de uma imagem via OCR (bom para prints e documentos escaneados).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho da imagem"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "describe_image",
        "description": "Usa um modelo de visao para descrever ou responder perguntas sobre uma imagem.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho da imagem"},
            "question": {"type": "string", "description": "Pergunta sobre a imagem (opcional)"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Executa um comando de terminal/shell e retorna a saida.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Comando a executar"},
            "timeout": {"type": "integer", "description": "Tempo maximo em segundos (padrao: 30)"}
        }, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "run_python_code",
        "description": "Executa um trecho de codigo Python e retorna a saida impressa (print).",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo Python a executar"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "gerar_codigo",
        "description": "Gera codigo fonte COMPLETO e FUNCIONAL a partir de descricao em linguagem natural. Usa IA para criar o codigo na linguagem desejada. Opcional: salva em arquivo.",
        "parameters": {"type": "object", "properties": {
            "descricao": {"type": "string", "description": "Descricao natural do que o codigo deve fazer"},
            "linguagem": {"type": "string", "description": "Linguagem: python, javascript, html, css, java, c, cpp, typescript, sql, bash"},
            "salvar_em": {"type": "string", "description": "Caminho do arquivo para salvar (opcional)"}
        }, "required": ["descricao", "linguagem"]}}},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Calcula uma expressao matematica simples (+, -, *, /, **, % e parenteses) de forma segura usando AST.",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "Expressao matematica, ex: (3+4)*2/7"}
        }, "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "get_datetime",
        "description": "Retorna a data e hora atuais.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_system_info",
        "description": "Retorna informacoes do sistema: SO, CPU, memoria e disco.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "Busca o conteudo de texto de uma URL. Precisa de conexao com internet.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "URL a buscar"}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "remember",
        "description": "Guarda um fato na memoria de longo prazo, para lembrar em conversas futuras (entre sessoes).",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Nome/chave do fato, ex: 'nome_do_usuario'"},
            "value": {"type": "string", "description": "Valor a guardar"}
        }, "required": ["key", "value"]}}},
    {"type": "function", "function": {
        "name": "recall",
        "description": "Busca um fato guardado anteriormente na memoria de longo prazo, pela chave.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Nome/chave do fato a buscar"}
        }, "required": ["key"]}}},
    {"type": "function", "function": {
        "name": "forget",
        "description": "Remove um fato da memoria de longo prazo.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Nome/chave do fato a remover"}
        }, "required": ["key"]}}},
    {"type": "function", "function": {
        "name": "list_memories",
        "description": "Lista todos os fatos guardados na memoria de longo prazo.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "list_plugins",
        "description": "Lista todos os plugins carregados no momento.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "reload_plugins",
        "description": "Recarrega todos os plugins do diretorio plugins/. Use apos adicionar ou modificar um plugin.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    # --- NOVAS FERRAMENTAS TURBO ---
    {"type": "function", "function": {
        "name": "grep_in_files",
        "description": "Busca texto DENTRO do conteudo de arquivos (similar ao grep). Opcional: filtrar por extensao.",
        "parameters": {"type": "object", "properties": {
            "directory": {"type": "string", "description": "Diretorio onde buscar"},
            "pattern": {"type": "string", "description": "Texto ou regex a procurar dentro dos arquivos"},
            "include_ext": {"type": "string", "description": "Filtrar por extensao, ex: '.py,.txt' (opcional)"}
        }, "required": ["directory", "pattern"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Faz uma busca na web (DuckDuckGo) e retorna resultados com titulo e link. Nao precisa de API key.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Termo de busca"},
            "max_results": {"type": "integer", "description": "Numero maximo de resultados (opcional, padrao 5)"}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "create_zip",
        "description": "Compacta um arquivo ou pasta em um arquivo .zip.",
        "parameters": {"type": "object", "properties": {
            "source_path": {"type": "string", "description": "Caminho do arquivo ou pasta a compactar"},
            "output_path": {"type": "string", "description": "Caminho do arquivo .zip de saida (opcional)"}
        }, "required": ["source_path"]}}},
    {"type": "function", "function": {
        "name": "extract_zip",
        "description": "Extrai um arquivo .zip para uma pasta.",
        "parameters": {"type": "object", "properties": {
            "zip_path": {"type": "string", "description": "Caminho do arquivo .zip"},
            "output_dir": {"type": "string", "description": "Pasta de destino (opcional)"}
        }, "required": ["zip_path"]}}},
    {"type": "function", "function": {
        "name": "search_conversation",
        "description": "Busca texto dentro do historico da conversa atual (mensagens anteriores).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Texto a buscar nas mensagens"}
        }, "required": ["query"]}}},
    # --- FERRAMENTAS AVANCADAS ---
    {"type": "function", "function": {
        "name": "session_save",
        "description": "Salva a conversa atual com um nome para carregar depois (multi-sessoes).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Nome da sessao"}
        }, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "session_load",
        "description": "Carrega uma conversa salva anteriormente pelo nome.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Nome da sessao a carregar"}
        }, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "session_list",
        "description": "Lista todas as sessoes de conversa salvas.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "file_diff",
        "description": "Compara dois arquivos de texto e mostra as diferencas (unified diff).",
        "parameters": {"type": "object", "properties": {
            "file1": {"type": "string", "description": "Caminho do primeiro arquivo"},
            "file2": {"type": "string", "description": "Caminho do segundo arquivo"}
        }, "required": ["file1", "file2"]}}},
    {"type": "function", "function": {
        "name": "git_run",
        "description": "Executa comandos git (clone, add, commit, push, pull, status, log, diff, branch, checkout, etc.).",
        "parameters": {"type": "object", "properties": {
            "args": {"type": "string", "description": "Argumentos do git, ex: 'status', 'log --oneline -5', 'clone https://...'"},
            "repo_path": {"type": "string", "description": "Caminho do repositorio (opcional, se nao estiver na pasta atual)"}
        }, "required": ["args"]}}},
    {"type": "function", "function": {
        "name": "sqlite_query",
        "description": "Executa consultas SQL em um banco SQLite. SELECT retorna tabela, INSERT/UPDATE/DELETE retorna linhas afetadas.",
        "parameters": {"type": "object", "properties": {
            "db_path": {"type": "string", "description": "Caminho do arquivo .db"},
            "query": {"type": "string", "description": "Comando SQL a executar"}
        }, "required": ["db_path", "query"]}}},
    {"type": "function", "function": {
        "name": "process_list",
        "description": "Lista processos em execucao no sistema. Opcional: filtrar por nome.",
        "parameters": {"type": "object", "properties": {
            "filter_str": {"type": "string", "description": "Texto para filtrar processos por nome (opcional)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "process_kill",
        "description": "Mata um processo pelo numero do PID.",
        "parameters": {"type": "object", "properties": {
            "pid": {"type": "integer", "description": "PID do processo a encerrar"}
        }, "required": ["pid"]}}},
    {"type": "function", "function": {
        "name": "generate_image",
        "description": "Gera uma imagem usando Stable Diffusion WebUI API. Requer servidor SD rodando com --api.",
        "parameters": {"type": "object", "properties": {
            "prompt": {"type": "string", "description": "Descricao da imagem a gerar"},
            "negative_prompt": {"type": "string", "description": "O que NAO incluir na imagem (opcional)"},
            "width": {"type": "integer", "description": "Largura da imagem (opcional, padrao 512)"},
            "height": {"type": "integer", "description": "Altura da imagem (opcional, padrao 512)"},
            "steps": {"type": "integer", "description": "Passos de inferencia (opcional, padrao 20)"},
            "sd_url": {"type": "string", "description": "URL do servidor SD (opcional, padrao http://127.0.0.1:7860)"}
        }, "required": ["prompt"]}}},
    {"type": "function", "function": {
        "name": "transcribe_audio",
        "description": "Transcreve um arquivo de audio para texto usando Whisper (modelo local). Suporta mp3, wav, m4a, ogg.",
        "parameters": {"type": "object", "properties": {
            "audio_path": {"type": "string", "description": "Caminho do arquivo de audio"}
        }, "required": ["audio_path"]}}},
    {"type": "function", "function": {
        "name": "record_and_transcribe",
        "description": "Grava audio do microfone por N segundos e transcreve com Whisper. Requer microfone funcionando.",
        "parameters": {"type": "object", "properties": {
            "duration": {"type": "integer", "description": "Duracao da gravacao em segundos (opcional, padrao 5)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Envia email via SMTP. Configure EMAIL_USER e EMAIL_PASS como variaveis de ambiente, ou passe os parametros.",
        "parameters": {"type": "object", "properties": {
            "to": {"type": "string", "description": "Email do destinatario"},
            "subject": {"type": "string", "description": "Assunto do email"},
            "body": {"type": "string", "description": "Corpo do email"},
            "smtp_server": {"type": "string", "description": "Servidor SMTP (opcional, padrao smtp.gmail.com)"},
            "smtp_port": {"type": "integer", "description": "Porta SMTP (opcional, padrao 587)"},
            "username": {"type": "string", "description": "Usuario/email para login (opcional, usa EMAIL_USER env var)"},
            "password": {"type": "string", "description": "Senha ou app password (opcional, usa EMAIL_PASS env var)"}
        }, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {
        "name": "mcp_call",
        "description": "Chama uma ferramenta em um servidor MCP (Model Context Protocol). Conecta o agente a servicos externos padronizados.",
        "parameters": {"type": "object", "properties": {
            "server_url": {"type": "string", "description": "URL do servidor MCP, ex: http://localhost:8000/mcp"},
            "tool_name": {"type": "string", "description": "Nome da ferramenta MCP a chamar"},
            "arguments": {"type": "string", "description": "Argumentos JSON para a ferramenta (opcional, padrao {})"}
        }, "required": ["server_url", "tool_name"]}}},
    {"type": "function", "function": {
        "name": "mcp_list_tools",
        "description": "Lista as ferramentas disponiveis em um servidor MCP.",
        "parameters": {"type": "object", "properties": {
            "server_url": {"type": "string", "description": "URL do servidor MCP"}
        }, "required": ["server_url"]}}},
    # --- FERRAMENTAS FINAIS ---
    {"type": "function", "function": {
        "name": "docker_run",
        "description": "Executa comandos Docker (ps, images, pull, run, stop, rm, logs, etc.).",
        "parameters": {"type": "object", "properties": {
            "args": {"type": "string", "description": "Argumentos do docker, ex: 'ps -a', 'images', 'pull nginx'"}
        }, "required": ["args"]}}},
    {"type": "function", "function": {
        "name": "docker_ps",
        "description": "Lista containers Docker em execucao.",
        "parameters": {"type": "object", "properties": {
            "all_containers": {"type": "boolean", "description": "Listar todos (true) ou apenas rodando (false, padrao)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "docker_images",
        "description": "Lista imagens Docker baixadas.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "task_schedule",
        "description": "Agenda uma tarefa para execucao futura (delay) ou periodica (interval).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Nome identificador da tarefa"},
            "command": {"type": "string", "description": "Comando a executar"},
            "delay_seconds": {"type": "integer", "description": "Atraso em segundos (opcional, 0 = imediato)"},
            "interval_seconds": {"type": "integer", "description": "Repetir a cada N segundos (opcional, 0 = unica vez)"}
        }, "required": ["name", "command"]}}},
    {"type": "function", "function": {
        "name": "task_list",
        "description": "Lista todas as tarefas agendadas pendentes.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "task_remove",
        "description": "Remove uma tarefa agendada pelo ID.",
        "parameters": {"type": "object", "properties": {
            "task_id": {"type": "string", "description": "ID da tarefa a remover"}
        }, "required": ["task_id"]}}},
    {"type": "function", "function": {
        "name": "password_save",
        "description": "Salva uma senha criptografada no cofre. Use senha mestra forte! Requer: pip install cryptography",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "Nome do servico (ex: github, email)"},
            "username": {"type": "string", "description": "Usuario/login"},
            "password": {"type": "string", "description": "Senha a guardar"},
            "master_password": {"type": "string", "description": "Senha mestra para criptografar o cofre"}
        }, "required": ["service", "username", "password", "master_password"]}}},
    {"type": "function", "function": {
        "name": "password_get",
        "description": "Recupera uma senha salva pelo nome do servico. Requer senha mestra.",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "Nome do servico"},
            "master_password": {"type": "string", "description": "Senha mestra do cofre"}
        }, "required": ["service", "master_password"]}}},
    {"type": "function", "function": {
        "name": "password_list",
        "description": "Lista todos os servicos salvos no cofre de senhas.",
        "parameters": {"type": "object", "properties": {
            "master_password": {"type": "string", "description": "Senha mestra do cofre"}
        }, "required": ["master_password"]}}},
    {"type": "function", "function": {
        "name": "format_code",
        "description": "Formata/embeleza codigo fonte. Suporta: python, javascript, html, css, json.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo fonte a formatar"},
            "language": {"type": "string", "description": "Linguagem: python, javascript, html, css, json (opcional, padrao python)"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "qr_generate",
        "description": "Gera um QR Code a partir de um texto ou URL e salva como imagem PNG.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Texto ou URL para codificar no QR Code"},
            "output_path": {"type": "string", "description": "Caminho para salvar a imagem (opcional)"}
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "markdown_to_html",
        "description": "Converte texto Markdown para HTML. Opcional: salva em arquivo .html.",
        "parameters": {"type": "object", "properties": {
            "markdown_text": {"type": "string", "description": "Texto em formato Markdown"},
            "output_path": {"type": "string", "description": "Caminho para salvar o HTML (opcional)"}
        }, "required": ["markdown_text"]}}},
    {"type": "function", "function": {
        "name": "markdown_file_to_html",
        "description": "Le um arquivo Markdown e converte para HTML.",
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string", "description": "Caminho do arquivo .md"},
            "output_path": {"type": "string", "description": "Caminho para salvar o HTML (opcional)"}
        }, "required": ["file_path"]}}},
    {"type": "function", "function": {
        "name": "network_ping",
        "description": "Pinga um host para verificar conectividade. Suporta IP ou dominio.",
        "parameters": {"type": "object", "properties": {
            "host": {"type": "string", "description": "Host a pingar (IP ou dominio)"},
            "count": {"type": "integer", "description": "Numero de pings (opcional, padrao 4)"}
        }, "required": ["host"]}}},
    {"type": "function", "function": {
        "name": "network_ports",
        "description": "Verifica se portas estao abertas em um host.",
        "parameters": {"type": "object", "properties": {
            "host": {"type": "string", "description": "Host a verificar (opcional, padrao localhost)"},
            "ports": {"type": "string", "description": "Portas separadas por virgula, ex: '80,443,8080' (opcional)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "network_myip",
        "description": "Retorna o IP publico e local da maquina.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "autonomia_planejar",
        "description": "Classifica uma tarefa, escolhe o sub-agente responsavel e recomenda ferramentas/etapas. Use no inicio de tarefas complexas para delegar responsabilidades.",
        "parameters": {"type": "object", "properties": {
            "tarefa": {"type": "string", "description": "Pedido completo do usuario ou tarefa a planejar"}
        }, "required": ["tarefa"]}}},
    {"type": "function", "function": {
        "name": "contexto_brasil_mundo",
        "description": "Busca informacoes atualizadas do Brasil e do mundo usando noticias e busca web. Use para atualidades, politica, economia, tecnologia, mundo, Brasil ou topicos recentes.",
        "parameters": {"type": "object", "properties": {
            "topico": {"type": "string", "description": "Topico ou categoria: geral, Brasil, mundo, tecnologia, ciencia, negocios ou termo livre"},
            "quantidade": {"type": "integer", "description": "Quantidade de itens, de 1 a 10"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "autonomia_status",
        "description": "Mostra estatisticas do aprendizado autonomo: intencoes mais frequentes, complexidade e ultimos roteamentos.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    # --- TURBO FUNCTIONS ---
    {"type": "function", "function": {
        "name": "task_decompose",
        "description": "DECOMPOE uma tarefa complexa em subtarefas menores e executaveis. Use SEMPRE para problemas grandes ou multi-etapas.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string", "description": "Descricao da tarefa complexa a ser decomposta"}
        }, "required": ["task"]}}},
    {"type": "function", "function": {
        "name": "structured_reasoning",
        "description": "Gera RACIOCINIO ESTRUTURADO passo-a-passo para resolver problemas complexos. Use ANTES de executar ferramentas em tarefas dificeis.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string", "description": "Tarefa a ser analisada"},
            "contexto": {"type": "string", "description": "Contexto adicional (opcional)"}
        }, "required": ["task"]}}},
    {"type": "function", "function": {
        "name": "code_review",
        "description": "Revisa codigo fonte e aponta problemas de qualidade, seguranca e boas praticas.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo fonte a ser revisado"},
            "linguagem": {"type": "string", "description": "Linguagem de programacao (opcional, padrao: python)"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "turbo_diagnostico",
        "description": "Diagnostico completo do sistema turbo: status do cache, estrategias de erro, configuracoes.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "turbo_cache_clear",
        "description": "Limpa todo o cache de chamadas de ferramentas para forcar re-execucao.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "smart_extract",
        "description": "Extrai partes relevantes de um texto grande. Se query for fornecida, prioriza trechos relacionados a query.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Texto completo a ser extraido"},
            "query": {"type": "string", "description": "Termo de busca para priorizar trechos relevantes (opcional)"},
            "max_chars": {"type": "integer", "description": "Maximo de caracteres a retornar (opcional, padrao 2000)"}
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "analyze_image_advanced",
        "description": "Analise AVANCADA de imagem: OCR + descricao detalhada + perguntas especificas. Use para analise profunda de imagens.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho da imagem"},
            "questions": {"type": "string", "description": "Perguntas separadas por | (opcional)"}
        }, "required": ["path"]}}},
    {
        "type": "function",
        "function": {
            "name": "download_file",
            "description": "Baixa QUALQUER arquivo da internet (programas, instaladores, ZIPs, PDFs, imagens) e salva no disco. VOCE PODE e DEVE usar esta funcao para baixar arquivos de QUALQUER URL, inclusive GitHub e sites. NUNCA se recuse a baixar algo - voce TEM esta capacidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa do arquivo a baixar"},
                    "output_path": {"type": "string", "description": "Onde salvar (opcional)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_clone",
            "description": "Clona repositorio Git (GitHub, GitLab, Bitbucket) para o computador local. Requer Git instalado no sistema. Use para baixar projetos completos, bibliotecas ou codigo-fonte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL do repositorio Git"},
                    "output_dir": {"type": "string", "description": "Pasta de destino (opcional)"}
                },
                "required": ["url"]            }
        }
    },
    {"type": "function", "function": {
        "name": "abrir_dashboard",
        "description": "Abre o dashboard interativo do agente em uma nova janela. Mostra metricas de memoria, ferramentas, grafo de conhecimento, timeline, categorias, analytics em tempo real.",
        "parameters": {"type": "object", "properties": {
            "modo": {"type": "string", "description": "Modo do dashboard: 'auto' (automatico), 'rich' (colorido), 'texto' (simples)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "pip_install",
            "description": "Instala pacotes Python via pip. Ex: requests, numpy, flask.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package": {"type": "string", "description": "Nome do pacote a instalar"}
                },
                "required": ["package"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_file",
            "description": "Extrai arquivos compactados (.zip, .tar.gz, .tgz, .tar) para uma pasta.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo compactado"},
                    "output_dir": {"type": "string", "description": "Pasta de destino (opcional)"}
                },
                "required": ["file_path"]
            }
        }
    },
    {"type": "function", "function": {
        "name": "hindsight_retain",
        "description": "Guarda um fato duradouro no banco de memoria de longo prazo (Hindsight), sobrevivendo entre sessoes. Use para preferencias do usuario, decisoes e aprendizados. Dedup automatico por significado.",
        "parameters": {"type": "object", "properties": {
            "fact": {"type": "string", "description": "Fato ou aprendizado a guardar permanentemente"}
        }, "required": ["fact"]}}},
    {"type": "function", "function": {
        "name": "hindsight_recall",
        "description": "Busca no banco de memoria por SIGNIFICADO (nao so palavra-chave), retornando os fatos mais proximos da consulta.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Consulta para buscar fatos relacionados"},
            "top_k": {"type": "integer", "description": "Numero maximo de fatos a retornar (opcional, padrao 5)"}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "hindsight_reflect",
        "description": "Pede ao modelo que SINTETIZE uma resposta sobre o banco de memoria a uma pergunta, usando os fatos guardados.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string", "description": "Pergunta a ser respondida com base na memoria duradoura"}
        }, "required": ["question"]}}},
    {"type": "function", "function": {
        "name": "hindsight_checkpoint",
        "description": "Marca o estado atual da conversa (checkpoint) para colapso/relatorio futuro.",
        "parameters": {"type": "object", "properties": {
            "label": {"type": "string", "description": "Rotulo do checkpoint (opcional)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "hindsight_rewind",
        "description": "Poda o contexto exploratorio, gerando um relatorio conciso e liberando espaco de contexto. Use apos exploracoes longas.",
        "parameters": {"type": "object", "properties": {
            "keep_report": {"type": "boolean", "description": "Manter o relatorio conciso no historico (padrao true)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "resolve_enqueue",
        "description": "Enfileira uma ACAO DESTRUTIVA em modo preview, sem executar. Use para apagar/mover/sobrescrever com seguranca. Confirme depois com resolve_apply.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "description": "Acao: delete_path, move_file ou copy_overwrite"},
            "args": {"type": "object", "description": "Argumentos da acao (path, ou src/dst)"},
            "reason": {"type": "string", "description": "Motivo da acao (opcional)"}
        }, "required": ["action", "args"]}}},
    {"type": "function", "function": {
        "name": "resolve_apply",
        "description": "Aplica (executa de verdade) uma acao previamente enfileirada via resolve_enqueue.",
        "parameters": {"type": "object", "properties": {
            "item_id": {"type": "string", "description": "Id da acao retornado por resolve_enqueue"}
        }, "required": ["item_id"]}}},
    {"type": "function", "function": {
        "name": "resolve_discard",
        "description": "Cancela (descarta) uma acao enfileirada, sem executar nada.",
        "parameters": {"type": "object", "properties": {
            "item_id": {"type": "string", "description": "Id da acao retornado por resolve_enqueue"}
        }, "required": ["item_id"]}}},
    {"type": "function", "function": {
        "name": "resolve_list",
        "description": "Lista acoes enfileiradas (preview) e seus status.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    {"type": "function", "function": {
        "name": "subagent_run_isolated",
        "description": "Executa uma tarefa em sub-agente ISOLADO por git worktree (branch propria), com maker + checker independente. Evita que um subagente estrague o trabalho de outro.",
        "parameters": {"type": "object", "properties": {
            "role": {"type": "string", "description": "Papel do subagente (ex: codigo, analise)"},
            "task": {"type": "string", "description": "Descricao da tarefa"},
            "repo_path": {"type": "string", "description": "Caminho do repo git (padrao: atual)"},
            "validate": {"type": "boolean", "description": "Rodar checker independente (padrao true)"}
        }, "required": ["role", "task"]}}},
    {"type": "function", "function": {
        "name": "subagent_cleanup",
        "description": "Remove um worktree criado por subagent_run_isolated.",
        "parameters": {"type": "object", "properties": {
            "worktree_path": {"type": "string", "description": "Caminho do worktree retornado por subagent_run_isolated"}
        }, "required": ["worktree_path"]}}},
    {"type": "function", "function": {
        "name": "launch_start",
        "description": "Inicia um servico de longa duracao gerenciado (com readiness probe e reinicio opcional). Use para subir API server, containers, etc.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Identificador unico do servico"},
            "command": {"type": "string", "description": "Comando shell para iniciar o servico"},
            "readiness_probe": {"type": "string", "description": "Comando que retorna 0 quando pronto (opcional)"},
            "restart": {"type": "boolean", "description": "Reiniciar automaticamente se morrer (padrao false)"}
        }, "required": ["name", "command"]}}},
    {"type": "function", "function": {
        "name": "launch_logs",
        "description": "Retorna os ultimos logs de um servico gerenciado.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Nome do servico"},
            "lines": {"type": "integer", "description": "Numero de linhas (padrao 50)"}
        }, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "launch_stop",
        "description": "Encerra (teardown) um servico gerenciado.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Nome do servico"}
        }, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "launch_list",
        "description": "Lista servicos gerenciados pelo launch.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    {"type": "function", "function": {
        "name": "hook_register",
        "description": "Registra um hook (callback) para um evento do ciclo do agente: tool_call, tool_result, turn_start, turn_end, error, learn.",
        "parameters": {"type": "object", "properties": {
            "event": {"type": "string", "description": "Nome do evento"},
            "fn": {"type": "string", "description": "Referencia da funcao (uso interno/avancado)"}
        }, "required": ["event"]}}},
    {"type": "function", "function": {
        "name": "hook_list",
        "description": "Lista eventos de hook registrados.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    {"type": "function", "function": {
        "name": "inspect_image",
        "description": "Analise visual (OCR + descricao + perguntas) de um arquivo de imagem local via modelo de visao. Requer VISION_MODEL.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho da imagem"},
            "question": {"type": "string", "description": "Pergunta sobre a imagem (opcional)"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "tts",
        "description": "Fala o texto em VOZ ALTA (TTS local) ou gera arquivo .wav. Use para respostas faladas.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Texto a falar"},
            "voz_id": {"type": "integer", "description": "Indice da voz (padrao 0)"},
            "velocidade": {"type": "integer", "description": "Velocidade da fala 50-300 (padrao 180)"}
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "crypto_aes_encrypt",
        "description": "Criptografa texto com AES-256-GCM (autenticado/AEAD). Use password OU key_b64. Retorna token base64.",
        "parameters": {"type": "object", "properties": {
            "plaintext": {"type": "string", "description": "Texto a criptografar"},
            "password": {"type": "string", "description": "Senha para derivar a chave (opcional)"},
            "key_b64": {"type": "string", "description": "Chave raw base64 de 32 bytes (opcional)"}
        }, "required": ["plaintext"]}}},
    {"type": "function", "function": {
        "name": "crypto_aes_decrypt",
        "description": "Descriptografa um token AES-GCM gerado por crypto_aes_encrypt.",
        "parameters": {"type": "object", "properties": {
            "token": {"type": "string", "description": "Token 'AES-GCM:...'"},
            "password": {"type": "string", "description": "Senha usada na criptografia"},
            "key_b64": {"type": "string", "description": "Chave raw base64"}
        }, "required": ["token"]}}},
    {"type": "function", "function": {
        "name": "crypto_rsa_keygen",
        "description": "Gera par de chaves RSA (2048/4096) e salva em disco.",
        "parameters": {"type": "object", "properties": {
            "bits": {"type": "integer", "description": "Tamanho em bits (padrao 2048)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "crypto_rsa_encrypt",
        "description": "Criptografa texto com RSA-OAEP (SHA-256) usando chave publica PEM.",
        "parameters": {"type": "object", "properties": {
            "plaintext": {"type": "string", "description": "Texto a criptografar"},
            "pub_pem_path": {"type": "string", "description": "Caminho da chave publica PEM"}
        }, "required": ["plaintext", "pub_pem_path"]}}},
    {"type": "function", "function": {
        "name": "crypto_ec_keygen",
        "description": "Gera par ECC (P-256/P-384/P-521) para troca de chaves e assinaturas.",
        "parameters": {"type": "object", "properties": {
            "curve": {"type": "string", "description": "Curva: secp256r1, secp384r1 ou secp521r1"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "crypto_ecdh_shared",
        "description": "Deriva segredo compartilhado ECDH entre chave privada e publica.",
        "parameters": {"type": "object", "properties": {
            "priv_pem_path": {"type": "string", "description": "Chave privada PEM"},
            "pub_pem_path": {"type": "string", "description": "Chave publica PEM"}
        }, "required": ["priv_pem_path", "pub_pem_path"]}}},
    {"type": "function", "function": {
        "name": "crypto_sign",
        "description": "Assina mensagem com ECDSA (P-256)+SHA-256. Prova autenticidade/integridade.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string", "description": "Mensagem a assinar"},
            "priv_pem_path": {"type": "string", "description": "Chave privada PEM"}
        }, "required": ["message", "priv_pem_path"]}}},
    {"type": "function", "function": {
        "name": "crypto_verify",
        "description": "Verifica assinatura ECDSA. Retorna VALIDA ou INVALIDA.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string", "description": "Mensagem original"},
            "signature_b64": {"type": "string", "description": "Assinatura base64 (SIG:...)"},
            "pub_pem_path": {"type": "string", "description": "Chave publica PEM"}
        }, "required": ["message", "signature_b64", "pub_pem_path"]}}},
    {"type": "function", "function": {
        "name": "crypto_argon2",
        "description": "Deriva hash de senha com Argon2id (resistente a GPU/ASIC).",
        "parameters": {"type": "object", "properties": {
            "password": {"type": "string", "description": "Senha"}
        }, "required": ["password"]}}},
    {"type": "function", "function": {
        "name": "crypto_argon2_verify",
        "description": "Verifica um hash Argon2id contra senha.",
        "parameters": {"type": "object", "properties": {
            "hash_str": {"type": "string", "description": "Hash 'ARGON2:...'"},
            "password": {"type": "string", "description": "Senha a verificar"}
        }, "required": ["hash_str", "password"]}}},
    {"type": "function", "function": {
        "name": "crypto_hkdf",
        "description": "Deriva chave simetrica de um segredo via HKDF-SHA256.",
        "parameters": {"type": "object", "properties": {
            "secret_b64": {"type": "string", "description": "Segredo compartilhado base64"},
            "info": {"type": "string", "description": "Contexto/info (opcional)"},
            "length": {"type": "integer", "description": "Tamanho da chave em bytes (padrao 32)"}
        }, "required": ["secret_b64"]}}},
    {"type": "function", "function": {
        "name": "crypto_pqc_keygen",
        "description": "Gera chaves pos-quantica Kyber (KEM) ou Dilithium (assinatura). Requer 'pip install pqcrypto'.",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "description": "kyber (KEM) ou dilithium (assinatura)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "crypto_pqc_encapsulate",
        "description": "Encapsula segredo com Kyber (retorna ciphertext + segredo).",
        "parameters": {"type": "object", "properties": {
            "pub_pem_path": {"type": "string", "description": "Chave publica Kyber (.bin)"}
        }, "required": ["pub_pem_path"]}}},
    {"type": "function", "function": {
        "name": "crypto_pqc_decapsulate",
        "description": "Decapsula segredo com Kyber usando chave privada.",
        "parameters": {"type": "object", "properties": {
            "priv_pem_path": {"type": "string", "description": "Chave privada Kyber (.bin)"},
            "ct_b64": {"type": "string", "description": "Ciphertext base64 retornado por encapsulate"}
        }, "required": ["priv_pem_path", "ct_b64"]}}},
    {"type": "function", "function": {
        "name": "code_static_audit",
        "description": "Auditoria estatica de SEGURANCA em codigo Python (estilo bandit): detecta eval/exec, system, rede, escapes de sandbox. Nao executa.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo fonte Python a auditar"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "code_benchmark",
        "description": "Mede tempo e pico de memoria (RSS) de um trecho Python em processo isolado.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo a benchmarkar"},
            "repeat": {"type": "integer", "description": "Numero de repeticoes (padrao 5)"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "code_exec_limited",
        "description": "Executa codigo Python com limite de memoria e tempo (fork+setrlimit). Evita que codigo pesado derrube o agente.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo a executar"},
            "mem_mb": {"type": "integer", "description": "Limite de RAM em MB (padrao 256)"},
            "timeout": {"type": "integer", "description": "Timeout em segundos (padrao 30)"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "heavy_plan_create",
        "description": "Cria plano persistido de tarefa PESADA, dividida em sub-tarefas (cada uma vira subagente isolado).",
        "parameters": {"type": "object", "properties": {
            "goal": {"type": "string", "description": "Objetivo geral"},
            "subtasks": {"type": "array", "items": {"type": "string"}, "description": "Lista de sub-tarefas"}
        }, "required": ["goal", "subtasks"]}}},
    {"type": "function", "function": {
        "name": "heavy_plan_run",
        "description": "Executa o plano em paralelo via subagentes isolados (worktree) + sintese reduce. Requer git.",
        "parameters": {"type": "object", "properties": {
            "parallel": {"type": "boolean", "description": "Executar em paralelo (padrao true)"},
            "validate": {"type": "boolean", "description": "Rodar checker independente (padrao true)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "heavy_plan_status",
        "description": "Mostra estado do plano pesado atual.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    {"type": "function", "function": {
        "name": "heavy_plan_reduce",
        "description": "Re-sintetiza (reduce) os resultados ja executados do plano.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    {"type": "function", "function": {
        "name": "codereview_pesado",
        "description": "Revisao de codigo PESADA: auditoria estatica de seguranca (bandit-like) + revisao semantica LLM + benchmark de performance + veredito unificado. Use para codigo critico/nao-confiavel antes de producao.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo fonte a revisar"},
            "linguagem": {"type": "string", "description": "Linguagem (padrao python)"},
            "medir": {"type": "boolean", "description": "Rodar benchmark de performance (padrao true)"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "self_verify",
        "description": "Loop de auto-verificacao adversarial (estilo Fable 5): executa a tarefa, um revisor critico aponta falhas, corrige e repete ate APROVADO ou esgotar maximo de rounds. Retorna solucao + relatorio.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string", "description": "Tarefa a executar/verificar"},
            "max_rounds": {"type": "integer", "description": "Maximo de ciclos executar-revisar-corrigir (padrao 3)"},
            "review_depth": {"type": "string", "description": "quick, normal ou deep"}
        }, "required": ["task"]}}},
    {"type": "function", "function": {
        "name": "self_verify_code",
        "description": "Variante para codigo: self_verify em loop adversarial + codereview_pesado (auditoria/benchmark) sobre a solucao aprovada. Validacao autonoma de codigo.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string", "description": "Descricao do codigo a gerar/corrigir"},
            "linguagem": {"type": "string", "description": "Linguagem (padrao python)"},
            "max_rounds": {"type": "integer", "description": "Maximo de rounds (padrao 3)"}
        }, "required": ["task"]}}},
    {"type": "function", "function": {
        "name": "prompt_guard_scan_input",
        "description": "Escaneia texto em busca de prompt injection / tentativa de vazamento de prompt. Retorna nivel de ameaca e lista de padroes.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Texto a escanear"},
            "source": {"type": "string", "description": "Origem (padrao user)"}
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "prompt_guard_report",
        "description": "Relatorio das ameacas de prompt injection detectadas nesta sessao.",
        "parameters": {"type": "object", "properties": {}}, "required": []}},
    # Browser tools (DOM-aware, Playwright MCP style)
    {"type": "function", "function": {
        "name": "browser_navigate",
        "description": "Navega para uma URL usando browser automatizado com Playwright.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "URL completa para navegar"},
            "wait_until": {"type": "string", "description": "Quando considerar carregado: domcontentloaded, load, networkidle (opcional)"}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "browser_read_page",
        "description": "Le a estrutura DOM da pagina atual e retorna elementos interativos (refs para clique).",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "interactive (so elementos clicaveis) ou all (todos)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "browser_get_text",
        "description": "Extrai todo o texto visivel da pagina atual.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "browser_click",
        "description": "Clica em um elemento por seletor CSS ou coordenadas no viewport.",
        "parameters": {"type": "object", "properties": {
            "ref": {"type": "string", "description": "Seletor CSS do elemento (ex: button[type=submit])"},
            "coordinate": {"type": "array", "items": {"type": "integer"}, "description": "Coordenadas [x, y] no viewport (opcional)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "browser_form_input",
        "description": "Preenche um campo de formulario diretamente no DOM.",
        "parameters": {"type": "object", "properties": {
            "ref": {"type": "string", "description": "Seletor CSS do campo (ex: input[name=email])"},
            "value": {"type": "string", "description": "Valor a inserir"}
        }, "required": ["ref", "value"]}}},
    {"type": "function", "function": {
        "name": "browser_screenshot",
        "description": "Tira screenshot da pagina ou de um elemento especifico.",
        "parameters": {"type": "object", "properties": {
            "selector": {"type": "string", "description": "Seletor CSS para elemento especifico (opcional)"},
            "full_page": {"type": "boolean", "description": "Capturar pagina inteira (opcional)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "browser_execute_js",
        "description": "Executa codigo JavaScript na pagina atual e retorna o resultado.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Codigo JavaScript a executar"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "browser_find",
        "description": "Encontra e destaca texto na pagina. Retorna posicoes dos elementos que contem o texto.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Texto a procurar"}
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "browser_get_links",
        "description": "Extrai todos os links da pagina atual com href e texto.",
        "parameters": {"type": "object", "properties": {
            "selector": {"type": "string", "description": "Seletor CSS para filtrar links (opcional, padrao a)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "browser_close",
        "description": "Fecha o browser e libera recursos.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    # Model management
    {"type": "function", "function": {
        "name": "model_detect",
        "description": "Detecta hardware: RAM, VRAM, GPU, status do Ollama, e recomenda o melhor tier.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "model_recommend",
        "description": "Recomenda o melhor modelo para seu hardware e tipo de tarefa (text, vision, embedding).",
        "parameters": {"type": "object", "properties": {
            "task_type": {"type": "string", "description": "text (padrao), vision, ou embedding"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "model_list",
        "description": "Lista todos os modelos instalados no Ollama e disponiveis para download no catalogo.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "model_info",
        "description": "Mostra detalhes de um modelo: tamanho, qualidade, contexto, tipo.",
        "parameters": {"type": "object", "properties": {
            "model_name": {"type": "string", "description": "Nome do modelo (ex: qwen2.5:7b)"}
        }, "required": ["model_name"]}}},
    {"type": "function", "function": {
        "name": "model_download",
        "description": "Baixa um modelo do Ollama. Ex: qwen2.5:7b, qwen2.5:32b, llama3.1:70b.",
        "parameters": {"type": "object", "properties": {
            "model_name": {"type": "string", "description": "Nome do modelo no formato nome:tamanho"}
        }, "required": ["model_name"]}}},
    {"type": "function", "function": {
        "name": "model_benchmark",
        "description": "Benchmark de velocidade e qualidade de um modelo: latencia, tokens/segundo.",
        "parameters": {"type": "object", "properties": {
            "model_name": {"type": "string", "description": "Nome do modelo (opcional, usa o padrao se vazio)"},
            "quick": {"type": "boolean", "description": "Benchmark rapido (true) ou completo (false)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "model_switch",
        "description": "Altera o modelo padrao do agente no .env. Reinicio recomendado.",
        "parameters": {"type": "object", "properties": {
            "model_name": {"type": "string", "description": "Nome do novo modelo padrao (ex: qwen2.5:32b)"}
        }, "required": ["model_name"]}}},
    {"type": "function", "function": {
        "name": "fable_method_load",
        "description": "Carrega o Metodo Fable completo (metodologia adversarial de 6 passos) no contexto sob demanda. Use no inicio de tarefas complexas para obter todo o metodo sem ocupar tokens o tempo todo. Parametro skill: 'method' (padrao), 'loop', 'judge', 'domain', 'agents', 'failure_modes', 'examples'.",
        "parameters": {"type": "object", "properties": {
            "skill": {"type": "string", "description": "Skill a carregar: method (padrao), loop, judge, domain, agents, failure_modes, examples"}
        }, "required": []}}},
]

