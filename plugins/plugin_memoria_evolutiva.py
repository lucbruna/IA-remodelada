"""
plugin_memoria_evolutiva.py
============================

Memoria Evolutiva — sistema de memoria avancado que aprende com o tempo.

Recursos:
  - Memoria semantica com busca por significado (tags geradas pelo proprio LLM)
  - Extracao automatica de fatos importantes das conversas
  - Perfil de usuario adaptativo (aprende preferencias, estilo, projetos)
  - Sumarios hierarquicos (diarios, semanais, mensais)
  - Grafo de conhecimento (conceitos interligados)
  - Curva de esquecimento (relevancia decai com o tempo)
  - Reflexao automatica (autocritica e melhoria de prompt)
"""

import json
import os
import time
import logging
import re
from datetime import datetime, date
from collections import defaultdict

PLUGIN_VERSION = "2.0.0"
PLUGIN_DESCRIPTION = "Sistema de memoria evolutiva com RAG local, perfil de usuario, grafo de conhecimento e auto-aprendizado"

# Diretorio de dados do plugin
PLUGIN_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agente_data", "memoria_evolutiva"
)

# Arquivos de dados
FATOS_FILE = os.path.join(PLUGIN_DATA_DIR, "fatos_semanticos.json")
PERFIL_FILE = os.path.join(PLUGIN_DATA_DIR, "perfil_usuario.json")
GRAFO_FILE = os.path.join(PLUGIN_DATA_DIR, "grafo_conhecimento.json")
SUMS_FILE = os.path.join(PLUGIN_DATA_DIR, "sumarios.json")
REFLECOES_FILE = os.path.join(PLUGIN_DATA_DIR, "reflexoes.json")
ESTATISTICAS_FILE = os.path.join(PLUGIN_DATA_DIR, "estatisticas.json")

# Limites
MAX_FATOS = 2000
RELEVANCIA_DECAY = 0.95  # multiplicador por dia sem acesso
SIMILARIDADE_LIMIAR = 0.3  # limiar minimo de similaridade semantica

# ChromaDB para busca VETORIAL real
VECTOR_DIR = os.path.join(PLUGIN_DATA_DIR, "chroma_db")
_COLLECTION_NAME = "memoria_vetorial"
_USE_VECTOR_SEARCH = True  # ativa busca vetorial

_ollama_model = "llama3.1"
_api = None  # setado pelo register()
_chroma_client = None
_chroma_collection = None
_embedding_model = None


def _get_embedding_model():
    """Retorna modelo de embeddings (singleton com lazy init)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedding_model
    except Exception as e:
        logging.warning("Nao foi possivel carregar modelo de embeddings: %s", e)
        return None


def _get_chroma_collection():
    """Retorna colecao ChromaDB (singleton com lazy init)."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    try:
        import chromadb
        _ensure_dir()
        _chroma_client = chromadb.PersistentClient(path=VECTOR_DIR)
        # Tenta obter colecao existente ou cria nova
        try:
            _chroma_collection = _chroma_client.get_collection(_COLLECTION_NAME)
        except Exception:
            _chroma_collection = _chroma_client.create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return _chroma_collection
    except Exception as e:
        logging.warning("ChromaDB nao disponivel: %s", e)
        return None


def _gerar_embedding(texto: str) -> list:
    """Gera embedding vetorial para um texto."""
    model = _get_embedding_model()
    if model is None:
        return None
    try:
        return model.encode(texto[:512]).tolist()
    except Exception as e:
        logging.warning("Erro ao gerar embedding: %s", e)
        return None


def _adicionar_ao_chroma(fato_id: str, texto: str, metadata: dict):
    """Adiciona um fato ao banco vetorial."""
    collection = _get_chroma_collection()
    if collection is None:
        return None
    embedding = _gerar_embedding(texto)
    if embedding is None:
        return None
    collection.add(
        ids=[fato_id],
        embeddings=[embedding],
        documents=[texto[:1000]],
        metadatas=[metadata],
    )
    return True


def _remover_do_chroma(fato_id: str):
    """Remove um fato do banco vetorial."""
    collection = _get_chroma_collection()
    if collection is None:
        return
    try:
        collection.delete(ids=[fato_id])
    except Exception:
        pass


def _buscar_vetorial(consulta: str, limite: int = 5) -> list:
    """Busca na memoria usando similaridade COSSENO (vetorial)."""
    collection = _get_chroma_collection()
    if collection is None:
        return None
    embedding = _gerar_embedding(consulta)
    if embedding is None:
        return None
    try:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(limite, 20),
            include=["documents", "metadatas", "distances"],
        )
        if not results or not results["ids"][0]:
            return []
        
        # Converte para formato compatível com memoria_buscar
        fatos_encontrados = []
        for i in range(len(results["ids"][0])):
            fato_id = results["ids"][0][i]
            doc = results["documents"][0][i] if results["documents"] else ""
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distancia = results["distances"][0][i] if results["distances"] else 0
            score = 1.0 - distancia  # cosseno -> similaridade
            fatos_encontrados.append({
                "id": fato_id,
                "texto": doc,
                "categoria": meta.get("categoria", "geral"),
                "importancia": meta.get("importancia", 3),
                "score": score,
            })
        return fatos_encontrados
    except Exception as e:
        logging.warning("Erro na busca vetorial: %s", e)
        return None


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def _ensure_dir():
    os.makedirs(PLUGIN_DATA_DIR, exist_ok=True)


def _load_json(path, default=None):
    if default is None:
        default = {} if path.endswith(".json") else []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning("Erro lendo %s: %s", path, e)
    return default


