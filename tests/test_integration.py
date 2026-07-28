"""
test_integration.py
===================
Testes de integracao: fluxo completo do agente com mocks.
"""

import os
import sys
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_data_dir():
    """Cria diretorio temporario para dados de teste."""
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# =====================================================================
# HISTORY DB
# =====================================================================

class TestHistoryDB:
    """Testes para o modulo SQLite de historico."""

    def test_import(self):
        from core.history_db import (
            save_messages, load_messages, append_message,
            search_messages, get_stats, delete_session,
        )
        assert callable(save_messages)
        assert callable(load_messages)

    def test_save_and_load(self, tmp_data_dir):
        from core.history_db import save_messages, load_messages
        test_db = os.path.join(tmp_data_dir, "test_history.db")
        with patch("core.history_db.DB_PATH", test_db):
            # Reinit with test DB
            import core.history_db as hdb
            hdb._local.conn = None
            hdb.DB_PATH = test_db
            hdb.init_history_db()

            messages = [
                {"role": "user", "content": "Ola"},
                {"role": "assistant", "content": "Ola! Como posso ajudar?"},
            ]
            save_messages(messages, "test_session")
            loaded = load_messages("test_session")
            assert len(loaded) == 2
            assert loaded[0]["content"] == "Ola"
            assert loaded[1]["content"] == "Ola! Como posso ajudar?"

    def test_append_message(self, tmp_data_dir):
        from core.history_db import append_message, load_messages
        test_db = os.path.join(tmp_data_dir, "test_append.db")
        with patch("core.history_db.DB_PATH", test_db):
            import core.history_db as hdb
            hdb._local.conn = None
            hdb.DB_PATH = test_db
            hdb.init_history_db()

            append_message("user", "Primeira mensagem", "s1")
            append_message("assistant", "Resposta", "s1")
            loaded = load_messages("s1")
            assert len(loaded) == 2

    def test_search_messages(self, tmp_data_dir):
        from core.history_db import save_messages, search_messages
        test_db = os.path.join(tmp_data_dir, "test_search.db")
        with patch("core.history_db.DB_PATH", test_db):
            import core.history_db as hdb
            hdb._local.conn = None
            hdb.DB_PATH = test_db
            hdb.init_history_db()

            messages = [
                {"role": "user", "content": "Qual e a capital do Brasil?"},
                {"role": "assistant", "content": "Brasilia e a capital."},
            ]
            save_messages(messages, "s1")
            results = search_messages("Brasil")
            assert len(results) >= 1

    def test_get_stats(self, tmp_data_dir):
        from core.history_db import save_messages, get_stats
        test_db = os.path.join(tmp_data_dir, "test_stats.db")
        with patch("core.history_db.DB_PATH", test_db):
            import core.history_db as hdb
            hdb._local.conn = None
            hdb.DB_PATH = test_db
            hdb.init_history_db()

            messages = [{"role": "user", "content": "teste"}]
            save_messages(messages, "s1")
            stats = get_stats()
            assert stats["total_messages"] >= 1
            assert stats["total_sessions"] >= 1


# =====================================================================
# COMPACT (TOKEN-BASED)
# =====================================================================

class TestCompact:
    """Testes para a compactacao baseada em tokens."""

    def test_compact_noop_when_small(self):
        from core.compact import compact_messages
        messages = [
            {"role": "user", "content": "Ola"},
            {"role": "assistant", "content": "Ola!"},
        ]
        result = compact_messages(messages, max_tokens=1000)
        assert len(result) == 2

    def test_compact_removes_empty_tools(self):
        from core.compact import compact_messages
        messages = [
            {"role": "user", "content": "teste"},
            {"role": "tool", "content": ""},
            {"role": "assistant", "content": "ok"},
        ]
        result = compact_messages(messages, max_tokens=1)
        assert len(result) == 2  # empty tool removed

    def test_compact_truncates_old(self):
        from core.compact import compact_messages
        messages = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "msg1 " * 100},
            {"role": "assistant", "content": "resp1 " * 100},
            {"role": "user", "content": "msg2 " * 100},
            {"role": "assistant", "content": "resp2 " * 100},
        ]
        result = compact_messages(messages, max_tokens=50)
        # System message should be preserved
        assert any(m["role"] == "system" for m in result)
        # But total should be within limit
        total = sum(len(m.get("content", "")) // 4 for m in result)
        assert total <= 100  # some slack for estimation


# =====================================================================
# MEMORY INTEGRATION
# =====================================================================

class TestMemoryIntegration:
    """Testes de integracao do sistema de memoria."""

    def test_memory_pipeline_import(self):
        from core.memory_pipeline import run_memory_pipeline, get_memory_context_str
        assert callable(run_memory_pipeline)
        assert callable(get_memory_context_str)

    def test_hindsight_import(self):
        from core.hindsight import (
            hindsight_retain, hindsight_context_for_turn,
        )
        assert callable(hindsight_retain)
        assert callable(hindsight_context_for_turn)

    def test_autonomy_import(self):
        from core.autonomy import (
            _latest_user_text, _autonomous_context_for_turn,
            _score_intents, _detect_complexity,
        )
        assert callable(_latest_user_text)
        assert callable(_score_intents)


# =====================================================================
# AGENT LOOP INTEGRATION
# =====================================================================

class TestAgentLoopIntegration:
    """Testes de integracao do agent_loop com mocks."""

    def test_ensure_system_prompt(self):
        from core.agent_loop import ensure_system_prompt
        messages = [{"role": "user", "content": "Ola"}]
        result = ensure_system_prompt(messages)
        assert result[0]["role"] == "system"
        assert len(result) == 2

    def test_public_messages(self):
        from core.agent_loop import public_messages
        messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "ola"},
            {"role": "system", "content": "autonomo", "_autonomous_context": True},
            {"role": "assistant", "content": "oi"},
        ]
        result = public_messages(messages)
        assert len(result) == 3  # autonomous context removed

    def test_is_refusal(self):
        from core.agent_loop import _is_refusal
        assert _is_refusal("Nao posso ajudar com isso") is True
        assert _is_refusal("Claro! Vou fazer isso.") is False
        assert _is_refusal("I can't do that") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
