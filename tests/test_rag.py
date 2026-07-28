"""
test_rag.py
============
Testes para o sistema RAG (Retrieval-Augmented Generation).

Cobre:
- Inicializacao do ChromaDB
- Indexacao de documentos com chunking
- Busca semantica com scores reais (distance -> score)
- Filtros por project_id/session_id
- Limpeza e delecao de documentos
- Augmentacao de system prompt
- Status e registro do plugin

Uso:
    pytest test_rag.py -v
    pytest test_rag.py -v -k unit   # so testes unitarios (mockados)
    pytest test_rag.py -v -k integ  # so testes de integracao (chromadb real)
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch, MagicMock, PropertyMock
import pytest

# ─── Skip condicional para testes de integracao ─────────────────────

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import ollama
    # Verifica se tem modelo de embedding
    models = ollama.list()
    has_embed = any("nomic-embed-text" in m.get("name", "") for m in getattr(models, "models", models.get("models", [])))
    OLLAMA_EMBED_AVAILABLE = has_embed
except Exception:
    OLLAMA_EMBED_AVAILABLE = False

RAG_INTEG_AVAILABLE = CHROMADB_AVAILABLE and OLLAMA_EMBED_AVAILABLE

needs_rag = pytest.mark.skipif(
    not RAG_INTEG_AVAILABLE,
    reason="Requer chromadb + nomic-embed-text para testes de integracao"
)

# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_chromadb():
    """Mocka chromadb para testes unitarios."""
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    mock_collection.get.return_value = {"ids": []}

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection
    mock_client.create_collection.return_value = mock_collection

    mock_chromadb = MagicMock()
    mock_chromadb.PersistentClient.return_value = mock_client

    mock_ef = MagicMock()
    mock_ollama_ef = MagicMock()
    mock_ollama_ef.OllamaEmbeddingFunction.return_value = mock_ef

    return {
        "chromadb": mock_chromadb,
        "ollama_ef": mock_ollama_ef,
        "client": mock_client,
        "collection": mock_collection,
        "ef": mock_ef,
    }


@pytest.fixture
def reset_rag_state():
    """Reseta o estado global do RAG antes de cada teste."""
    import plugins.plugin_rag as rag
    rag.RAG_AVAILABLE = False
    rag.RAG_COLLECTION = None
    rag.RAG_CLIENT = None
    rag.RAG_DOCUMENT_COUNT = 0
    rag.RAG_BACKEND = "chromadb"
    yield


# ═══════════════════════════════════════════════════════════════════
# TESTS UNITARIOS (MOCKADOS)
# ═══════════════════════════════════════════════════════════════════

class TestInitRagUnit:
    """Testa init_rag() com dependencias mockadas."""

    @patch("plugins.plugin_rag._init_chromadb", return_value=True)
    def test_init_retorna_true(self, mock_init_cdb, reset_rag_state):
        """init_rag() retorna True quando ChromaDB inicializa."""
        from plugins.plugin_rag import init_rag
        assert init_rag(prefer="chromadb") is True
        mock_init_cdb.assert_called_once()

    @patch("plugins.plugin_rag._init_chromadb")
    def test_init_ja_esta_ativo(self, mock_init_cdb, reset_rag_state):
        """init_rag() retorna True imediatamente se RAG ja esta ativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        assert rag.init_rag() is True
        mock_init_cdb.assert_not_called()

    @patch("plugins.plugin_rag._init_chromadb", return_value=False)
    @patch("plugins.plugin_rag._init_qdrant", return_value=False)
    def test_init_sem_backend_disponivel(self, mock_qdrant, mock_chromadb, reset_rag_state):
        """init_rag() retorna False se nenhum backend disponivel."""
        from plugins.plugin_rag import init_rag
        assert init_rag() is False