def _save_json(path, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _now_ts():
    return int(time.time())


def _hoje():
    return date.today().isoformat()


def _chunks(text, size=800):
    """Divide texto grande em chunks para processamento."""
    return [text[i:i+size] for i in range(0, len(text), size)]


def _gerar_tags_llm(texto, max_tags=6):
    """Usa o proprio LLM para gerar tags semanticas de um texto."""
    try:
        import ollama
        resp = ollama.chat(
            model=_ollama_model,
            messages=[{
                "role": "user",
                "content": (
                    "Extraia de {max_tags} a {max_tags} palavras-chave ou frases curtas "
                    "que melhor representem o significado do texto abaixo. "
                    "Respondapenas as tags separadas por virgula, sem explicacoes.\n\n"
                    f"{texto[:2000]}"
                )
            }],
            options={"temperature": 0.1, "num_ctx": 4096}
        )
        texto_tags = resp["message"]["content"].strip()
        tags = [t.strip().lower() for t in texto_tags.split(",") if t.strip()]
        return tags[:max_tags]
    except Exception:
        # Fallback: extrai palavras mais frequentes
        palavras = re.findall(r'\b[a-z]{4,}\b', texto.lower())
        freq = defaultdict(int)
        for p in palavras:
            freq[p] += 1
        sorted_palavras = sorted(freq, key=freq.get, reverse=True)
        return sorted_palavras[:max_tags] if sorted_palavras else ["informacao"]


def _gerar_embedding_tag(texto):
    """Gera representacao semântica compacta (tags + resumo)."""
    tags = _gerar_tags_llm(texto[:1500])
    palavras_importantes = set(t.lower() for t in tags)
    palavras_texto = set(re.findall(r'\b[a-z]{3,}\b', texto.lower()))
    palavras_importantes.update(palavras_texto)
    return list(palavras_importantes)


def _similaridade_tags(tags1, tags2):
    """Calcula similaridade de Jaccard entre dois conjuntos de tags."""
    if not tags1 or not tags2:
        return 0.0
    set1, set2 = set(tags1), set(tags2)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union else 0.0


# ---------------------------------------------------------------------------
# FATOS SEMANTICOS (memoria com busca por significado)
# ---------------------------------------------------------------------------

def _carregar_fatos():
    return _load_json(FATOS_FILE, [])


def _salvar_fatos(fatos):
    _save_json(FATOS_FILE, fatos)


def memoria_guardar(texto: str, categoria: str = "geral", importancia: int = 3) -> str:
    """Guarda um fato na memoria semantica. Importancia: 1 (baixa) a 5 (alta)."""
    fatos = _carregar_fatos()
    importancia = max(1, min(5, importancia))

    tags = _gerar_tags_llm(texto[:1000])

    fato = {
        "id": _now_ts(),
        "texto": texto.strip(),
        "tags": tags,
        "categoria": categoria,
        "importancia": importancia,
        "criado_em": _hoje(),
        "ultimo_acesso": _now_ts(),
        "acessos": 0,
        "relevancia": 1.0,
    }

    # Verifica duplicata
    dedup_texto = texto.strip().lower()[:200]
    for f in fatos:
        if f["texto"].strip().lower()[:200] == dedup_texto:
            f["ultimo_acesso"] = _now_ts()
            f["acessos"] += 1
            f["relevancia"] = min(1.0, f["relevancia"] + 0.1)
            _salvar_fatos(fatos)
            return f"Fato ja existente, relevancia aumentada para {f['relevancia']:.2f}."

    fatos.append(fato)

    # Adiciona ao ChromaDB (vetorial)
    fato_id = str(fato["id"])
    _adicionar_ao_chroma(
        fato_id,
        texto.strip(),
        {
            "categoria": categoria,
            "importancia": str(importancia),
            "criado_em": _hoje(),
        }
    )

    # Mantem limite
    if len(fatos) > MAX_FATOS:
        fatos.sort(key=lambda x: (
            x["relevancia"] * x["importancia"] / 5.0,
            x["acessos"],
            x.get("ultimo_acesso", 0)
        ), reverse=True)
        fatos = fatos[:MAX_FATOS]

    _salvar_fatos(fatos)
    return f"Fato guardado na memoria semantica (tags: {', '.join(tags[:4])}). Total: {len(fatos)} fatos."


def memoria_buscar(consulta: str, limite: int = 5) -> str:
    """Busca na memoria semantica por significado (nao apenas palavra exata)."""
    fatos = _carregar_fatos()
    if not fatos:
        return "Memoria semantica vazia. Nada encontrado."

    tags_consulta = _gerar_tags_llm(consulta[:1000])
    palavras_consulta = set(re.findall(r'\b[a-z]{3,}\b', consulta.lower()))

    if not tags_consulta and not palavras_consulta:
        return "Nao foi possivel extrair termos de busca."

    # Tenta busca VETORIAL primeiro (ChromaDB + embeddings)
    resultados_vetoriais = _buscar_vetorial(consulta, limite)
    
    if resultados_vetoriais:
        # Usa resultados vetoriais (mais precisos)
        resultados = [(r["score"], {
            "texto": r["texto"],
            "tags": [],
            "categoria": r["categoria"],
            "importancia": r["importancia"],
            "relevancia": r["score"],
        }) for r in resultados_vetoriais]
    else:
        # Fallback: busca por tags (semantica via LLM)
        resultados = []
        for f in fatos:
            tags_fato = set(f.get("tags", []))
            palavras_fato = set(re.findall(r'\b[a-z]{3,}\b', f.get("texto", "").lower()))

            # Similaridade semantica (tags)
            sim_tags = _similaridade_tags(tags_consulta, tags_fato)

            # Similaridade textual (palavras)
            inter_pal = len(palavras_consulta & palavras_fato)
            union_pal = len(palavras_consulta | palavras_fato) or 1
            sim_palavras = inter_pal / union_pal

            # Pontuacao final
            score = (sim_tags * 0.6 + sim_palavras * 0.4)
            score *= f.get("relevancia", 1.0)
            score *= f.get("importancia", 3) / 5.0

            if score > SIMILARIDADE_LIMIAR:
                resultados.append((score, f))

        resultados.sort(key=lambda x: x[0], reverse=True)
        resultados = resultados[:limite]

        if not resultados:
            # Fallback: busca textual
            consulta_lower = consulta.lower()
            for f in fatos:
                if consulta_lower in f.get("texto", "").lower():
                    score = 0.1
                    resultados.append((score, f))
            resultados.sort(key=lambda x: x[0], reverse=True)
            resultados = resultados[:limite]

    if not resultados:
        return f"Nada relevante encontrado para: {consulta}"

    linhas = [f"--- Memoria Semantica (melhores {len(resultados)}) ---"]
    for i, (score, f) in enumerate(resultados, 1):
        # Atualiza acesso
        f["ultimo_acesso"] = _now_ts()
        f["acessos"] = f.get("acessos", 0) + 1
        f["relevancia"] = min(1.0, f.get("relevancia", 0.5) + 0.05)

        texto = f["texto"][:300]
        tags = ", ".join(f.get("tags", [])[:4])
        linhas.append(
            f"{i}. [score={score:.2f}] (cat: {f.get('categoria','?')}, "
            f"imp: {f.get('importancia',3)})"
        )
        linhas.append(f"   {texto}")
        if tags:
            linhas.append(f"   tags: {tags}")

    _salvar_fatos(fatos)
    return "\n".join(linhas)


def memoria_listar(categoria: str = "", limite: int = 20) -> str:
    """Lista fatos da memoria semantica, opcionalmente filtrados por categoria."""
    fatos = _carregar_fatos()
    if not fatos:
        return "Memoria semantica vazia."

    if categoria:
        fatos = [f for f in fatos if f.get("categoria") == categoria]

    if not fatos:
        return f"Nenhum fato na categoria '{categoria}'."

    fatos.sort(key=lambda x: (
        x.get("relevancia", 0) * x.get("importancia", 3),
        x.get("acessos", 0)
    ), reverse=True)

    linhas = [f"--- Memoria Semantica: {len(fatos)} fatos ---"]
    for f in fatos[:limite]:
        texto = f["texto"][:200]
        linhas.append(
            f"  [rel={f.get('relevancia',0):.2f} imp={f.get('importancia',3)} "
            f"acessos={f.get('acessos',0)}] {texto}"
        )
    return "\n".join(linhas)


def memoria_esquecer(termo: str) -> str:
    """Remove fatos da memoria que contenham o termo."""
    fatos = _carregar_fatos()
    antes = len(fatos)
    termo_lower = termo.lower()
    fatos = [f for f in fatos if termo_lower not in f.get("texto", "").lower()]
    depois = len(fatos)
    _salvar_fatos(fatos)
    return f"Removidos {antes - depois} fatos contendo '{termo}'. Restam {depois}."


def memoria_estatisticas() -> str:
    """Estatisticas da memoria semantica."""
    fatos = _carregar_fatos()
    if not fatos:
        return "Memoria semantica vazia."

    cats = defaultdict(int)
    imp_total = 0
    acessos_total = 0
    for f in fatos:
        cats[f.get("categoria", "geral")] += 1
        imp_total += f.get("importancia", 3)
        acessos_total += f.get("acessos", 0)

    media_imp = imp_total / len(fatos)
    media_acessos = acessos_total / len(fatos)

    linhas = ["--- Estatisticas da Memoria Semantica ---"]
    linhas.append(f"Total de fatos: {len(fatos)}")
    linhas.append(f"Categorias: {dict(cats)}")
    linhas.append(f"Importancia media: {media_imp:.2f}/5")
    linhas.append(f"Acessos medio por fato: {media_acessos:.1f}")
    top = sorted(fatos, key=lambda x: x.get("acessos", 0), reverse=True)[:3]
    if top:
        linhas.append("Fatos mais acessados:")
        for t in top:
            linhas.append(f"  [{t.get('acessos',0)}x] {t['texto'][:100]}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# PERFIL DE USUARIO (aprende preferencias)
# ---------------------------------------------------------------------------

def _carregar_perfil():
    return _load_json(PERFIL_FILE, {
        "preferencias": {},
        "estilo_comunicacao": "neutro",
        "projetos": [],
        "interesses": [],
        "ultima_interacao": _hoje(),
        "total_interacoes": 0,
        "lingua_preferida": "pt-br",
        "observacoes": [],
    })


def _salvar_perfil(perfil):
    _save_json(PERFIL_FILE, perfil)


def perfil_mostrar() -> str:
    """Mostra o perfil atual do usuario aprendido pela IA."""
    perfil = _carregar_perfil()
    linhas = ["--- Perfil do Usuario ---"]
    linhas.append(f"Estilo de comunicacao: {perfil.get('estilo_comunicacao', 'neutro')}")
    linhas.append(f"Lingua preferida: {perfil.get('lingua_preferida', 'pt-br')}")
    linhas.append(f"Total de interacoes: {perfil.get('total_interacoes', 0)}")
    linhas.append(f"Ultima interacao: {perfil.get('ultima_interacao', '?')}")

    pref = perfil.get("preferencias", {})
    if pref:
        linhas.append("\nPreferencias detectadas:")
        for k, v in pref.items():
            linhas.append(f"  {k}: {v}")

    projetos = perfil.get("projetos", [])
    if projetos:
        linhas.append(f"\nProjetos ({len(projetos)}):")
        for p in projetos[-10:]:
            linhas.append(f"  -> {p}")

    interesses = perfil.get("interesses", [])
    if interesses:
        linhas.append(f"\nInteresses ({len(interesses)}):")
        linhas.append(f"  {', '.join(interesses[-10:])}")

    obs = perfil.get("observacoes", [])
    if obs:
        linhas.append(f"\nObservacoes ({len(obs)}):")
        for o in obs[-5:]:
            linhas.append(f"  - {o}")

    return "\n".join(linhas)


def perfil_aprender(texto: str) -> str:
    """Analisa uma interacao e atualiza o perfil do usuario automaticamente."""
    perfil = _carregar_perfil()
    perfil["total_interacoes"] += 1
    perfil["ultima_interacao"] = _hoje()

    texto_lower = texto.lower()
    mudancas = []

    # Detecta estilo de comunicacao
    if any(p in texto for p in ["por favor", "obrigado", "poderia", "gentilmente"]):
        perfil["estilo_comunicacao"] = "educado"
        mudancas.append("estilo: educado")
    elif any(p in texto for p in ["rapido", "direto", "vai", "faz logo"]):
        perfil["estilo_comunicacao"] = "direto"
        mudancas.append("estilo: direto")

    # Detecta lingua
    if any(p in texto_lower for p in ["hello", "please", "thank you", "how to", "what is"]):
        perfil["lingua_preferida"] = "en"
        mudancas.append("idioma: ingles")

    # Detecta projetos
    padrao_projeto = re.findall(r'(?:projeto|app|sistema|site|bot|script)\s+["""]?([a-zA-Z0-9_\- ]+)["""]?', texto_lower)
    for p in padrao_projeto:
        nome = p.strip()
        if nome and nome not in perfil["projetos"]:
            perfil["projetos"].append(nome)
            mudancas.append(f"projeto detectado: {nome}")

    # Extrai interesses com LLM
    if len(texto) > 50:
        try:
            import ollama
            resp = ollama.chat(
                model=_ollama_model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Extraia 2-4 interesses ou topicos principais da mensagem do usuario abaixo. "
                        "Responda apenas as palavras separadas por virgula:\n\n"
                        f"{texto[:1500]}"
                    )
                }],
                options={"temperature": 0.1, "num_ctx": 4096}
            )
            novos_interesses = [
                t.strip().lower() for t in resp["message"]["content"].split(",")
                if t.strip() and len(t.strip()) > 2
            ]
            for ni in novos_interesses:
                if ni not in perfil["interesses"]:
                    perfil["interesses"].append(ni)
                    mudancas.append(f"interesse: {ni}")
        except Exception:
            pass

    # Gera observacao automatica se for relevante
    if len(texto) > 100 and len(mudancas) > 0:
        obs = f"[{_hoje()}] {mudancas[-1]} — \"{texto[:100]}...\""
        perfil["observacoes"].append(obs)
        if len(perfil["observacoes"]) > 50:
            perfil["observacoes"] = perfil["observacoes"][-50:]

    # Mantem limites
    if len(perfil["projetos"]) > 50:
        perfil["projetos"] = perfil["projetos"][-50:]
    if len(perfil["interesses"]) > 100:
        perfil["interesses"] = perfil["interesses"][-100:]

    _salvar_perfil(perfil)
    if mudancas:
        return f"Perfil atualizado: {', '.join(mudancas)}"
    return "Perfil mantido (sem alteracoes significativas)."


