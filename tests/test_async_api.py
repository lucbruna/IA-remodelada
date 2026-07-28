"""Testes do pipeline assíncrono e do normalizador de modelo.

Garante que:
  - run_agent_turn_async produz o mesmo resultado de run_agent_turn;
  - run_agent_turn_stream_async emite tokens e finaliza corretamente;
  - o event loop não é bloqueado (execução em thread/queue);
  - _normalize_model protege contra '?', vazio ou None.
"""

import asyncio

import pytest

from core import agent_loop
from core.agent_loop import run_agent_turn_async, run_agent_turn_stream_async
from agente_api_server import _normalize_model


def _fake_chat(model, messages, tools=None):
    """Substitui a chamada síncrona ao Ollama por resposta fake."""
    return {
        "message": {
            "role": "assistant",
            "content": "Resposta assíncrona de teste.",
        }
    }


def _fake_stream(model, messages, tools=None, on_token=None, on_tool=None):
    for tok in ["Resposta ", "assíncrona ", "de ", "teste."]:
        if on_token:
            on_token(tok)
    return {
        "message": {
            "role": "assistant",
            "content": "Resposta assíncrona de teste.",
        }
    }


@pytest.mark.asyncio
async def test_run_agent_turn_async_returns_messages(monkeypatch):
    monkeypatch.setattr(agent_loop, "_chat_with_retries", _fake_chat)
    monkeypatch.setattr(agent_loop.agente_turbo, "semantic_cache_get", lambda *a, **k: None)
    monkeypatch.setattr(agent_loop.agente_turbo, "smart_context_compress", lambda m, *a, **k: m)
    messages = [{"role": "user", "content": "oi unico async"}]
    result = await run_agent_turn_async(messages, model="qwen2.5:1.5b")
    assert isinstance(result, list)
    assert result[-1]["role"] == "assistant"
    assert "Resposta assíncrona" in result[-1]["content"]


@pytest.mark.asyncio
async def test_run_agent_turn_async_does_not_block_event_loop(monkeypatch):
    """Se fosse bloqueante, o sleep abaixo não intercalaria com a execução."""
    monkeypatch.setattr(agent_loop, "_chat_with_retries", _fake_chat)
    monkeypatch.setattr(agent_loop.agente_turbo, "semantic_cache_get", lambda *a, **k: None)

    ticks = []

    async def ticker():
        for _ in range(5):
            ticks.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)

    messages = [{"role": "user", "content": "oi"}]
    await asyncio.gather(run_agent_turn_async(messages), ticker())
    # O ticker rodou (event loop livre) durante a tarefa async.
    assert len(ticks) == 5


@pytest.mark.asyncio
async def test_run_agent_turn_stream_async_emits_tokens(monkeypatch):
    monkeypatch.setattr(agent_loop, "_stream_chat", _fake_stream)
    # Desativa cache semântico/compressão para forçar o caminho de streaming.
    monkeypatch.setattr(agent_loop.agente_turbo, "semantic_cache_get", lambda *a, **k: None)
    monkeypatch.setattr(agent_loop.agente_turbo, "smart_context_compress", lambda m, *a, **k: m)
    from asyncio import Queue

    queue: Queue = Queue()
    messages = [{"role": "user", "content": "oi unico streaming"}]
    result = await run_agent_turn_stream_async(messages, model="qwen2.5:1.5b", queue=queue)

    # call_soon_threadsafe agenda os puts; damos chance ao loop de esvaziá-los.
    collected = []
    for _ in range(50):
        await asyncio.sleep(0)
        while not queue.empty():
            kind, payload = queue.get_nowait()
            if kind == "token":
                collected.append(payload)
        if len("".join(collected)) >= len("Resposta assíncrona de teste."):
            break

    assert "".join(collected) == "Resposta assíncrona de teste."
    assert result[-1]["role"] == "assistant"


@pytest.mark.parametrize("value,expected", [
    (None, "qwen2.5:1.5b"),
    ("", "qwen2.5:1.5b"),
    ("?", "qwen2.5:1.5b"),
    ("null", "qwen2.5:1.5b"),
    ("None", "qwen2.5:1.5b"),
    ("  ", "qwen2.5:1.5b"),
    ("llama3.1", "llama3.1"),
])
def test_normalize_model(value, expected):
    assert _normalize_model(value) == expected
