def test_memoria_de_projeto_e_contrato(tmp_path, monkeypatch):
    import plugins.plugin_operacao_profissional as plugin
    (tmp_path / "app.py").write_text("def calcular_total(valor):\n    return valor * 2\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(plugin, "DATA_DIR", tmp_path / "dados")
    assert "1 arquivos" in plugin.indexar_memoria_projeto()
    assert "app.py" in plugin.buscar_memoria_projeto("calcular total")
    assert plugin.validar_contrato_delegacao('{"resultado": "ok"}').startswith("Contrato incompleto")
    assert plugin.validar_contrato_delegacao('{"resultado":"ok","arquivos_alterados":[],"testes_executados":[],"riscos":[]}') == "Contrato aprovado."