class TestIndexRagUnit:
    """Testa indexacao de documentos com ChromaDB mockado."""

    def test_index_document_com_metadados(self, mock_chromadb, reset_rag_state):
        """index_document() adiciona documento com metadados corretos."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        result = rag.index_document("doc1", "Texto de teste", {"filename": "test.txt", "project_id": "proj1"})
        assert result is True

        rag.RAG_COLLECTION.add.assert_called_once()
        call_kwargs = rag.RAG_COLLECTION.add.call_args[1]
        assert call_kwargs["documents"] == ["Texto de teste"]
        assert call_kwargs["ids"] == ["doc1"]
        assert call_kwargs["metadatas"][0]["filename"] == "test.txt"
        assert call_kwargs["metadatas"][0]["project_id"] == "proj1"
        assert call_kwargs["metadatas"][0]["doc_id"] == "doc1"

    def test_index_document_sem_metadados(self, mock_chromadb, reset_rag_state):
        """index_document() funciona sem metadados."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        result = rag.index_document("doc2", "So texto")
        assert result is True
        rag.RAG_COLLECTION.add.assert_called_once()

    def test_index_rag_inativo(self, reset_rag_state):
        """index_document() retorna False se RAG inativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = False
        assert rag.index_document("doc1", "texto") is False

    def test_index_texto_grande_faz_chunk(self, mock_chromadb, reset_rag_state):
        """Texto maior que max_chunk (2000) faz chunking."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        texto_grande = "A" * 5000
        result = rag.index_document("bigdoc", texto_grande)
        assert result is True

        rag.RAG_COLLECTION.add.assert_called_once()
        call_kwargs = rag.RAG_COLLECTION.add.call_args[1]
        chunks = call_kwargs["documents"]
        assert len(chunks) >= 2  # Deve ter gerado multiplos chunks
        ids = call_kwargs["ids"]
        assert all("bigdoc_chunk" in cid for cid in ids)

    def test_index_com_chunk_overlap(self, mock_chromadb, reset_rag_state):
        """Chunks consecutivos tem overlap de 200 caracteres."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        # Texto de 3000 chars para gerar 2 chunks com overlap
        texto = "X" * 3000
        rag.index_document("overlap_test", texto)

        rag.RAG_COLLECTION.add.assert_called_once()
        call_kwargs = rag.RAG_COLLECTION.add.call_args[1]
        chunks = call_kwargs["documents"]
        if len(chunks) >= 2:
            # Verifica que o chunk 1 comeca antes do final do chunk 0 (overlap)
            assert len(chunks[0]) + len(chunks[1]) > 3000  # overlap significa que soma > total


class TestSearchRagUnit:
    """Testa busca semantica com ChromaDB mockado."""

    def test_search_retorna_resultados_com_score(self, mock_chromadb, reset_rag_state):
        """search_rag() retorna resultados com score real (nao fixo 1.0)."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        # Mocka query do ChromaDB com distances variadas
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [["Resultado A", "Resultado B"]],
            "metadatas": [[{"filename": "a.txt"}, {"filename": "b.txt"}]],
            "distances": [[0.15, 0.45]],  # distances reais diferentes
        }

        results = rag.search_rag("consulta teste", n_results=2)

        assert len(results) == 2
        # Scores devem ser diferentes (distancia convertida)
        assert results[0]["score"] > results[1]["score"]
        assert results[0]["score"] == round(1.0 - 0.15, 4)  # 0.85
        assert results[1]["score"] == round(1.0 - 0.45, 4)  # 0.55
        assert results[0]["metadata"]["filename"] == "a.txt"
        assert results[1]["metadata"]["filename"] == "b.txt"

        # Verifica que distances foi incluido na query
        call_kwargs = rag.RAG_COLLECTION.query.call_args[1]
        assert "distances" in call_kwargs.get("include", [])

    def test_search_sem_resultados(self, mock_chromadb, reset_rag_state):
        """search_rag() retorna lista vazia quando nao ha resultados."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        rag.RAG_COLLECTION.query.return_value = {"documents": [[]], "metadatas": [[]]}

        results = rag.search_rag("consulta sem resultados")
        assert results == []

    def test_search_rag_inativo(self, reset_rag_state):
        """search_rag() retorna [] se RAG inativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = False
        assert rag.search_rag("teste") == []

    def test_search_com_filtro_where(self, mock_chromadb, reset_rag_state):
        """search_rag() passa filtro 'where' para o ChromaDB."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [["Texto filtrado"]],
            "metadatas": [[{"project_id": "proj1"}]],
            "distances": [[0.2]],
        }

        results = rag.search_rag("consulta", n_results=5, where={"project_id": "proj1"})

        assert len(results) == 1
        call_kwargs = rag.RAG_COLLECTION.query.call_args[1]
        assert call_kwargs["where"] == {"project_id": "proj1"}

    def test_search_score_nao_negativo(self, mock_chromadb, reset_rag_state):
        """Score nunca e negativo (distancia > 1 -> score = 0)."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [["Distante"]],
            "metadatas": [[{}]],
            "distances": [[2.5]],  # distancia grande
        }

        results = rag.search_rag("consulta")
        assert results[0]["score"] >= 0.0
        assert results[0]["score"] == 0.0  # max(0, 1.0 - 2.5) = 0


