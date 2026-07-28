from ._common import *
# =======================================================================
# EXPORTACAO DE CONVERSA (Markdown / HTML)
# =======================================================================

def _format_mensagem_para_export(m: dict) -> str:
    """Formata o nome do remetente baseado no role."""
    role = m.get("role", "")
    if role == "user":
        return "Você"
    elif role == "assistant":
        return "Agente"
    elif role == "tool":
        return "⚙ Ferramenta"
    elif role == "system":
        return "Sistema"
    return role.capitalize()


def _parse_data_br(data_str: str) -> Optional[datetime]:
    """Converte data no formato dd/mm/aaaa para datetime.

    Aceita "dd/mm/aaaa" ou "dd/mm/aa" (ano com 2 digitos = 2000+).
    Retorna None se a data for invalida.
    """
    try:
        data_limpa = data_str.strip()
        if len(data_limpa) <= 8:  # dd/mm/aa
            return datetime.strptime(data_limpa, "%d/%m/%y")
        return datetime.strptime(data_limpa, "%d/%m/%Y")
    except (ValueError, TypeError):
        return None


def _filtrar_mensagens_por_data(
    messages: list,
    start_date: str = "",
    end_date: str = "",
    role_filter: str = "",
) -> list:
    """Filtra mensagens por intervalo de datas e/ou remetente.

    As mensagens devem ter um campo 'timestamp' no formato 'dd/mm/aaaa' ou
    'dd/mm/aaaa HH:MM:SS'. Se uma mensagem nao tiver timestamp, ela sera
    incluida (passa pelo filtro).

    Args:
        messages: Lista de mensagens
        start_date: Data inicial no formato dd/mm/aaaa (vazio = sem limite inferior)
        end_date: Data final no formato dd/mm/aaaa (vazio = sem limite superior)
        role_filter: Filtrar por remetente. Valores: "user", "assistant",
                     "tool", "system", ou "" (todos).

    Returns:
        Lista de mensagens filtrada
    """
    if not start_date and not end_date and not role_filter:
        return messages  # sem filtro

    # Converte datas de referencia para datetime.date
    data_inicio = _parse_data_br(start_date) if start_date else None
    data_fim = _parse_data_br(end_date) if end_date else None

    if data_inicio is None and start_date:
        logging.warning("Data inicial invalida ignorada: %s", start_date)
    if data_fim is None and end_date:
        logging.warning("Data final invalida ignorada: %s", end_date)

    filtradas = []
    for m in messages:
        # Filtro por remetente (role)
        if role_filter:
            if m.get("role") != role_filter:
                continue

        ts = m.get("timestamp", "")
        if not start_date and not end_date:
            # So filtro de role, sem filtro de data
            filtradas.append(m)
            continue

        if not ts:
            # Mensagem sem timestamp passa pelo filtro (inclusiva)
            filtradas.append(m)
            continue

        # Extrai apenas a data e converte para datetime
        data_msg_str = ts.split(" ")[0] if " " in ts else ts
        data_msg = _parse_data_br(data_msg_str)
        if data_msg is None:
            # Timestamp invalido, inclui para nao perder mensagens
            filtradas.append(m)
            continue

        data_msg = data_msg.date()

        incluir = True
        if data_inicio is not None:
            incluir = incluir and (data_msg >= data_inicio.date())
        if data_fim is not None:
            incluir = incluir and (data_msg <= data_fim.date())

        if incluir:
            filtradas.append(m)

    return filtradas


