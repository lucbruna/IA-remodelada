def test_aprovacao_tem_escopo_e_validade(tmp_path, monkeypatch):
    import plugins.plugin_governanca_execucao as plugin
    monkeypatch.setattr(plugin, "APPROVALS_FILE", tmp_path / "aprovacoes.json")
    created = plugin.solicitar_aprovacao("run_command", "rodar testes")
    approval_id = created.split(": ", 1)[1].splitlines()[0]
    assert plugin.verificar_aprovacao(approval_id, "run_command").startswith("negada")
    assert "registrada" in plugin.aprovar_acao(approval_id)
    assert plugin.verificar_aprovacao(approval_id, "run_command") == "aprovada"
    assert plugin.verificar_aprovacao(approval_id, "delete_path").startswith("negada")
