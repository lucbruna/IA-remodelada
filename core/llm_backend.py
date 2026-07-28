"""
core/llm_backend.py
===================
Abstracao de backend LLM multi-provedor.

Inspired by:
  - OpenAI SDK: client pattern com retries, streaming, structured outputs
  - Anthropic SDK: tool_use pattern, extended thinking, system prompts
  - Fable 5: self-verification adversarial loop

Suporta:
  - Ollama (local, padrao)
  - OpenAI (GPT-4, GPT-4o, etc.)
  - Anthropic (Claude 3.5, Claude 4, etc.)

Usage:
    from core.llm_backend import get_backend, ChatMessage
    backend = get_backend()  # detecta automaticamente
    response = backend.chat([ChatMessage(role="user", content="Ola")])
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Generator
from enum import Enum

from ._common import (
    MODEL, NUM_CTX, TEMPERATURE, OLLAMA_TIMEOUT_SECONDS,
    OLLAMA_MAX_RETRIES, OLLAMA_KEEP_ALIVE,
)


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Mensagem padronizada entre backends."""
    role: str
    content: str = ""
    tool_calls: list = field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ChatResponse:
    """Resposta padronizada entre backends."""
    content: str = ""
    tool_calls: list = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    raw: Any = None


class LLMBackend(ABC):
    """Interface abstrata para backends LLM."""

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        tools: list = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False,
        **kwargs,
    ) -> ChatResponse:
        """Envia mensagens e retorna resposta."""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[ChatMessage],
        tools: list = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs,
    ) -> Generator[ChatResponse, None, None]:
        """Envia mensagens e yield tokens incrementalmente."""
        pass

    @abstractmethod
    def embed(self, text: str, model: str = None) -> list:
        """Gera embedding de um texto."""
        pass

    @abstractmethod
    def list_models(self) -> list:
        """Lista modelos disponiveis."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica se o backend esta disponivel."""
        pass


