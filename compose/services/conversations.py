"""Conversation storage service for persisting chat history.

Stores conversations as JSON files in compose/data/conversations/
with an index.json for fast listing.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field

# Configuration for auto-title generation
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Use a cheap/fast model for title generation
TITLE_MODEL = "anthropic/claude-3-haiku"  # Fast and cheap


class Message(BaseModel):
    """A single message in a conversation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sources: list[dict] = Field(default_factory=list)


class ConversationMeta(BaseModel):
    """Conversation metadata for index listing."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    model: str = ""


class Conversation(BaseModel):
    """Full conversation with messages."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New conversation"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    model: str = ""
    messages: list[Message] = Field(default_factory=list)

    def to_meta(self) -> ConversationMeta:
        """Convert to metadata for index."""
        return ConversationMeta(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
            message_count=len(self.messages),
            model=self.model,
        )


class ConversationIndex(BaseModel):
    """Index of all conversations."""

    conversations: list[ConversationMeta] = Field(default_factory=list)


class ConversationService:
    """Service for managing conversation storage."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize service with data directory.

        Args:
            data_dir: Path to conversations directory.
                      Defaults to compose/data/conversations/
        """
        if data_dir is None:
            # Default to compose/data/conversations relative to this file
            base = Path(__file__).parent.parent / "data" / "conversations"
            self.data_dir = base
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"

        # Ensure index exists
        if not self.index_path.exists():
            self._save_index(ConversationIndex())

    def _load_index(self) -> ConversationIndex:
        """Load the conversation index."""
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
                return ConversationIndex(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return ConversationIndex()

    def _save_index(self, index: ConversationIndex) -> None:
        """Save the conversation index."""
        with open(self.index_path, "w") as f:
            json.dump(index.model_dump(), f, indent=2)

    def _conversation_path(self, conversation_id: str) -> Path:
        """Get path to conversation file."""
        return self.data_dir / f"{conversation_id}.json"

    def list_conversations(self) -> list[ConversationMeta]:
        """List all conversations (metadata only).

        Returns conversations sorted by updated_at descending.
        """
        index = self._load_index()
        # Sort by updated_at descending (most recent first)
        return sorted(
            index.conversations, key=lambda c: c.updated_at, reverse=True
        )

    def create_conversation(
        self, title: str = "New conversation", model: str = ""
    ) -> Conversation:
        """Create a new conversation.

        Args:
            title: Initial title
            model: Model ID being used

        Returns:
            The created conversation
        """
        conversation = Conversation(title=title, model=model)

        # Save conversation file
        with open(self._conversation_path(conversation.id), "w") as f:
            json.dump(conversation.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        index.conversations.append(conversation.to_meta())
        self._save_index(index)

        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation or None if not found
        """
        path = self._conversation_path(conversation_id)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)
                return Conversation(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[Conversation]:
        """Update conversation metadata.

        Args:
            conversation_id: The conversation ID
            title: New title (optional)
            model: New model (optional)

        Returns:
            Updated conversation or None if not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if model is not None:
            conversation.model = model

        conversation.updated_at = datetime.now(timezone.utc).isoformat()

        # Save conversation file
        with open(self._conversation_path(conversation_id), "w") as f:
            json.dump(conversation.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        for i, meta in enumerate(index.conversations):
            if meta.id == conversation_id:
                index.conversations[i] = conversation.to_meta()
                break
        self._save_index(index)

        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted, False if not found
        """
        path = self._conversation_path(conversation_id)
        if not path.exists():
            return False

        # Delete file
        path.unlink()

        # Update index
        index = self._load_index()
        index.conversations = [
            c for c in index.conversations if c.id != conversation_id
        ]
        self._save_index(index)

        return True

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[dict]] = None,
    ) -> Optional[Message]:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation ID
            role: "user" or "assistant"
            content: Message content
            sources: Optional list of sources (for assistant messages)

        Returns:
            The created message or None if conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        message = Message(
            role=role,
            content=content,
            sources=sources or [],
        )

        conversation.messages.append(message)
        conversation.updated_at = datetime.now(timezone.utc).isoformat()

        # Save conversation file
        with open(self._conversation_path(conversation_id), "w") as f:
            json.dump(conversation.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        for i, meta in enumerate(index.conversations):
            if meta.id == conversation_id:
                index.conversations[i] = conversation.to_meta()
                break
        self._save_index(index)

        return message

    def search_conversations(self, query: str) -> list[ConversationMeta]:
        """Search conversations by title and content.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching conversation metadata
        """
        query_lower = query.lower()
        results = []

        index = self._load_index()
        for meta in index.conversations:
            # Check title
            if query_lower in meta.title.lower():
                results.append(meta)
                continue

            # Check message content
            conversation = self.get_conversation(meta.id)
            if conversation:
                for msg in conversation.messages:
                    if query_lower in msg.content.lower():
                        results.append(meta)
                        break

        # Sort by updated_at descending
        return sorted(results, key=lambda c: c.updated_at, reverse=True)

    async def generate_title(self, first_message: str) -> str:
        """Generate a title for a conversation using LLM.

        Args:
            first_message: The first user message in the conversation

        Returns:
            Generated title (3-6 words) or truncated message as fallback
        """
        # Fallback: truncate first message
        fallback = first_message[:50].strip()
        if len(first_message) > 50:
            fallback = fallback.rsplit(" ", 1)[0] + "..."

        if not OPENROUTER_API_KEY:
            return fallback

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": TITLE_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"Generate a very short title (3-6 words) for a conversation that starts with this message. Return ONLY the title, no quotes or explanation:\n\n{first_message[:500]}",
                            }
                        ],
                        "max_tokens": 20,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                title = data["choices"][0]["message"]["content"].strip()
                # Clean up: remove quotes if present
                title = title.strip('"\'')
                # Limit length
                if len(title) > 60:
                    title = title[:57] + "..."
                return title or fallback

        except Exception as e:
            print(f"Title generation failed: {e}")
            return fallback


# Singleton instance
_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get or create the conversation service singleton."""
    global _service
    if _service is None:
        # Check for container path first, fall back to local
        container_path = Path("/app/src/compose/data/conversations")
        if container_path.exists():
            _service = ConversationService(str(container_path))
        else:
            _service = ConversationService()
    return _service
