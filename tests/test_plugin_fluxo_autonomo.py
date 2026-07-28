def _configured_plugin(tmp_path, monkeypatch):
    import plugins.plugin_fluxo_autonomo as plugin
    monkeypatch.setattr(plugin, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(plugin, "STATE_FILE", tmp_path / "dados" / "tarefas.json")
    return plugin


def test_fluxo_respeita_transicoes(tmp_path, monkeypatch):
    plugin = _configured_plugin(tmp_path, monkeypatch)
    started = plugin.iniciar_fluxo("Criar calculadora")
    task_id = started.split(": ", 1)[1].splitlines()[0]

    assert "planejado -> executando" in plugin.atualizar_fluxo(task_id, "executando")
    assert "executando -> validando" in plugin.atualizar_fluxo(task_id, "validando")
    assert "Transicao nao permitida" in plugin.atualizar_fluxo(task_id, "executando")


def test_fluxo_registra_evidencia(tmp_path, monkeypatch):
    plugin = _configured_plugin(tmp_path, monkeypatch)
    task_id = plugin.iniciar_fluxo("Validar API").split(": ", 1)[1].splitlines()[0]
    assert "Evidencia registrada" in plugin.registrar_evidencia(task_id, "pytest", "3 passed", True)
    assert "Evidencias: 1" in plugin.status_fluxo(task_id)