def export_conversation_markdown(
    messages: list,
    filepath: str = "",
    start_date: str = "",
    end_date: str = "",
    role_filter: str = "",
) -> str:
    """Exporta o historico da conversa para formato Markdown (.md).

    Args:
        messages: Lista de mensagens (role + content, opcionalmente com timestamp)
        filepath: Caminho opcional do arquivo. Se vazio, gera nome automatico.
        start_date: Filtrar mensagens a partir desta data (dd/mm/aaaa). Opcional.
        end_date: Filtrar mensagens ate esta data (dd/mm/aaaa). Opcional.
        role_filter: Filtrar por remetente. Valores: "user", "assistant",
                     "tool", "system", "" (todos). Opcional.

    Returns:
        Mensagem de confirmacao ou erro
    """
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(DATA_DIR, f"conversa_{timestamp}.md")

    if not filepath.endswith(".md"):
        filepath += ".md"

    # Filtra por data e remetente
    export_msgs = _filtrar_mensagens_por_data(messages, start_date, end_date, role_filter)

    # Depois filtra apenas mensagens com conteudo (ignora system sem conteudo e tool_calls internas)
    export_msgs = [
        m for m in export_msgs
        if m.get("content") and m.get("role") != "system"
    ]

    if not export_msgs:
        motivo = " no periodo/remetente selecionado" if (start_date or end_date or role_filter) else ""
        return f"Nao ha mensagens para exportar{motivo}."

    # Informa os filtros aplicados no cabecalho
    partes_info = []
    if start_date and end_date:
        partes_info.append(f"Periodo: {start_date} a {end_date}")
    elif start_date:
        partes_info.append(f"A partir de: {start_date}")
    elif end_date:
        partes_info.append(f"Ate: {end_date}")
    if role_filter:
        role_nome = _format_mensagem_para_export({"role": role_filter})
        partes_info.append(f"Remetente: {role_nome}")
    info_data = f"  |  {' | '.join(partes_info)}" if partes_info else ""

    linhas = [
        f"# 🤖 Conversa com Agente Local\n",
        f"**Exportada em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n",
        f"**Modelo:** {MODEL}{info_data}\n",
        f"**Total de mensagens:** {len(export_msgs)}\n",
        "---\n",
    ]

    for m in export_msgs:
        quem = _format_mensagem_para_export(m)
        conteudo = m.get("content", "").strip()
        # Se tiver timestamp, adiciona como sublinhado
        ts = m.get("timestamp", "")
        cabecalho = f"### {quem}"
        if ts:
            cabecalho += f"  — _{ts}_"
        linhas.append(f"{cabecalho}\n")
        linhas.append(f"{conteudo}\n")

    try:
        parent = os.path.dirname(os.path.abspath(filepath))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))
        return f"Conversa exportada como Markdown: {os.path.abspath(filepath)}"
    except Exception as e:
        return f"Erro ao exportar Markdown: {e}"


