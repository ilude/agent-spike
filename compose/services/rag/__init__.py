"""RAG (Retrieval Augmented Generation) services.

Provides context retrieval for LLM prompts using SurrealDB vector search.
"""

from .surrealdb_rag import SurrealDBRAG

__all__ = ["SurrealDBRAG"]
