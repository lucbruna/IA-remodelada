"""
test_agente_cli.py
==================
Testes de integracao para o loop principal do agente_cli (chat_loop()).

Simula entradas do usuario via mock do input() e captura a saida
com capsys, testando todos os comandos especiais e o fluxo de
envio de mensagens (com run_agent_turn mockado).

Uso:
    pytest test_agente_cli.py -v
    pytest test_agente_cli.py -v -k sair
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch


# Forca cores vazias (como em terminal nao-interativo)
# Isso precisa ser feito antes de importar agente_cli


# =====================================================================
# Helper: simula multiplas entradas do usuario
# =====================================================================

def _simular_entradas(*entradas):
    """Cria um side_effect para input() que retorna cada entrada por vez.
    A ultima entrada e sempre 'sair' para garantir que o loop termine.
    """
    lista = list(entradas)
    # Garante que o loop termina
    if not lista or lista[-1].lower() not in ("sair", "exit", "quit", "__EOF__"):
        lista.append("sair")
    return lista


# =====================================================================
# Tests: Comandos de saida
# =====================================================================

class TestComandosSaida:
    """Testa os comandos que encerram o chat_loop()."""

    def test_sair(self, capsys):
        """Comando 'sair' encerra o loop."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Até mais" in saida

    def test_exit(self, capsys):
        """Comando 'exit' encerra o loop."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["exit"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Até mais" in saida

    def test_quit(self, capsys):
        """Comando 'quit' encerra o loop."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["quit"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Até mais" in saida

    def test_eof(self, capsys):
        """EOFError (Ctrl+D) encerra o loop."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=EOFError("EOF")), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Até mais" in saida

    def test_keyboard_interrupt(self, capsys):
        """KeyboardInterrupt (Ctrl+C) encerra o loop."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=KeyboardInterrupt()), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Até mais" in saida


# =====================================================================
# Tests: Comandos de navegacao
# =====================================================================

class TestComandosNavegacao:
    """Testa comandos que nao chamam o modelo."""

    def test_ajuda(self, capsys):
        """Comando '/ajuda' exibe ajuda formatada."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/ajuda", "sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "AJUDA" in saida
        assert "export-md" in saida
        assert "export-html" in saida
        assert "/memorias" in saida

    def test_help(self, capsys):
        """Comando '/help' exibe ajuda (alias do /ajuda)."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/help", "sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "AJUDA" in saida

    def test_memorias(self, capsys):
        """Comando '/memorias' lista memorias."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/memorias", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.list_memories", return_value="memoria1: teste"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "MEMÓRIAS" in saida or "MEMORIAS" in saida
        assert "memoria1" in saida

    def test_plugins(self, capsys):
        """Comando '/plugins' lista plugins carregados."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/plugins", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.list_plugins", return_value="Nenhum plugin carregado."):
            chat_loop()
        saida = capsys.readouterr().out
        assert "PLUGINS" in saida

    @patch("agente_cli.reload_plugins", return_value="3 carregados de 3 encontrados.")
    def test_plugins_reload(self, mock_reload, capsys):
        """Comando '/plugins-reload' recarrega plugins do disco."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/plugins-reload", "sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "3 carregados" in saida
        mock_reload.assert_called_once()

    def test_nova_conversa(self, capsys):
        """Comando 'nova conversa' reinicia as mensagens."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["nova conversa", "sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "reiniciada" in saida.lower()

    def test_entrada_vazia(self, capsys):
        """Entrada vazia (espacos) e ignorada, loop continua."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["   ", "sair"]), \
             patch("agente_cli.run_agent_turn"):
            chat_loop()
        saida = capsys.readouterr().out
        # Nao deve ter chamado run_agent_turn
        # Apenas a mensagem de saida deve aparecer (alem do welcome)
        assert "Até mais" in saida


# =====================================================================
# Tests: Exportacao
# =====================================================================

class TestExportacao:
    """Testa os comandos de exportacao."""

    def test_export_md_sem_filtro(self, capsys):
        """Comando '/export-md' exporta conversa como Markdown."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-md", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_markdown",
                   return_value="Conversa exportada como Markdown: /tmp/teste.md"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "exportada" in saida.lower()

    def test_export_md_com_role(self, capsys):
        """Comando '/export-md user' filtra por remetente."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-md user", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_markdown") as mock_export:
            chat_loop()
        # Verifica que role_filter='user' foi passado
        _, kwargs = mock_export.call_args
        assert kwargs.get("role_filter") == "user"

    def test_export_md_com_data_e_role(self, capsys):
        """Comando '/export-md 16/07 16/07 user' combina filtros."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-md 16/07/2026 16/07/2026 user", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_markdown") as mock_export:
            chat_loop()
        _, kwargs = mock_export.call_args
        assert kwargs.get("start_date") == "16/07/2026"
        assert kwargs.get("end_date") == "16/07/2026"
        assert kwargs.get("role_filter") == "user"

    def test_export_html(self, capsys):
        """Comando '/export-html' exporta conversa como HTML."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-html", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_html",
                   return_value="Conversa exportada como HTML: /tmp/teste.html"):
            chat_loop()
        saida = capsys.readouterr().out
        assert "exportada" in saida.lower()

    def test_export_html_com_role(self, capsys):
        """Comando '/export-html assistant' filtra por remetente."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-html assistant", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_html") as mock_export:
            chat_loop()
        _, kwargs = mock_export.call_args
        assert kwargs.get("role_filter") == "assistant"

    def test_export_sem_mensagens(self, capsys):
        """Export sem mensagens exibe aviso em amarelo."""
        from agente_cli import chat_loop
        with patch("builtins.input", side_effect=["/export-md", "sair"]), \
             patch("agente_cli.run_agent_turn"), \
             patch("agente_cli.export_conversation_markdown",
                   return_value="Nao ha mensagens para exportar."):
            chat_loop()
        saida = capsys.readouterr().out
        assert "Nao ha mensagens" in saida


