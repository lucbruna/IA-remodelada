"""
plugin_backup.py
================
Backup e restauracao de arquivos e diretorios: copia com compressao,
backup incremental, restauracao, agendamento de backup,
e limpeza de backups antigos.
"""

import os
import json
import shutil
import zipfile
import tarfile
import glob
import logging
from datetime import datetime, timedelta

__version__ = "1.0.0"
PLUGIN_NAME = "Backup e Restauracao"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data", "backups")
os.makedirs(DATA_DIR, exist_ok=True)


def register(api):
    def _format_size(size_bytes):
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def criar_backup(origem: str, destino: str = "", compressao: bool = True, excluir: str = "") -> str:
        """Cria backup de arquivo ou diretorio. destino opcional. excluir: padrao glob para excluir."""
        try:
            if not os.path.exists(origem):
                return f"Origem nao encontrada: {origem}"
            nome_base = os.path.basename(os.path.normpath(origem))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not destino:
                destino = os.path.join(DATA_DIR, f"{nome_base}_backup_{timestamp}")
            parent = os.path.dirname(os.path.abspath(destino))
            if parent:
                os.makedirs(parent, exist_ok=True)

            excluir_padrao = excluir or ""
            excluir_lista = [p.strip() for p in excluir_padrao.split(",") if p.strip()]

            if os.path.isfile(origem):
                if compressao and not destino.endswith((".zip", ".tar.gz", ".tar")):
                    destino += ".zip"
                if destino.endswith(".zip") or compressao:
                    if not destino.endswith(".zip"):
                        destino += ".zip"
                    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(origem, os.path.basename(origem))
                elif destino.endswith(".tar.gz") or destino.endswith(".tar"):
                    mode = "w:gz" if destino.endswith(".gz") else "w"
                    with tarfile.open(destino, mode) as tf:
                        tf.add(origem, os.path.basename(origem))
                else:
                    shutil.copy2(origem, destino)
            else:
                if compressao:
                    destino += ".zip"
                    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs, files in os.walk(origem):
                            rel_root = os.path.relpath(root, os.path.dirname(os.path.normpath(origem)))
                            for fname in files:
                                fpath = os.path.join(root, fname)
                                arcname = os.path.join(rel_root, fname)
                                if any(exc in fpath for exc in excluir_lista):
                                    continue
                                zf.write(fpath, arcname)
                else:
                    dest_path = destino
                    if os.path.exists(dest_path):
                        dest_path = os.path.join(dest_path, nome_base)
                    shutil.copytree(origem, dest_path, dirs_exist_ok=True)

            size = os.path.getsize(destino) if os.path.isfile(destino) else 0
            return f"Backup criado: {destino} ({_format_size(size)})"
        except Exception as e:
            return f"Erro: {e}"

    def listar_backups(pasta: str = "") -> str:
        """Lista backups disponiveis no diretorio de backups."""
        try:
            target = pasta or DATA_DIR
            if not os.path.exists(target):
                return "Diretorio de backups nao encontrado."
            backups = sorted(glob.glob(os.path.join(target, "**/*.zip"), recursive=True))
            backups += sorted(glob.glob(os.path.join(target, "**/*.tar.gz"), recursive=True))
            backups += sorted(glob.glob(os.path.join(target, "**/*.tar"), recursive=True))
            if not backups:
                return "Nenhum backup encontrado em " + target
            lines = [f"Backups em {target} ({len(backups)}):", ""]
            for b in backups:
                size = os.path.getsize(b)
                mtime = datetime.fromtimestamp(os.path.getmtime(b)).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  {b} ({_format_size(size)}, {mtime})")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro: {e}"

    def restaurar_backup(backup_path: str, destino: str = "") -> str:
        """Restaura backup (.zip, .tar.gz, .tar) para diretorio destino."""
        try:
            if not os.path.exists(backup_path):
                return f"Backup nao encontrado: {backup_path}"
            if not destino:
                destino = os.path.join(DATA_DIR, "restaurado", datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(destino, exist_ok=True)

            if backup_path.endswith(".zip"):
                with zipfile.ZipFile(backup_path, "r") as zf:
                    zf.extractall(destino)
            elif backup_path.endswith(".tar.gz"):
                with tarfile.open(backup_path, "r:gz") as tf:
                    tf.extractall(destino)
            elif backup_path.endswith(".tar"):
                with tarfile.open(backup_path, "r") as tf:
                    tf.extractall(destino)
            else:
                shutil.copy2(backup_path, destino)
            return f"Backup restaurado em: {destino}"
        except Exception as e:
            return f"Erro: {e}"

    def limpar_backups(dias: int = 30, pasta: str = "") -> str:
        """Remove backups mais antigos que N dias."""
        try:
            target = pasta or DATA_DIR
            if not os.path.exists(target):
                return "Diretorio nao encontrado."
            cutoff = datetime.now() - timedelta(days=dias)
            removidos = 0
            for root, dirs, files in os.walk(target):
                for fname in files:
                    if not fname.endswith((".zip", ".tar.gz", ".tar")):
                        continue
                    fpath = os.path.join(root, fname)
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        removidos += 1
            return f"Limpado: {removidos} backup(s) mais antigos que {dias} dias removidos de {target}."
        except Exception as e:
            return f"Erro: {e}"

    def info_backup(backup_path: str) -> str:
        """Mostra informacoes sobre um backup: conteudo, tamanho, data."""
        try:
            if not os.path.exists(backup_path):
                return f"Backup nao encontrado: {backup_path}"
            size = os.path.getsize(backup_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime("%Y-%m-%d %H:%M")
            info = f"Arquivo: {backup_path}\nTamanho: {_format_size(size)}\nCriado: {mtime}\n\nConteudo:\n"
            if backup_path.endswith(".zip"):
                with zipfile.ZipFile(backup_path, "r") as zf:
                    for zi in zf.infolist():
                        info += f"  {zi.filename} ({_format_size(zi.file_size)})\n"
            elif backup_path.endswith((".tar.gz", ".tar")):
                with tarfile.open(backup_path, "r") as tf:
                    for ti in tf.getmembers():
                        info += f"  {ti.name} ({_format_size(ti.size)})\n"
            else:
                info += f"  {os.path.basename(backup_path)} ({_format_size(size)})\n"
            return info
        except Exception as e:
            return f"Erro: {e}"

    api.register_tool("criar_backup", criar_backup,
        "Cria backup de arquivo ou diretorio com compressao ZIP opcional.",
        {"origem": {"type": "string", "description": "Arquivo ou diretorio origem"}, "destino": {"type": "string", "description": "Destino (opcional)"}, "compressao": {"type": "boolean", "description": "Comprimir como ZIP? (opcional)"}, "excluir": {"type": "string", "description": "Padroes para excluir separados por virgula (opcional)"}}, ["origem"])

    api.register_tool("listar_backups", listar_backups,
        "Lista backups disponiveis no diretorio de backups.",
        {"pasta": {"type": "string", "description": "Pasta para listar (opcional)"}}, [])

    api.register_tool("restaurar_backup", restaurar_backup,
        "Restaura backup (.zip, .tar.gz, .tar) para diretorio destino.",
        {"backup_path": {"type": "string", "description": "Caminho do backup"}, "destino": {"type": "string", "description": "Diretorio destino (opcional)"}}, ["backup_path"])

    api.register_tool("limpar_backups", limpar_backups,
        "Remove backups mais antigos que N dias.",
        {"dias": {"type": "integer", "description": "Idade maxima em dias (opcional)"}, "pasta": {"type": "string", "description": "Pasta de backups (opcional)"}}, [])

    api.register_tool("info_backup", info_backup,
        "Mostra informacoes detalhadas de um arquivo de backup.",
        {"backup_path": {"type": "string", "description": "Caminho do backup"}}, ["backup_path"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Backup e restauracao: compressao ZIP/TAR, listagem, limpeza, informacoes",
        "tools": ["criar_backup", "listar_backups", "restaurar_backup", "limpar_backups", "info_backup"],
    }