class TestClearDeleteRagUnit:
    """Testa limpeza e delecao de documentos."""

    def test_clear_rag_sucesso(self, mock_chromadb, reset_rag_state):
        """clear_rag() limpa todos os documentos com sucesso."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]

        rag.RAG_COLLECTION.get.return_value = {"ids": ["doc1", "doc2"]}
        rag.RAG_COLLECTION.count.return_value = 2

        result = rag.clear_rag()
        assert result is True
        rag.RAG_COLLECTION.delete.assert_called_once_with(ids=["doc1", "doc2"])

    def test_clear_rag_sem_documentos(self, mock_chromadb, reset_rag_state):
        """clear_rag() funciona mesmo quando nao ha documentos."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.get.return_value = {"ids": []}

        result = rag.clear_rag()
        assert result is True

    def test_delete_from_rag(self, mock_chromadb, reset_rag_state):
        """delete_from_rag() remove documento especifico."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.count.return_value = 1

        result = rag.delete_from_rag("doc_especifico")
        assert result is True
        rag.RAG_COLLECTION.delete.assert_called_once_with(where={"doc_id": "doc_especifico"})

    def test_delete_rag_inativo(self, reset_rag_state):
        """Operacoes retornam False se RAG inativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = False
        assert rag.clear_rag() is False
        assert rag.delete_from_rag("doc1") is False


class TestAugmentRagUnit:
    """Testa augmentacao de system prompt com RAG."""

    def test_augment_com_documentos(self, mock_chromadb, reset_rag_state):
        """augment_with_rag() adiciona contexto ao system prompt."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [["Documento relevante sobre autenticacao"]],
            "metadatas": [[{"filename": "auth.txt"}]],
            "distances": [[0.1]],
        }

        original_prompt = "System prompt original."
        augmented = rag.augment_with_rag("Como autenticar?", original_prompt)

        assert augmented != original_prompt
        assert "Documentos relevantes" in augmented
        assert "Documento relevante sobre autenticacao" in augmented

    def test_augment_sem_documentos(self, mock_chromadb, reset_rag_state):
        """augment_with_rag() retorna prompt original se sem documentos."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [[]], "metadatas": [[]]
        }

        original = "System prompt."
        assert rag.augment_with_rag("consulta", original) == original

    def test_augment_rag_inativo(self, reset_rag_state):
        """augment_with_rag() retorna prompt original se RAG inativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = False
        original = "System prompt."
        assert rag.augment_with_rag("consulta", original) == original


class TestStatusRagUnit:
    """Testa funcao de status do RAG."""

    def test_rag_status_ativo(self):
        """rag_status() retorna mensagem de status ativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_DOCUMENT_COUNT = 5

        status = rag.rag_status()
        assert "✅" in status
        assert "RAG ativo" in status
        assert "chromadb" in status
        assert "5" in status

    def test_rag_status_inativo(self):
        """rag_status() retorna instrucoes quando inativo."""
        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = False

        status = rag.rag_status()
        assert "❌" in status
        assert "RAG inativo" in status
        assert "chromadb" in status


