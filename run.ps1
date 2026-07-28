# =============================================================================
# run.ps1 — IA Remodelada (Windows)
# Wrapper dos comandos padronizados sem dependência do `make`.
# Uso:  .\run.ps1 <comando>   (ex.: .\run.ps1 test)
# =============================================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Comandos disponíveis:"
    Write-Host "  install      Instala dependências básicas (requirements.txt)"
    Write-Host "  install-dev  Instala dependências de desenvolvimento (testes, lint)"
    Write-Host "  test         Roda todos os testes"
    Write-Host "  test-core    Roda apenas os testes do núcleo"
    Write-Host "  lint         Verifica sintaxe crítica (py_compile)"
    Write-Host "  run-cli      Inicia o agente no terminal"
    Write-Host "  run-gui      Inicia a interface gráfica (Tkinter)"
    Write-Host "  run-api      Inicia o servidor de API (http://localhost:8000)"
    Write-Host "  clean        Remove caches e artefatos de teste"
}

switch ($Command) {
    "help"        { Show-Help }
    "install"     { pip install -r requirements.txt }
    "install-dev" {
        pip install -r requirements.txt
        pip install pytest pytest-timeout pytest-asyncio flake8 bandit
    }
    "test"        { python -m pytest tests/ -q }
    "test-core"   { python -m pytest tests/test_agente_core.py -q }
    "lint"        {
        python -m compileall -q core agente_core.py agente_cli.py agente_gui.py agente_api_server.py agente_turbo.py orquestrador_mestre.py
        Write-Host "Sintaxe OK"
    }
    "run-cli"     { python agente_cli.py }
    "run-gui"     { python agente_gui.py }
    "run-api"     { python agente_api_server.py }
    "clean"       {
        Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force .pytest_cache, htmlcov -ErrorAction SilentlyContinue
        Write-Host "Limpeza concluída."
    }
    default       { Write-Host "Comando desconhecido: $Command"; Show-Help }
}