def perfil_observar(observacao: str) -> str:
    """Adiciona uma observacao manual ao perfil do usuario."""
    perfil = _carregar_perfil()
    perfil["observacoes"].append(f"[{_hoje()}] {observacao}")
    if len(perfil["observacoes"]) > 50:
        perfil["observacoes"] = perfil["observacoes"][-50:]
    _salvar_perfil(perfil)
    return f"Observacao adicionada ao perfil."


# ---------------------------------------------------------------------------
# GRAFO DE CONHECIMENTO (conceitos interligados)
# ---------------------------------------------------------------------------

def _carregar_grafo():
    return _load_json(GRAFO_FILE, {"nos": {}, "arestas": []})


def _salvar_grafo(grafo):
    _save_json(GRAFO_FILE, grafo)


def _normalizar_conceito(texto):
    """Normaliza um trecho para conceito chave."""
    texto = texto.strip().lower()
    texto = re.sub(r'[^a-z0-9_\- ]', '', texto)
    return texto[:100]


def grafo_adicionar(conceito: str, descricao: str = "", relacao_com: str = "") -> str:
    """Adiciona um conceito ao grafo de conhecimento, opcionalmente ligado a outro."""
    grafo = _carregar_grafo()
    node_id = _normalizar_conceito(conceito)
    if not node_id:
        return "Conceito invalido."

    # Adiciona/atualiza no
    if node_id in grafo["nos"]:
        grafo["nos"][node_id]["acessos"] += 1
        grafo["nos"][node_id]["ultimo_acesso"] = _hoje()
        if descricao and descricao not in grafo["nos"][node_id].get("descricoes", []):
            grafo["nos"][node_id].setdefault("descricoes", []).append(descricao[:200])
        msg = f"Conceito atualizado: {conceito}"
    else:
        grafo["nos"][node_id] = {
            "rotulo": conceito[:100],
            "descricoes": [descricao[:200]] if descricao else [],
            "criado_em": _hoje(),
            "ultimo_acesso": _hoje(),
            "acessos": 1,
        }
        msg = f"Novo conceito: {conceito}"

    # Adiciona relacao
    if relacao_com:
        rel_id = _normalizar_conceito(relacao_com)
        if rel_id and rel_id != node_id:
            if rel_id not in grafo["nos"]:
                grafo["nos"][rel_id] = {
                    "rotulo": relacao_com[:100],
                    "descricoes": [],
                    "criado_em": _hoje(),
                    "ultimo_acesso": _hoje(),
                    "acessos": 1,
                }

            aresta_existente = False
            for a in grafo["arestas"]:
                if a["origem"] == node_id and a["destino"] == rel_id:
                    a["peso"] += 1
                    aresta_existente = True
                    break
                if a["origem"] == rel_id and a["destino"] == node_id:
                    a["peso"] += 1
                    aresta_existente = True
                    break
            if not aresta_existente:
                grafo["arestas"].append({
                    "origem": node_id,
                    "destino": rel_id,
                    "peso": 1,
                    "criado_em": _hoje(),
                })
            msg += f" | relacao: {conceito} <-> {relacao_com}"

    _salvar_grafo(grafo)
    return msg


