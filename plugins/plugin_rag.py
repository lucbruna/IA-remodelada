"""
plugin_rag.py
==============
Plugin RAG (Retrieval-Augmented Generation) — Busca semântica em documentos.

Usa ChromaDB como backend principal e Qdrant como alternativa.
Fornece indexação de documentos, busca semântica e augmentation de prompts.

Funciona em TODAS as interfaces (CLI, API, Streamlit, Web).
"""

__version__ = "1.0.0"

import os
import json
import logging
from typing import Optional

# ─── Diretórios ────────────────────────────────────────────────────
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PLUGIN_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "agente_data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# ─── Estado global ─────────────────────────────────────────────────
RAG_AVAILABLE = False
RAG_BACKEND = "chromadb"  # "chromadb" ou "qdrant"
RAG_COLLECTION = None
RAG_CLIENT = None
RAG_COLLECTION_NAME = "documentos"
RAG_DOCUMENT_COUNT = 0

# Modelo de embedding preferido
EMBEDDING_MODEL = "nomic-embed-text"


def _find_embedding_model() -> Optional[str]:
    """Encontra um modelo de embedding disponível no Ollama."""
    try:
        import ollama
        for model_name in ["nomic-embed-text", "all-minilm", "mxbai-embed-large", "llama3.2"]:
            try:
                # Verifica se o modelo existe localmente
                ollama.show(model_name)
                return model_name
            except Exception:
                try:
                    # Tenta baixar
                    ollama.pull(model_name)
                    return model_name
                except Exception:
                    continue
        return None
    except Exception:
        return None


def _init_chromadb() -> bool:
    """Inicializa ChromaDB como backend RAG."""
    global RAG_AVAILABLE, RAG_COLLECTION, RAG_CLIENT, RAG_DOCUMENT_COUNT, RAG_BACKEND

    try:
        import chromadb
        from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction
    except ImportError:
        print("  ⚠ RAG: chromadb não instalado (pip install chromadb)")
        return False

    embed_model = _find_embedding_model()
    if not embed_model:
        print(f"  ⚠ RAG: Nenhum modelo de embedding encontrado. Execute: ollama pull {EMBEDDING_MODEL}")
        return False

    try:
        ollama_ef = OllamaEmbeddingFunction(
            url="http://localhost:11434",
            model_name=embed_model
        )

        RAG_CLIENT = chromadb.PersistentClient(path=CHROMA_DIR)

        try:
            RAG_COLLECTION = RAG_CLIENT.get_collection(RAG_COLLECTION_NAME)
        except Exception:
            RAG_COLLECTION = RAG_CLIENT.create_collection(
                name=RAG_COLLECTION_NAME,
                embedding_function=ollama_ef
            )

        RAG_AVAILABLE = True
        RAG_BACKEND = "chromadb"
        RAG_DOCUMENT_COUNT = RAG_COLLECTION.count()
        print(f"  [RAG] ativo - backend: ChromaDB, modelo: {embed_model}, docs: {RAG_DOCUMENT_COUNT}")
        return True

    except Exception as e:
        print(f"  [RAG] Erro ao inicializar ChromaDB: {e}")
        return False


def _init_qdrant() -> bool:
    """Inicializa Qdrant como backend RAG (alternativa, experimental).
    
    Nota: Requer sentence-transformers para embeddings, ou ChromaDB
    para usar o OllamaEmbeddingFunction.
    """
    global RAG_AVAILABLE, RAG_COLLECTION, RAG_CLIENT, RAG_DOCUMENT_COUNT, RAG_BACKEND

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
    except ImportError:
        return False

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
    except ImportError:
        return False

    try:
        # Tenta conectar ao servidor Qdrant (Docker), depois cai para local mode
        RAG_CLIENT = QdrantClient(url="http://localhost:6333", timeout=2)
        RAG_CLIENT.get_collections()
        print("  [RAG] Conectado ao servidor Qdrant (http://localhost:6333)")
    except Exception:
        # Fallback para local mode
        qdrant_path = os.path.join(DATA_DIR, "qdrant_db")
        os.makedirs(qdrant_path, exist_ok=True)
        try:
            RAG_CLIENT = QdrantClient(path=qdrant_path)
            print(f"  [RAG] Usando Qdrant local ({qdrant_path})")
        except Exception as e:
            print(f"  [RAG] Qdrant nao disponivel: {e}")
            return False

    try:
        # Cria colecao se nao existir
        collections = RAG_CLIENT.get_collections()
        exists = any(c.name == RAG_COLLECTION_NAME for c in collections.collections)

        if not exists:
            RAG_CLIENT.create_collection(
                collection_name=RAG_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE,
                ),
            )

        RAG_AVAILABLE = True
        RAG_BACKEND = "qdrant"
        try:
            count_result = RAG_CLIENT.count(collection_name=RAG_COLLECTION_NAME)
            RAG_DOCUMENT_COUNT = count_result.count
        except Exception:
            RAG_DOCUMENT_COUNT = 0
        print(f"  [RAG] ativo - backend: Qdrant, docs: {RAG_DOCUMENT_COUNT}")
        return True

    except Exception as e:
        print(f"  [RAG] Erro ao inicializar Qdrant: {e}")
        return False


