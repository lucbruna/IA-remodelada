from ._common import *
import shutil

# =======================================================================
# RESOLVE - acoes em rascunho (padrao 'resolve' do oh-my-pi)
# -----------------------------------------------------------------------
# Acoes potencialmente destrutivas (apagar, mover, sobrescrever) sao
# ENFILEIRADAS como preview em vez de executadas na hora. O usuario (ou o
# proprio modelo, via resolve_apply) confirma antes de aplicar. Se nao
# confirmar, descarta com resolve_discard. Evita perda acidental de dados.
# =======================================================================

RESOLVE_FILE = os.path.join(DATA_DIR, "agente_data", "memoria_evolutiva", "resolve_queue.json")

# Acoes suportadas: cada uma recebe args e sabe se aplicar e como desfazer.
_RESOLVE_ACTIONS = {}


def _register_action(name, apply_fn, describe_fn):
    _RESOLVE_ACTIONS[name] = {"apply": apply_fn, "describe": describe_fn}


def _load_queue() -> list:
    return _load_json(RESOLVE_FILE, [])


def _save_queue(q: list) -> None:
    os.makedirs(os.path.dirname(RESOLVE_FILE), exist_ok=True)
    _save_json(RESOLVE_FILE, q)


def resolve_enqueue(action: str, args: dict, reason: str = "") -> str:
    """Enfileira uma acao destrutiva em modo preview (nao executa ainda).

    Acoes disponiveis: delete_path, move_file, copy_overwrite.
    O modelo deve chamar resolve_apply(id) para confirmar ou
    resolve_discard(id) para cancelar.
    """
    action = (action or "").strip()
    if action not in _RESOLVE_ACTIONS:
        return (f"Acao '{action}' nao suportada pelo resolve. "
                f"Suportadas: {', '.join(_RESOLVE_ACTIONS)}")
    args = args or {}
    q = _load_queue()
    item_id = "r" + datetime.now().strftime("%Y%m%d%H%M%S") + str(len(q))
    entry = {
        "id": item_id,
        "action": action,
        "args": args,
        "reason": reason,
        "ts": datetime.now().isoformat(),
        "status": "pending",
    }
    q.append(entry)
    _save_queue(q)
    desc = _RESOLVE_ACTIONS[action]["describe"](args)
    return (f"[PREVIEW] Acao enfileirada (id={item_id}): {desc}\n"
            f"Confirme com resolve_apply('{item_id}') ou cancele com "
            f"resolve_discard('{item_id}').")


def resolve_apply(item_id: str) -> str:
    """Aplica (executa de verdade) uma acao previamente enfileirada."""
    q = _load_queue()
    for item in q:
        if item["id"] == item_id and item["status"] == "pending":
            try:
                result = _RESOLVE_ACTIONS[item["action"]]["apply"](item["args"])
            except Exception as e:
                item["status"] = "failed"
                _save_queue(q)
                return f"Falha ao aplicar {item_id}: {e}"
            item["status"] = "applied"
            _save_queue(q)
            return f"[APPLIED] {item_id}: {result}"
    return f"Nenhuma acao pendente com id '{item_id}'."


def resolve_discard(item_id: str) -> str:
    """Cancela (descarta) uma acao enfileirada, sem executar."""
    q = _load_queue()
    for item in q:
        if item["id"] == item_id and item["status"] == "pending":
            item["status"] = "discarded"
            _save_queue(q)
            return f"[DISCARDED] Acao {item_id} cancelada. Nada foi executado."
    return f"Nenhuma acao pendente com id '{item_id}'."


def resolve_list() -> str:
    """Lista acoes enfileiradas e seus status."""
    q = _load_queue()
    if not q:
        return "Fila de acoes vazia."
    linhas = []
    for item in q:
        desc = _RESOLVE_ACTIONS.get(item["action"], {}).get(
            "describe", lambda a: item["action"])(item["args"])
        linhas.append(f"{item['id']} [{item['status']}] {desc}")
    return "Fila de acoes (resolve):\n" + "\n".join(linhas)


# --- Definicao das acoes suportadas ---

def _apply_delete(args):
    path = args["path"]
    if not os.path.exists(path):
        return f"Caminho inexistente: {path}"
    if os.path.isdir(path):
        shutil.rmtree(path)
        return f"Pasta removida: {path}"
    os.remove(path)
    return f"Arquivo removido: {path}"


def _desc_delete(args):
    return f"APAGAR {args.get('path')}"


def _apply_move(args):
    src, dst = args["src"], args["dst"]
    shutil.move(src, dst)
    return f"Movido: {src} -> {dst}"


def _desc_move(args):
    return f"MOVER {args.get('src')} -> {args.get('dst')}"


def _apply_copy_overwrite(args):
    src, dst = args["src"], args["dst"]
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        parent = os.path.dirname(os.path.abspath(dst))
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)
    return f"Copiado (sobrescreve): {src} -> {dst}"


def _desc_copy_overwrite(args):
    return f"COPIAR/SOBRESCREVER {args.get('src')} -> {args.get('dst')}"


_register_action("delete_path", _apply_delete, _desc_delete)
_register_action("move_file", _apply_move, _desc_move)
_register_action("copy_overwrite", _apply_copy_overwrite, _desc_copy_overwrite)
