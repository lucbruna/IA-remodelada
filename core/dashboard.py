from ._common import *
from .memory import *
def abrir_dashboard(modo: str = "texto") -> str:
    """Abre o dashboard interativo do agente em uma nova janela/janela do terminal.

    O dashboard mostra metricas em tempo real: memoria, ferramentas usadas,
    grafo de conhecimento, analytics, top ferramentas, categorias e muito mais.
    Funciona com ou sem a biblioteca Rich (modo texto simples fallback).

    Args:
        modo: "texto" para modo simples (funciona sem Rich),
              "rich" para modo grafico colorido (requer pip install rich),
              "auto" para detectar automaticamente (padrao)

    Returns:
        Mensagem de confirmacao informando que o dashboard foi aberto    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_dashboard.py")

    if not os.path.exists(script_path):
        return f"Erro: arquivo do dashboard nao encontrado em: {script_path}"

    try:
        # Abre o dashboard em uma NOVA janela de terminal para nao travar o chat
        # CREATE_NEW_CONSOLE faz o dashboard abrir em sua propria janela no Windows
        if hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
            flags = subprocess.CREATE_NEW_CONSOLE
        else:
            flags = 0

        if modo == "texto":
            processo = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags
            )
        else:
            processo = subprocess.Popen(
                [sys.executable, script_path],
                creationflags=flags
            )
        
        pid = processo.pid
        return (
            f"📊 Dashboard aberto em nova janela! (PID: {pid})\n"
            f"   O dashboard mostra metricas de memoria, ferramentas, grafo, timeline e mais.\n"
            f"   Feche a janela do dashboard quando quiser voltar ao chat.\n"
            f"   Dica: use abrir_dashboard(modo='texto') para versao simples no terminal."
        )
    except Exception as e:
        return f"Erro ao abrir dashboard: {e}"


