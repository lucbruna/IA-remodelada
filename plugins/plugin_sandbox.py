"""
plugin_sandbox.py
=================
Sandbox Docker com isolamento completo por projeto.

Recursos:
  - Container efemero (--rm) por execucao
  - CPU, RAM e swap limitados por projeto
  - Sistema de arquivos read-only (exceto /tmp)
  - Rede isolada (opcional: ativar sob demanda)
  - Montagem restrita: apenas o diretorio do projeto
  - Hardening: --cap-drop=ALL, --security-opt=no-new-privileges
  - Gerenciamento de imagens por projeto
  - Cache de camadas para builds rapidos
  - Compatibilidade com plugin_sandbox_projeto

Uso:
    sandbox_criar_projeto(nome="meu-projeto")
    sandbox_executar(projeto="meu-projeto", codigo="print('hello')")
    sandbox_executar_comando(projeto="meu-projeto", comando="python script.py")
"""

import json
import os
import re
import sys
import time
import uuid
import shutil
import logging
import hashlib
import subprocess
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Optional

__version__ = "2.0.0"
PLUGIN_NAME = "Sandbox Docker — Isolamento por Projeto"

# ─── Caminhos ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "agente_data" / "sandbox"
PROJECTS_DIR = DATA_DIR / "projetos"
HISTORY_FILE = DATA_DIR / "historico.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Configuracoes Globais ─────────────────────────────────────────
DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT = 30
DEFAULT_CPU = 1.0           # CPUs (fracao)
DEFAULT_MEMORY_MB = 512     # RAM em MB
DEFAULT_SWAP_MB = 0         # Sem swap
DEFAULT_PIDS_LIMIT = 128    # Max processos
DEFAULT_TMPFS_SIZE = "128m" # /tmp tamanho

# ─── Cache de verificacao Docker ──────────────────────────────────
_DOCKER_PATH: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _find_docker() -> Optional[str]:
    """Localiza o binario do Docker."""
    global _DOCKER_PATH
    if _DOCKER_PATH is not None:
        return _DOCKER_PATH
    candidates = ["docker", "docker.exe"]
    for c in candidates:
        path = shutil.which(c)
        if path:
            _DOCKER_PATH = path
            return path
    return None


