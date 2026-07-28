def test_sandbox_rejeita_projeto_fora_do_workspace():
    from plugins.plugin_sandbox import _sanitizar_nome, _projeto_dir, PROJECTS_DIR

    # Testa que nomes com path traversal sao sanitizados
    nome_sujo = "../../etc/passwd"
    nome_limpo = _sanitizar_nome(nome_sujo)
    assert ".." not in nome_limpo, f"Path traversal nao foi removido: {nome_limpo}"
    assert "/" not in nome_limpo, f"Barra nao foi removida: {nome_limpo}"
    assert "\\" not in nome_limpo, f"Barra invertida nao foi removida: {nome_limpo}"

    # Testa que o diretorio do projeto fica dentro de PROJECTS_DIR
    projeto_path = _projeto_dir("teste-seguro")
    assert str(projeto_path).startswith(str(PROJECTS_DIR)), \
        f"Projeto fora de PROJECTS_DIR: {projeto_path}"


def test_avaliacoes_relatorio_vazio_em_diretorio_temporario(tmp_path, monkeypatch):
    import plugins.plugin_avaliacoes_continuas as plugin
    monkeypatch.setattr(plugin, "DATA_FILE", tmp_path / "execucoes.json")
    report = plugin.relatorio_avaliacoes()
    assert report["total"] == 0
    assert report["approval_rate"] == 0.0


def test_fluxo_retorna_tarefa_estruturada(tmp_path, monkeypatch):
    import plugins.plugin_fluxo_autonomo as plugin
    monkeypatch.setattr(plugin, "STATE_FILE", tmp_path / "tarefas.json")
    plugin.iniciar_fluxo("validar dashboard")
    tasks = plugin.listar_tarefas()
    assert tasks[0]["estado"] == "planejado"
    assert tasks[0]["evidencias"] == []
