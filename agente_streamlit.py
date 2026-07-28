"""
agente_streamlit.py
====================
Interface web moderna com Streamlit para o Agente Local.
Importa direto do agente_core — não precisa do servidor API rodando!

USO:
  pip install streamlit
  streamlit run agente_streamlit.py
"""

import os
import sys
import time
import json
from datetime import datetime
from collections import Counter

import streamlit as st

# ─── Core ───────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agente_core import (
    SYSTEM_PROMPT, MODEL, VISION_MODEL, NUM_CTX, TEMPERATURE,
    run_agent_turn, load_conversation_history, save_conversation_history,
    AVAILABLE_FUNCTIONS, remember, list_memories,
    get_system_info, reload_plugins,
    export_conversation_markdown, export_conversation_html,
    get_plugin_manager, ensure_ollama,
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
            # Remove tag ":latest" para exibição limpa
            display_name = name.split(":")[0] if ":" in name else name
            size_bytes = d.get("size", 0) or 0
            size_gb = size_bytes / (1024**3)
            models.append({
                "name": name,
                "display": f"{display_name} ({size_gb:.1f} GB)" if size_gb > 0 else display_name,
                "size_gb": size_gb,
            })
        # Ordena por tamanho (menor primeiro)
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

# ─── Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🤖 Agente Local",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tema escuro personalizado
st.markdown("""
<style>
    /* Tema escuro refinado */
    .stApp { background: #0f0f1a; }
    .stApp > header { background: #1a1a2e !important; }
    
    /* Cards */
    .card {
        background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px;
        padding: 16px; margin-bottom: 12px;
    }
    .card h3 { color: #7c5cfc; font-size: 0.85rem; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px; }
    .card .metric { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.85rem; }
    .card .metric .label { color: #6c6c8a; }
    .card .metric .value { color: #e0e0f0; font-weight: 600; }
    .card .metric .value.green { color: #4ade80; }
    .card .metric .value.yellow { color: #fbbf24; }
    .card .metric .value.red { color: #f87171; }
    .card .metric .value.purple { color: #7c5cfc; }
    
    /* Chat messages */
    .chat-msg {
        padding: 12px 18px; border-radius: 12px; margin-bottom: 12px;
        line-height: 1.6; animation: fadeIn 0.3s;
    }
    .chat-msg.user {
        background: #2a1f5e; border-bottom-right-radius: 4px; margin-left: 20%;
    }
    .chat-msg.agent {
        background: #1a2a3e; border-bottom-left-radius: 4px; margin-right: 20%;
    }
    .chat-msg.tool {
        background: #1a2e2a; font-family: monospace; font-size: 0.85rem; color: #4ade80;
    }
    .chat-msg .sender { font-size: 0.7rem; font-weight: 700; margin-bottom: 4px; text-transform: uppercase; }
    .chat-msg.user .sender { color: #7c5cfc; }
    .chat-msg.agent .sender { color: #4ade80; }
    .chat-msg.tool .sender { color: #fbbf24; }
    .chat-msg .content { white-space: pre-wrap; word-break: break-word; }
    .chat-msg .time { font-size: 0.6rem; color: #6c6c8a; margin-top: 4px; text-align: right; }
    
    /* Metric boxes */
    .metric-box {
        background: #16162a; border-radius: 8px; padding: 12px 16px;
        text-align: center; border: 1px solid #2a2a4a;
    }
    .metric-box .val { font-size: 1.5rem; font-weight: 700; color: #7c5cfc; }
    .metric-box .lbl { font-size: 0.65rem; color: #6c6c8a; margin-top: 2px; text-transform: uppercase; }
    .metric-box.green .val { color: #4ade80; }
    .metric-box.yellow .val { color: #fbbf24; }
    
    /* Bar chart */
    .bar-container { margin: 4px 0; display: flex; align-items: center; gap: 8px; }
    .bar-label { color: #6c6c8a; font-size: 0.75rem; width: 100px; text-align: right; flex-shrink: 0; }
    .bar-fill { height: 18px; border-radius: 4px; min-width: 4px; transition: width 0.5s; }
    
    /* Divider */
    .divider { border: none; border-top: 1px solid #2a2a4a; margin: 16px 0; }
    
    /* Fix Streamlit defaults */
    .stButton > button { border-radius: 8px !important; }
    .stTextInput > div > div > input { border-radius: 8px !important; background: #16162a !important; color: #e0e0f0 !important; border: 1px solid #2a2a4a !important; }
    .stTextArea > div > div > textarea { border-radius: 12px !important; background: #16162a !important; color: #e0e0f0 !important; border: 1px solid #2a2a4a !important; }
    .stSelectbox > div > div { border-radius: 8px !important; background: #16162a !important; }
    .stExpander { background: #1a1a2e !important; border: 1px solid #2a2a4a !important; border-radius: 12px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0 !important; }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

# ─── Session State ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    # Carrega historico salvo
    history = load_conversation_history()
    if history:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            m for m in history if m.get("role") != "system"
        ]
        st.session_state.history_loaded = True
    else:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.history_loaded = False

if "tool_call_count" not in st.session_state:
    st.session_state.tool_call_count = 0
if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()
if "ollama_checked" not in st.session_state:
    st.session_state.ollama_checked = False


def add_message(role: str, content: str):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })


def run_chat(user_input: str):
    """Processa a mensagem do usuario e atualiza o estado."""
    add_message("user", user_input)

    # Usa o modelo selecionado no session_state ou o padrão
    current_model = st.session_state.get("model_selector", MODEL)

    with st.spinner("🤖 Agente pensando..."):
        try:
            updated = run_agent_turn(
                st.session_state.messages,
                model=current_model,
            )
            st.session_state.messages = updated

            # Conta tool calls
            tool_msgs = [m for m in updated if m.get("role") == "tool"]
            if tool_msgs:
                st.session_state.tool_call_count += len(tool_msgs)

            # Salva historico
            save_msgs = [m for m in updated if m.get("role") != "system"]
            save_conversation_history(save_msgs)

        except Exception as e:
            add_message("system", f"❌ Erro: {e}")
            st.error(f"Erro ao processar: {e}")


def clear_chat():
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.tool_call_count = 0
    save_conversation_history([])
    st.rerun()


def get_last_response() -> str:
    """Pega a ultima resposta do agente."""
    for m in reversed(st.session_state.messages):
        if m.get("role") == "assistant" and m.get("content"):
            return m["content"]
    return ""


def format_msg_html(msg) -> str:
    """Formata uma mensagem para HTML."""
    role = msg.get("role", "")
    content = msg.get("content", "")
    ts = msg.get("timestamp", "")
    
    if role == "system":
        return ""
    
    sender_map = {"user": "👤 Voce", "assistant": "🤖 Agente", "tool": "⚙ Sistema"}
    sender = sender_map.get(role, role)
    
    # Simple rendering
    html_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_content = html_content.replace("\n", "<br>")
    # Code blocks
    import re
    html_content = re.sub(
        r'```(\w*)\n(.+?)```',
        lambda m: f'<pre style="background:rgba(0,0,0,.4);padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0"><code>{m.group(2)}</code></pre>',
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(r'`([^`]+)`', r'<code style="background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px">\1</code>', html_content)
    
    time_str = f'<div class="time">{ts}</div>' if ts else ""
    return f'<div class="chat-msg {role}"><div class="sender">{sender}</div><div class="content">{html_content}</div>{time_str}</div>'


# ===================================================================
# SIDEBAR
# ===================================================================
with st.sidebar:
    st.markdown("<h1 style='font-size:1.3rem;background:linear-gradient(135deg,#7c5cfc,#4ade80);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px'>🤖 Agente Local</h1>", unsafe_allow_html=True)
    
    # Status
    st.markdown('<div class="card"><h3>📊 Status</h3>', unsafe_allow_html=True)

    # Seletor de modelos
    available_models = get_available_ollama_models()
    if available_models:
        model_options = [m["name"] for m in available_models]
        model_display = {m["name"]: m["display"] for m in available_models}

        # Encontra o índice do modelo atual
        current_index = 0
        if MODEL in model_options:
            current_index = model_options.index(MODEL)

        selected_model = st.selectbox(
            "🤖 Modelo",
            options=model_options,
            index=current_index,
            format_func=lambda x: model_display.get(x, x),
            key="model_selector",
            label_visibility="collapsed",
        )

        # Se o modelo mudou, atualiza
        if selected_model != MODEL:
            if update_env_model(selected_model):
                st.success(f"Modelo alterado para: {selected_model}")
                st.rerun()
    else:
        st.markdown(f'<div class="metric-box"><div class="val">{MODEL}</div><div class="lbl">Modelo</div></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        runtime = int(time.time() - st.session_state.session_start)
        h, m = runtime // 3600, (runtime % 3600) // 60
        st.markdown(f'<div class="metric-box green"><div class="val">{h}h{m}m</div><div class="lbl">Sessao</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        msg_count = len([m for m in st.session_state.messages if m.get("role") != "system"])
        st.markdown(f'<div class="metric-box yellow"><div class="val">{msg_count}</div><div class="lbl">Mensagens</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="val">{st.session_state.tool_call_count}</div><div class="lbl">Tool Calls</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Acoes
    st.markdown('<div class="card"><h3>⚡ Ações</h3>', unsafe_allow_html=True)
    
    if st.button("🗑️ Limpar Conversa", use_container_width=True):
        clear_chat()
    
    if st.button("📤 Exportar MD", use_container_width=True):
        msgs = [m for m in st.session_state.messages if m.get("role") != "system"]
        result = export_conversation_markdown(msgs)
        st.success(result)
    
    if st.button("📤 Exportar HTML", use_container_width=True):
        msgs = [m for m in st.session_state.messages if m.get("role") != "system"]
        result = export_conversation_html(msgs)
        st.success(result)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Memoria
    st.markdown('<div class="card"><h3>💾 Memória</h3>', unsafe_allow_html=True)
    mem_text = list_memories()
    if mem_text and mem_text != "A memoria esta vazia.":
        lines = mem_text.split("\n")[:10]
        for line in lines:
            if ":" in line:
                idx = line.index(":")
                key, val = line[:idx].strip(), line[idx+1:].strip()
                st.markdown(f'<div style="font-size:0.8rem;padding:3px 0"><span style="color:#7c5cfc;font-weight:600">{key}</span>: <span style="color:#6c6c8a">{val[:60]}</span></div>', unsafe_allow_html=True)
        if len(lines) > 10:
            st.caption(f"... e mais {len(lines) - 10} memorias")
    else:
        st.caption("Nenhuma memoria salva")
    
    # Add memory form
    with st.expander("➕ Adicionar memoria"):
        mem_key = st.text_input("Chave", key="mem_key_input", label_visibility="collapsed", placeholder="Chave")
        mem_val = st.text_input("Valor", key="mem_val_input", label_visibility="collapsed", placeholder="Valor")
        if st.button("Salvar", use_container_width=True) and mem_key and mem_val:
            result = remember(mem_key, mem_val)
            st.success(result)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Plugins
    st.markdown('<div class="card"><h3>🔌 Plugins</h3>', unsafe_allow_html=True)
    pm = get_plugin_manager()
    loaded = pm.loaded_count
    total = pm.plugin_count
    st.markdown(f'<div style="font-size:0.8rem"><span style="color:#4ade80">{loaded}</span>/{total} carregados</div>', unsafe_allow_html=True)
    if st.button("🔄 Recarregar", use_container_width=True):
        result = reload_plugins()
        st.success(result)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sistema
    st.markdown('<div class="card"><h3>🖥️ Sistema</h3>', unsafe_allow_html=True)
    sys_info = get_system_info()
    for line in sys_info.split("\n")[:4]:
        if ":" in line:
            idx = line.index(":")
            k, v = line[:idx].strip(), line[idx+1:].strip()
            st.markdown(f'<div class="metric"><span class="label">{k}</span><span class="value">{v}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ===================================================================
# MAIN - CHAT
# ===================================================================

# Header
current_model = st.session_state.get("model_selector", MODEL)
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
    <div>
        <h2 style="color:#e0e0f0;margin:0">🤖 Conversa</h2>
        <p style="color:#6c6c8a;font-size:0.8rem;margin:4px 0 0 0">
            Modelo: {current_model} | {len(AVAILABLE_FUNCTIONS)} ferramentas | Contexto: {NUM_CTX} tokens
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# Exibe mensagens
msg_container = st.container()
with msg_container:
    for msg in st.session_state.messages:
        html = format_msg_html(msg)
        if html:
            st.markdown(html, unsafe_allow_html=True)

# Input
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([6, 1])
    with col1:
        user_input = st.text_area(
            "Mensagem",
            placeholder="Digite sua mensagem para o agente...",
            key="chat_input",
            label_visibility="collapsed",
            height=70,
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➤ Enviar", use_container_width=True, type="primary"):
            if user_input.strip():
                run_chat(user_input.strip())
                st.rerun()

# Tecla Enter para enviar (via JavaScript)
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        const textarea = document.querySelector('textarea');
        if (textarea && document.activeElement === textarea) {
            e.preventDefault();
            const btn = document.querySelector('button[kind="primary"]');
            if (btn) btn.click();
        }
    }
});
</script>
""", unsafe_allow_html=True)