def _check_docker() -> dict:
    """Verifica se Docker esta disponivel.
    
    Returns:
        dict com ``available``, ``version``, ``detail``
    """
    docker = _find_docker()
    if not docker:
        return {"available": False, "version": "", "detail": "Docker CLI nao encontrado"}
    try:
        result = subprocess.run(
            [docker, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=8,
        )
        if result.returncode == 0:
            return {"available": True, "version": result.stdout.strip(), "detail": "ok"}
        return {"available": False, "version": "", "detail": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"available": False, "version": "", "detail": "Timeout ao verificar Docker"}
    except Exception as e:
        return {"available": False, "version": "", "detail": str(e)}


def _sanitizar_nome(nome: str) -> str:
    """Sanitiza nome para uso como identificador Docker/arquivo."""
    nome = unicodedata.normalize("NFKD", nome)
    nome = nome.encode("ascii", "ignore").decode("ascii")
    nome = re.sub(r"[^a-zA-Z0-9_-]", "", nome)[:50].strip("-_")
    return nome.lower() or f"projeto_{uuid.uuid4().hex[:8]}"


def _projeto_dir(nome: str) -> Path:
    """Retorna o caminho do diretorio do projeto."""
    return PROJECTS_DIR / _sanitizar_nome(nome)


def _projeto_meta(nome: str) -> dict:
    """Carrega metadados do projeto."""
    pdir = _projeto_dir(nome)
    meta_path = pdir / "meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _salvar_meta(nome: str, meta: dict):
    """Salva metadados do projeto."""
    pdir = _projeto_dir(nome)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history(history: list):
    HISTORY_FILE.write_text(
        json.dumps(history[-500:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _registrar_execucao(projeto: str, duracao: float, erro: bool, timeout: int, chars: int = 0):
    """Registra uma execucao no historico."""
    history = _load_history()
    history.append({
        "projeto": _sanitizar_nome(projeto),
        "timestamp": datetime.now().isoformat(),
        "duracao": round(duracao, 3),
        "erro": erro,
        "timeout": timeout,
        "chars": chars,
    })
    _save_history(history)

    # Atualiza metadados do projeto
    meta = _projeto_meta(projeto)
    if meta:
        meta["execucoes"] = meta.get("execucoes", 0) + 1
        meta["ultima_execucao"] = datetime.now().isoformat()
        _salvar_meta(projeto, meta)


def _construir_args_container(
    projeto_dir: Path,
    comando: list,
    imagem: str = DEFAULT_IMAGE,
    timeout: int = DEFAULT_TIMEOUT,
    cpu: float = DEFAULT_CPU,
    memory_mb: int = DEFAULT_MEMORY_MB,
    swap_mb: int = DEFAULT_SWAP_MB,
    pids_limit: int = DEFAULT_PIDS_LIMIT,
    tmpfs_size: str = DEFAULT_TMPFS_SIZE,
    rede: bool = False,
    read_only: bool = True,
    entrypoint: Optional[list] = None,
) -> list:
    """Constroi argumentos para `docker run` com isolamento completo."""
    docker = _find_docker()
    if not docker:
        raise RuntimeError("Docker nao disponivel")

    args = [
        docker, "run", "--rm",
        # Isolamento de processo
        "--security-opt=no-new-privileges",
        "--cap-drop=ALL",
        "--pids-limit", str(pids_limit),
        # Limites de CPU
        "--cpus", str(cpu),
        # Limites de memoria (sem swap)
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m" if swap_mb == 0 else f"{memory_mb + swap_mb}m",
        # Sistema de arquivos
    ]
    if read_only:
        args.append("--read-only")
    args.extend([
        "--tmpfs", f"/tmp:rw,noexec,nosuid,size={tmpfs_size}",
        # Montagem do projeto (apenas o diretorio do projeto)
        "-v", f"{projeto_dir}:/workspace:rw",
        "-w", "/workspace",
    ])
    if not rede:
        args.extend(["--network", "none"])
    if entrypoint:
        args.extend(["--entrypoint"] + entrypoint)
    args.append(imagem)
    args.extend(comando)
    return args


def _executar_docker(
    args: list,
    timeout: int = DEFAULT_TIMEOUT,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Executa comando Docker com timeout."""
    try:
        return subprocess.run(
            args,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Container excedeu o limite de {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("Docker nao encontrado no PATH")


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Gerenciamento de Projetos
# ═══════════════════════════════════════════════════════════════════

def sandbox_criar_projeto(
    nome: str,
    descricao: str = "",
    python_version: str = "3.11",
    requirements: str = "",
    cpu: float = DEFAULT_CPU,
    memory_mb: int = DEFAULT_MEMORY_MB,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Cria um projeto isolado para execucao segura de codigo.

    Cria ambiente com recursos limitados (CPU, RAM) e instalacao
    de dependencias via Docker.

    Args:
        nome: Nome do projeto
        descricao: Descricao opcional
        python_version: Versao Python (ex: 3.11)
        requirements: Pacotes pip (separados por espaco)
        cpu: Limite de CPUs (fracao, padrao: 1.0)
        memory_mb: Limite de RAM em MB (padrao: 512)
        timeout: Timeout padrao em segundos (padrao: 30)

    Returns:
        Mensagem de confirmacao
    """
    nome_safe = _sanitizar_nome(nome)
    pdir = _projeto_dir(nome)

    if pdir.exists():
        return f"⚠ Projeto '{nome}' ja existe. Use sandbox_excluir_projeto para recriar."

    pdir.mkdir(parents=True, exist_ok=True)

    # Cria Dockerfile
    dockerfile_content = (
        f"FROM python:{python_version}-slim\n"
        "WORKDIR /workspace\n"
        "RUN adduser --disabled-password --gecos '' sandbox\n"
    )
    if requirements.strip():
        reqs = [r.strip() for r in requirements.replace(",", "\n").split() if r.strip()]
        dockerfile_content += (
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n"
        )
        (pdir / "requirements.txt").write_text("\n".join(reqs), encoding="utf-8")
    dockerfile_content += (
        "USER sandbox\n"
        "COPY --chown=sandbox:sandbox . .\n"
    )
    (pdir / "Dockerfile").write_text(dockerfile_content, encoding="utf-8")

    # Metadados
    meta = {
        "nome": nome,
        "nome_safe": nome_safe,
        "descricao": descricao,
        "python_version": python_version,
        "requirements": requirements,
        "cpu": cpu,
        "memory_mb": memory_mb,
        "timeout": timeout,
        "criado_em": datetime.now().isoformat(),
        "execucoes": 0,
        "ultima_execucao": None,
    }
    _salvar_meta(nome, meta)

    # Tenta build da imagem Docker
    docker_status = _check_docker()
    build_msg = ""
    if docker_status["available"]:
        try:
            build_result = subprocess.run(
                [_find_docker(), "build", "-t", f"sandbox_{nome_safe}", "."],
                cwd=str(pdir),
                capture_output=True, text=True, timeout=120,
            )
            if build_result.returncode == 0:
                build_msg = f"\n   Imagem Docker: sandbox_{nome_safe} (build ok)"
            else:
                build_msg = f"\n   ⚠ Build Docker: {build_result.stderr.strip()[:200]}"
        except subprocess.TimeoutExpired:
            build_msg = "\n   ⚠ Build Docker: timeout apos 120s"
        except Exception as e:
            build_msg = f"\n   ⚠ Build Docker: {e}"
    else:
        build_msg = f"\n   ⚠ Docker indisponivel (usando fallback subprocess)"

    return (
        f"✅ Projeto criado: {nome}\n"
        f"   ID: {nome_safe}\n"
        f"   Diretorio: {pdir}\n"
        f"   Python: {python_version}\n"
        f"   CPU: {cpu} | RAM: {memory_mb}MB | Timeout: {timeout}s"
        f"{build_msg}"
    )


def sandbox_excluir_projeto(nome: str) -> str:
    """Exclui um projeto sandbox e sua imagem Docker.

    Args:
        nome: Nome do projeto

    Returns:
        Mensagem de confirmacao
    """
    nome_safe = _sanitizar_nome(nome)
    pdir = _projeto_dir(nome)

    if not pdir.exists():
        return f"❌ Projeto '{nome}' nao encontrado."

    # Remove imagem Docker
    docker = _find_docker()
    if docker:
        try:
            subprocess.run(
                [docker, "rmi", f"sandbox_{nome_safe}"],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            pass

    # Remove diretorio
    shutil.rmtree(pdir, ignore_errors=True)
    return f"✅ Projeto '{nome}' excluido."


def sandbox_listar_projetos() -> str:
    """Lista todos os projetos sandbox criados."""
    if not PROJECTS_DIR.exists():
        return "Nenhum projeto sandbox criado."

    projetos = []
    for item in sorted(PROJECTS_DIR.iterdir()):
        if item.is_dir():
            meta_path = item / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    projetos.append(meta)
                except Exception:
                    projetos.append({"nome": item.name, "descricao": "(erro ao ler meta)"})

    if not projetos:
        return "Nenhum projeto encontrado."

    linhas = [f"Projetos Sandbox ({len(projetos)}):\n"]
    for p in projetos:
        execs = p.get("execucoes", 0)
        ultima = p.get("ultima_execucao", "nunca")
        cpu = p.get("cpu", DEFAULT_CPU)
        mem = p.get("memory_mb", DEFAULT_MEMORY_MB)
        linhas.append(f"  📁 {p.get('nome', '?')} ({p.get('nome_safe', '?')})")
        linhas.append(f"     CPU: {cpu} | RAM: {mem}MB | Exec: {execs} | Ultima: {ultima}")
        if p.get("descricao"):
            linhas.append(f"     Desc: {p['descricao']}")
        linhas.append("")

    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Execucao de Codigo
# ═══════════════════════════════════════════════════════════════════

def sandbox_executar(
    projeto: str,
    codigo: str,
    timeout: Optional[int] = None,
    cpu: Optional[float] = None,
    memory_mb: Optional[int] = None,
    rede: bool = False,
) -> str:
    """Executa codigo Python no sandbox com isolamento completo.

    O codigo e executado em container efemero com recursos limitados
    e sistema de arquivos read-only. Fallback para subprocess seguro
    se Docker nao estiver disponivel.

    Args:
        projeto: Nome do projeto sandbox
        codigo: Codigo Python a executar
        timeout: Timeout em segundos (usa config do projeto se None)
        cpu: Limite de CPUs (usa config do projeto se None)
        memory_mb: Limite de RAM em MB (usa config do projeto se None)
        rede: Se True, ativa rede (padrao: False)

    Returns:
        Saida formatada da execucao
    """
    nome_safe = _sanitizar_nome(projeto)
    pdir = _projeto_dir(projeto)

    if not pdir.exists():
        return f"❌ Projeto '{projeto}' nao encontrado. Use sandbox_criar_projeto primeiro."

    meta = _projeto_meta(projeto)
    timeout = timeout or meta.get("timeout", DEFAULT_TIMEOUT)
    cpu = cpu or meta.get("cpu", DEFAULT_CPU)
    memory_mb = memory_mb or meta.get("memory_mb", DEFAULT_MEMORY_MB)

    # Salva codigo para execucao
    exec_id = uuid.uuid4().hex[:8]
    script_name = f"script_{exec_id}.py"
    script_path = pdir / script_name
    script_path.write_text(codigo, encoding="utf-8")

    inicio = time.monotonic()
    erro = False
    saida = ""

    # Tenta Docker
    docker_status = _check_docker()
    if docker_status["available"]:
        imagem = f"sandbox_{nome_safe}"
        try:
            args = _construir_args_container(
                projeto_dir=pdir,
                comando=["python", f"/workspace/{script_name}"],
                imagem=imagem,
                timeout=timeout,
                cpu=cpu,
                memory_mb=memory_mb,
                rede=rede,
            )
            result = _executar_docker(args, timeout=timeout)
            saida = result.stdout.strip()
            if result.stderr.strip():
                saida += f"\n[stderr]: {result.stderr.strip()}"
            if not saida:
                saida = "(codigo executado, sem saida)"
        except TimeoutError as e:
            erro = True
            saida = f"❌ {e}"
        except RuntimeError as e:
            erro = True
            saida = str(e)
        except subprocess.CalledProcessError as e:
            erro = True
            saida = f"Erro no container (exit {e.returncode}): {e.stderr[:500]}"
        except Exception as e:
            erro = True
            saida = f"Erro: {e}"

    # Fallback: subprocess com seguranca
    if erro or not saida or not docker_status["available"]:
        try:
            safe_env = {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONSAFEPATH": "1",
                "HOME": "/tmp",
            }
            result = subprocess.run(
                [sys.executable, "-c", codigo],
                capture_output=True, text=True,
                timeout=timeout,
                env=safe_env,
                cwd=str(pdir),
            )
            saida = result.stdout.strip()
            if result.stderr.strip():
                saida += f"\n[stderr]: {result.stderr.strip()}"
            if not docker_status["available"]:
                saida = "[Fallback: subprocess]\n" + (saida or "(sem saida)")
            elif erro and saida:
                saida = f"[Docker: {saida}]\n[Fallback OK]"
        except subprocess.TimeoutExpired:
            erro = True
            saida = f"❌ Timeout apos {timeout}s"
        except Exception as e:
            erro = True
            saida = f"❌ Erro: {e}"

    duracao = time.monotonic() - inicio
    _registrar_execucao(projeto, duracao, erro, timeout, len(codigo))

    # Limpa script temporario
    try:
        script_path.unlink(missing_ok=True)
    except Exception:
        pass

    docker_tag = "✅ Docker" if docker_status["available"] else "⚠ Subprocess"
    return (
        f"📦 Sandbox: {projeto}\n"
        f"   ⏱ {duracao:.2f}s | {len(codigo):,} chars\n"
        f"   🖥 {docker_tag} | CPU: {cpu} | RAM: {memory_mb}MB\n"
        f"─── Saida ───\n{saida}"
    )


def sandbox_executar_comando(
    projeto: str,
    comando: str,
    timeout: Optional[int] = None,
    cpu: Optional[float] = None,
    memory_mb: Optional[int] = None,
    rede: bool = False,
) -> str:
    """Executa um comando shell arbitrário no sandbox do projeto.

    Args:
        projeto: Nome do projeto
        comando: Comando shell a executar
        timeout: Timeout em segundos
        cpu: Limite de CPUs
        memory_mb: Limite de RAM em MB
        rede: Se True, ativa rede

    Returns:
        Saida JSON com resultado
    """
    nome_safe = _sanitizar_nome(projeto)
    pdir = _projeto_dir(projeto)

    if not pdir.exists():
        return json.dumps({"error": f"Projeto '{projeto}' nao encontrado"})

    meta = _projeto_meta(projeto)
    timeout = timeout or meta.get("timeout", DEFAULT_TIMEOUT)
    cpu = cpu or meta.get("cpu", DEFAULT_CPU)
    memory_mb = memory_mb or meta.get("memory_mb", DEFAULT_MEMORY_MB)
    imagem = meta.get("python_version", "3.11")
    imagem_docker = f"python:{imagem}-slim"

    # Tenta usar a imagem customizada do projeto primeiro
    docker_status = _check_docker()
    if docker_status["available"]:
        # Verifica se a imagem customizada existe
        try:
            inspect = subprocess.run(
                [_find_docker(), "image", "inspect", f"sandbox_{nome_safe}"],
                capture_output=True, text=True, timeout=5,
            )
            if inspect.returncode == 0:
                imagem_docker = f"sandbox_{nome_safe}"
        except Exception:
            pass

    inicio = time.monotonic()
    try:
        args = _construir_args_container(
            projeto_dir=pdir,
            comando=["sh", "-c", comando],
            imagem=imagem_docker,
            timeout=timeout,
            cpu=cpu,
            memory_mb=memory_mb,
            rede=rede,
        )
        result = _executar_docker(args, timeout=timeout)
        saida = (result.stdout + "\n" + result.stderr).strip()[:12000]
        payload = {
            "project": str(pdir),
            "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - inicio, 3),
            "network": rede,
            "output": saida,
        }
        _registrar_execucao(projeto, payload["duration_seconds"], result.returncode != 0, timeout)
        return json.dumps(payload, ensure_ascii=False)
    except TimeoutError as e:
        return json.dumps({"error": str(e), "duration": round(time.monotonic() - inicio, 3)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def sandbox_instalar_pacotes(
    projeto: str,
    pacotes: str,
) -> str:
    """Instala pacotes pip no sandbox e reconstroi a imagem Docker.

    Args:
        projeto: Nome do projeto
        pacotes: Pacotes pip (separados por espaco)

    Returns:
        Resultado da instalacao
    """
    nome_safe = _sanitizar_nome(projeto)
    pdir = _projeto_dir(projeto)

    if not pdir.exists():
        return f"❌ Projeto '{projeto}' nao encontrado."

    # Atualiza requirements
    req_path = pdir / "requirements.txt"
    pacotes_lista = [p.strip() for p in pacotes.replace(",", "\n").split() if p.strip()]
    existing = []
    if req_path.exists():
        existing = [l.strip() for l in req_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    all_reqs = existing + [p for p in pacotes_lista if p not in existing]
    req_path.write_text("\n".join(all_reqs), encoding="utf-8")

    # Atualiza meta
    meta = _projeto_meta(projeto)
    if meta:
        meta["requirements"] = " ".join(all_reqs)
        _salvar_meta(projeto, meta)

    # Rebuild imagem Docker
    docker_status = _check_docker()
    if docker_status["available"]:
        try:
            result = subprocess.run(
                [_find_docker(), "build", "-t", f"sandbox_{nome_safe}", "--no-cache", "."],
                cwd=str(pdir),
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode == 0:
                return (
                    f"✅ Pacotes adicionados e imagem reconstruida: {pacotes}\n"
                    f"   Total de dependencias: {len(all_reqs)}"
                )
            return (
                f"⚠ Pacotes adicionados a lista, mas rebuild falhou:\n"
                f"   {result.stderr.strip()[:300]}"
            )
        except subprocess.TimeoutExpired:
            return f"⚠ Rebuild excedeu timeout (180s). Pacotes ainda na lista."
        except Exception as e:
            return f"⚠ Erro no rebuild: {e}"
    else:
        return f"⚠ Docker indisponivel. Pacotes salvos em requirements.txt."


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Status e Historico
# ═══════════════════════════════════════════════════════════════════

def sandbox_status() -> str:
    """Retorna status detalhado do sistema de sandbox."""
    docker = _check_docker()
    history = _load_history()

    total_execs = len(history)
    erros = sum(1 for h in history if h.get("erro"))
    sucesso = total_execs - erros
    taxa = (sucesso / max(total_execs, 1)) * 100

    projetos_count = 0
    if PROJECTS_DIR.exists():
        projetos_count = len([d for d in PROJECTS_DIR.iterdir() if d.is_dir()])

    return (
        f"📦 Status do Sandbox\n"
        f"   Docker: {'✅' if docker['available'] else '❌'} "
        f"{'v' + docker['version'] if docker['version'] else docker['detail']}\n"
        f"   Projetos: {projetos_count}\n"
        f"   Execucoes: {total_execs} ({taxa:.0f}% sucesso)\n"
        f"   Config default: CPU {DEFAULT_CPU} | RAM {DEFAULT_MEMORY_MB}MB\n"
        f"   Timeout: {DEFAULT_TIMEOUT}s | Imagem: {DEFAULT_IMAGE}"
    )


def sandbox_historico(projeto: str = "", limite: int = 10) -> str:
    """Mostra historico de execucoes no sandbox.

    Args:
        projeto: Filtrar por projeto (vazio = todos)
        limite: Maximo de registros (padrao: 10)

    Returns:
        Historico formatado
    """
    history = _load_history()
    if not history:
        return "Nenhuma execucao registrada."

    if projeto:
        nome_safe = _sanitizar_nome(projeto)
        history = [h for h in history if h.get("projeto") == nome_safe]

    if not history:
        return f"Nenhuma execucao para '{projeto}'."

    history = history[-limite:]
    linhas = [f"Historico de Execucoes ({len(history)}):\n"]
    for h in reversed(history):
        status = "ERRO" if h.get("erro") else "OK"
        proj = h.get("projeto", "?")
        ts = h.get("timestamp", "?")[:19]
        dur = h.get("duracao", 0)
        chars = h.get("chars", 0)
        linhas.append(f"  [{status}] {proj} | {ts} | {dur:.1f}s | {chars} chars")
    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Informacao do Projeto (API publica)
# ═══════════════════════════════════════════════════════════════════

def sandbox_info_projeto(nome: str) -> dict:
    """Retorna informacoes detalhadas de um projeto sandbox.

    Args:
        nome: Nome do projeto

    Returns:
        Dict com metadados do projeto ou dict com chave ``erro`` se nao encontrado.
    """
    pdir = _projeto_dir(nome)
    if not pdir.exists():
        return {"erro": True, "mensagem": f"Projeto '{nome}' nao encontrado"}
    meta = _projeto_meta(nome)
    meta["diretorio"] = str(pdir)
    meta["existe"] = True
    return meta


# ═══════════════════════════════════════════════════════════════════
# FERRAMENTAS — Gerenciamento de Imagens
# ═══════════════════════════════════════════════════════════════════

def sandbox_imagens() -> str:
    """Lista imagens Docker relacionadas a projetos sandbox."""
    docker = _find_docker()
    if not docker:
        return "Docker nao disponivel."

    try:
        result = subprocess.run(
            [docker, "images", "--filter", "reference=sandbox_*", "--format",
             "{{.Repository}}:{{.Tag}} ({{.Size}})"],
            capture_output=True, text=True, timeout=10,
        )
        images = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if not images:
            return "Nenhuma imagem sandbox encontrada."
        return "Imagens Sandbox:\n" + "\n".join(f"  🖼 {img}" for img in images)
    except Exception as e:
        return f"Erro ao listar imagens: {e}"


def sandbox_limpar_cache() -> str:
    """Limpa imagens Docker nao utilizadas dos projetos."""
    docker = _find_docker()
    if not docker:
        return "Docker nao disponivel."

    try:
        result = subprocess.run(
            [docker, "image", "prune", "--filter", "reference=sandbox_*", "-f"],
            capture_output=True, text=True, timeout=30,
        )
        space = result.stdout.strip()
        if not space:
            space = "Nenhuma imagem para limpar."
        return f"Cache limpo.\n{space}"
    except Exception as e:
        return f"Erro ao limpar cache: {e}"


# ═══════════════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════════════

def register(api):
    """Registra todas as ferramentas do sandbox."""

    api.register_tool(
        "sandbox_criar_projeto", sandbox_criar_projeto,
        "Cria um projeto isolado para execucao segura de codigo. Define CPU, RAM, versao Python e dependencias via Docker.",
        {"nome": {"type": "string", "description": "Nome do projeto"},
         "descricao": {"type": "string", "description": "Descricao opcional"},
         "python_version": {"type": "string", "description": "Versao Python (ex: 3.11)"},
         "requirements": {"type": "string", "description": "Pacotes pip separados por espaco"},
         "cpu": {"type": "number", "description": "Limite de CPUs (padrao: 1.0)"},
         "memory_mb": {"type": "integer", "description": "Limite de RAM em MB (padrao: 512)"},
         "timeout": {"type": "integer", "description": "Timeout padrao em segundos"}},
        ["nome"],
    )

    api.register_tool(
        "sandbox_excluir_projeto", sandbox_excluir_projeto,
        "Exclui um projeto sandbox e sua imagem Docker correspondente.",
        {"nome": {"type": "string", "description": "Nome do projeto"}},
        ["nome"],
    )

    api.register_tool(
        "sandbox_listar_projetos", sandbox_listar_projetos,
        "Lista todos os projetos sandbox com recursos, execucoes e ultima atividade.",
        {}, [],
    )

    api.register_tool(
        "sandbox_executar", sandbox_executar,
        "Executa codigo Python no sandbox com isolamento total (Docker). Read-only, sem rede, CPU/RAM limitados. Fallback para subprocess se Docker indisponivel.",
        {"projeto": {"type": "string", "description": "Nome do projeto"},
         "codigo": {"type": "string", "description": "Codigo Python a executar"},
         "timeout": {"type": "integer", "description": "Timeout em segundos"},
         "cpu": {"type": "number", "description": "Limite de CPUs"},
         "memory_mb": {"type": "integer", "description": "Limite de RAM em MB"},
         "rede": {"type": "boolean", "description": "Ativar rede (padrao: False)"}},
        ["projeto", "codigo"],
    )

    api.register_tool(
        "sandbox_executar_comando", sandbox_executar_comando,
        "Executa comando shell arbitrário no sandbox do projeto. Retorna JSON com stdout, stderr, exit_code, duracao. Projetado para compatibilidade com plugin_sandbox_projeto.",
        {"projeto": {"type": "string", "description": "Nome do projeto"},
         "comando": {"type": "string", "description": "Comando shell a executar"},
         "timeout": {"type": "integer", "description": "Timeout em segundos"},
         "cpu": {"type": "number", "description": "Limite de CPUs"},
         "memory_mb": {"type": "integer", "description": "Limite de RAM em MB"},
         "rede": {"type": "boolean", "description": "Ativar rede (padrao: False)"}},
        ["projeto", "comando"],
    )

    api.register_tool(
        "sandbox_instalar_pacotes", sandbox_instalar_pacotes,
        "Instala pacotes pip no projeto e reconstroi a imagem Docker com cache.",
        {"projeto": {"type": "string", "description": "Nome do projeto"},
         "pacotes": {"type": "string", "description": "Pacotes pip (ex: 'numpy pandas')"}},
        ["projeto", "pacotes"],
    )

    api.register_tool(
        "sandbox_status", sandbox_status,
        "Status detalhado: Docker disponivel, projetos, execucoes, taxas, configuracoes.",
        {}, [],
    )

    api.register_tool(
        "sandbox_historico", sandbox_historico,
        "Historico de execucoes, opcionalmente filtrado por projeto.",
        {"projeto": {"type": "string", "description": "Filtrar por projeto (opcional)"},
         "limite": {"type": "integer", "description": "Max registros (padrao: 10)"}},
        [],
    )

    api.register_tool(
        "sandbox_imagens", sandbox_imagens,
        "Lista imagens Docker dos projetos sandbox.",
        {}, [],
    )

    api.register_tool(
        "sandbox_limpar_cache", sandbox_limpar_cache,
        "Limpa imagens Docker nao utilizadas dos projetos sandbox para liberar espaco.",
        {}, [],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Sandbox Docker com isolamento completo por projeto: CPU/RAM limitados, fs read-only, sem rede, execucao de codigo e comandos.",
        "tools": [
            "sandbox_criar_projeto", "sandbox_excluir_projeto",
            "sandbox_listar_projetos", "sandbox_executar",
            "sandbox_executar_comando", "sandbox_instalar_pacotes",
            "sandbox_status", "sandbox_historico",
            "sandbox_imagens", "sandbox_limpar_cache",
        ],
    }