def grafo_visualizar(conceito: str, profundidade: int = 2) -> str:
    """Mostra o grafo de conhecimento a partir de um conceito central."""
    grafo = _carregar_grafo()
    node_id = _normalizar_conceito(conceito)

    if node_id not in grafo["nos"]:
        return f"Conceito '{conceito}' nao encontrado no grafo."

    # BFS limitada
    visitados = set()
    fronteira = [(node_id, 0)]
    niveis = defaultdict(list)
    while fronteira:
        atual, nivel = fronteira.pop(0)
        if atual in visitados or nivel > profundidade:
            continue
        visitados.add(atual)
        niveis[nivel].append(atual)
        for a in grafo["arestas"]:
            if a["origem"] == atual and a["destino"] not in visitados:
                fronteira.append((a["destino"], nivel + 1))
            if a["destino"] == atual and a["origem"] not in visitados:
                fronteira.append((a["origem"], nivel + 1))

    linhas = [f"--- Grafo: {conceito} ---"]
    linhas.append(f"Total nos: {len(grafo['nos'])} | Arestas: {len(grafo['arestas'])}")
    for nivel in sorted(niveis.keys()):
        for nid in niveis[nivel]:
            no = grafo["nos"].get(nid, {})
            rotulo = no.get("rotulo", nid)
            desc = no.get("descricoes", [])
            prefixo = "  " * nivel + ("-> " if nivel > 0 else "")
            linhas.append(f"{prefixo}{rotulo}")
            if desc:
                linhas.append(f"{prefixo}  \"{desc[0][:80]}\"")
            # Mostra arestas
            for a in grafo["arestas"]:
                if a["origem"] == nid and a["destino"] in visitados:
                    linhas.append(f"{prefixo}  ---[{a['peso']}]--> {grafo['nos'].get(a['destino'],{}).get('rotulo','?')}")
    return "\n".join(linhas)