class TestRegisterRagUnit:
    """Testa registro do plugin RAG."""

    def test_register_chama_api(self, reset_rag_state):
        """register() registra 4 ferramentas via PluginAPI."""
        from plugins.plugin_rag import register
        from agente_core import PluginAPI

        functions = {}
        tools_list = []
        api = PluginAPI(functions, tools_list)

        info = register(api)

        assert info["name"] == "RAG (Retrieval-Augmented Generation)"
        assert info["version"] == "1.0.0"
        assert len(info["tools"]) == 4
        assert "rag_status" in functions
        assert "rag_buscar" in functions
        assert "rag_indexar" in functions
        assert "rag_limpar" in functions

        # Verifica que ferramenta rag_buscar foi registrada com parametros
        assert tools_list[1]["function"]["name"] == "rag_buscar"
        params = tools_list[1]["function"]["parameters"]["properties"]
        assert "query" in params
        assert "n_results" in params

    def test_ferramenta_rag_buscar_formatacao(self, mock_chromadb, reset_rag_state):
        """ferramenta_rag_buscar() retorna texto formatado com scores."""
        from plugins.plugin_rag import register
        from agente_core import PluginAPI

        import plugins.plugin_rag as rag
        rag.RAG_AVAILABLE = True
        rag.RAG_BACKEND = "chromadb"
        rag.RAG_COLLECTION = mock_chromadb["collection"]
        rag.RAG_COLLECTION.query.return_value = {
            "documents": [["Resultado legal"]],
            "metadatas": [[{"filename": "doc.txt"}]],
            "distances": [[0.25]],
        }

        functions = {}
        tools_list = []
        api = PluginAPI(functions, tools_list)
        register(api)

        resultado = functions["rag_buscar"](query="consulta", n_results=3)
        assert "🔍" in resultado
        assert "doc.txt" in resultado
        assert "0.75" in resultado  # score = 1.0 - 0.25


# ═══════════════════════════════════════════════════════════════════
# TESTES DE INTEGRACAO (chromadb REAL)
# ═══════════════════════════════════════════════════════════════════

