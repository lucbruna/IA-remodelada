
from plugins.plugin_validacao_universal import _safe_target, validar_entrega


def test_safe_target_rejeita_fora_do_workspace(tmp_path):
    try:
        _safe_target(str(tmp_path))
    except ValueError:
        return
    raise AssertionError("O validador aceitou alvo fora do workspace")


def test_validar_entrega_compila_arquivo(tmp_path, monkeypatch):
    import plugins.plugin_validacao_universal as plugin

    project = tmp_path / "projeto"
    project.mkdir()
    (project / "app.py").write_text("def somar(a, b):\n    return a + b\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(plugin, "REPORTS_FILE", tmp_path / "dados" / "relatorios.json")

    result = validar_entrega("projeto", executar_testes=False)

    assert "APROVADO" in result
    assert (tmp_path / "dados" / "relatorios.json").exists()
