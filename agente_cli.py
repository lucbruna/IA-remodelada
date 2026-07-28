"""
agente_cli.py
==============
Versao TERMINAL do agente, com cores e formatação profissional.
Lembra de conversas anteriores, tem memoria de longo prazo,
encadeia varias ferramentas quando precisa, e mostra em tempo
real cada acao que esta executando.

REQUISITOS:
  pip install ollama requests psutil PyPDF2 pillow pytesseract

COMO RODAR:
  python agente_cli.py

COMANDOS ESPECIAIS:
  sair / exit / quit  -> encerra o programa
  nova conversa       -> limpa o historico da tela (a memoria de fatos continua)
  /memorias           -> lista todos os fatos guardados na memoria
  /ajuda              -> mostra esta mensagem de ajuda
"""

import os
import sys
import shutil

from typing import Optional

from agente_core import (
    SYSTEM_PROMPT,
    MODEL,
    ensure_ollama,
    run_agent_turn,
    load_conversation_history,
    list_memories,
    export_conversation_markdown,
    export_conversation_html,
    list_plugins,
    reload_plugins,
    search_conversation,
    session_save,
    session_load,
    session_list,
    run_memory_pipeline,
    turbo_diagnostico,
    turbo_cache_clear,
    task_decompose,
    structured_reasoning,
    code_review,
)


# ─── Modelos disponíveis ────────────────────────────────────────────
def get_available_ollama_models() -> list:
    """Lista todos os modelos disponíveis no Ollama local."""
    try:
        import ollama
        response = ollama.list()
        raw_models = response.get("models", []) if hasattr(response, "get") else getattr(response, "models", [])
        models = []
        for m in raw_models:
            if hasattr(m, "model_dump"):
                d = m.model_dump()
            elif isinstance(m, dict):
                d = m
            else:
                d = {}
            name = d.get("name") or d.get("model") or "?"
            size_bytes = d.get("size", 0) or 0
            size_gb = size_bytes / (1024**3)
            models.append({
                "name": name,
                "display": f"{name} ({size_gb:.1f} GB)" if size_gb > 0 else name,
                "size_gb": size_gb,
            })
        models.sort(key=lambda x: x["size_gb"])
        return models
    except Exception:
        return []