def grafo_listar() -> str:
    """Lista os conceitos mais acessados no grafo."""
    grafo = _carregar_grafo()
    if not grafo["nos"]:
        return "Grafo de conhecimento vazio."
    sorted_nos = sorted(
        grafo["nos"].items(),
        key=lambda x: x[1].get("acessos", 0),
        reverse=True
    )
    linhas = [f"--- Grafo de Conhecimento: {len(grafo['nos'])} nos, {len(grafo['arestas'])} arestas ---"]
    for nid, info in sorted_nos[:30]:
        conexoes = sum(
            1 for a in grafo["arestas"]
            if a["origem"] == nid or a["destino"] == nid
        )
        linhas.append(f"  {info['rotulo']} (acessos: {info.get('acessos',0)}, conexoes: {conexoes})")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# SUMARIOS HIERARQUICOS
# ---------------------------------------------------------------------------

def _carregar_sumarios():
    return _load_json(SUMS_FILE, {"diario": {}, "semanal": {}, "mensal": {}})


def _salvar_sumarios(data):
    _save_json(SUMS_FILE, data)


def sumario_gerar(tipo: str = "diario", texto: str = "") -> str:
    """Gera sumario de conversa. Tipos: diario, semanal, mensal."""
    if tipo not in ("diario", "semanal", "mensal"):
        return "Tipo invalido. Use: diario, semanal ou mensal."

    if not texto:
        return f"Nada para sumarizar ({tipo})."

    try:
        import ollama
        resp = ollama.chat(
            model=_ollama_model,
            messages=[{
                "role": "user",
                "content": (
                    f"Resuma a conversa abaixo em um {tipo} conciso.\n"
                    "Inclua: topicos principais, decisoes tomadas, codigo/arquivos criados, "
                    "pendencias. Seja objetivo.\n\n"
                    f"{texto[:3000]}"
                )
            }],
            options={"temperature": 0.2, "num_ctx": 8192}
        )
        sumario = resp["message"]["content"].strip()
    except Exception as e:
        return f"Erro ao gerar sumario: {e}"

    data = _carregar_sumarios()
    chave = _hoje() if tipo == "diario" else datetime.now().strftime("%Y-W%W") if tipo == "semanal" else datetime.now().strftime("%Y-%m")

    # Acumula
    if chave in data[tipo]:
        data[tipo][chave] += "\n---\n" + sumario
    else:
        data[tipo][chave] = sumario

    _salvar_sumarios(data)
    return f"Sumario {tipo} gerado e salvo ({chave}).\n{sumario}"


