"""
plugin_api_externa.py
=====================
API Externa para modelos LLM — Together.ai e Fireworks como fallback
para tarefas pesadas quando o Ollama local não dá conta.

Recursos:
  - Chat com modelos via Together.ai (API key: TOGETHER_API_KEY)
  - Chat com modelos via Fireworks (API key: FIREWORKS_API_KEY)
  - Suporte a tool calling (function calling)
  - Fallback automático: Ollama → Together → Fireworks
  - Verificação de status das APIs
  - Streaming de tokens (modo síncrono para plugins)
  - Cache de respostas para reduzir custos
"""

import os
import json
import time
import logging
import hashlib
from typing import Optional

__version__ = "1.0.0"
PLUGIN_NAME = "API Externa — Together.ai & Fireworks"

# ─── Diretório de cache ────────────────────────────────────────────
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agente_data", "api_cache"
)
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Configuração ──────────────────────────────────────────────────
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")

# Modelos padrão
TOGETHER_DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
FIREWORKS_DEFAULT_MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct"

# Cache TTL (segundos)
CACHE_TTL = 300  # 5 minutos

# Timeout para chamadas API
API_TIMEOUT = 60

# ─── Endpoints ─────────────────────────────────────────────────────
TOGETHER_URL = "https://api.together.xyz/v1/chat/completions"
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"


# ─── Cache ─────────────────────────────────────────────────────────

def _cache_key(model: str, messages: list, tools: list = None) -> str:
    """Gera chave única para cache baseada nos parâmetros."""
    data = json.dumps({"model": model, "messages": messages, "tools": tools},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.md5(data.encode()).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    """Recupera resposta do cache se ainda válida."""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if time.time() - cached["timestamp"] < CACHE_TTL:
            return cached["response"]
    except Exception:
        pass
    return None


def _cache_set(key: str, response: str):
    """Armazena resposta no cache."""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "response": response,
            }, f, ensure_ascii=False)
    except Exception:
        pass


# ─── Funções auxiliares ───────────────────────────────────────────

def _check_together() -> bool:
    """Verifica se Together.ai está configurado."""
    return bool(TOGETHER_API_KEY)


def _check_fireworks() -> bool:
    """Verifica se Fireworks está configurado."""
    return bool(FIREWORKS_API_KEY)


