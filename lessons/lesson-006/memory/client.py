"""
Mem0 client wrapper for simplified memory operations.

This module provides a user-friendly wrapper around the Mem0 Memory class,
making it easier to add, search, retrieve, update, and delete memories.
"""

from typing import Any, Optional

from mem0 import Memory

from .config import ensure_api_key


class MemoryClient:
    """
    Wrapper around Mem0 Memory for agent memory management.

    Provides simplified methods for:
    - Adding memories from conversations
    - Searching memories semantically
    - Retrieving all memories for a user
    - Updating existing memories
    - Deleting memories

    Note: Uses Mem0's default configuration with environment variables.
    Requires OPENAI_API_KEY in environment.

    Example:
        ```python
        client = MemoryClient()

        # Add memory
        client.add(
            messages=[
                {"role": "user", "content": "I love action movies"}
            ],
            user_id="alice"
        )

        # Search memory
        memories = client.search("movie preferences", user_id="alice")
        print(memories)  # [{"memory": "User loves action movies", ...}]
        ```
    """

    def __init__(self, top_k: int = 5):
        """
        Initialize memory client.

        Uses Mem0's default configuration:
        - OpenAI gpt-4o-mini for fact extraction
        - OpenAI text-embedding-3-small for embeddings
        - Qdrant vector store at ~/.mem0/qdrant
        - SQLite history at ~/.mem0/history.db

        Args:
            top_k: Default number of memories to retrieve in searches

        Raises:
            ValueError: If OPENAI_API_KEY not found in environment
        """
        ensure_api_key()  # Verify API key exists
        self.top_k = top_k
        self.memory = Memory()  # Use default configuration

    def add(
        self,
        messages: list[dict[str, str]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict:
        """
        Add memories from conversation messages.

        Mem0 will extract relevant facts from the messages and store them.

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (for user-level memory)
            agent_id: Agent identifier (for agent-level memory)
            run_id: Run identifier (for run-level memory)
            metadata: Additional metadata to store

        Returns:
            Dictionary with memory IDs and extracted facts

        Example:
            ```python
            result = client.add(
                messages=[
                    {"role": "user", "content": "I prefer tech content"},
                    {"role": "assistant", "content": "Got it! I'll recommend tech videos."}
                ],
                user_id="alice",
                metadata={"source": "youtube_tagging"}
            )
            print(result)  # {"memories": [...], "message": "..."}
            ```
        """
        return self.memory.add(
            messages=messages,
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            metadata=metadata,
        )

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Search memories semantically.

        Args:
            query: Search query (semantic, not exact match)
            user_id: Filter by user ID
            agent_id: Filter by agent ID
            run_id: Filter by run ID
            limit: Maximum number of results (default: top_k from init)

        Returns:
            List of memory dicts with 'memory' text and relevance scores

        Example:
            ```python
            memories = client.search(
                query="user's content preferences",
                user_id="alice",
                limit=3
            )
            for mem in memories:
                print(f"{mem['memory']} (score: {mem.get('score', 'N/A')})")
            ```
        """
        limit = limit or self.top_k
        return self.memory.search(
            query=query,
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            limit=limit,
        )

    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Get all memories for a user/agent/run.

        Args:
            user_id: Filter by user ID
            agent_id: Filter by agent ID
            run_id: Filter by run ID

        Returns:
            List of all memory dicts

        Example:
            ```python
            all_memories = client.get_all(user_id="alice")
            print(f"Total memories: {len(all_memories)}")
            ```
        """
        return self.memory.get_all(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
        )

    def update(self, memory_id: str, data: str) -> dict:
        """
        Update an existing memory.

        Args:
            memory_id: ID of memory to update
            data: New memory content

        Returns:
            Updated memory dict

        Example:
            ```python
            updated = client.update(
                memory_id="mem_123abc",
                data="User prefers action and sci-fi movies"
            )
            ```
        """
        return self.memory.update(memory_id=memory_id, data=data)

    def delete(self, memory_id: str) -> dict:
        """
        Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            Deletion confirmation dict

        Example:
            ```python
            result = client.delete(memory_id="mem_123abc")
            print(result)  # {"message": "Memory deleted successfully"}
            ```
        """
        return self.memory.delete(memory_id=memory_id)

    def delete_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> dict:
        """
        Delete all memories for a user/agent/run.

        Args:
            user_id: Delete all memories for this user
            agent_id: Delete all memories for this agent
            run_id: Delete all memories for this run

        Returns:
            Deletion confirmation dict

        Example:
            ```python
            result = client.delete_all(user_id="alice")
            print(result)  # {"message": "All memories deleted"}
            ```
        """
        return self.memory.delete_all(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
        )

    def format_memories_for_prompt(self, memories: list[dict]) -> str:
        """
        Format memories for inclusion in system prompts.

        Args:
            memories: List of memory dicts from search() or get_all()

        Returns:
            Formatted string suitable for system prompts

        Example:
            ```python
            memories = client.search("preferences", user_id="alice")
            context = client.format_memories_for_prompt(memories)

            system_prompt = f\"""
            You are a helpful assistant.

            <user_memory>
            {context}
            </user_memory>
            \"""
            ```
        """
        if not memories:
            return "No previous memories found."

        formatted = []
        for i, mem in enumerate(memories, 1):
            memory_text = mem.get("memory", "")
            score = mem.get("score", "N/A")
            formatted.append(f"{i}. {memory_text} (relevance: {score})")

        return "\n".join(formatted)