def sumario_mostrar(tipo: str = "diario", periodo: str = "") -> str:
    """Mostra sumarios salvos."""
    data = _carregar_sumarios()
    if tipo not in data:
        return "Tipo invalido."

    if periodo:
        if periodo in data[tipo]:
            return f"--- Sumario {tipo}: {periodo} ---\n{data[tipo][periodo]}"
        return f"Sumario {tipo} nao encontrado: {periodo}"

    chaves = sorted(data[tipo].keys(), reverse=True)[:10]
    if not chaves:
        return f"Nenhum sumario {tipo} encontrado."

    linhas = [f"--- Sumarios {tipo} disponiveis ---"]
    for c in chaves:
        preview = data[tipo][c][:80].replace("\n", " ")
        linhas.append(f"  {c}: {preview}...")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# REFLEXAO E AUTO-MELHORIA
# ---------------------------------------------------------------------------

def _processar_entrada(texto):
    """Processa uma interacao e extrai aprendizados."""
    if not texto or len(texto) < 10:
        return ""

    # Atualiza perfil
    resultado_perfil = perfil_aprender(texto)

    # Extrai fatos importantes
    palavras = len(texto.split())
    if palavras > 15:
        try:
            import ollama
            resp = ollama.chat(
                model=_ollama_model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Extraia fatos importantes, decisoes ou informacoes uteis "
                        "da mensagem abaixo. Se nao houver nada relevante, responda "
                        "apenas 'nada'.\n\n"
                        f"{texto[:2000]}"
                    )
                }],
                options={"temperature": 0.1, "num_ctx": 4096}
            )
            extracao = resp["message"]["content"].strip()
            if extracao.lower() not in ("nada", "", "nenhum", "nenhuma"):
                linhas = [l.strip() for l in extracao.split("\n") if l.strip()]
                for linha in linhas:
                    if len(linha) > 15:
                        memoria_guardar(linha, categoria="conversa", importancia=3)
        except Exception:
            pass

    return resultado_perfil


def refletir() -> str:
    """Auto-reflexao: analisa o que aprendeu e sugere melhorias."""
    perfil = _carregar_perfil()
    fatos = _carregar_fatos()
    grafo = _carregar_grafo()

    linhas = ["--- Auto-Reflexao da IA ---"]

    total_interacoes = perfil.get("total_interacoes", 0)
    linhas.append(f"\nInteracoes totais: {total_interacoes}")

    if fatos:
        linhas.append(f"Fatos na memoria: {len(fatos)}")
        cats = defaultdict(int)
        for f in fatos:
            cats[f.get("categoria", "geral")] += 1
        linhas.append(f"Categorias: {dict(cats[:5])}")

    if grafo["nos"]:
        linhas.append(f"Grafo: {len(grafo['nos'])} nos, {len(grafo['arestas'])} arestas")

    interesses = perfil.get("interesses", [])
    if interesses:
        linhas.append(f"Interesses do usuario: {', '.join(interesses[-6:])}")

    projetos = perfil.get("projetos", [])
    if projetos:
        linhas.append(f"Projetos do usuario: {', '.join(projetos[-5:])}")

    # Gera sugestao de melhoria
    if total_interacoes > 10:
        linhas.append("\nSugestoes de melhoria:")
        if len(fatos) < 5:
            linhas.append("- Interagir mais com o usuario para aprender sobre ele")
        if len(perfil.get("projetos", [])) == 0:
            linhas.append("- Perguntar sobre projetos atuais do usuario")
        if len(grafo["nos"]) < 3:
            linhas.append("- Construir grafo de conhecimento com topicos recorrentes")

    return "\n".join(linhas)


def aprender_com_erro(erro: str, contexto: str = "") -> str:
    """Registra um erro para nao repetir no futuro."""
    refs = _load_json(REFLECOES_FILE, [])
    ref = {
        "erro": erro[:500],
        "contexto": contexto[:500],
        "data": _hoje(),
        "vezes": 1,
    }

    for r in refs:
        if r["erro"][:100] == erro[:100]:
            r["vezes"] += 1
            r["data"] = _hoje()
            _save_json(REFLECOES_FILE, refs)
            return f"Erro ja registrado ({r['vezes']}x)."

    refs.append(ref)
    if len(refs) > 100:
        refs = refs[-100:]
    _save_json(REFLECOES_FILE, refs)
    return f"Erro registrado para aprendizado futuro."