def _call_api(url: str, api_key: str, model: str, messages: list,
              tools: list = None, temperature: float = 0.5,
              max_tokens: int = 4096) -> Optional[dict]:
    """Chama uma API compatível com OpenAI (Together/Fireworks).

    Args:
        url: URL do endpoint
        api_key: Chave da API
        model: Nome do modelo
        messages: Lista de mensagens no formato OpenAI
        tools: Lista de ferramentas (opcional)
        temperature: Temperatura (0.0-2.0)
        max_tokens: Máximo de tokens na resposta

    Returns:
        Resposta da API em formato dict, ou None em caso de erro
    """
    try:
        import requests
    except ImportError:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    try:
        resp = requests.post(
            url, headers=headers, json=body,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logging.warning("API HTTP error (%s): %s", url, e)
        return None
    except requests.exceptions.Timeout:
        logging.warning("API timeout (%s): %s", url, API_TIMEOUT)
        return None
    except Exception as e:
        logging.warning("API error (%s): %s", url, e)
        return None


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Chat via API
# ═══════════════════════════════════════════════════════════════════

def api_chat_together(
    messages: str,
    model: str = "",
    temperature: float = 0.5,
    max_tokens: int = 4096,
    use_cache: bool = True,
) -> str:
    """Envia mensagens para Together.ai e retorna a resposta do modelo.

    Precisa da variável de ambiente TOGETHER_API_KEY configurada.
    Ótimo para tarefas pesadas que exigem modelos maiores (70B+).

    Args:
        messages: Lista de mensagens no formato JSON
                  (ex: '[{"role":"user","content":"Olá"}]')
        model: Modelo a usar (padrão: Llama-3.3-70B)
        temperature: Criatividade (0.0-2.0, padrão: 0.5)
        max_tokens: Máximo de tokens (padrão: 4096)
        use_cache: Usar cache de respostas (padrão: True)

    Returns:
        Resposta do modelo ou mensagem de erro
    """
    if not _check_together():
        return (
            "❌ Together.ai não configurado. "
            "Defina a variável TOGETHER_API_KEY no ambiente."
        )

    try:
        msg_list = json.loads(messages) if isinstance(messages, str) else messages
    except json.JSONDecodeError:
        return "❌ Mensagens inválidas: não é um JSON válido."

    model_name = model or TOGETHER_DEFAULT_MODEL

    # Verifica cache
    cache_key_str = _cache_key(model_name, msg_list)
    if use_cache:
        cached = _cache_get(cache_key_str)
        if cached:
            return f"[CACHE] {cached}"

    result = _call_api(
        TOGETHER_URL, TOGETHER_API_KEY, model_name,
        msg_list, temperature=temperature, max_tokens=max_tokens,
    )

    if result is None:
        return "❌ Erro ao chamar Together.ai. Verifique sua API key e conexão."

    try:
        content = result["choices"][0]["message"]["content"] or ""
        if use_cache and content:
            _cache_set(cache_key_str, content)
        return content if content else "(resposta vazia)"
    except (KeyError, IndexError) as e:
        return f"❌ Resposta inesperada da API: {e}"


def api_chat_fireworks(
    messages: str,
    model: str = "",
    temperature: float = 0.5,
    max_tokens: int = 4096,
    use_cache: bool = True,
) -> str:
    """Envia mensagens para Fireworks e retorna a resposta do modelo.

    Precisa da variável de ambiente FIREWORKS_API_KEY configurada.
    Modelo padrão: Llama-3.3-70B-Instruct.

    Args:
        messages: Lista de mensagens no formato JSON
        model: Modelo a usar (padrão: Llama-3.3-70B)
        temperature: Criatividade (0.0-2.0)
        max_tokens: Máximo de tokens
        use_cache: Usar cache de respostas

    Returns:
        Resposta do modelo ou mensagem de erro
    """
    if not _check_fireworks():
        return (
            "❌ Fireworks não configurado. "
            "Defina a variável FIREWORKS_API_KEY no ambiente."
        )

    try:
        msg_list = json.loads(messages) if isinstance(messages, str) else messages
    except json.JSONDecodeError:
        return "❌ Mensagens inválidas: não é um JSON válido."

    model_name = model or FIREWORKS_DEFAULT_MODEL

    cache_key_str = _cache_key(model_name, msg_list)
    if use_cache:
        cached = _cache_get(cache_key_str)
        if cached:
            return f"[CACHE] {cached}"

    result = _call_api(
        FIREWORKS_URL, FIREWORKS_API_KEY, model_name,
        msg_list, temperature=temperature, max_tokens=max_tokens,
    )

    if result is None:
        return "❌ Erro ao chamar Fireworks. Verifique sua API key e conexão."

    try:
        content = result["choices"][0]["message"]["content"] or ""
        if use_cache and content:
            _cache_set(cache_key_str, content)
        return content if content else "(resposta vazia)"
    except (KeyError, IndexError) as e:
        return f"❌ Resposta inesperada da API: {e}"


def api_chat_auto(
    messages: str,
    model: str = "",
    temperature: float = 0.5,
    max_tokens: int = 4096,
    prefer: str = "together",
) -> str:
    """Tenta Together.ai primeiro, depois Fireworks como fallback.

    Escolhe automaticamente o provedor disponível.
    Together → Fireworks → erro.

    Args:
        messages: Lista de mensagens no formato JSON
        model: Modelo a usar (vazio = padrão do provedor)
        temperature: Criatividade (0.0-2.0)
        max_tokens: Máximo de tokens
        prefer: Provedor preferido ('together' ou 'fireworks')

    Returns:
        Resposta do modelo ou erro se ambos falharem
    """
    provedores = []

    if prefer == "fireworks":
        if _check_fireworks():
            provedores.append(("Fireworks", api_chat_fireworks))
        if _check_together():
            provedores.append(("Together", api_chat_together))
    else:
        if _check_together():
            provedores.append(("Together", api_chat_together))
        if _check_fireworks():
            provedores.append(("Fireworks", api_chat_fireworks))

    if not provedores:
        return (
            "❌ Nenhum provedor configurado. Defina TOGETHER_API_KEY "
            "ou FIREWORKS_API_KEY no ambiente."
        )

    erros = []
    for nome, func in provedores:
        resultado = func(messages, model=model, temperature=temperature,
                         max_tokens=max_tokens, use_cache=True)
        if not resultado.startswith("❌"):
            return resultado
        erros.append(f"{nome}: {resultado}")

    return "❌ Todos os provedores falharam:\n" + "\n".join(erros)


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Tool Calling via API
# ═══════════════════════════════════════════════════════════════════

def api_tool_call_together(
    messages: str,
    tools: str,
    model: str = "",
    temperature: float = 0.3,
) -> str:
    """Chama Together.ai com suporte a ferramentas (function calling).

    Útil para tarefas que exigem chamadas de ferramentas com modelos
    grandes (70B) que o Ollama local pode não conseguir rodar.

    Args:
        messages: Mensagens no formato JSON
        tools: Lista de ferramentas no formato JSON
        model: Modelo (padrão: Llama-3.3-70B)
        temperature: Temperatura mais baixa para tools (padrão: 0.3)

    Returns:
        Resposta formatada com tool_calls se houver
    """
    if not _check_together():
        return "❌ Together.ai não configurado."

    try:
        msg_list = json.loads(messages) if isinstance(messages, str) else messages
        tools_list = json.loads(tools) if isinstance(tools, str) else tools
    except json.JSONDecodeError as e:
        return f"❌ JSON inválido: {e}"

    model_name = model or TOGETHER_DEFAULT_MODEL

    result = _call_api(
        TOGETHER_URL, TOGETHER_API_KEY, model_name,
        msg_list, tools=tools_list,
        temperature=temperature,
    )

    if result is None:
        return "❌ Erro ao chamar Together.ai com tool calling."

    try:
        choice = result["choices"][0]["message"]
        content = choice.get("content", "") or ""
        tool_calls = choice.get("tool_calls", [])

        if not tool_calls:
            return content if content else "(sem resposta)"

        # Formata resposta com tool_calls
        output = [content] if content else []
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "?")
            fn_args = fn.get("arguments", "{}")
            output.append(f"🔧 CHAMAR FERRAMENTA: {fn_name}")
            output.append(f"   Argumentos: {fn_args}")

        return "\n".join(output)
    except (KeyError, IndexError) as e:
        return f"❌ Resposta inválida: {e}"