class OllamaBackend(LLMBackend):
    """Backend Ollama (local)."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import ollama
            self._client = ollama
        return self._client

    def chat(self, messages, tools=None, model=None, temperature=None,
             max_tokens=None, stream=False, **kwargs) -> ChatResponse:
        client = self._get_client()
        model = model or MODEL
        temp = temperature if temperature is not None else TEMPERATURE
        opts = {"num_ctx": NUM_CTX, "temperature": temp}
        if max_tokens:
            opts["num_predict"] = max_tokens

        msg_dicts = [m.to_dict() for m in messages]
        try:
            resp = client.chat(
                model=model,
                messages=msg_dicts,
                tools=tools or [],
                keep_alive=OLLAMA_KEEP_ALIVE,
                options=opts,
                stream=False,
            )
            msg = resp.get("message", {})
            return ChatResponse(
                content=msg.get("content", ""),
                tool_calls=msg.get("tool_calls", []),
                model=model,
                usage={"total_tokens": resp.get("eval_count", 0)},
                finish_reason="stop",
                raw=resp,
            )
        except Exception as e:
            logging.error("Ollama chat error: %s", e)
            raise

    def chat_stream(self, messages, tools=None, model=None, temperature=None,
                    max_tokens=None, **kwargs) -> Generator[ChatResponse, None, None]:
        client = self._get_client()
        model = model or MODEL
        temp = temperature if temperature is not None else TEMPERATURE
        opts = {"num_ctx": NUM_CTX, "temperature": temp}

        msg_dicts = [m.to_dict() for m in messages]
        stream = client.chat(
            model=model,
            messages=msg_dicts,
            tools=tools or [],
            keep_alive=OLLAMA_KEEP_ALIVE,
            options=opts,
            stream=True,
        )
        content_parts = []
        tool_calls = []
        for chunk in stream:
            msg = chunk.get("message", {})
            delta = msg.get("content")
            if delta:
                content_parts.append(delta)
                yield ChatResponse(content=delta, model=model)
            tc = msg.get("tool_calls")
            if tc:
                tool_calls.extend(tc)

        if tool_calls:
            yield ChatResponse(content="", tool_calls=tool_calls, model=model)

    def embed(self, text, model="nomic-embed-text") -> list:
        client = self._get_client()
        resp = client.embeddings(model=model, prompt=text)
        return resp.get("embedding", [])

    def list_models(self) -> list:
        client = self._get_client()
        try:
            resp = client.list()
            raw = resp.get("models", []) if hasattr(resp, "get") else getattr(resp, "models", [])
            return [
                {"name": m.get("name") or m.get("model", "?"), "provider": "ollama"}
                for m in raw
            ]
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False


class OpenAIBackend(LLMBackend):
    """Backend OpenAI (GPT-4, GPT-4o, etc.)."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ValueError("OPENAI_API_KEY nao configurada")
            import openai
            self._client = openai.OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    def _convert_tools(self, tools: list) -> list:
        """Converte ferramentas do formato Ollama para OpenAI."""
        if not tools:
            return []
        converted = []
        for t in tools:
            if isinstance(t, dict) and "function" in t:
                converted.append({
                    "type": "function",
                    "function": t["function"],
                })
            else:
                converted.append(t)
        return converted

    def chat(self, messages, tools=None, model=None, temperature=None,
             max_tokens=None, stream=False, **kwargs) -> ChatResponse:
        client = self._get_client()
        model = model or "gpt-4o"
        temp = temperature if temperature is not None else 0.5

        msg_dicts = []
        for m in messages:
            d = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            if m.name:
                d["name"] = m.name
            msg_dicts.append(d)

        kwargs_chat = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temp,
        }
        if max_tokens:
            kwargs_chat["max_tokens"] = max_tokens
        if tools:
            kwargs_chat["tools"] = self._convert_tools(tools)

        resp = client.chat.completions.create(**kwargs_chat)
        choice = resp.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })

        return ChatResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            finish_reason=choice.finish_reason or "",
            raw=resp,
        )

    def chat_stream(self, messages, tools=None, model=None, temperature=None,
                    max_tokens=None, **kwargs) -> Generator[ChatResponse, None, None]:
        client = self._get_client()
        model = model or "gpt-4o"
        temp = temperature if temperature is not None else 0.5

        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        kwargs_chat = {"model": model, "messages": msg_dicts, "temperature": temp, "stream": True}
        if max_tokens:
            kwargs_chat["max_tokens"] = max_tokens
        if tools:
            kwargs_chat["tools"] = self._convert_tools(tools)

        stream = client.chat.completions.create(**kwargs_chat)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield ChatResponse(content=chunk.choices[0].delta.content, model=model)

    def embed(self, text, model="text-embedding-3-small") -> list:
        client = self._get_client()
        resp = client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding

    def list_models(self) -> list:
        if not self._api_key:
            return []
        try:
            client = self._get_client()
            resp = client.models.list()
            return [
                {"name": m.id, "provider": "openai"}
                for m in resp.data
                if "gpt" in m.id or "o1" in m.id or "o3" in m.id
            ]
        except Exception:
            return []

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False