def erros_listar() -> str:
    """Lista erros aprendidos (para evitar repeticoes)."""
    refs = _load_json(REFLECOES_FILE, [])
    if not refs:
        return "Nenhum erro registrado ate agora."

    refs.sort(key=lambda x: x.get("vezes", 0), reverse=True)
    linhas = [f"--- Licoes Aprendidas ({len(refs)} registros) ---"]
    for r in refs[:15]:
        linhas.append(f"  [{r['vezes']}x] {r['erro'][:120]}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# FERRAMENTA INTEGRADA: aprendizado em lote
# ---------------------------------------------------------------------------

def processar_conversa(texto: str) -> str:
    """Processa uma mensagem do usuario: aprende perfil, extrai fatos, atualiza grafo."""
    if not texto or len(texto) < 5:
        return ""

    resultados = []

    # 1. Aprende perfil
    r_perfil = perfil_aprender(texto)
    if "atualizado" in r_perfil:
        resultados.append(r_perfil)

    # 2. Extrai fatos importantes
    if len(texto) > 30:
        try:
            import ollama
            resp = ollama.chat(
                model=_ollama_model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Extraia informacoes importantes, preferencias, decisoes, "
                        "ou dados tecnicos da mensagem abaixo. "
                        "Liste cada fato em uma linha separada iniciando com '-'. "
                        "Se nada relevante, responda 'nada'.\n\n"
                        f"{texto[:2000]}"
                    )
                }],
                options={"temperature": 0.1, "num_ctx": 4096}
            )
            extracao = resp["message"]["content"].strip()
            if extracao.lower() not in ("nada", "", "nenhum", "nenhuma"):
                linhas_fatos = [
                    l.strip().lstrip("- ") for l in extracao.split("\n")
                    if l.strip() and not l.startswith("nada")
                ]
                for linha in linhas_fatos[:5]:
                    if len(linha) > 15:
                        r = memoria_guardar(linha, categoria="conversa", importancia=3)
                        resultados.append(f"  Fato: {linha[:80]}")
        except Exception:
            pass

    # 3. Extrai conceitos para o grafo
    if len(texto) > 50:
        try:
            import ollama
            resp = ollama.chat(
                model=_ollama_model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Extraia 1-3 conceitos-chave ou topicos da mensagem abaixo. "
                        "Para cada um, indique se ha relacao entre eles. "
                        "Formato: CONCEITO: descricao | RELACAO: conceito1 -> conceito2\n\n"
                        f"{texto[:2000]}"
                    )
                }],
                options={"temperature": 0.1, "num_ctx": 4096}
            )
            extracao = resp["message"]["content"].strip()
            for linha in extracao.split("\n"):
                linha = linha.strip()
                if linha.startswith("CONCEITO:"):
                    partes = linha[9:].split(":", 1)
                    nome = partes[0].strip()
                    desc = partes[1].strip() if len(partes) > 1 else ""
                    if nome and len(nome) > 2:
                        grafo_adicionar(nome, desc)
                        resultados.append(f"  Conceito: {nome}")
                elif linha.startswith("RELACAO:"):
                    rel = linha[8:].strip()
                    if "->" in rel:
                        partes = rel.split("->", 1)
                        o, d = partes[0].strip(), partes[1].strip()
                        if o and d and len(o) > 2 and len(d) > 2:
                            grafo_adicionar(o, "", d)
                            resultados.append(f"  Relacao: {o} <-> {d}")
        except Exception:
            pass

    if not resultados:
        return ""

    return "Memoria Evolutiva processou:\n" + "\n".join(resultados[:8])


# ---------------------------------------------------------------------------
# REFORCO IMEDIATO (curva de esquecimento)
# ---------------------------------------------------------------------------

def aplicar_decay():
    """Aplica decaimento de relevancia aos fatos nao acessados ha mais de 7 dias."""
    fatos = _carregar_fatos()
    agora = _now_ts()
    mudancas = 0
    for f in fatos:
        dias_sem_acesso = (agora - f.get("ultimo_acesso", agora)) / 86400
        if dias_sem_acesso > 7:
            decay = RELEVANCIA_DECAY ** (dias_sem_acesso / 7)
            nova_relevancia = max(0.05, f.get("relevancia", 1.0) * decay)
            if nova_relevancia < f.get("relevancia", 1.0):
                f["relevancia"] = nova_relevancia
                mudancas += 1

    if mudancas:
        _salvar_fatos(fatos)
    return mudancas


# ---------------------------------------------------------------------------
# FUNCAO DE OTIMIZACAO DE PROMPT
# ---------------------------------------------------------------------------

def gerar_contexto_memoria() -> str:
    """Gera um bloco de contexto com as memorias mais relevantes para incluir no prompt."""
    partes = []

    # Fatos mais relevantes
    fatos = _carregar_fatos()
    if fatos:
        fatos_ordenados = sorted(
            fatos,
            key=lambda x: x.get("relevancia", 0) * x.get("importancia", 3) / 5.0,
            reverse=True
        )[:5]
        if fatos_ordenados:
            linhas_fatos = ["Memorias recentes relevantes:"]
            for f in fatos_ordenados:
                linhas_fatos.append(f"  - {f['texto'][:200]}")
            partes.append("\n".join(linhas_fatos))

    # Perfil
    perfil = _carregar_perfil()
    if perfil.get("projetos"):
        partes.append(f"Projetos do usuario: {', '.join(perfil['projetos'][-3:])}")
    if perfil.get("interesses"):
        partes.append(f"Interesses: {', '.join(perfil['interesses'][-5:])}")
    obs = perfil.get("observacoes", [])
    if obs:
        partes.append(f"Obs: {obs[-1][:150]}")

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# REGISTER
# ---------------------------------------------------------------------------