# Dica
st.caption("💡 Pressione Enter para enviar, Shift+Enter para nova linha")


# ===================================================================
# FOOTER - Dashboard Metrics
# ===================================================================
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#6c6c8a;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px'>📊 Dashboard Rapido</h3>", unsafe_allow_html=True)

# Carrega dados de analytics se disponiveis
analytics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_data", "analytics")
eventos_file = os.path.join(analytics_dir, "eventos.json")

tool_stats = Counter()
if os.path.exists(eventos_file):
    try:
        with open(eventos_file, "r", encoding="utf-8") as f:
            eventos = json.load(f)
        for e in eventos:
            if isinstance(e, dict) and e.get("evento") == "tool_call":
                name = e.get("dados", {}).get("ferramenta", "?")
                tool_stats[name] += 1
    except Exception:
        pass

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("<div class='card'><h3>🔧 Top Ferramentas</h3>", unsafe_allow_html=True)
    if tool_stats:
        max_count = max(tool_stats.values())
        for name, count in tool_stats.most_common(8):
            pct = count / max_count * 100
            color = "#7c5cfc" if pct > 60 else "#4ade80" if pct > 30 else "#fbbf24"
            st.markdown(f"""
                <div class="bar-container">
                    <span class="bar-label">{name[:18]}</span>
                    <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
                    <span style="color:#e0e0f0;font-size:0.75rem;font-weight:600">{count}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhuma ferramenta usada ainda")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'><h3>🧠 Memoria Evolutiva</h3>", unsafe_allow_html=True)
    mem_evol_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_data", "memoria_evolutiva")
    
    fatos_file = os.path.join(mem_evol_dir, "fatos_semanticos.json")
    fatos = []
    if os.path.exists(fatos_file):
        try:
            with open(fatos_file, "r", encoding="utf-8") as f:
                fatos = json.load(f)
        except Exception:
            pass
    
    perfil_file = os.path.join(mem_evol_dir, "perfil_usuario.json")
    perfil = {}
    if os.path.exists(perfil_file):
        try:
            with open(perfil_file, "r", encoding="utf-8") as f:
                perfil = json.load(f)
        except Exception:
            pass
    
    grafo_file = os.path.join(mem_evol_dir, "grafo_conhecimento.json")
    grafo = {"nos": {}, "arestas": []}
    if os.path.exists(grafo_file):
        try:
            with open(grafo_file, "r", encoding="utf-8") as f:
                grafo = json.load(f)
        except Exception:
            pass
    
    st.markdown(f"""
        <div class="metric"><span class="label">🧠 Fatos semanticos</span><span class="value purple">{len(fatos)}</span></div>
        <div class="metric"><span class="label">💬 Interacoes</span><span class="value">{perfil.get('total_interacoes', 0)}</span></div>
        <div class="metric"><span class="label">📁 Projetos</span><span class="value">{len(perfil.get('projetos', []))}</span></div>
        <div class="metric"><span class="label">🎯 Interesses</span><span class="value">{len(perfil.get('interesses', []))}</span></div>
        <div class="metric"><span class="label">🔗 Grafo nos</span><span class="value purple">{len(grafo.get('nos', {}))}</span></div>
        <div class="metric"><span class="label">🔗 Grafo arestas</span><span class="value">{len(grafo.get('arestas', []))}</span></div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='card'><h3>ℹ️ Sobre</h3>", unsafe_allow_html=True)
    # Usa o modelo selecionado no session_state ou o padrão
    current_model = st.session_state.get("model_selector", MODEL)
    st.markdown(f"""
        <div class="metric"><span class="label">Modelo</span><span class="value purple">{current_model}</span></div>
        <div class="metric"><span class="label">Visao</span><span class="value green">{VISION_MODEL}</span></div>
        <div class="metric"><span class="label">Contexto</span><span class="value">{NUM_CTX} tokens</span></div>
        <div class="metric"><span class="label">Temperatura</span><span class="value yellow">{TEMPERATURE}</span></div>
        <div class="metric"><span class="label">Ferramentas</span><span class="value purple">{len(AVAILABLE_FUNCTIONS)}</span></div>
        <div class="metric"><span class="label">Plugins</span><span class="value">{loaded}/{total}</span></div>
    """, unsafe_allow_html=True)

    # Botao de diagnostico
    if st.button("🔍 Diagnosticar", use_container_width=True):
        info = []
        info.append(f"✅ Ollama: {ensure_ollama()}")
        info.append(f"✅ Modelo: {current_model}")
        info.append(f"✅ Sessao: {h}h{m}m")
        info.append(f"✅ Mensagens: {msg_count}")
        for line in info:
            st.markdown(f'<div style="color:#4ade80;font-size:0.8rem">{line}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    pass
