"""Global memory service for persisting user preferences across conversations.

Implements ChatGPT-style auto-extraction: the LLM automatically identifies and
stores user preferences, facts, and context from conversations.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field


# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MEMORY_MODEL = "anthropic/claude-3-haiku"  # Fast and cheap for extraction


class MemoryItem(BaseModel):
    """A single memory item storing a user fact or preference."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str  # The memory content (e.g., "User prefers concise code examples")
    category: str = Field(default="general")  # e.g., "preference", "fact", "context"
    source_conversation_id: Optional[str] = None  # Which conversation it came from
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    relevance_score: float = Field(default=1.0)  # 0-1, higher = more relevant


class MemoryIndex(BaseModel):
    """Index of all memory items."""

    memories: list[MemoryItem] = Field(default_factory=list)


class MemoryService:
    """Service for managing global memory storage."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize service with data directory.

        Args:
            data_dir: Path to memory directory.
                      Defaults to compose/data/memory/
        """
        if data_dir is None:
            # Default to compose/data/memory relative to this file
            base = Path(__file__).parent.parent / "data" / "memory"
            self.data_dir = base
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"

        # Ensure index exists
        if not self.index_path.exists():
            self._save_index(MemoryIndex())

    def _load_index(self) -> MemoryIndex:
        """Load the memory index."""
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
                return MemoryIndex(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return MemoryIndex()

    def _save_index(self, index: MemoryIndex) -> None:
        """Save the memory index."""
        with open(self.index_path, "w") as f:
            json.dump(index.model_dump(), f, indent=2)

    def list_memories(self, category: Optional[str] = None) -> list[MemoryItem]:
        """List all memories, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of memory items sorted by relevance (highest first)
        """
        index = self._load_index()
        memories = index.memories

        if category:
            memories = [m for m in memories if m.category == category]

        # Sort by relevance score descending
        return sorted(memories, key=lambda m: m.relevance_score, reverse=True)

    def add_memory(
        self,
        content: str,
        category: str = "general",
        source_conversation_id: Optional[str] = None,
        relevance_score: float = 1.0,
    ) -> MemoryItem:
        """Add a new memory item.

        Args:
            content: The memory content
            category: Category (preference, fact, context, general)
            source_conversation_id: Optional conversation ID where this was extracted
            relevance_score: Initial relevance score (0-1)

        Returns:
            The created memory item
        """
        memory = MemoryItem(
            content=content,
            category=category,
            source_conversation_id=source_conversation_id,
            relevance_score=relevance_score,
        )

        index = self._load_index()
        index.memories.append(memory)
        self._save_index(index)

        return memory

    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            The memory or None if not found
        """
        index = self._load_index()
        for memory in index.memories:
            if memory.id == memory_id:
                return memory
        return None

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        category: Optional[str] = None,
        relevance_score: Optional[float] = None,
    ) -> Optional[MemoryItem]:
        """Update a memory item.

        Args:
            memory_id: The memory ID
            content: New content (optional)
            category: New category (optional)
            relevance_score: New relevance score (optional)

        Returns:
            Updated memory or None if not found
        """
        index = self._load_index()
        for i, memory in enumerate(index.memories):
            if memory.id == memory_id:
                if content is not None:
                    memory.content = content
                if category is not None:
                    memory.category = category
                if relevance_score is not None:
                    memory.relevance_score = relevance_score
                memory.updated_at = datetime.now(timezone.utc).isoformat()
                index.memories[i] = memory
                self._save_index(index)
                return memory
        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: The memory ID

        Returns:
            True if deleted, False if not found
        """
        index = self._load_index()
        original_len = len(index.memories)
        index.memories = [m for m in index.memories if m.id != memory_id]

        if len(index.memories) < original_len:
            self._save_index(index)
            return True
        return False

    def clear_all(self) -> int:
        """Clear all memories.

        Returns:
            Number of memories deleted
        """
        index = self._load_index()
        count = len(index.memories)
        index.memories = []
        self._save_index(index)
        return count

    def search_memories(self, query: str) -> list[MemoryItem]:
        """Search memories by content (simple substring match).

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        index = self._load_index()
        matching = [m for m in index.memories if query_lower in m.content.lower()]
        return sorted(matching, key=lambda m: m.relevance_score, reverse=True)

    def get_relevant_memories(self, context: str, limit: int = 5) -> list[MemoryItem]:
        """Get memories relevant to a given context.

        Simple implementation: returns memories that share keywords with context.
        A more sophisticated implementation would use embeddings.

        Args:
            context: The context to match against (e.g., user message)
            limit: Maximum number of memories to return

        Returns:
            List of relevant memories
        """
        # Simple keyword matching (could be replaced with embeddings)
        context_words = set(context.lower().split())
        index = self._load_index()

        scored = []
        for memory in index.memories:
            memory_words = set(memory.content.lower().split())
            overlap = len(context_words & memory_words)
            if overlap > 0:
                # Score based on overlap and original relevance
                score = (overlap / len(memory_words)) * memory.relevance_score
                scored.append((score, memory))

        # Sort by score and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def build_memory_context(self, user_message: str, limit: int = 5) -> str:
        """Build a memory context string for injection into chat.

        Args:
            user_message: The user's message to find relevant memories for
            limit: Maximum memories to include

        Returns:
            Formatted string of relevant memories, or empty string if none
        """
        relevant = self.get_relevant_memories(user_message, limit)
        if not relevant:
            return ""

        lines = ["Here are some things you remember about the user:"]
        for memory in relevant:
            lines.append(f"- {memory.content}")
        return "\n".join(lines)

    async def extract_memories_from_conversation(
        self,
        user_message: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
    ) -> list[MemoryItem]:
        """Auto-extract memories from a conversation turn.

        Uses LLM to identify user preferences, facts, and context worth remembering.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            conversation_id: Optional source conversation ID

        Returns:
            List of extracted memory items (already saved)
        """
        if not OPENROUTER_API_KEY:
            return []

        extraction_prompt = f"""Analyze this conversation turn and extract any user preferences, facts, or context that should be remembered for future conversations. Focus on:
- User preferences (coding style, communication preferences, technical level)
- Important facts about the user (job, projects, tools they use)
- Context that would be useful in future conversations

Conversation:
User: {user_message[:1000]}
Assistant: {assistant_response[:1000]}

Output format: Return a JSON array of objects with "content" and "category" fields.
Categories: "preference", "fact", "context"

If nothing worth remembering, return an empty array: []

Only extract truly useful information. Be concise. Maximum 3 items.

JSON:"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": MEMORY_MODEL,
                        "messages": [{"role": "user", "content": extraction_prompt}],
                        "max_tokens": 300,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                result = data["choices"][0]["message"]["content"].strip()

                # Parse JSON response
                # Handle potential markdown code blocks
                if result.startswith("```"):
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]
                result = result.strip()

                extracted = json.loads(result)
                if not isinstance(extracted, list):
                    return []

                # Save extracted memories
                memories = []
                for item in extracted[:3]:  # Max 3 items
                    if "content" in item:
                        memory = self.add_memory(
                            content=item["content"],
                            category=item.get("category", "general"),
                            source_conversation_id=conversation_id,
                        )
                        memories.append(memory)

                return memories

        except Exception as e:
            print(f"Memory extraction failed: {e}")
            return []


# Singleton instance
_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the memory service singleton."""
    global _service
    if _service is None:
        # Check for container path first, fall back to local
        container_path = Path("/app/src/compose/data/memory")
        if container_path.exists():
            _service = MemoryService(str(container_path))
        else:
            _service = MemoryService()
    return _service