def api_tool_call_fireworks(
    messages: str,
    tools: str,
    model: str = "",
    temperature: float = 0.3,
) -> str:
    """Chama Fireworks com suporte a ferramentas (function calling).

    Args:
        messages: Mensagens no formato JSON
        tools: Lista de ferramentas no formato JSON
        model: Modelo (padrão: Llama-3.3-70B)
        temperature: Temperatura (padrão: 0.3)

    Returns:
        Resposta formatada com tool_calls se houver
    """
    if not _check_fireworks():
        return "❌ Fireworks não configurado."

    try:
        msg_list = json.loads(messages) if isinstance(messages, str) else messages
        tools_list = json.loads(tools) if isinstance(tools, str) else tools
    except json.JSONDecodeError as e:
        return f"❌ JSON inválido: {e}"

    model_name = model or FIREWORKS_DEFAULT_MODEL

    result = _call_api(
        FIREWORKS_URL, FIREWORKS_API_KEY, model_name,
        msg_list, tools=tools_list,
        temperature=temperature,
    )

    if result is None:
        return "❌ Erro ao chamar Fireworks com tool calling."

    try:
        choice = result["choices"][0]["message"]
        content = choice.get("content", "") or ""
        tool_calls = choice.get("tool_calls", [])

        if not tool_calls:
            return content if content else "(sem resposta)"

        output = [content] if content else []
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "?")
            fn_args = fn.get("arguments", "{}")
            output.append(f"🔧 CHAMAR FERRAMENTA: {fn_name}")
            output.append(f"   Argumentos: {fn_args}")

        return "\n".join(output)
    except (KeyError, IndexError) as e:
        return f"❌ Resposta inválida: {e}"


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Gerenciamento
# ═══════════════════════════════════════════════════════════════════

def api_status() -> str:
    """Mostra o status das APIs externas configuradas.

    Verifica se Together.ai e Fireworks estão disponíveis,
    quais modelos estão configurados e estatísticas de uso.

    Returns:
        Status detalhado dos provedores
    """
    lines = ["📊 Status das APIs Externas", "=" * 40]

    # Together
    if _check_together():
        key_display = TOGETHER_API_KEY[:8] + "..."
        lines.append(f"\n✅ Together.ai — Configurado")
        lines.append(f"   API Key: {key_display}")
        lines.append(f"   Modelo: {TOGETHER_DEFAULT_MODEL}")
        lines.append(f"   Endpoint: {TOGETHER_URL}")
    else:
        lines.append(f"\n❌ Together.ai — Não configurado")
        lines.append(f"   Defina TOGETHER_API_KEY no ambiente")

    # Fireworks
    if _check_fireworks():
        key_display = FIREWORKS_API_KEY[:8] + "..."
        lines.append(f"\n✅ Fireworks.ai — Configurado")
        lines.append(f"   API Key: {key_display}")
        lines.append(f"   Modelo: {FIREWORKS_DEFAULT_MODEL}")
        lines.append(f"   Endpoint: {FIREWORKS_URL}")
    else:
        lines.append(f"\n❌ Fireworks.ai — Não configurado")
        lines.append(f"   Defina FIREWORKS_API_KEY no ambiente")

    # Cache
    try:
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
        lines.append(f"\n📦 Cache: {len(cache_files)} respostas armazenadas")
    except Exception:
        pass

    return "\n".join(lines)


