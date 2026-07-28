"""
plugin_mem0.py
===============
Camada de memoria universal para agentes de IA via Mem0.

Mem0 oferece:
- Memoria multi-nivel (User, Session, Agent)
- Entity linking entre memorias
- Multi-signal retrieval (semantic + BM25 + entity)
- Temporal reasoning (ranking temporal)
- Token-efficient (7K tokens vs 26K full-context)

Modos de operacao:
- Self-hosted: docker compose up (Qdrant backend)
- Cloud: MEM0_API_KEY no .env
- Library: sem servidor, direto no codigo

Compativel com Ollama para embeddings locais.
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Mem0 (Memoria Avancada)"

import os
import json
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────
MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
MEM0_URL = os.environ.get("MEM0_URL", "")
MEM0_USER_ID = os.environ.get("MEM0_USER_ID", "default_user")
MEM0_AGENT_ID = os.environ.get("MEM0_AGENT_ID", "agente_local")
MEM0_COLLECTION = os.environ.get("MEM0_COLLECTION", "agente_memories")
MEM0_HOSTED = os.environ.get("MEM0_HOSTED", "false").lower() == "true"

# ─── Estado global ─────────────────────────────────────────────────
_mem0_instance = None
_mem0_available = False


def _get_mem0():
    """Retorna instancia Mem0 configurada."""
    global _mem0_instance, _mem0_available

    if _mem0_instance is not None:
        return _mem0_instance, None

    try:
        from mem0 import Memory
    except ImportError:
        return None, "Instale: pip install mem0ai"

    config = {}

    # Modo cloud
    if MEM0_API_KEY and MEM0_HOSTED:
        config = {
            "api_key": MEM0_API_KEY,
        }
    # Modo self-hosted
    elif MEM0_URL:
        config = {
            "host": MEM0_URL,
        }
    # Modo local com Qdrant
    else:
        try:
            from qdrant_client import QdrantClient
            qdrant_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "agente_data", "mem0_qdrant"
            )
            os.makedirs(qdrant_path, exist_ok=True)

            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": MEM0_COLLECTION,
                        "path": qdrant_path,
                    }
                }
            }

            # Tenta usar Ollama para embeddings
            try:
                import ollama
                ollama.show("nomic-embed-text")
                config["embedder"] = {
                    "provider": "ollama",
                    "config": {
                        "model": "nomic-embed-text",
                    }
                }
            except Exception:
                pass

            # Tenta usar LLM local via Ollama
            try:
                import ollama
                ollama.show("qwen2.5:7b")
                config["llm"] = {
                    "provider": "ollama",
                    "config": {
                        "model": "qwen2.5:7b",
                    }
                }
            except Exception:
                pass

        except ImportError:
            return None, "Para modo local, instale: pip install qdrant-client"

    try:
        _mem0_instance = Memory.from_config(config)
        _mem0_available = True
        return _mem0_instance, None
    except Exception as e:
        return None, f"Erro ao inicializar Mem0: {e}"


def register(api):
    """Registra ferramentas Mem0 no agente."""

    def mem0_status() -> str:
        """Verifica status do Mem0 (configuracao, modo, disponibilidade)."""
        mem0, err = _get_mem0()
        if err:
            return f"❌ Mem0 indisponivel: {err}"

        mode = "Cloud" if MEM0_API_KEY and MEM0_HOSTED else \
               "Self-hosted" if MEM0_URL else "Local (Qdrant)"

        return (
            f"✅ Mem0 ativo\n"
            f"   Modo: {mode}\n"
            f"   User ID: {MEM0_USER_ID}\n"
            f"   Agent ID: {MEM0_AGENT_ID}\n"
            f"   Collection: {MEM0_COLLECTION}"
        )

    def mem0_add(text: str, user_id: str = "", metadata_json: str = "{}") -> str:
        """Adiciona uma memoria a camada Mem0.
        
        Args:
            text: Texto/conteudo para memorizar
            user_id: ID do usuario (opcional, usa padrao se vazio)
            metadata_json: Metadados em JSON para filtragem posterior
        """
        mem0, err = _get_mem0()
        if err:
            return err

        uid = user_id or MEM0_USER_ID

        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except Exception:
            metadata = {}

        try:
            result = mem0.add(
                text,
                user_id=uid,
                agent_id=MEM0_AGENT_ID,
                metadata=metadata if metadata else None,
                infer=False,  # Extracao controlada pelo agente
            )

            memories_added = 0
            if isinstance(result, dict) and "results" in result:
                memories_added = len(result["results"])
            elif isinstance(result, list):
                memories_added = len(result)

            return f"✅ Memoria adicionada. {memories_added} fatos extraidos e armazenados."

        except Exception as e:
            return f"Erro ao adicionar memoria: {e}"

    def mem0_search(query: str, user_id: str = "", limit: int = 5) -> str:
        """Busca memorias relevantes usando retrieval multi-sinal.
        
        Args:
            query: Pergunta ou termo de busca
            user_id: ID do usuario para filtrar (opcional)
            limit: Maximo de resultados (1-20)
        """
        mem0, err = _get_mem0()
        if err:
            return err

        uid = user_id or MEM0_USER_ID

        try:
            results = mem0.search(
                query,
                user_id=uid,
                agent_id=MEM0_AGENT_ID,
                limit=min(limit, 20),
            )

            if not results:
                return "Nenhuma memoria encontrada."

            memories = []
            if isinstance(results, dict) and "results" in results:
                memories = results["results"]
            elif isinstance(results, list):
                memories = results

            output = [f"**Memorias para:** '{query}'\n"]
            for i, mem in enumerate(memories, 1):
                score = mem.get("score", 0)
                mem_text = mem.get("memory", mem.get("text", ""))
                mem_id = mem.get("id", "")
                created = mem.get("created_at", "")
                updated = mem.get("updated_at", "")

                output.append(f"**{i}.** (score: {score:.2f}) {mem_text[:200]}")
                if mem_id:
                    output.append(f"   ID: {mem_id}")
                if created:
                    output.append(f"   Criado: {created}")
                if updated and updated != created:
                    output.append(f"   Atualizado: {updated}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            return f"Erro na busca Mem0: {e}"

    def mem0_get(memory_id: str) -> str:
        """Recupera uma memoria especifica pelo ID.
        
        Args:
            memory_id: ID da memoria
        """
        mem0, err = _get_mem0()
        if err:
            return err

        try:
            result = mem0.get(memory_id)

            if not result:
                return f"Memoria '{memory_id}' nao encontrada."

            output = [f"**Memoria {memory_id}:**\n"]
            if isinstance(result, dict):
                for key, value in result.items():
                    if key != "id":
                        output.append(f"- **{key}:** {str(value)[:300]}")
            else:
                output.append(str(result))

            return "\n".join(output)

        except Exception as e:
            return f"Erro ao recuperar memoria: {e}"

    def mem0_list(user_id: str = "", limit: int = 20) -> str:
        """Lista todas as memorias armazenadas.
        
        Args:
            user_id: Filtrar por usuario (opcional)
            limit: Maximo de memorias (1-100)
        """
        mem0, err = _get_mem0()
        if err:
            return err

        uid = user_id or MEM0_USER_ID

        try:
            results = mem0.list(
                user_id=uid,
                agent_id=MEM0_AGENT_ID,
                limit=min(limit, 100),
            )

            if not results:
                return "Nenhuma memoria armazenada."

            memories = []
            if isinstance(results, dict) and "results" in results:
                memories = results["results"]
            elif isinstance(results, list):
                memories = results

            output = [f"**{len(memories)} memorias encontradas:**\n"]
            for i, mem in enumerate(memories, 1):
                mem_text = mem.get("memory", mem.get("text", ""))
                mem_id = mem.get("id", "")
                category = mem.get("metadata", {}).get("category", "geral")
                created = mem.get("created_at", "")

                output.append(f"{i}. [{category}] {mem_text[:150]}")
                output.append(f"   ID: {mem_id} | {created}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            return f"Erro ao listar memorias: {e}"

    def mem0_update(memory_id: str, text: str) -> str:
        """Atualiza uma memoria existente.
        
        Args:
            memory_id: ID da memoria para atualizar
            text: Novo conteudo da memoria
        """
        mem0, err = _get_mem0()
        if err:
            return err

        try:
            result = mem0.update(memory_id, text)

            if result:
                return f"✅ Memoria {memory_id} atualizada com sucesso."
            return f"⚠️ Atualizacao retornou resultado vazio para {memory_id}."

        except Exception as e:
            return f"Erro ao atualizar memoria: {e}"

    def mem0_delete(memory_id: str) -> str:
        """Deleta uma memoria especifica.
        
        Args:
            memory_id: ID da memoria para deletar
        """
        mem0, err = _get_mem0()
        if err:
            return err

        try:
            mem0.delete(memory_id)
            return f"✅ Memoria {memory_id} deletada."

        except Exception as e:
            return f"Erro ao deletar memoria: {e}"

    def mem0_delete_all(user_id: str = "") -> str:
        """Deleta todas as memorias de um usuario/agent.
        
        Args:
            user_id: ID do usuario (opcional, usa padrao se vazio)
        """
        mem0, err = _get_mem0()
        if err:
            return err

        uid = user_id or MEM0_USER_ID

        try:
            mem0.delete_all(
                user_id=uid,
                agent_id=MEM0_AGENT_ID,
            )
            return f"✅ Todas as memorias de '{uid}' deletadas."

        except Exception as e:
            return f"Erro ao deletar memorias: {e}"

    def mem0_get_all(user_id: str = "") -> str:
        """Retorna todas as memorias em formato JSON para backup/analise.
        
        Args:
            user_id: Filtrar por usuario (opcional)
        """
        mem0, err = _get_mem0()
        if err:
            return err

        uid = user_id or MEM0_USER_ID

        try:
            results = mem0.get_all(
                user_id=uid,
                agent_id=MEM0_AGENT_ID,
            )

            memories = []
            if isinstance(results, dict) and "results" in results:
                memories = results["results"]
            elif isinstance(results, list):
                memories = results

            return json.dumps(memories, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Erro ao exportar memorias: {e}"

    # ─── Registro das ferramentas ───────────────────────────────────

    api.register_tool("mem0_status", mem0_status,
        "Verifica status do Mem0 (modo, configuracao, disponibilidade).",
        {}, [])

    api.register_tool("mem0_add", mem0_add,
        "Adiciona uma memoria a camada Mem0. Faca o agente armazenar fatos importantes sobre o usuario ou conversas.",
        {
            "text": {"type": "string", "description": "Texto/conteudo para memorizar"},
            "user_id": {"type": "string", "description": "ID do usuario (opcional, usa padrao se vazio)"},
            "metadata_json": {"type": "string", "description": "Metadados em JSON para filtragem (opcional)"},
        }, ["text"])

    api.register_tool("mem0_search", mem0_search,
        "Busca memorias relevantes usando retrieval multi-sinal (semantic + keyword + entity).",
        {
            "query": {"type": "string", "description": "Pergunta ou termo de busca"},
            "user_id": {"type": "string", "description": "ID do usuario para filtrar (opcional)"},
            "limit": {"type": "integer", "description": "Maximo de resultados 1-20 (opcional, padrao: 5)"},
        }, ["query"])

    api.register_tool("mem0_get", mem0_get,
        "Recupera uma memoria especifica pelo ID.",
        {
            "memory_id": {"type": "string", "description": "ID da memoria"},
        }, ["memory_id"])

    api.register_tool("mem0_list", mem0_list,
        "Lista todas as memorias armazenadas de um usuario/agent.",
        {
            "user_id": {"type": "string", "description": "Filtrar por usuario (opcional)"},
            "limit": {"type": "integer", "description": "Maximo 1-100 (opcional, padrao: 20)"},
        }, [])

    api.register_tool("mem0_update", mem0_update,
        "Atualiza uma memoria existente com novo conteudo.",
        {
            "memory_id": {"type": "string", "description": "ID da memoria para atualizar"},
            "text": {"type": "string", "description": "Novo conteudo da memoria"},
        }, ["memory_id", "text"])

    api.register_tool("mem0_delete", mem0_delete,
        "Deleta uma memoria especifica pelo ID.",
        {
            "memory_id": {"type": "string", "description": "ID da memoria para deletar"},
        }, ["memory_id"])

    api.register_tool("mem0_delete_all", mem0_delete_all,
        "Deleta todas as memorias de um usuario/agent.",
        {
            "user_id": {"type": "string", "description": "ID do usuario (opcional)"},
        }, [])

    api.register_tool("mem0_get_all", mem0_get_all,
        "Exporta todas as memorias em JSON (para backup ou analise).",
        {
            "user_id": {"type": "string", "description": "Filtrar por usuario (opcional)"},
        }, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Camada de memoria universal via Mem0: multi-nivel, entity linking, temporal reasoning, token-efficient.",
        "tools": ["mem0_status", "mem0_add", "mem0_search", "mem0_get", "mem0_list", "mem0_update", "mem0_delete", "mem0_delete_all", "mem0_get_all"],
    }