class AnthropicBackend(LLMBackend):
    """Backend Anthropic (Claude 3.5, Claude 4, etc.)."""

    def __init__(self, api_key: str = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ValueError("ANTHROPIC_API_KEY nao configurada")
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _convert_messages(self, messages: List[ChatMessage]):
        """Converte mensagens para formato Anthropic (system separado)."""
        system = ""
        msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                msgs.append({"role": m.role, "content": m.content})
        return system, msgs

    def _convert_tools(self, tools: list) -> list:
        """Converte ferramentas para formato Anthropic."""
        if not tools:
            return []
        converted = []
        for t in tools:
            if isinstance(t, dict) and "function" in t:
                fn = t["function"]
                converted.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })
        return converted

    def chat(self, messages, tools=None, model=None, temperature=None,
             max_tokens=None, stream=False, **kwargs) -> ChatResponse:
        client = self._get_client()
        model = model or "claude-sonnet-4-20250514"
        temp = temperature if temperature is not None else 0.5
        max_tok = max_tokens or 4096

        system, msgs = self._convert_messages(messages)
        kwargs_chat = {
            "model": model,
            "max_tokens": max_tok,
            "messages": msgs,
            "temperature": temp,
        }
        if system:
            kwargs_chat["system"] = system
        if tools:
            kwargs_chat["tools"] = self._convert_tools(tools)

        resp = client.messages.create(**kwargs_chat)

        content = ""
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.input_tokens,
                "completion_tokens": resp.usage.output_tokens,
            },
            finish_reason=resp.stop_reason or "",
            raw=resp,
        )

    def chat_stream(self, messages, tools=None, model=None, temperature=None,
                    max_tokens=None, **kwargs) -> Generator[ChatResponse, None, None]:
        client = self._get_client()
        model = model or "claude-sonnet-4-20250514"
        temp = temperature if temperature is not None else 0.5

        system, msgs = self._convert_messages(messages)
        kwargs_chat = {
            "model": model,
            "max_tokens": max_tokens or 4096,
            "messages": msgs,
            "temperature": temp,
        }
        if system:
            kwargs_chat["system"] = system
        if tools:
            kwargs_chat["tools"] = self._convert_tools(tools)

        with client.messages.stream(**kwargs_chat) as stream:
            for text in stream.text_stream:
                yield ChatResponse(content=text, model=model)

    def embed(self, text, model="text-embedding-3-small") -> list:
        raise NotImplementedError("Anthropic nao suporta embeddings nativamente")

    def list_models(self) -> list:
        if not self._api_key:
            return []
        # Anthropic nao tem endpoint de listagem, retorna modelos conhecidos
        return [
            {"name": "claude-sonnet-4-20250514", "provider": "anthropic"},
            {"name": "claude-opus-4-20250514", "provider": "anthropic"},
            {"name": "claude-3-5-haiku-20241022", "provider": "anthropic"},
        ]

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            client = self._get_client()
            client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False


# --- Cost Tracking ---

_COST_TABLE = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5.4": {"input": 4.00, "output": 20.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
}
_COST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agente_data", "cost_tracking.json")


def _load_costs() -> dict:
    try:
        import json
        if os.path.exists(_COST_FILE):
            with open(_COST_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"total_spent": 0.0, "calls": []}


def _save_costs(costs: dict) -> None:
    try:
        import json
        os.makedirs(os.path.dirname(_COST_FILE), exist_ok=True)
        with open(_COST_FILE, "w") as f:
            json.dump(costs, f, indent=2)
    except Exception:
        pass