# =====================================================================
# Tests: Mensagem normal (com run_agent_turn mockado)
# =====================================================================

class TestMensagemNormal:
    """Testa o fluxo de envio de mensagem ao agente."""

    def test_mensagem_chama_run_agent_turn(self, capsys):
        """Mensagem normal chama run_agent_turn e exibe resposta."""
        from agente_cli import chat_loop

        # Mock de run_agent_turn para retornar uma conversa simulada
        def mock_run_turn(messages, model, on_step=None):
            messages.append({
                "role": "assistant",
                "content": "Olá! Como posso ajudar?",
            })
            return messages

        with patch("builtins.input", side_effect=["ola", "sair"]), \
             patch("agente_cli.run_agent_turn", side_effect=mock_run_turn):
            chat_loop()

        saida = capsys.readouterr().out
        assert "Olá" in saida
        assert "Agente" in saida

    def test_mensagem_exibe_separador(self, capsys):
        """Resposta do agente e exibida com separadores."""
        from agente_cli import chat_loop

        def mock_run_turn(messages, model, on_step=None):
            messages.append({
                "role": "assistant",
                "content": "Resposta de teste",
            })
            return messages

        with patch("builtins.input", side_effect=["qual a capital do brasil?", "sair"]), \
             patch("agente_cli.run_agent_turn", side_effect=mock_run_turn):
            chat_loop()

        saida = capsys.readouterr().out
        assert "Resposta de teste" in saida

    def test_mensagem_sem_resposta(self, capsys):
        """Mensagem que retorna sem resposta do assistant nao quebra."""
        from agente_cli import chat_loop

        def mock_run_turn(messages, model, on_step=None):
            # Nao adiciona mensagem assistant
            return messages

        with patch("builtins.input", side_effect=["teste", "sair"]), \
             patch("agente_cli.run_agent_turn", side_effect=mock_run_turn):
            chat_loop()

        saida = capsys.readouterr().out
        # Nao deve lancar excecao, apenas continuar e sair
        assert "Até mais" in saida

    def test_run_agent_turn_exception(self, capsys):
        """Excecao em run_agent_turn e capturada e exibida."""
        from agente_cli import chat_loop

        with patch("builtins.input", side_effect=["teste", "sair"]), \
             patch("agente_cli.run_agent_turn", side_effect=Exception("Erro simulado")):
            chat_loop()

        saida = capsys.readouterr().out
        assert "Erro" in saida or "inesperado" in saida

    def test_multiplas_mensagens(self, capsys):
        """Multiplas mensagens em sequencia funcionam."""
        from agente_cli import chat_loop

        respostas = iter(["Primeira resposta", "Segunda resposta"])

        def mock_run_turn(messages, model, on_step=None):
            messages.append({
                "role": "assistant",
                "content": next(respostas),
            })
            return messages

        with patch("builtins.input", side_effect=["msg1", "msg2", "sair"]), \
             patch("agente_cli.run_agent_turn", side_effect=mock_run_turn):
            chat_loop()

        saida = capsys.readouterr().out
        assert "Primeira resposta" in saida
        assert "Segunda resposta" in saida