def update_env_model(model_name: str) -> bool:
    """Atualiza o modelo no arquivo .env."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    lines = []
    found = False

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("AGENTE_MODEL="):
                    lines.append(f"AGENTE_MODEL={model_name}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.insert(0, f"AGENTE_MODEL={model_name}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Atualiza variável de ambiente em runtime
    os.environ["AGENTE_MODEL"] = model_name
    return True


# =======================================================================
# CORES PARA O TERMINAL (compativel Windows e Unix)
# =======================================================================

class Cores:
    """Cores ANSI com fallback para Windows que nao suporta."""
    _suporta_cor = sys.stdout.isatty()

    if _suporta_cor:
        AZUL = "\033[1;34m"
        VERDE = "\033[1;32m"
        AMARELO = "\033[1;33m"
        VERMELHO = "\033[1;31m"
        CIANO = "\033[1;36m"
        MAGENTA = "\033[1;35m"
        CINZA = "\033[2;37m"
        BEGE = "\033[93m"
        BRANCO = "\033[1;37m"
        RESET = "\033[0m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        FUNDO_AZUL = "\033[44m"
    else:
        AZUL = VERDE = AMARELO = VERMELHO = ""
        CIANO = MAGENTA = CINZA = BEGE = BRANCO = ""
        RESET = BOLD = DIM = FUNDO_AZUL = ""


def _get_terminal_cols() -> int:
    """Obtem a largura do terminal de forma segura."""
    try:
        cols = shutil.get_terminal_size().columns
        return max(cols, 40)  # nunca menos que 40 colunas
    except Exception:
        return 60  # fallback


def print_colored(text: str, color: str = Cores.BRANCO, prefix: str = "") -> None:
    """Imprime texto colorido no terminal."""
    if prefix:
        print(f"{color}{prefix}{Cores.RESET} {text}")
    else:
        try:
            print(f"{color}{text}{Cores.RESET}")
        except UnicodeEncodeError:
            safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
            print(f"{color}{safe}{Cores.RESET}")


def print_separador() -> None:
    """Imprime uma linha separadora."""
    cols = _get_terminal_cols()
    try:
        print(f"{Cores.CINZA}{'─' * cols}{Cores.RESET}")
    except UnicodeEncodeError:
        safe = ('-' * cols).encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
        print(f"{Cores.CINZA}{safe}{Cores.RESET}")


def _exibir_boas_vindas() -> None:
    """Exibe a tela de boas-vindas formatada."""
    cols = _get_terminal_cols()
    largura_interna = min(cols - 2, 56)
    print()
    try:
        print_colored("╔" + "═" * largura_interna + "╗", Cores.CIANO)
        print_colored("║" + " " * largura_interna + "║", Cores.CIANO)
        print_colored(f"║{'🤖 Agente Local':^{largura_interna}}║", Cores.CIANO)
        print_colored(f"║{'Modelo: ' + MODEL:^{largura_interna}}║", Cores.CINZA)
        print_colored("║" + " " * largura_interna + "║", Cores.CIANO)
        print_colored("╚" + "═" * largura_interna + "╝", Cores.CIANO)
    except UnicodeEncodeError:
        print_colored("+" + "=" * largura_interna + "+", Cores.CIANO)
        print_colored("|" + " " * largura_interna + "|", Cores.CIANO)
        print_colored(f"|{'Agente Local':^{largura_interna}}|", Cores.CIANO)
        print_colored(f"|{'Modelo: ' + MODEL:^{largura_interna}}|", Cores.CINZA)
        print_colored("|" + " " * largura_interna + "|", Cores.CIANO)
        print_colored("+" + "=" * largura_interna + "+", Cores.CIANO)
    print()
    print_colored("Comandos: 'sair' para encerrar | 'nova conversa' para reiniciar | '/ajuda' para ajuda", Cores.CINZA)
    print()


def _configurar_autocomplete() -> None:
    """Configura autocomplete com readline se disponivel."""
    try:
        import readline
    except ImportError:
        return  # readline nao disponivel no Windows nativo

    COMANDOS = [
        "sair", "exit", "quit",
        "nova conversa",
        "/memorias",
        "/plugins", "/plugins-reload",
        "/export-md", "/export-html",
        "/ajuda", "/help",
        "/conversa-buscar",
        "/subagente",
        "/session salvar", "/session carregar", "/session listar",
        "/voz",
        "/memoria-status", "/memoria-buscar", "/perfil", "/grafo",
        "/turbo", "/turbo-cache", "/turbo-decompor", "/turbo-raciocinar",
        "/turbo-revisar",
    ]

    def completer(text: str, state: int) -> Optional[str]:
        opcoes = [cmd for cmd in COMANDOS if cmd.startswith(text.lower())]
        if state < len(opcoes):
            return opcoes[state]
        return None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")

def chat_loop():
    # Tenta iniciar o Ollama automaticamente se nao estiver rodando
    if not ensure_ollama():
        print_colored("⚠ Ollama nao esta rodando. Execute 'ollama serve' em outro terminal.", Cores.AMARELO)
        print_colored("  Ou inicie manualmente e execute este programa novamente.", Cores.CINZA)

    history = load_conversation_history()
    if history:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            m for m in history if m.get("role") != "system"
        ]
        print_colored(f"Histórico anterior carregado ({len(history)} mensagens).", Cores.CINZA)
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # --- Boas vindas ---
    _exibir_boas_vindas()
    _configurar_autocomplete()

    while True:
        try:
            user_input = input(f"{Cores.VERDE}Você{Cores.RESET} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Cores.AMARELO}Até mais! (histórico e memória salvos){Cores.RESET}")
            break

        if not user_input:
            continue

        # Comandos especiais
        if user_input.lower() in ("sair", "exit", "quit"):
            print(f"\n{Cores.AMARELO}Até mais! (histórico e memória salvos){Cores.RESET}")
            break

        if user_input.lower() == "nova conversa":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print_colored("Conversa reiniciada (memória de fatos continua guardada).", Cores.CINZA)
            print()
            continue

        if user_input.lower() == "/memorias":
            print_colored("\n📝 MEMÓRIAS DE LONGO PRAZO:", Cores.MAGENTA)
            print_colored(list_memories(), Cores.CINZA)
            print()
            continue

        if user_input.lower() == "/plugins":
            print_colored("\n🔌 PLUGINS CARREGADOS:", Cores.MAGENTA)
            print_colored(list_plugins(), Cores.CINZA)
            print()
            continue

        if user_input.lower() == "/plugins-reload":
            resultado = reload_plugins()
            print_colored(f"\n🔄 {resultado}", Cores.VERDE)
            print()
            continue

        if user_input.lower().startswith("/export-md"):
            partes = user_input.split(maxsplit=4)
            start_date, end_date, role_filter = "", "", ""
            for p in partes[1:]:
                if "/" in p:
                    if not start_date:
                        start_date = p
                    elif not end_date:
                        end_date = p
                else:
                    role_filter = p
            resultado = export_conversation_markdown(
                messages, start_date=start_date, end_date=end_date, role_filter=role_filter
            )
            if "Nao ha mensagens" in resultado:
                print_colored(f"\n⚠ {resultado}", Cores.AMARELO)
            else:
                print_colored(f"\n📄 {resultado}", Cores.VERDE)
            print()
            continue

        if user_input.lower().startswith("/export-html"):
            partes = user_input.split(maxsplit=4)
            start_date, end_date, role_filter = "", "", ""
            for p in partes[1:]:
                if "/" in p:
                    if not start_date:
                        start_date = p
                    elif not end_date:
                        end_date = p
                else:
                    role_filter = p
            resultado = export_conversation_html(
                messages, start_date=start_date, end_date=end_date, role_filter=role_filter
            )
            if "Nao ha mensagens" in resultado:
                print_colored(f"\n⚠ {resultado}", Cores.AMARELO)
            else:
                print_colored(f"\n🌐 {resultado}", Cores.VERDE)
            print()
            continue

        if user_input.lower().startswith("/conversa-buscar"):
            partes = user_input.split(maxsplit=1)
            query = partes[1] if len(partes) > 1 else ""
            if not query:
                print_colored("\n⚠ Uso: /conversa-buscar <texto>", Cores.AMARELO)
            else:
                resultado = search_conversation(query)
                print_colored(f"\n🔍 Resultados para '{query}':", Cores.CIANO)
                print_colored(resultado, Cores.CINZA)
            print()
            continue

        if user_input.lower() == "/subagente":
            print_colored("\n🧠 SUB-AGENTES DISPONIVEIS:", Cores.MAGENTA)
            print_colored("  subagente_codigo    - Especialista em programacao", Cores.CINZA)
            print_colored("  subagente_analise   - Especialista em analise e pesquisa", Cores.CINZA)
            print_colored("  subagente_criativo  - Especialista em criatividade", Cores.CINZA)
            print_colored("  Use: 'subagente_codigo: <tarefa>' na conversa", Cores.DIM)
            print()
            continue

        # --- Memoria Evolutiva ---
        if user_input.lower() in ("/memoria-status", "/memoria-estatisticas"):
            try:
                from plugins.plugin_memoria_evolutiva import memoria_estatisticas, refletir, perfil_mostrar
                print_colored(f"\n{memoria_estatisticas()}", Cores.CIANO)
                print_colored(f"\n{perfil_mostrar()}", Cores.VERDE)
                print_colored(f"\n{refletir()}", Cores.MAGENTA)
            except Exception:
                print_colored("\n⚠ Memoria Evolutiva nao disponivel (plugin ausente).", Cores.AMARELO)
            print()
            continue

        if user_input.lower().startswith("/memoria-buscar"):
            partes = user_input.split(maxsplit=1)
            query = partes[1] if len(partes) > 1 else ""
            if not query:
                print_colored("\n⚠ Uso: /memoria-buscar <texto>", Cores.AMARELO)
            else:
                try:
                    from plugins.plugin_memoria_evolutiva import memoria_buscar
                    resultado = memoria_buscar(query)
                    print_colored(f"\n🧠 Resultados para '{query}':", Cores.CIANO)
                    print_colored(resultado, Cores.CINZA)
                except Exception as e:
                    print_colored(f"\n⚠ Erro: {e}", Cores.VERMELHO)
            print()
            continue

        if user_input.lower() == "/perfil":
            try:
                from plugins.plugin_memoria_evolutiva import perfil_mostrar
                print_colored(f"\n{perfil_mostrar()}", Cores.VERDE)
            except Exception:
                print_colored("\n⚠ Perfil nao disponivel (plugin ausente).", Cores.AMARELO)
            print()
            continue

        if user_input.lower().startswith("/grafo"):
            partes = user_input.split(maxsplit=1)
            conceito = partes[1] if len(partes) > 1 else ""
            try:
                if conceito:
                    from plugins.plugin_memoria_evolutiva import grafo_visualizar
                    print_colored(f"\n{grafo_visualizar(conceito)}", Cores.CIANO)
                else:
                    from plugins.plugin_memoria_evolutiva import grafo_listar
                    print_colored(f"\n{grafo_listar()}", Cores.CIANO)
            except Exception:
                print_colored("\n⚠ Grafo nao disponivel (plugin ausente).", Cores.AMARELO)
            print()
            continue

        if user_input.lower().startswith("/session"):
            partes = user_input.split(maxsplit=2)
            subcmd = partes[1] if len(partes) > 1 else ""
            if subcmd == "salvar" and len(partes) > 2:
                print_colored(f"\n💾 {session_save(partes[2])}", Cores.VERDE)
            elif subcmd == "carregar" and len(partes) > 2:
                print_colored(f"\n📂 {session_load(partes[2])}", Cores.VERDE)
            elif subcmd == "listar":
                print_colored(f"\n📋 {session_list()}", Cores.CIANO)
            else:
                print_colored("\n⚠ Uso: /session salvar <nome> | /session carregar <nome> | /session listar", Cores.AMARELO)
            print()
            continue

        if user_input.lower() == "/voz":
            print_colored("\n🎤 Gravando por 5 segundos... (fale agora)", Cores.CIANO)
            try:
                from agente_core import record_and_transcribe
                texto = record_and_transcribe(5)
                print_colored(f"\n📝 Transcricao: {texto}", Cores.VERDE)
                if texto and not texto.startswith("Erro") and texto != "(silencio detectado)":
                    user_input = texto
                    # Falls through to send the transcribed text as a message
                else:
                    print()
                    continue
            except Exception as e:
                print_colored(f"\n❌ Erro: {e}", Cores.VERMELHO)
                print()
                continue

        # --- TURBO COMMANDS ---
        if user_input.lower() == "/turbo":
            print_colored(f"\n🚀 {turbo_diagnostico()}", Cores.CIANO)
            print()
            continue

        if user_input.lower() == "/turbo-cache":
            print_colored(f"\n🗑️ {turbo_cache_clear()}", Cores.VERDE)
            print()
            continue

        if user_input.lower().startswith("/turbo-decompor"):
            partes = user_input.split(maxsplit=1)
            task = partes[1] if len(partes) > 1 else ""
            if not task:
                print_colored("\n⚠ Uso: /turbo-decompor <tarefa complexa>", Cores.AMARELO)
            else:
                print_colored(f"\n🧩 {task_decompose(task)}", Cores.CIANO)
            print()
            continue

        if user_input.lower().startswith("/turbo-raciocinar"):
            partes = user_input.split(maxsplit=1)
            task = partes[1] if len(partes) > 1 else ""
            if not task:
                print_colored("\n⚠ Uso: /turbo-raciocinar <tarefa>", Cores.AMARELO)
            else:
                print_colored(f"\n🧠 {structured_reasoning(task)}", Cores.MAGENTA)
            print()
            continue

        if user_input.lower().startswith("/turbo-revisar"):
            partes = user_input.split(maxsplit=1)
            task = partes[1] if len(partes) > 1 else ""
            if not task:
                print_colored("\n⚠ Uso: /turbo-revisar <codigo a revisar>", Cores.AMARELO)
            else:
                print_colored(f"\n🔍 {code_review(task)}", Cores.CIANO)
            print()
            continue

        if user_input.lower().startswith("/model"):
            partes = user_input.split(maxsplit=1)
            if len(partes) > 1:
                new_model = partes[1].strip()
                if update_env_model(new_model):
                    print_colored(f"\n✅ Modelo alterado para: {new_model}", Cores.VERDE)
                    print_colored("   Reinicie o programa para aplicar完全.", Cores.CINZA)
                else:
                    print_colored("\n❌ Erro ao alterar modelo", Cores.VERMELHO)
            else:
                # Lista modelos disponíveis
                models = get_available_ollama_models()
                if models:
                    print_colored("\n🤖 Modelos disponíveis:", Cores.CIANO)
                    for i, m in enumerate(models, 1):
                        current = " (atual)" if m["name"] == MODEL else ""
                        print(f"  {Cores.BOLD}{i}.{current}{Cores.RESET} {m['display']}")
                    print(f"\n  Uso: {Cores.BOLD}/model <nome>{Cores.RESET} ou {Cores.BOLD}/model <numero>{Cores.RESET}")
                else:
                    print_colored("\n⚠ Nenhum modelo encontrado no Ollama", Cores.AMARELO)
            print()
            continue

        if user_input.lower() in ("/ajuda", "/help"):
            print_colored("\n📖 AJUDA - Comandos disponíveis:", Cores.CIANO)
            print(f"  {Cores.BOLD}Qualquer texto{Cores.RESET}    -> Envia mensagem para o agente")
            print(f"  {Cores.BOLD}sair{Cores.RESET}             -> Encerra o programa")
            print(f"  {Cores.BOLD}nova conversa{Cores.RESET}    -> Reinicia o chat (memória continua)")
            print(f"  {Cores.BOLD}/memorias{Cores.RESET}         -> Lista fatos guardados na memória")
            print(f"  {Cores.BOLD}/plugins{Cores.RESET}          -> Lista plugins carregados")
            print(f"  {Cores.BOLD}/plugins-reload{Cores.RESET}   -> Recarrega plugins do disco")
            print(f"  {Cores.BOLD}/export-md{Cores.RESET}               -> Exporta conversa como Markdown (.md)")
            print(f"  {Cores.BOLD}/export-md user{Cores.RESET}           -> Exporta apenas mensagens do usuario")
            print(f"  {Cores.BOLD}/export-md 01/01 30/06{Cores.RESET}   -> Exporta mensagens entre as datas")
            print(f"  {Cores.BOLD}/export-md 16/07 16/07 user{Cores.RESET} -> Exporta mensagens do usuario em 16/07")
            print(f"  {Cores.BOLD}/export-html{Cores.RESET}              -> Exporta conversa como HTML (.html)")
            print(f"  {Cores.BOLD}/export-html assistant{Cores.RESET}    -> Exporta apenas mensagens do agente")
            print(f"  {Cores.BOLD}/conversa-buscar{Cores.RESET}  -> Busca texto no historico da conversa")
            print(f"  {Cores.BOLD}/subagente{Cores.RESET}          -> Lista os sub-agentes especialistas")
            print(f"  {Cores.BOLD}/session{Cores.RESET}            -> Gerencia sessoes (salvar/carregar/listar)")
            print(f"  {Cores.BOLD}/voz{Cores.RESET}                -> Grava audio e transcreve com Whisper")
            print(f"  {Cores.BOLD}/ajuda{Cores.RESET}            -> Mostra esta mensagem")
            print(f"  {Cores.BOLD}/memoria-status{Cores.RESET}    -> Estatisticas, perfil e auto-reflexao")
            print(f"  {Cores.BOLD}/memoria-buscar{Cores.RESET}    -> Busca semantica na memoria")
            print(f"  {Cores.BOLD}/perfil{Cores.RESET}            -> Mostra perfil aprendido do usuario")
            print(f"  {Cores.BOLD}/grafo [conceito]{Cores.RESET}  -> Grafo de conhecimento")
            print(f"  {Cores.BOLD}/turbo{Cores.RESET}              -> Diagnóstico do sistema turbo")
            print(f"  {Cores.BOLD}/turbo-cache{Cores.RESET}        -> Limpar cache turbo")
            print(f"  {Cores.BOLD}/turbo-decompor <tarefa>{Cores.RESET} -> Decompor tarefa complexa")
            print(f"  {Cores.BOLD}/turbo-raciocinar <tarefa>{Cores.RESET} -> Raciocínio estruturado")
            print(f"  {Cores.BOLD}/turbo-revisar <codigo>{Cores.RESET} -> Revisar código fonte")
            print(f"  {Cores.BOLD}/model{Cores.RESET}              -> Lista modelos disponíveis ou altera modelo")
            print(f"  {Cores.BOLD}/model <nome>{Cores.RESET}       -> Altera modelo (ex: /model gemma4:E4B)")
            print()
            continue

        messages.append({
            "role": "user",
            "content": user_input,
        })

        # Aprendizado automatico (memoria evolutiva)
        feedback_memoria = run_memory_pipeline(user_input)
        if feedback_memoria:
            print_colored(f"{Cores.DIM}🧠 {feedback_memoria[:200]}{Cores.RESET}")

        def show_step(text):
            print(f"{Cores.BEGE}  ⚙ {text}{Cores.RESET}")

        # Streaming: imprime tokens da resposta final assim que chegam.
        streaming_active = False

        def on_token(token):
            nonlocal streaming_active
            if not streaming_active:
                print()
                print_separador()
                print(f"{Cores.AZUL}Agente{Cores.RESET} » ", end="", flush=True)
                streaming_active = True
            # Substitui quebras de linha mantendo legibilidade no terminal.
            safe = token.replace("\r\n", "\n").replace("\r", "\n")
            print(f"{Cores.RESET}{safe}", end="", flush=True)

        try:
            print()
            # Executa em thread separada para permitir cancelamento (Ctrl+C)
            # sem travar o processo e isolar falhas de I/O do modelo.
            import threading
            _result = {"messages": None, "error": None}

            def _worker():
                try:
                    _result["messages"] = run_agent_turn(
                        messages, model=MODEL, on_step=show_step, on_token=on_token
                    )
                except Exception as e:  # pragma: no cover - isolamento de thread
                    _result["error"] = e

            _thread = threading.Thread(target=_worker, daemon=True)
            _thread.start()
            _thread.join()
            if _result["error"]:
                raise _result["error"]

            messages = _result["messages"]
            if streaming_active:
                print()  # nova linha após o streaming
                print_separador()
                print()
            else:
                print()
        except KeyboardInterrupt:
            print(f"\n{Cores.AMARELO}[Interrompido pelo usuario] A resposta foi parcial.{Cores.RESET}\n")
            continue
        except Exception as e:
            print(f"\n{Cores.VERMELHO}[Erro inesperado] {e}{Cores.RESET}\n")
            continue

        # Garante exibição caso o streaming não tenha sido acionado
        # (ex.: resposta vazia ou erro de comunicação tratado internamente).
        if not streaming_active:
            for m in reversed(messages):
                if m.get("role") == "assistant" and m.get("content"):
                    print_separador()
                    print(f"{Cores.AZUL}Agente{Cores.RESET} » {m['content']}")
                    print_separador()
                    print()
                    break


if __name__ == "__main__":
    chat_loop()