def api_clear_cache() -> str:
    """Limpa o cache de respostas das APIs externas."""
    try:
        count = 0
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, f))
                count += 1
        return f"🧹 Cache limpo: {count} arquivos removidos."
    except Exception as e:
        return f"Erro ao limpar cache: {e}"


def api_heavy_task(
    task: str,
    context: str = "",
    provider: str = "auto",
) -> str:
    """Executa uma tarefa pesada usando API externa (Together/Fireworks).

    Ideal para tarefas que exigem:
      - Modelos grandes (70B+ parâmetros)
      - Raciocínio complexo (matemática, lógica, engenharia)
      - Geração de código extenso
      - Análise de documentos grandes

    Args:
        task: Descrição da tarefa a ser executada
        context: Contexto adicional (opcional)
        provider: Provedor ('together', 'fireworks', 'auto')

    Returns:
        Resposta detalhada do modelo
    """
    prompt = f"Tarefa: {task}"
    if context:
        prompt += f"\n\nContexto:\n{context[:3000]}"
    prompt += (
        "\n\nSeja detalhado e preciso na resposta. "
        "Inclua exemplos, código ou explicações conforme necessário."
    )

    messages_json = json.dumps([
        {
            "role": "system",
            "content": (
                "Você é um assistente de IA especializado em tarefas complexas. "
                "Responda de forma detalhada, precisa e organizada."
            ),
        },
        {"role": "user", "content": prompt},
    ], ensure_ascii=False)

    if provider == "fireworks":
        return api_chat_fireworks(messages_json)
    else:
        return api_chat_auto(messages_json, prefer="together")


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Modelos disponíveis
# ═══════════════════════════════════════════════════════════════════