def init_rag(prefer: str = "chromadb") -> bool:
    """Inicializa o sistema RAG.

    Args:
        prefer: Backend preferido ("chromadb" ou "qdrant")

    Returns:
        True se RAG foi inicializado com sucesso
    """
    global RAG_AVAILABLE

    if RAG_AVAILABLE:
        return True

    if prefer == "qdrant":
        if _init_qdrant():
            return True
        return _init_chromadb()
    else:
        if _init_chromadb():
            return True
        return _init_qdrant()


def index_document(doc_id: str, text: str, metadata: dict = None) -> bool:
    """Indexa um documento no RAG para busca semântica.

    Args:
        doc_id: Identificador único do documento
        text: Texto do documento a ser indexado
        metadata: Metadados opcionais (filename, conversation_id, etc.)

    Returns:
        True se indexado com sucesso
    """
    if not RAG_AVAILABLE:
        return False

    if metadata is None:
        metadata = {}

    try:
        if RAG_BACKEND == "chromadb":
            return _index_chromadb(doc_id, text, metadata)
        elif RAG_BACKEND == "qdrant":
            return _index_qdrant(doc_id, text, metadata)
    except Exception as e:
        print(f"  ⚠ Erro ao indexar no RAG: {e}")
    return False


def _index_chromadb(doc_id: str, text: str, metadata: dict) -> bool:
    """Indexa no ChromaDB com chunking automático e overlap."""
    global RAG_DOCUMENT_COUNT

    chunks = []
    chunk_ids = []
    max_chunk = 2000
    overlap = 200  # 10% de overlap entre chunks
    step = max_chunk - overlap

    if len(text) > max_chunk:
        i = 0
        while i < len(text):
            chunk = text[i:i + max_chunk]
            if chunk:
                chunks.append(chunk)
                chunk_ids.append(f"{doc_id}_chunk{i // step}")
            i += step
    else:
        chunks = [text]
        chunk_ids = [doc_id]

    metadatas = []
    for cid in chunk_ids:
        m = dict(metadata)
        m["doc_id"] = doc_id
        metadatas.append(m)

    RAG_COLLECTION.add(
        documents=chunks,
        ids=chunk_ids,
        metadatas=metadatas,
    )

    RAG_DOCUMENT_COUNT = RAG_COLLECTION.count()
    return True


def _index_qdrant(doc_id: str, text: str, metadata: dict) -> bool:
    """Indexa no Qdrant com chunking automatico, overlap e embeddings via sentence-transformers."""
    from qdrant_client.http import models
    import uuid

    chunks = []
    max_chunk = 2000
    overlap = 200  # 10% de overlap entre chunks
    step = max_chunk - overlap

    if len(text) > max_chunk:
        i = 0
        while i < len(text):
            chunk = text[i:i + max_chunk]
            if chunk:
                chunks.append(chunk)
            i += step
    else:
        chunks = [text]

    # Gera embeddings para cada chunk
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode(chunks).tolist()
    except ImportError:
        return False

    points = []
    for i, chunk in enumerate(chunks):
        m = dict(metadata)
        m["doc_id"] = doc_id
        m["text"] = chunk
        points.append(models.PointStruct(
            id=str(uuid.uuid4()),
            payload=m,
            vector=vectors[i],
        ))

    RAG_CLIENT.upsert(
        collection_name=RAG_COLLECTION_NAME,
        points=points,
    )

    try:
        count_result = RAG_CLIENT.count(collection_name=RAG_COLLECTION_NAME)
        RAG_DOCUMENT_COUNT = count_result.count
    except Exception:
        pass
    return True