def track_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = _load_costs()
    rates = _COST_TABLE.get(model, {"input": 1.0, "output": 2.0})
    cost = (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])
    costs["total_spent"] += cost
    costs["calls"].append({"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens, "cost": cost})
    if len(costs["calls"]) > 10000:
        costs["calls"] = costs["calls"][-1000:]
    _save_costs(costs)
    return cost


def get_total_cost() -> float:
    return _load_costs().get("total_spent", 0.0)


# --- Prompt Caching ---

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agente_data", "prompt_cache")


class PromptCache:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        os.makedirs(_CACHE_DIR, exist_ok=True)

    def _key(self, model: str, messages: list) -> str:
        import hashlib
        raw = model + "|" + str([(m.role, m.content[:200]) for m in messages])
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, model: str, messages: list) -> Optional[str]:
        import json
        key = self._key(model, messages)
        path = os.path.join(_CACHE_DIR, f"{key}.json")
        if not os.path.exists(path):
            return None
        try:
            age = time.time() - os.path.getmtime(path)
            if age > self.ttl:
                os.remove(path)
                return None
            with open(path) as f:
                return json.load(f).get("response", "")
        except Exception:
            return None

    def set(self, model: str, messages: list, response: str) -> None:
        import json
        key = self._key(model, messages)
        path = os.path.join(_CACHE_DIR, f"{key}.json")
        try:
            with open(path, "w") as f:
                json.dump({"response": response, "model": model, "ts": time.time()}, f)
        except Exception:
            pass


_cache = PromptCache()


# --- Fallback Backend ---

class FallbackBackend(LLMBackend):
    """Backend que tenta local primeiro, depois fallback para API."""

    def __init__(self):
        self._local = OllamaBackend()
        self._api = None
        self._api_provider = None

    def _get_api_backend(self) -> LLMBackend:
        if self._api is None:
            if os.environ.get("OPENAI_API_KEY"):
                self._api = OpenAIBackend()
                self._api_provider = "openai"
            elif os.environ.get("ANTHROPIC_API_KEY"):
                self._api = AnthropicBackend()
                self._api_provider = "anthropic"
        return self._api

    def _should_fallback(self, error: Exception) -> bool:
        err_str = str(error).lower()
        return any(kw in err_str for kw in ["timeout", "connection", "unavailable", "not found", "404", "500"])

    def chat(self, messages, tools=None, model=None, temperature=None,
             max_tokens=None, stream=False, **kwargs) -> ChatResponse:
        from config import LLM_FALLBACK_ENABLED, LLM_FALLBACK_MODEL
        cached = _cache.get(model or "", messages)
        if cached:
            return ChatResponse(content=cached, model=model or "cache")

        try:
            return self._local.chat(messages, tools, model, temperature, max_tokens, stream, **kwargs)
        except Exception as e:
            if LLM_FALLBACK_ENABLED and self._should_fallback(e):
                api = self._get_api_backend()
                if api:
                    try:
                        fb_model = model or LLM_FALLBACK_MODEL
                        resp = api.chat(messages, tools, fb_model, temperature, max_tokens, stream, **kwargs)
                        usage = resp.usage or {}
                        track_cost(fb_model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                        _cache.set(fb_model, messages, resp.content)
                        return resp
                    except Exception:
                        pass
            raise

    def chat_stream(self, messages, tools=None, model=None, temperature=None,
                    max_tokens=None, **kwargs):
        try:
            yield from self._local.chat_stream(messages, tools, model, temperature, max_tokens, **kwargs)
        except Exception:
            api = self._get_api_backend()
            if api:
                yield from api.chat_stream(messages, tools, model, temperature, max_tokens, **kwargs)

    def embed(self, text, model="nomic-embed-text") -> list:
        return self._local.embed(text, model)

    def list_models(self) -> list:
        local = self._local.list_models()
        api = self._get_api_backend()
        if api:
            try:
                local.extend(api.list_models())
            except Exception:
                pass
        return local

    def health_check(self) -> bool:
        return self._local.health_check() or (self._get_api_backend() is not None)


# --- Factory ---

_backends = {}


def get_backend(provider: str = None) -> LLMBackend:
    """Retorna o backend LLM configurado.

    Auto-deteccao:
      1. Se provider explicitado, usa esse
      2. Se OPENAI_API_KEY configurada, usa OpenAI
      3. Se ANTHROPIC_API_KEY configurada, usa Anthropic
      4. Senao, usa Ollama (local)
    """
    global _backends

    if provider:
        key = provider.lower()
    else:
        if os.environ.get("OPENAI_API_KEY"):
            key = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            key = "anthropic"
        else:
            key = "ollama"

    if key not in _backends:
        if key == "openai":
            _backends[key] = OpenAIBackend()
        elif key == "anthropic":
            _backends[key] = AnthropicBackend()
        else:
            _backends[key] = OllamaBackend()

    return _backends[key]


def list_all_models() -> dict:
    """Lista modelos de todos os backends disponiveis."""
    result = {}
    for name in ["ollama", "openai", "anthropic"]:
        try:
            backend = get_backend(name)
            models = backend.list_models()
            if models:
                result[name] = models
        except Exception:
            pass
    return result


def health_check_all() -> dict:
    """Health check de todos os backends."""
    result = {}
    for name in ["ollama", "openai", "anthropic"]:
        try:
            backend = get_backend(name)
            result[name] = backend.health_check()
        except Exception:
            result[name] = False
    return result