def api_list_models(provider: str = "all") -> str:
    """Lista modelos recomendados para cada provedor.

    Args:
        provider: 'together', 'fireworks', ou 'all' (padrão)

    Returns:
        Lista de modelos com descrições
    """
    models = {
        "together": [
            ("meta-llama/Llama-3.3-70B-Instruct-Turbo",
             "⭐⭐ Melhor para tarefas complexas e raciocínio"),
            ("Qwen/Qwen2.5-72B-Instruct-Turbo",
             "⭐⭐ Excelente para código e tarefas gerais"),
            ("deepseek-ai/DeepSeek-R1",
             "⭐ Especialista em raciocínio lógico e matemática"),
            ("mistralai/Mixtral-8x22B-Instruct-v0.1",
             "⭐ Bom custo-benefício para tarefas diversas"),
            ("meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
             "⭐ Suporte a imagens (visão)"),
        ],
        "fireworks": [
            ("accounts/fireworks/models/llama-v3p3-70b-instruct",
             "⭐⭐ Melhor para tarefas complexas"),
            ("accounts/fireworks/models/qwen2p5-72b-instruct",
             "⭐⭐ Excelente para código"),
            ("accounts/fireworks/models/deepseek-r1",
             "⭐ Especialista em raciocínio"),
        ],
    }

    lines = ["📋 Modelos Recomendados", "=" * 40]

    if provider in ("together", "all"):
        lines.append("\n🔥 Together.ai:")
        for model, desc in models["together"]:
            lines.append(f"  • {model}")
            lines.append(f"    {desc}")

    if provider in ("fireworks", "all"):
        lines.append("\n🎆 Fireworks.ai:")
        for model, desc in models["fireworks"]:
            lines.append(f"  • {model}")
            lines.append(f"    {desc}")

    lines.append("\n💡 Dica: Passe o nome do modelo no parâmetro 'model'")
    lines.append("   para usar um modelo específico.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════════════

def register(api):
    """Registra todas as ferramentas de API externa."""

    api.register_tool(
        "api_chat_together", api_chat_together,
        "🔥 Envia mensagens para Together.ai (Llama-3.3-70B) e retorna a resposta. "
        "Ideal para tarefas pesadas que exigem modelos grandes. "
        "Requer TOGETHER_API_KEY no ambiente.",
        {
            "messages": {"type": "string", "description": "Mensagens em JSON: [{\"role\":\"user\",\"content\":\"...\"}]"},
            "model": {"type": "string", "description": "Modelo (opcional, padrão: Llama-3.3-70B)"},
            "temperature": {"type": "number", "description": "Criatividade 0-2 (padrão: 0.5)"},
            "max_tokens": {"type": "integer", "description": "Máx tokens (padrão: 4096)"},
            "use_cache": {"type": "boolean", "description": "Usar cache (padrão: True)"},
        },
        ["messages"],
    )

    api.register_tool(
        "api_chat_fireworks", api_chat_fireworks,
        "🎆 Envia mensagens para Fireworks.ai (Llama-3.3-70B) e retorna a resposta. "
        "Ótimo fallback para Together.ai. Requer FIREWORKS_API_KEY no ambiente.",
        {
            "messages": {"type": "string", "description": "Mensagens em JSON"},
            "model": {"type": "string", "description": "Modelo (opcional)"},
            "temperature": {"type": "number", "description": "Criatividade 0-2 (padrão: 0.5)"},
            "max_tokens": {"type": "integer", "description": "Máx tokens (padrão: 4096)"},
            "use_cache": {"type": "boolean", "description": "Usar cache (padrão: True)"},
        },
        ["messages"],
    )

    api.register_tool(
        "api_chat_auto", api_chat_auto,
        "🔄 Tenta Together.ai primeiro, depois Fireworks como fallback automático. "
        "Escolhe o melhor provedor disponível sem você precisar especificar.",
        {
            "messages": {"type": "string", "description": "Mensagens em JSON"},
            "model": {"type": "string", "description": "Modelo (opcional)"},
            "temperature": {"type": "number", "description": "Criatividade 0-2 (padrão: 0.5)"},
            "max_tokens": {"type": "integer", "description": "Máx tokens (padrão: 4096)"},
            "prefer": {"type": "string", "description": "Preferência: 'together' ou 'fireworks' (padrão: 'together')"},
        },
        ["messages"],
    )

    api.register_tool(
        "api_tool_call_together", api_tool_call_together,
        "🔧 Chama Together.ai com suporte a ferramentas (function calling). "
        "Para tarefas que exigem chamar funções com modelos 70B.",
        {
            "messages": {"type": "string", "description": "Mensagens em JSON"},
            "tools": {"type": "string", "description": "Ferramentas em JSON"},
            "model": {"type": "string", "description": "Modelo (opcional)"},
            "temperature": {"type": "number", "description": "Temperatura (padrão: 0.3)"},
        },
        ["messages", "tools"],
    )

    api.register_tool(
        "api_tool_call_fireworks", api_tool_call_fireworks,
        "🔧 Chama Fireworks.ai com suporte a ferramentas (function calling). "
        "Fallback para tool calling quando Together não disponível.",
        {
            "messages": {"type": "string", "description": "Mensagens em JSON"},
            "tools": {"type": "string", "description": "Ferramentas em JSON"},
            "model": {"type": "string", "description": "Modelo (opcional)"},
            "temperature": {"type": "number", "description": "Temperatura (padrão: 0.3)"},
        },
        ["messages", "tools"],
    )

    api.register_tool(
        "api_heavy_task", api_heavy_task,
        "🏋️ Executa uma tarefa pesada usando API externa. "
        "Ideal para: raciocínio complexo, código extenso, análise de documentos, "
        "matemática avançada. Usa Together.ai ou Fireworks automaticamente.",
        {
            "task": {"type": "string", "description": "Descrição da tarefa"},
            "context": {"type": "string", "description": "Contexto adicional (opcional)"},
            "provider": {"type": "string", "description": "Provedor: 'together', 'fireworks', 'auto' (padrão: 'auto')"},
        },
        ["task"],
    )

    api.register_tool(
        "api_status", api_status,
        "📊 Mostra o status das APIs externas: Together.ai e Fireworks configurados, "
        "modelos padrão e estatísticas de cache.",
        {},
        [],
    )

    api.register_tool(
        "api_clear_cache", api_clear_cache,
        "🧹 Limpa o cache de respostas das APIs externas para forçar requisições novas.",
        {},
        [],
    )

    api.register_tool(
        "api_list_models", api_list_models,
        "📋 Lista modelos recomendados para Together.ai e Fireworks.ai "
        "com descrições de uso recomendado.",
        {
            "provider": {"type": "string", "description": "Filtrar: 'together', 'fireworks', 'all' (padrão: 'all')"},
        },
        [],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "APIs externas Together.ai e Fireworks.ai como fallback para tarefas pesadas com modelos 70B+",
        "tools": [
            "api_chat_together", "api_chat_fireworks", "api_chat_auto",
            "api_tool_call_together", "api_tool_call_fireworks",
            "api_heavy_task", "api_status", "api_clear_cache",
            "api_list_models",
        ],
    }