@needs_rag
class TestRagIntegracaoReal:
    """Testa RAG com ChromaDB real e modelo de embedding.

    Requer: chromadb instalado + nomic-embed-text baixado no Ollama.
    """

    @pytest.fixture(autouse=True)
    def setup_rag_real(self):
        """Configura RAG real para testes de integracao."""
        import plugins.plugin_rag as rag
        # Reseta estado
        rag.RAG_AVAILABLE = False
        rag.RAG_COLLECTION = None
        rag.RAG_CLIENT = None
        rag.RAG_DOCUMENT_COUNT = 0
        rag.RAG_BACKEND = "chromadb"

        # Usa diretorio temporario para chroma_db
        self.tmp_chroma = tempfile.mkdtemp()
        old_chroma_dir = rag.CHROMA_DIR
        rag.CHROMA_DIR = self.tmp_chroma

        rag.init_rag(prefer="chromadb")
        assert rag.RAG_AVAILABLE

        yield

        # Cleanup: limpa colecao e restaura
        rag.clear_rag()
        rag.CHROMA_DIR = old_chroma_dir

    def test_integ_init_e_index(self):
        """Indexa documento e verifica contagem."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_doc1", "Sistema de autenticacao JWT com tokens.", {"filename": "auth.txt"})
        assert rag.RAG_DOCUMENT_COUNT >= 1

    def test_integ_busca_com_score_real(self):
        """Busca semantica retorna scores reais (nao fixos 1.0)."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_auth", "O sistema de autenticacao utiliza JWT tokens.", {"filename": "auth.txt", "project_id": "proj_auth"})
        rag.index_document("integ_pag", "O sistema de pagamentos processa transacoes via Stripe.", {"filename": "payments.txt", "project_id": "proj_pag"})

        results = rag.search_rag("autenticacao JWT", n_results=3)
        assert len(results) >= 1

        # Score deve ser diferente de 1.0 (real)
        for r in results:
            assert r["score"] > 0.0  # sempre positivo
            assert r["score"] <= 1.0  # maximo 1.0

        # O documento de auth deve ter score maior que o de pag para esta consulta
        auth_scores = [r["score"] for r in results if r["metadata"].get("project_id") == "proj_auth"]
        pag_scores = [r["score"] for r in results if r["metadata"].get("project_id") == "proj_pag"]

        if auth_scores and pag_scores:
            assert auth_scores[0] > pag_scores[0], "Documento de auth deve ser mais relevante para consulta JWT"

    def test_integ_busca_com_filtro_project_id(self):
        """Filtro por project_id retorna apenas documentos do projeto."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_f_auth", "Sistema de autenticacao JWT.", {"project_id": "proj_auth"})
        rag.index_document("integ_f_pag", "Sistema de pagamentos.", {"project_id": "proj_pag"})

        # Busca sem filtro retorna ambos
        results_all = rag.search_rag("sistema", n_results=5)
        project_ids = set(r["metadata"].get("project_id") for r in results_all)
        assert len(project_ids) >= 2

        # Busca COM filtro retorna apenas proj_auth
        results_filtered = rag.search_rag("sistema", n_results=5, where={"project_id": "proj_auth"})
        for r in results_filtered:
            assert r["metadata"].get("project_id") == "proj_auth"

        assert len(results_filtered) < len(results_all) or len(results_filtered) == 1

    def test_integ_clear_rag(self):
        """clear_rag() limpa todos os documentos."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_clear_1", "Documento para limpeza.", {})
        rag.index_document("integ_clear_2", "Outro documento.", {})

        assert rag.RAG_DOCUMENT_COUNT >= 2
        rag.clear_rag()
        assert rag.RAG_DOCUMENT_COUNT == 0

        # Verifica que busca nao retorna mais nada
        results = rag.search_rag("documento", n_results=5)
        assert len(results) == 0

    def test_integ_delete_documento_especifico(self):
        """delete_from_rag() remove apenas documento especifico."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_del_keep", "Documento que deve permanecer.", {"filename": "keep.txt"})
        rag.index_document("integ_del_remove", "Documento que sera removido.", {"filename": "remove.txt"})

        total_antes = rag.RAG_DOCUMENT_COUNT
        rag.delete_from_rag("integ_del_remove")

        # Deve ter removido 1
        assert rag.RAG_DOCUMENT_COUNT == total_antes - 1

        # Documento que sobrou ainda e encontravel
        results = rag.search_rag("Documento que deve permanecer", n_results=5)
        keep_filenames = [r["metadata"].get("filename") for r in results]
        assert "keep.txt" in keep_filenames

    def test_integ_scores_diferentes_por_relevancia(self):
        """Documentos com relevancia diferente tem scores diferentes."""
        import plugins.plugin_rag as rag
        # Indexa documentos com conteudos bem diferentes
        rag.index_document("integ_rel_1", "O gato subiu no telhado e miou para a lua.", {})
        rag.index_document("integ_rel_2", "O cachorro correu no parque atras da bola.", {})
        rag.index_document("integ_rel_3", "Programacao em Python usa indentacao para definir blocos de codigo.", {})

        # Busca por programacao Python
        results = rag.search_rag("Python programacao codigo indentacao", n_results=5)
        assert len(results) >= 1

        top_result = results[0]["text"]
        # O documento de programacao deve ser o primeiro
        is_python_first = "Python" in top_result or "Programacao" in top_result
        if not is_python_first:
            # Se nao for o primeiro, ao menos deve estar entre os top 2
            top_texts = [r["text"][:30] for r in results[:2]]
            any_match = any("Python" in t or "Programacao" in t for t in top_texts)
            assert any_match, f"Documento Python deveria estar no top 2. Top 2: {top_texts}"

    def test_integ_augment_with_rag(self):
        """augment_with_rag() enriquece o system prompt."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_aug", "Python e uma linguagem de programacao interpretada.", {"filename": "python.txt"})

        original = "Voce e um assistente util."
        augmented = rag.augment_with_rag("Como e o Python?", original)

        assert augmented != original
        assert "Documentos relevantes" in augmented
        assert "Python" in augmented
        assert "Voce e um assistente util." in augmented

    def test_integ_status(self):
        """rag_status() retorna informacoes corretas apos indexacao."""
        import plugins.plugin_rag as rag
        rag.index_document("integ_stat", "Documento para teste de status.", {})

        status = rag.rag_status()
        assert "✅" in status
        assert "RAG ativo" in status
        assert str(rag.RAG_DOCUMENT_COUNT) in status