def register(api):
    """Registra todas as ferramentas de memoria evolutiva."""
    global _api
    _api = api

    # Assegura diretorios
    _ensure_dir()

    # --- Ferramentas de memoria semantica ---
    api.register_tool(
        name="memoria_guardar",
        func=memoria_guardar,
        description="Guarda um fato na memoria semantica (busca por significado). Params: texto (obrigatorio), categoria (geral, conversa, codigo, preferencia), importancia (1-5).",
        parameters={
            "texto": {"type": "string", "description": "Fato a guardar"},
            "categoria": {"type": "string", "description": "Categoria: geral, conversa, codigo, preferencia"},
            "importancia": {"type": "integer", "description": "Importancia de 1 (baixa) a 5 (alta)"},
        },
        required=["texto"],
    )

    api.register_tool(
        name="memoria_buscar",
        func=memoria_buscar,
        description="Busca na memoria semantica por SIGNIFICADO (nao apenas palavras exatas). Ideal para lembrar de conversas antigas.",
        parameters={
            "consulta": {"type": "string", "description": "O que deseja buscar"},
            "limite": {"type": "integer", "description": "Maximo de resultados (opcional, 5)"},
        },
        required=["consulta"],
    )

    api.register_tool(
        name="memoria_listar",
        func=memoria_listar,
        description="Lista os fatos guardados na memoria semantica, opcionalmente filtrados por categoria.",
        parameters={
            "categoria": {"type": "string", "description": "Filtrar por categoria (opcional)"},
            "limite": {"type": "integer", "description": "Maximo de resultados (opcional)"},
        },
        required=[],
    )

    api.register_tool(
        name="memoria_esquecer",
        func=memoria_esquecer,
        description="Remove fatos da memoria semantica que contenham um termo especifico.",
        parameters={
            "termo": {"type": "string", "description": "Termo a remover da memoria"},
        },
        required=["termo"],
    )

    api.register_tool(
        name="memoria_estatisticas",
        func=memoria_estatisticas,
        description="Mostra estatisticas da memoria semantica (quantidade, categorias, mais acessados).",
        parameters={},
        required=[],
    )

    # --- Ferramentas de perfil ---
    api.register_tool(
        name="perfil_mostrar",
        func=perfil_mostrar,
        description="Mostra o perfil atual do usuario que a IA aprendeu (preferencias, projetos, interesses).",
        parameters={},
        required=[],
    )

    api.register_tool(
        name="perfil_aprender",
        func=perfil_aprender,
        description="Analisa um texto e atualiza o perfil do usuario automaticamente (estilo, lingua, projetos, interesses).",
        parameters={
            "texto": {"type": "string", "description": "Texto a analisar"},
        },
        required=["texto"],
    )

    api.register_tool(
        name="perfil_observar",
        func=perfil_observar,
        description="Adiciona uma observacao manual ao perfil do usuario.",
        parameters={
            "observacao": {"type": "string", "description": "Observacao a adicionar"},
        },
        required=["observacao"],
    )

    # --- Ferramentas de grafo ---
    api.register_tool(
        name="grafo_adicionar",
        func=grafo_adicionar,
        description="Adiciona um conceito ao grafo de conhecimento, opcionalmente ligado a outro.",
        parameters={
            "conceito": {"type": "string", "description": "Nome do conceito"},
            "descricao": {"type": "string", "description": "Descricao do conceito (opcional)"},
            "relacao_com": {"type": "string", "description": "Conceito relacionado (opcional)"},
        },
        required=["conceito"],
    )

    api.register_tool(
        name="grafo_visualizar",
        func=grafo_visualizar,
        description="Mostra o grafo de conhecimento a partir de um conceito central (conexoes).",
        parameters={
            "conceito": {"type": "string", "description": "Conceito central"},
            "profundidade": {"type": "integer", "description": "Profundidade da exploracao (1-3)"},
        },
        required=["conceito"],
    )

    api.register_tool(
        name="grafo_listar",
        func=grafo_listar,
        description="Lista os conceitos mais relevantes do grafo de conhecimento.",
        parameters={},
        required=[],
    )

    # --- Ferramentas de sumario ---
    api.register_tool(
        name="sumario_gerar",
        func=sumario_gerar,
        description="Gera sumario de conversa (diario, semanal, mensal) e salva para consulta futura.",
        parameters={
            "tipo": {"type": "string", "description": "diario, semanal ou mensal"},
            "texto": {"type": "string", "description": "Texto da conversa a sumarizar"},
        },
        required=["tipo", "texto"],
    )

    api.register_tool(
        name="sumario_mostrar",
        func=sumario_mostrar,
        description="Mostra sumarios salvos anteriores.",
        parameters={
            "tipo": {"type": "string", "description": "diario, semanal ou mensal"},
            "periodo": {"type": "string", "description": "Periodo especifico (opcional, ex: 2025-03-15)"},
        },
        required=["tipo"],
    )

    # --- Ferramentas de auto-melhoria ---
    api.register_tool(
        name="refletir",
        func=refletir,
        description="Auto-reflexao: mostra estatisticas de aprendizado e sugere melhorias para a IA.",
        parameters={},
        required=[],
    )

    api.register_tool(
        name="aprender_com_erro",
        func=aprender_com_erro,
        description="Registra um erro para nao repetir no futuro (aprendizado continuo).",
        parameters={
            "erro": {"type": "string", "description": "Descricao do erro"},
            "contexto": {"type": "string", "description": "Contexto onde ocorreu (opcional)"},
        },
        required=["erro"],
    )

    api.register_tool(
        name="erros_listar",
        func=erros_listar,
        description="Lista erros passados registrados para aprendizado.",
        parameters={},
        required=[],
    )

    # --- Ferramenta integrada ---
    api.register_tool(
        name="processar_conversa",
        func=processar_conversa,
        description="Processa uma mensagem: extrai fatos, atualiza perfil e grafo automaticamente.",
        parameters={
            "texto": {"type": "string", "description": "Texto completo da mensagem do usuario"},
        },
        required=["texto"],
    )

    api.register_tool(
        name="memoria_contexto",
        func=gerar_contexto_memoria,
        description="Gera um bloco de contexto com as memorias mais relevantes (para incluir no prompt do sistema).",
        parameters={},
        required=[],
    )

    return {
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "tools": [
            "memoria_guardar", "memoria_buscar", "memoria_listar",
            "memoria_esquecer", "memoria_estatisticas",
            "perfil_mostrar", "perfil_aprender", "perfil_observar",
            "grafo_adicionar", "grafo_visualizar", "grafo_listar",
            "sumario_gerar", "sumario_mostrar",
            "refletir", "aprender_com_erro", "erros_listar",
            "processar_conversa", "memoria_contexto",
        ],
    }
