"""Conversation storage service using SurrealDB.

Stores conversations and messages in SurrealDB tables:
- conversation: metadata (id, title, model, created_at, updated_at)
- message: individual messages linked by conversation_id
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from .surrealdb.driver import execute_query

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

    def to_meta(self, message_count: Optional[int] = None) -> ConversationMeta:
        """Convert to metadata for index."""
        return ConversationMeta(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
            message_count=message_count if message_count is not None else len(self.messages),
            model=self.model,
        )


class ConversationService:
    """Service for managing conversation storage in SurrealDB."""

    def __init__(self):
        """Initialize service. No configuration needed - uses SurrealDB config."""
        pass

    async def list_conversations(self) -> list[ConversationMeta]:
        """List all conversations (metadata only).

        Returns conversations sorted by updated_at descending.
        """
        # Get conversations with message count
        query = """
        SELECT
            id,
            title,
            model,
            created_at,
            updated_at,
            (SELECT count() FROM message WHERE conversation_id = $parent.id GROUP ALL)[0].count AS message_count
        FROM conversation
        ORDER BY updated_at DESC;
        """

        results = await execute_query(query)

        conversations = []
        for r in results:
            # Handle SurrealDB record ID format (e.g., "conversation:abc123")
            # RecordID objects need str() conversion first
            conv_id = str(r.get("id", ""))
            if ":" in conv_id:
                conv_id = conv_id.split(":", 1)[1]

            # Handle datetime conversion
            created_at = r.get("created_at", "")
            updated_at = r.get("updated_at", "")
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            if hasattr(updated_at, "isoformat"):
                updated_at = updated_at.isoformat()

            conversations.append(ConversationMeta(
                id=conv_id,
                title=r.get("title", "New conversation"),
                created_at=created_at,
                updated_at=updated_at,
                message_count=r.get("message_count") or 0,
                model=r.get("model") or "",
            ))

        return conversations

    async def create_conversation(
        self, title: str = "New conversation", model: str = ""
    ) -> Conversation:
        """Create a new conversation.

        Args:
            title: Initial title
            model: Model ID being used

        Returns:
            The created conversation
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        query = """
        INSERT INTO conversation {
            id: $id,
            title: $title,
            model: $model,
            created_at: time::now(),
            updated_at: time::now()
        };
        """

        await execute_query(query, {
            "id": conversation_id,
            "title": title,
            "model": model,
        })

        return Conversation(
            id=conversation_id,
            title=title,
            model=model,
            created_at=now,
            updated_at=now,
            messages=[],
        )

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation or None if not found
        """
        # Get conversation metadata
        conv_query = """
        SELECT * FROM conversation WHERE id = $id LIMIT 1;
        """

        conv_results = await execute_query(conv_query, {"id": conversation_id})
        if not conv_results:
            return None

        conv_data = conv_results[0]

        # Handle datetime conversion
        created_at = conv_data.get("created_at", "")
        updated_at = conv_data.get("updated_at", "")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()

        # Get messages for this conversation
        msg_query = """
        SELECT * FROM message WHERE conversation_id = $conversation_id ORDER BY timestamp ASC;
        """

        msg_results = await execute_query(msg_query, {"conversation_id": conversation_id})

        messages = []
        for m in msg_results:
            # Handle message ID format - RecordID objects need str() conversion first
            msg_id = str(m.get("id", ""))
            if ":" in msg_id:
                msg_id = msg_id.split(":", 1)[1]

            # Handle timestamp conversion
            timestamp = m.get("timestamp", "")
            if hasattr(timestamp, "isoformat"):
                timestamp = timestamp.isoformat()

            messages.append(Message(
                id=msg_id,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=timestamp,
                sources=m.get("sources") or [],
            ))

        return Conversation(
            id=conversation_id,
            title=conv_data.get("title", "New conversation"),
            created_at=created_at,
            updated_at=updated_at,
            model=conv_data.get("model") or "",
            messages=messages,
        )

    async def update_conversation(
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
        # Check if conversation exists
        existing = await self.get_conversation(conversation_id)
        if not existing:
            return None

        # Build update query dynamically
        updates = ["updated_at = time::now()"]
        params = {"id": conversation_id}

        if title is not None:
            updates.append("title = $title")
            params["title"] = title
        if model is not None:
            updates.append("model = $model")
            params["model"] = model

        query = f"""
        UPDATE conversation SET {", ".join(updates)} WHERE id = $id;
        """

        await execute_query(query, params)

        # Return updated conversation
        return await self.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted, False if not found
        """
        # Check if conversation exists
        check_query = """
        SELECT id FROM conversation WHERE id = $id LIMIT 1;
        """
        results = await execute_query(check_query, {"id": conversation_id})
        if not results:
            return False

        # Delete messages first (referential integrity)
        msg_query = """
        DELETE FROM message WHERE conversation_id = $conversation_id;
        """
        await execute_query(msg_query, {"conversation_id": conversation_id})

        # Delete conversation
        conv_query = """
        DELETE FROM conversation WHERE id = $id;
        """
        await execute_query(conv_query, {"id": conversation_id})

        return True

    async def add_message(
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
        # Check if conversation exists
        check_query = """
        SELECT id FROM conversation WHERE id = $id LIMIT 1;
        """
        results = await execute_query(check_query, {"id": conversation_id})
        if not results:
            return None

        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Insert message
        msg_query = """
        INSERT INTO message {
            id: $id,
            conversation_id: $conversation_id,
            role: $role,
            content: $content,
            sources: $sources,
            timestamp: time::now()
        };
        """

        await execute_query(msg_query, {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources or [],
        })

        # Update conversation updated_at
        update_query = """
        UPDATE conversation SET updated_at = time::now() WHERE id = $id;
        """
        await execute_query(update_query, {"id": conversation_id})

        return Message(
            id=message_id,
            role=role,
            content=content,
            timestamp=now,
            sources=sources or [],
        )

    async def search_conversations(self, query: str) -> list[ConversationMeta]:
        """Search conversations by title and content.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching conversation metadata
        """
        # Search in conversation titles and message content using CONTAINS
        search_query = """
        SELECT DISTINCT
            c.id AS id,
            c.title AS title,
            c.model AS model,
            c.created_at AS created_at,
            c.updated_at AS updated_at,
            (SELECT count() FROM message WHERE conversation_id = c.id GROUP ALL)[0].count AS message_count
        FROM conversation AS c
        WHERE
            string::lowercase(c.title) CONTAINS string::lowercase($query)
            OR c.id IN (
                SELECT VALUE conversation_id FROM message WHERE string::lowercase(content) CONTAINS string::lowercase($query)
            )
        ORDER BY c.updated_at DESC;
        """

        results = await execute_query(search_query, {"query": query})

        conversations = []
        for r in results:
            # Handle SurrealDB record ID format - RecordID objects need str() conversion first
            conv_id = str(r.get("id", ""))
            if ":" in conv_id:
                conv_id = conv_id.split(":", 1)[1]

            # Handle datetime conversion
            created_at = r.get("created_at", "")
            updated_at = r.get("updated_at", "")
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            if hasattr(updated_at, "isoformat"):
                updated_at = updated_at.isoformat()

            conversations.append(ConversationMeta(
                id=conv_id,
                title=r.get("title", "New conversation"),
                created_at=created_at,
                updated_at=updated_at,
                message_count=r.get("message_count") or 0,
                model=r.get("model") or "",
            ))

        return conversations

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
                title = title.strip('"' + "'")
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
        _service = ConversationService()
    return _service