def search_rag(query: str, n_results: int = 3, where: dict = None) -> list:
    """Busca documentos relevantes no RAG.

    Args:
        query: Texto da busca
        n_results: Número máximo de resultados
        where: Filtro opcional (ex: {"project_id": "projeto1"})

    Returns:
        Lista de dicionários com 'text', 'metadata' e 'score'
    """
    if not RAG_AVAILABLE:
        return []

    try:
        if RAG_BACKEND == "chromadb":
            return _search_chromadb(query, n_results, where)
        elif RAG_BACKEND == "qdrant":
            return _search_qdrant(query, n_results, where)
    except Exception as e:
        print(f"  ⚠ Erro na busca RAG: {e}")
    return []


def _search_chromadb(query: str, n_results: int, where: dict = None) -> list:
    """Busca no ChromaDB com score real (distância cosseno)."""
    query_kwargs = {
        "query_texts": [query],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    results = RAG_COLLECTION.query(**query_kwargs)

    docs = []
    if results and results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            meta = {}
            if results.get("metadatas") and len(results["metadatas"][0]) > i:
                meta = results["metadatas"][0][i]
            # Converte distância (menor = melhor) para score (maior = melhor)
            distance = 0.0
            if results.get("distances") and len(results["distances"][0]) > i:
                distance = results["distances"][0][i]
            score = max(0.0, 1.0 - distance)  # distancia 0 = score 1.0
            docs.append({
                "text": doc[:500],
                "metadata": meta,
                "score": round(score, 4),
            })
    return docs


def _search_qdrant(query: str, n_results: int, where: dict = None) -> list:
    """Busca no Qdrant usando similaridade de cosseno."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_vector = model.encode(query).tolist()

        search_kwargs = {
            "collection_name": RAG_COLLECTION_NAME,
            "query_vector": query_vector,
            "limit": n_results,
        }
        if where:
            from qdrant_client.http import models
            conditions = [
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in where.items()
            ]
            search_kwargs["query_filter"] = models.Filter(must=conditions)

        results = RAG_CLIENT.search(**search_kwargs)

        docs = []
        for r in results:
            docs.append({
                "text": r.payload.get("text", str(r.payload))[:500],
                "metadata": dict(r.payload) if r.payload else {},
                "score": round(r.score, 4),
            })
        return docs
    except Exception:
        return []


def augment_with_rag(user_msg: str, system_prompt: str) -> str:
    """Aumenta o system prompt com contexto RAG.

    Args:
        user_msg: Mensagem do usuário para buscar documentos relevantes
        system_prompt: System prompt original

    Returns:
        System prompt aumentado com contexto RAG, ou original se RAG inativo
    """
    if not RAG_AVAILABLE:
        return system_prompt

    docs = search_rag(user_msg)
    if not docs:
        return system_prompt

    context_text = "\n\n---\n**Documentos relevantes:**\n"
    for d in docs:
        preview = d['text'][:300].replace('{', '(').replace('}', ')')
        context_text += f"- {preview}\n"

    return system_prompt + context_text


def rag_status() -> str:
    """Retorna status detalhado do RAG."""
    if RAG_AVAILABLE:
        return (
            f"✅ RAG ativo\n"
            f"   Backend: {RAG_BACKEND}\n"
            f"   Documentos indexados: {RAG_DOCUMENT_COUNT}\n"
            f"   Diretório: {CHROMA_DIR}"
        )
    else:
        return (
            "❌ RAG inativo\n"
            "\n"
            "Para ativar:\n"
            "  1. Instale chromadb: pip install chromadb\n"
            "  2. Baixe modelo: ollama pull nomic-embed-text\n"
            "  3. Use init_rag() no seu código\n"
            "  \n"
            "Alternativa Qdrant:\n"
            "  1. pip install qdrant-client\n"
            "  2. docker run -p 6333:6333 qdrant/qdrant\n"
            "  \n"
            "Ou use modo local do Qdrant (sem Docker)."
        )


def clear_rag() -> bool:
    """Limpa todos os documentos do RAG."""
    global RAG_DOCUMENT_COUNT

    if not RAG_AVAILABLE:
        return False

    try:
        if RAG_BACKEND == "chromadb":
            all_ids = RAG_COLLECTION.get()['ids']
            if all_ids:
                RAG_COLLECTION.delete(ids=all_ids)
            RAG_DOCUMENT_COUNT = 0
        elif RAG_BACKEND == "qdrant":
            from qdrant_client.http import models
            RAG_CLIENT.delete(
                collection_name=RAG_COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter()
                ),
            )
            RAG_DOCUMENT_COUNT = 0
        return True
    except Exception as e:
        print(f"  ⚠ Erro ao limpar RAG: {e}")
        return False


def delete_from_rag(doc_id: str) -> bool:
    """Remove um documento específico do RAG."""
    global RAG_DOCUMENT_COUNT

    if not RAG_AVAILABLE:
        return False

    try:
        if RAG_BACKEND == "chromadb":
            RAG_COLLECTION.delete(
                where={"doc_id": doc_id}
            )
            RAG_DOCUMENT_COUNT = RAG_COLLECTION.count()
        elif RAG_BACKEND == "qdrant":
            from qdrant_client.http import models
            RAG_CLIENT.delete(
                collection_name=RAG_COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                ),
            )
            try:
                count_result = RAG_CLIENT.count(collection_name=RAG_COLLECTION_NAME)
                RAG_DOCUMENT_COUNT = count_result.count
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"  ⚠ Erro ao deletar do RAG: {e}")
        return False


# ─── Registro do Plugin ────────────────────────────────────────────

def register(api):
    """Registra as ferramentas RAG no agente."""

    # Inicializa RAG automaticamente ao registrar o plugin
    init_rag()

    def ferramenta_rag_status() -> str:
        """Retorna o status do sistema RAG (ativo/inativo, documentos indexados, backend)."""
        return rag_status()

    def ferramenta_rag_buscar(query: str, n_results: int = 3, filtros_json: str = "") -> str:
        """Busca documentos semanticamente similares no RAG."""
        filtros = {}
        if filtros_json:
            try:
                filtros = json.loads(filtros_json)
            except Exception:
                pass
        docs = search_rag(query, n_results, where=filtros if filtros else None)
        if not docs:
            return "Nenhum documento relevante encontrado."
        linhas = [f"🔍 Resultados para: '{query}'\n"]
        for i, d in enumerate(docs, 1):
            meta = d.get("metadata", {})
            filename = meta.get("filename", "desconhecido")
            score = d.get("score", 0)
            linhas.append(f"{i}. [{filename}] (score: {score:.2f})")
            linhas.append(f"   {d['text'][:200]}...")
            linhas.append("")
        return "\n".join(linhas)

    def ferramenta_rag_indexar(texto: str, doc_id: str = "", metadata_json: str = "{}") -> str:
        """Indexa um texto no RAG para busca semântica futura."""
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())[:8]
        try:
            metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
        except Exception:
            metadata = {}
        success = index_document(doc_id, texto, metadata)
        if success:
            return f"✅ Documento '{doc_id}' indexado no RAG ({len(texto)} caracteres). Total: {RAG_DOCUMENT_COUNT}"
        else:
            return "❌ Erro ao indexar no RAG. Verifique se o RAG está ativo."

    def ferramenta_rag_limpar() -> str:
        """Remove todos os documentos do RAG."""
        if clear_rag():
            return "✅ RAG limpo com sucesso."
        return "❌ Erro ao limpar RAG."

    api.register_tool(
        name="rag_status",
        func=ferramenta_rag_status,
        description="Retorna o status do sistema RAG (Retrieval-Augmented Generation): se está ativo, backend usado, e quantos documentos estão indexados.",
        parameters={},
        required=[],
    )

    api.register_tool(
        name="rag_buscar",
        func=ferramenta_rag_buscar,
        description="Busca documentos semanticamente similares no RAG. Use para encontrar informações relevantes em documentos indexados.",
        parameters={
            "query": {"type": "string", "description": "Texto da busca semântica"},
            "n_results": {"type": "integer", "description": "Número de resultados (padrão: 3, máx: 10)"},
            "filtros_json": {"type": "string", "description": "Filtros opcionais em JSON, por exemplo {\"project_id\":\"app\",\"conversation_id\":\"abc\",\"category\":\"erro\"}"},
        },
        required=["query"],
    )

    api.register_tool(
        name="rag_indexar",
        func=ferramenta_rag_indexar,
        description="Indexa um texto no RAG para busca semântica futura. O texto será dividido em chunks e armazenado com embedding vetorial.",
        parameters={
            "texto": {"type": "string", "description": "Texto a ser indexado"},
            "doc_id": {"type": "string", "description": "ID opcional do documento (UUID automático se vazio)"},
            "metadata_json": {"type": "string", "description": "Metadados em JSON (ex: {\"filename\": \"doc.txt\"})"},
        },
        required=["texto"],
    )

    api.register_tool(
        name="rag_limpar",
        func=ferramenta_rag_limpar,
        description="Remove todos os documentos do RAG. Use com cuidado.",
        parameters={},
        required=[],
    )

    return {
        "name": "RAG (Retrieval-Augmented Generation)",
        "version": __version__,
        "description": "Busca semântica em documentos usando ChromaDB ou Qdrant. Indexação, busca e status.",
        "tools": ["rag_status", "rag_buscar", "rag_indexar", "rag_limpar"],
    }