def export_conversation_html(
    messages: list,
    filepath: str = "",
    start_date: str = "",
    end_date: str = "",
    role_filter: str = "",
) -> str:
    """Exporta o historico da conversa para formato HTML com estilo moderno.

    Gera um HTML completo com CSS embutido (tema escuro), pronto para
    abrir em qualquer navegador.

    Args:
        messages: Lista de mensagens (role + content, opcionalmente com timestamp)
        filepath: Caminho opcional do arquivo. Se vazio, gera nome automatico.
        start_date: Filtrar mensagens a partir desta data (dd/mm/aaaa). Opcional.
        end_date: Filtrar mensagens ate esta data (dd/mm/aaaa). Opcional.
        role_filter: Filtrar por remetente. Valores: "user", "assistant",
                     "tool", "system", "" (todos). Opcional.

    Returns:
        Mensagem de confirmacao ou erro
    """
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(DATA_DIR, f"conversa_{timestamp}.html")

    if not filepath.endswith(".html"):
        filepath += ".html"

    # Filtra por data e remetente
    export_msgs = _filtrar_mensagens_por_data(messages, start_date, end_date, role_filter)

    # Depois filtra apenas mensagens com conteudo
    export_msgs = [
        m for m in export_msgs
        if m.get("content") and m.get("role") != "system"
    ]

    if not export_msgs:
        motivo = " no periodo/remetente selecionado" if (start_date or end_date or role_filter) else ""
        return f"Nao ha mensagens para exportar{motivo}."

    # Mapeia role para classe CSS e icone
    role_map = {
        "user": ("user", "👤"),
        "assistant": ("agent", "🤖"),
        "tool": ("tool", "⚙"),
    }

    mensagens_html = []
    for m in export_msgs:
        role = m.get("role", "")
        css_class, icone = role_map.get(role, ("system", "ℹ"))
        quem = _format_mensagem_para_export(m)
        conteudo = m.get("content", "").strip()
        # Escapa HTML no conteudo
        conteudo_escape = (conteudo
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))
        # Converte links \n para <br>
        conteudo_html = conteudo_escape.replace("\n", "<br>")

        # Timestamp opcional no cabecalho
        ts = m.get("timestamp", "")
        if ts:
            cabecalho = f"{icone} {quem} <span class=\"ts\">{ts}</span>"
        else:
            cabecalho = f"{icone} {quem}"

        mensagens_html.append(
            f'            <div class="message {css_class}">\n'
            f'                <div class="msg-header">{cabecalho}</div>\n'
            f'                <div class="msg-content">{conteudo_html}</div>\n'
            f'            </div>'
        )

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Informa os filtros aplicados no cabecalho
    partes_info = []
    if start_date and end_date:
        partes_info.append(f"Periodo: {start_date} a {end_date}")
    elif start_date:
        partes_info.append(f"A partir de: {start_date}")
    elif end_date:
        partes_info.append(f"Ate: {end_date}")
    if role_filter:
        role_nome = _format_mensagem_para_export({"role": role_filter})
        partes_info.append(f"Remetente: {role_nome}")
    info_data = f" &nbsp;|&nbsp; {' | '.join(partes_info)}" if partes_info else ""

    mensagens_joined = "\n".join(mensagens_html)
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Conversa com Agente Local</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 20px;
    line-height: 1.6;
  }}
  .container {{
    max-width: 800px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 1.5em;
    color: #cba6f7;
    margin-bottom: 4px;
  }}
  .meta {{
    color: #6c7086;
    font-size: 0.85em;
    margin-bottom: 20px;
  }}
  .message {{
    background: #181825;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 14px;
    border-left: 4px solid transparent;
  }}
  .message.user {{ border-left-color: #89b4fa; }}
  .message.agent {{ border-left-color: #a6e3a1; }}
  .message.tool {{ border-left-color: #f9e2af; }}
  .message.system {{ border-left-color: #6c7086; }}
  .msg-header {{
    font-weight: 600;
    font-size: 0.9em;
    margin-bottom: 6px;
  }}
  .message.user .msg-header {{ color: #89b4fa; }}
  .message.agent .msg-header {{ color: #a6e3a1; }}
  .message.tool .msg-header {{ color: #f9e2af; }}
  .msg-content {{
    color: #cdd6f4;
    font-size: 0.95em;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  .ts {{
    font-weight: 400;
    font-size: 0.8em;
    color: #585b70;
    margin-left: 8px;
  }}
  .footer {{
    text-align: center;
    color: #585b70;
    font-size: 0.8em;
    margin-top: 30px;
    padding-top: 12px;
    border-top: 1px solid #313244;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>🤖 Conversa com Agente Local</h1>
  <div class="meta">
    Exportada em: {timestamp} &nbsp;|&nbsp; Modelo: {MODEL} &nbsp;|&nbsp; Mensagens: {len(export_msgs)}{info_data}
  </div>
  <hr style="border: none; border-top: 1px solid #313244; margin-bottom: 20px;">
{mensagens_joined}
  <div class="footer">Gerado por Agente Local</div>
</div>
</body>
</html>"""

    try:
        parent = os.path.dirname(os.path.abspath(filepath))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return f"Conversa exportada como HTML: {os.path.abspath(filepath)}"
    except Exception as e:
        return f"Erro ao exportar HTML: {e}"


