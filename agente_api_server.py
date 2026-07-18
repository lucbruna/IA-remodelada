"""
agente_api_server.py
=====================
Servidor Web API (FastAPI) para o Agente Local.
Expõe todas as 70+ ferramentas via REST com documentação Swagger.

COMO RODAR:
  python agente_api_server.py
  # Acessar: http://localhost:8000/docs (Swagger UI)

DEPENDÊNCIAS:
  pip install fastapi uvicorn
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

# ─── FastAPI ────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

# ─── Agente Core ────────────────────────────────────────────────────
from agente_core import (
    SYSTEM_PROMPT, MODEL, run_agent_turn, load_conversation_history,
    save_conversation_history, AVAILABLE_FUNCTIONS, TOOLS_LIST,
    list_memories, list_plugins, reload_plugins, get_system_info,
    export_conversation_markdown, export_conversation_html,
    search_conversation, session_save, session_load, session_list,
)

# ─── Config ─────────────────────────────────────────────────────────
HOST = os.environ.get("AGENTE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AGENTE_PORT", "8000"))
MODEL_NAME = os.environ.get("AGENTE_MODEL", MODEL)

# ─── Estado global ──────────────────────────────────────────────────
messages = []
messages_lock = threading.Lock()
conversation_start = time.time()
tool_call_count = 0
saved_history = False


# ─── Schemas Pydantic ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class ChatResponse(BaseModel):
    reply: str
    tool_calls: int = 0
    messages_count: int = 0

class ToolCallRequest(BaseModel):
    arguments: dict = {}

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict
    required: list

class MemoryItem(BaseModel):
    key: str
    value: str

class PluginInstallRequest(BaseModel):
    url: str

class ExportRequest(BaseModel):
    format: str = "md"  # md ou html
    start_date: str = ""
    end_date: str = ""
    role_filter: str = ""


# ─── App Setup ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o histórico na inicialização."""
    global messages, saved_history
    history = load_conversation_history()
    with messages_lock:
        if history:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                m for m in history if m.get("role") != "system"
            ]
        else:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    saved_history = bool(history)
    yield
    # Salva no shutdown
    with messages_lock:
        msgs = [m for m in messages if m.get("role") != "system"]
        if msgs:
            save_conversation_history(msgs)


