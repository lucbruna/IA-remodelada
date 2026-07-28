"""
core/backup_util.py
===================
Backup automatico dos dados do agente.

Cria backups incrementais do diretorio agente_data/ com:
  - Rotacao automatica (mantem N ultimos backups)
  - Compressao gzip
  - Checksum para verificacao de integridade
  - Backup agendado via cron ou chamada manual
"""

import os
import json
import gzip
import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path

from ._common import DATA_DIR, _load_json, _save_json, logging

BACKUP_DIR = os.path.join(DATA_DIR, "backups")
BACKUP_INDEX = os.path.join(BACKUP_DIR, "index.json")
MAX_BACKUPS = int(os.environ.get("AGENTE_MAX_BACKUPS", "10"))


def _ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _file_hash(path: str) -> str:
    """SHA256 de um arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def create_backup(name: str = "") -> dict:
    """Cria um backup comprimido do diretorio de dados.

    Args:
        name: Nome opcional do backup (default: timestamp)

    Returns:
        dict com metadados do backup criado
    """
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = name or f"backup_{timestamp}"
    backup_file = os.path.join(BACKUP_DIR, f"{backup_name}.tar.gz")

    # Arquivos para backup (exclui backups anteriores e arquivos temporarios)
    exclude = {"backups", "__pycache__", ".pytest_cache", "uploads"}
    data_path = Path(DATA_DIR)

    try:
        # Cria tar.gz dos dados
        import tarfile
        with tarfile.open(backup_file, "w:gz") as tar:
            for item in data_path.rglob("*"):
                if item.is_file():
                    # Pula diretorio de backups
                    rel = item.relative_to(data_path)
                    if any(part in exclude for part in rel.parts):
                        continue
                    tar.add(item, arcname=str(rel))

        # Metadados
        file_size = os.path.getsize(backup_file)
        checksum = _file_hash(backup_file)

        meta = {
            "name": backup_name,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "file": backup_file,
            "size_bytes": file_size,
            "checksum": checksum,
        }

        # Atualiza indice
        index = _load_json(BACKUP_INDEX, {"backups": []})
        index["backups"].append(meta)

        # Rotacao: mantem apenas MAX_BACKUPS
        if len(index["backups"]) > MAX_BACKUPS:
            removed = index["backups"][:-MAX_BACKUPS]
            index["backups"] = index["backups"][-MAX_BACKUPS:]
            for old in removed:
                old_file = old.get("file", "")
                if os.path.exists(old_file):
                    os.remove(old_file)

        _save_json(BACKUP_INDEX, index)

        logging.info("Backup criado: %s (%.1f KB)", backup_name, file_size / 1024)
        return {
            "status": "ok",
            "name": backup_name,
            "file": backup_file,
            "size_bytes": file_size,
            "checksum": checksum,
        }

    except Exception as e:
        logging.error("Erro ao criar backup: %s", e)
        return {"status": "error", "message": str(e)}


def list_backups() -> list:
    """Lista todos os backups disponiveis."""
    index = _load_json(BACKUP_INDEX, {"backups": []})
    return index.get("backups", [])


def restore_backup(name: str) -> dict:
    """Restaura um backup pelo nome.

    ATENCAO: Sobrescreve os dados atuais!
    """
    index = _load_json(BACKUP_INDEX, {"backups": []})
    backup = None
    for b in index.get("backups", []):
        if b.get("name") == name:
            backup = b
            break

    if not backup:
        return {"status": "error", "message": f"Backup '{name}' nao encontrado"}

    backup_file = backup.get("file", "")
    if not os.path.exists(backup_file):
        return {"status": "error", "message": f"Arquivo de backup nao existe: {backup_file}"}

    # Verifica checksum
    current_hash = _file_hash(backup_file)
    if current_hash != backup.get("checksum"):
        return {"status": "error", "message": "Checksum do backup invalido (arquivo corrompido?)"}

    try:
        import tarfile
        # Restaura para o diretorio de dados
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(path=DATA_DIR)

        logging.info("Backup restaurado: %s", name)
        return {"status": "ok", "name": name, "restored_at": datetime.now().isoformat()}

    except Exception as e:
        logging.error("Erro ao restaurar backup: %s", e)
        return {"status": "error", "message": str(e)}


def delete_backup(name: str) -> dict:
    """Deleta um backup pelo nome."""
    index = _load_json(BACKUP_INDEX, {"backups": []})
    for i, b in enumerate(index.get("backups", [])):
        if b.get("name") == name:
            backup_file = b.get("file", "")
            if os.path.exists(backup_file):
                os.remove(backup_file)
            index["backups"].pop(i)
            _save_json(BACKUP_INDEX, index)
            return {"status": "ok", "name": name}
    return {"status": "error", "message": f"Backup '{name}' nao encontrado"}


def get_backup_stats() -> dict:
    """Retorna estatisticas dos backups."""
    index = _load_json(BACKUP_INDEX, {"backups": []})
    backups = index.get("backups", [])
    total_size = sum(b.get("size_bytes", 0) for b in backups)
    return {
        "total_backups": len(backups),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "max_backups": MAX_BACKUPS,
        "oldest": backups[0]["created_at"] if backups else None,
        "newest": backups[-1]["created_at"] if backups else None,
    }