app = FastAPI(
    title="🤖 Agente Local API",
    description="API REST completa do Agente Local. Expõe todas as ferramentas, memória e plugins.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: permite acesso de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial com informações da API."""
    runtime = int(time.time() - conversation_start)
    h, m = runtime // 3600, (runtime % 3600) // 60
    
    with messages_lock:
        msg_count = len(messages)
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Agente Local API</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: #1e1e2e; color: #cdd6f4;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 20px;
        }}
        .card {{
            background: #181825; border-radius: 16px;
            padding: 40px; max-width: 600px; width: 100%;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #cba6f7; margin-bottom: 8px; }}
        .sub {{ color: #6c7086; margin-bottom: 24px; }}
        .info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }}
        .item {{ background: #313244; border-radius: 10px; padding: 12px 16px; }}
        .item .label {{ font-size: 0.75em; color: #585b70; text-transform: uppercase; }}
        .item .value {{ font-size: 1.1em; font-weight: 600; color: #cdd6f4; }}
        .links {{ display: flex; gap: 12px; flex-wrap: wrap; }}
        .links a {{
            background: #89b4fa; color: #1e1e2e; text-decoration: none;
            padding: 10px 20px; border-radius: 8px; font-weight: 600;
            transition: 0.2s; flex: 1; text-align: center;
        }}
        .links a:hover {{ background: #b4d0fb; transform: translateY(-1px); }}
        .links a.green {{ background: #a6e3a1; }}
        .links a.green:hover {{ background: #b8ebc0; }}
        .links a.yellow {{ background: #f9e2af; }}
        .links a.yellow:hover {{ background: #fcefc8; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🤖 Agente Local API</h1>
        <p class="sub">Todas as {len(AVAILABLE_FUNCTIONS)} ferramentas do agente via REST</p>
        <div class="info">
            <div class="item">
                <div class="label">Modelo</div>
                <div class="value">{MODEL_NAME}</div>
            </div>
            <div class="item">
                <div class="label">Mensagens</div>
                <div class="value">{msg_count}</div>
            </div>
            <div class="item">
                <div class="label">Sessão</div>
                <div class="value">{h}h{m}m</div>
            </div>
            <div class="item">
                <div class="label">Ferramentas</div>
                <div class="value">{len(AVAILABLE_FUNCTIONS)}</div>
            </div>
        </div>
        <div class="links">
            <a href="/docs">📖 Swagger UI</a>
            <a href="/redoc" class="green">📕 ReDoc</a>
            <a href="/tools" class="yellow">🔧 Ferramentas</a>
        </div>
    </div>
</body>
</html>"""


# ─── Chat ───────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Envia uma mensagem para o agente e obtém resposta."""
    global messages, tool_call_count
    
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(400, "Mensagem vazia")
    
    with messages_lock:
        messages.append({
            "role": "user",
            "content": user_msg,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })
        
        steps = []
        def on_step(text):
            steps.append(text)
        
        try:
            updated = run_agent_turn(messages, model=MODEL_NAME, on_step=on_step)
            messages[:] = updated
            
            reply = ""
            for m in reversed(messages):
                if m.get("role") == "assistant" and m.get("content"):
                    reply = m["content"]
                    break
            
            tool_call_count += len(steps)
            msg_count = len(messages)
        
        except Exception as e:
            raise HTTPException(500, f"Erro ao processar: {e}")
    
    return ChatResponse(
        reply=reply or "(sem resposta)",
        tool_calls=len(steps),
        messages_count=msg_count,
    )


@app.get("/chat/history")
async def get_history(limit: int = Query(50, ge=1, le=500)):
    """Retorna o histórico da conversa atual."""
    with messages_lock:
        msgs = []
        for m in messages[-limit:]:
            if m.get("role") != "system":
                msgs.append({
                    "role": m.get("role"),
                    "content": m.get("content", "")[:500],
                    "timestamp": m.get("timestamp", ""),
                })
        return {"messages": msgs, "total": len(messages)}


@app.post("/chat/clear")
async def clear_conversation():
    """Limpa a conversa atual (memória permanece)."""
    global messages
    with messages_lock:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    return {"status": "ok", "message": "Conversa reiniciada"}


@app.post("/chat/export")
async def export_conversation(req: ExportRequest):
    """Exporta a conversa em Markdown ou HTML."""
    with messages_lock:
        if req.format == "html":
            result = export_conversation_html(
                messages, start_date=req.start_date,
                end_date=req.end_date, role_filter=req.role_filter,
            )
        else:
            result = export_conversation_markdown(
                messages, start_date=req.start_date,
                end_date=req.end_date, role_filter=req.role_filter,
            )
    if "Erro" in result:
        raise HTTPException(500, result)
    return {"status": "ok", "result": result}


# ─── Ferramentas ────────────────────────────────────────────────────

@app.get("/tools", response_model=dict)
async def list_tools():
    """Lista todas as ferramentas disponíveis com descrições e parâmetros."""
    tools = {}
    for t in TOOLS_LIST:
        fn = t.get("function", {})
        name = fn.get("name", "?")
        tools[name] = {
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {}).get("properties", {}),
            "required": fn.get("parameters", {}).get("required", []),
        }
    return {
        "total": len(tools),
        "tools": tools,
    }


@app.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Retorna informações de uma ferramenta específica."""
    func = AVAILABLE_FUNCTIONS.get(tool_name)
    if not func:
        raise HTTPException(404, f"Ferramenta '{tool_name}' não encontrada")
    
    # Busca na TOOLS_LIST
    for t in TOOLS_LIST:
        fn = t.get("function", {})
        if fn.get("name") == tool_name:
            return {
                "name": tool_name,
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}).get("properties", {}),
                "required": fn.get("parameters", {}).get("required", []),
            }
    
    return {"name": tool_name, "note": "Ferramenta carregada mas sem metadados"}


@app.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, args: ToolCallRequest = Body(default_factory=ToolCallRequest)):
    """Chama uma ferramenta específica com argumentos."""
    func = AVAILABLE_FUNCTIONS.get(tool_name)
    if not func:
        raise HTTPException(404, f"Ferramenta '{tool_name}' não encontrada")
    
    try:
        result = func(**args.arguments)
        return {"status": "ok", "tool": tool_name, "result": str(result)}
    except TypeError as e:
        raise HTTPException(400, f"Argumentos inválidos: {e}")
    except Exception as e:
        raise HTTPException(500, f"Erro ao executar: {e}")


# ─── Memória ────────────────────────────────────────────────────────

@app.get("/memory")
async def get_memory():
    """Lista todos os fatos na memória de longo prazo."""
    return {"memories": list_memories()}


@app.post("/memory")
async def add_memory(item: MemoryItem):
    """Adiciona um fato à memória de longo prazo."""
    from agente_core import remember
    result = remember(item.key, item.value)
    return {"status": "ok", "result": result}


@app.delete("/memory/{key}")
async def delete_memory(key: str):
    """Remove um fato da memória."""
    from agente_core import forget
    result = forget(key)
    return {"status": "ok", "result": result}


# ─── Plugins ────────────────────────────────────────────────────────

@app.get("/plugins")
async def get_plugins():
    """Lista todos os plugins carregados."""
    info = list_plugins()
    return {"plugins": info}


@app.post("/plugins/reload")
async def reload_plugins_endpoint():
    """Recarrega todos os plugins do disco."""
    result = reload_plugins()
    return {"status": "ok", "result": result}


@app.post("/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    """Instala um plugin a partir de uma URL (arquivo .py)."""
    try:
        import urllib.request
        
        # Extrai nome do arquivo
        filename = req.url.split("/")[-1]
        if not filename.endswith(".py"):
            filename += ".py"
        
        plugins_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "plugins"
        )
        dest = os.path.join(plugins_dir, filename)
        
        # Download
        urllib.request.urlretrieve(req.url, dest)
        
        # Recarrega
        result = reload_plugins()
        
        return {
            "status": "ok",
            "file": filename,
            "saved_to": dest,
            "reload": result,
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao instalar plugin: {e}")


# ─── Sistema ────────────────────────────────────────────────────────

@app.get("/system/info")
async def system_info():
    """Retorna informações do sistema."""
    return {"info": get_system_info()}


@app.get("/system/status")
async def system_status():
    """Retorna status detalhado do servidor."""
    runtime = int(time.time() - conversation_start)
    with messages_lock:
        msg_count = len(messages)
    
    return {
        "model": MODEL_NAME,
        "tools_count": len(AVAILABLE_FUNCTIONS),
        "messages_count": msg_count,
        "runtime_seconds": runtime,
        "tool_calls_total": tool_call_count,
        "history_loaded": saved_history,
    }


# ─── Sessões ────────────────────────────────────────────────────────

@app.get("/sessions")
async def list_sessions():
    """Lista sessões salvas."""
    return {"sessions": session_list()}


@app.post("/sessions/{name}")
async def save_session(name: str):
    """Salva a conversa atual como uma sessão nomeada."""
    result = session_save(name)
    return {"status": "ok", "result": result}


@app.get("/sessions/{name}/load")
async def load_session(name: str):
    """Carrega uma sessão salva."""
    global messages
    result = session_load(name)
    # Recarrega mensagens
    history = load_conversation_history()
    with messages_lock:
        if history:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                m for m in history if m.get("role") != "system"
            ]
    return {"status": "ok", "result": result}


# ─── Busca ──────────────────────────────────────────────────────────

@app.get("/search")
async def search(query: str = Query(..., min_length=1)):
    """Busca texto no histórico da conversa."""
    result = search_conversation(query)
    return {"query": query, "results": result}


# ─── Main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  🤖  Agente Local API Server                ║")
    print(f"║                                             ║")
    print(f"║  📖 Swagger UI: http://localhost:{PORT}/docs     ║")
    print(f"║  📕 ReDoc:     http://localhost:{PORT}/redoc    ║")
    print(f"║  🔧 Tools:     {len(AVAILABLE_FUNCTIONS)} ferramentas    ║")
    print(f"║  🤖 Modelo:    {MODEL_NAME}                    ║")
    print(f"╚══════════════════════════════════════════════╝")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
