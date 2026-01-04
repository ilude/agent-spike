"""Integration tests for ConversationService against real SurrealDB.

Tests conversation CRUD, message management, and search queries.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from surrealdb import AsyncSurreal


class TestConversationCRUDIntegration:
    """Integration tests for conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, clean_tables: AsyncSurreal):
        """Test creating a conversation with INSERT syntax."""
        db = clean_tables

        # Create conversation using INSERT (as the service does)
        result = await db.query("""
            INSERT INTO conversation {
                id: $id,
                title: $title,
                model: $model,
                user_id: $user_id,
                created_at: time::now(),
                updated_at: time::now()
            };
        """, {
            "id": "conv1",
            "title": "Test Conversation",
            "model": "claude-3-haiku",
            "user_id": "user1",
        })

        assert len(result) > 0
        assert result[0]["title"] == "Test Conversation"

    @pytest.mark.asyncio
    async def test_get_conversation_by_id(self, clean_tables: AsyncSurreal):
        """Test retrieving conversation using record ID syntax."""
        db = clean_tables

        # Create conversation
        await db.query("""
            INSERT INTO conversation {
                id: "gettest",
                title: "Get Test Conv",
                model: "gpt-4",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Get using record ID syntax (as the service does)
        result = await db.query("SELECT * FROM conversation:`gettest`")

        assert len(result) > 0
        assert result[0]["title"] == "Get Test Conv"

    @pytest.mark.asyncio
    async def test_update_conversation(self, clean_tables: AsyncSurreal):
        """Test updating conversation using record ID syntax."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "updatetest",
                title: "Original Title",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Update using record ID syntax
        result = await db.query("""
            UPDATE conversation:`updatetest` SET
                title = $title,
                updated_at = time::now();
        """, {"title": "Updated Title"})

        assert len(result) > 0
        assert result[0]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, clean_tables: AsyncSurreal):
        """Test deleting conversation using record ID syntax."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "deltest",
                title: "To Delete",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Verify exists
        exists = await db.query("SELECT * FROM conversation:`deltest`")
        assert len(exists) > 0

        # Delete
        await db.query("DELETE conversation:`deltest`")

        # Verify deleted
        after = await db.query("SELECT * FROM conversation:`deltest`")
        assert len(after) == 0


class TestConversationListIntegration:
    """Integration tests for listing conversations."""

    @pytest.mark.asyncio
    async def test_list_conversations_with_message_count(self, clean_tables: AsyncSurreal):
        """Test listing with message count subquery."""
        db = clean_tables

        # Create conversation
        await db.query("""
            INSERT INTO conversation {
                id: "listconv",
                title: "List Test",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Create messages
        await db.query("""
            INSERT INTO message {
                id: "msg1",
                conversation_id: "listconv",
                role: "user",
                content: "Hello",
                timestamp: time::now()
            };
        """)
        await db.query("""
            INSERT INTO message {
                id: "msg2",
                conversation_id: "listconv",
                role: "assistant",
                content: "Hi there!",
                timestamp: time::now()
            };
        """)

        # Query with message count subquery (as the service does)
        # Note: conversation_id in message is stored as string, $parent.id is record reference
        # Need to extract ID from record reference for comparison
        result = await db.query("""
            SELECT
                id,
                title,
                model,
                created_at,
                updated_at,
                count(SELECT * FROM message WHERE conversation_id = record::id($parent.id)) AS message_count
            FROM conversation
            ORDER BY updated_at DESC;
        """)

        assert len(result) == 1
        assert result[0]["title"] == "List Test"
        assert result[0]["message_count"] == 2

    @pytest.mark.asyncio
    async def test_list_conversations_by_user(self, clean_tables: AsyncSurreal):
        """Test listing conversations filtered by user_id."""
        db = clean_tables

        # Create conversations for different users
        await db.query("""
            INSERT INTO conversation {
                id: "user1conv",
                title: "User 1 Conv",
                model: "",
                user_id: "user1",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO conversation {
                id: "user2conv",
                title: "User 2 Conv",
                model: "",
                user_id: "user2",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Query filtered by user
        result = await db.query("""
            SELECT id, title, user_id FROM conversation
            WHERE user_id = $user_id;
        """, {"user_id": "user1"})

        assert len(result) == 1
        assert result[0]["title"] == "User 1 Conv"


class TestMessageIntegration:
    """Integration tests for message operations."""

    @pytest.mark.asyncio
    async def test_add_message(self, clean_tables: AsyncSurreal):
        """Test adding a message to a conversation."""
        db = clean_tables

        # Create conversation first
        await db.query("""
            INSERT INTO conversation {
                id: "msgtest",
                title: "Message Test",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Add message
        result = await db.query("""
            INSERT INTO message {
                id: $id,
                conversation_id: $conversation_id,
                role: $role,
                content: $content,
                sources: $sources,
                timestamp: time::now()
            };
        """, {
            "id": "newmsg",
            "conversation_id": "msgtest",
            "role": "user",
            "content": "Hello world!",
            "sources": [],
        })

        assert len(result) > 0
        assert result[0]["content"] == "Hello world!"

    @pytest.mark.asyncio
    async def test_get_messages_for_conversation(self, clean_tables: AsyncSurreal):
        """Test retrieving messages for a conversation."""
        db = clean_tables

        # Create conversation and messages
        await db.query("""
            INSERT INTO conversation {
                id: "getmsgs",
                title: "Get Messages Test",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO message {
                id: "m1",
                conversation_id: "getmsgs",
                role: "user",
                content: "First message",
                timestamp: time::now()
            };
        """)
        await db.query("""
            INSERT INTO message {
                id: "m2",
                conversation_id: "getmsgs",
                role: "assistant",
                content: "Second message",
                timestamp: time::now()
            };
        """)

        # Get messages (as the service does)
        result = await db.query("""
            SELECT * FROM message
            WHERE conversation_id = $conversation_id
            ORDER BY timestamp ASC;
        """, {"conversation_id": "getmsgs"})

        assert len(result) == 2
        assert result[0]["content"] == "First message"
        assert result[1]["content"] == "Second message"

    @pytest.mark.asyncio
    async def test_delete_messages_cascade(self, clean_tables: AsyncSurreal):
        """Test deleting messages when conversation is deleted."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "cascade",
                title: "Cascade Test",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO message {
                id: "casc1",
                conversation_id: "cascade",
                role: "user",
                content: "Message to delete",
                timestamp: time::now()
            };
        """)

        # Verify message exists
        msgs_before = await db.query("SELECT * FROM message WHERE conversation_id = 'cascade'")
        assert len(msgs_before) == 1

        # Delete messages first (as the service does)
        await db.query("DELETE FROM message WHERE conversation_id = $conversation_id", {"conversation_id": "cascade"})

        # Verify messages deleted
        msgs_after = await db.query("SELECT * FROM message WHERE conversation_id = 'cascade'")
        assert len(msgs_after) == 0


class TestSearchIntegration:
    """Integration tests for search queries."""

    @pytest.mark.asyncio
    async def test_search_by_title(self, clean_tables: AsyncSurreal):
        """Test searching conversations by title."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "searchtitle",
                title: "Python Programming Tips",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO conversation {
                id: "searchother",
                title: "JavaScript Basics",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Search using CONTAINS (as the service does)
        # Note: must include updated_at in SELECT to ORDER BY it
        result = await db.query("""
            SELECT id, title, updated_at FROM conversation
            WHERE string::lowercase(title) CONTAINS string::lowercase($query)
            ORDER BY updated_at DESC;
        """, {"query": "python"})

        assert len(result) == 1
        assert result[0]["title"] == "Python Programming Tips"

    @pytest.mark.asyncio
    async def test_search_by_message_content(self, clean_tables: AsyncSurreal):
        """Test searching by message content."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "searchmsg",
                title: "General Chat",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO message {
                id: "smsg1",
                conversation_id: "searchmsg",
                role: "user",
                content: "How do I use Docker containers?",
                timestamp: time::now()
            };
        """)

        # Search messages
        msgs = await db.query("""
            SELECT conversation_id FROM message
            WHERE string::lowercase(content) CONTAINS string::lowercase($query);
        """, {"query": "docker"})

        assert len(msgs) == 1
        assert msgs[0]["conversation_id"] == "searchmsg"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, clean_tables: AsyncSurreal):
        """Test case-insensitive search."""
        db = clean_tables

        await db.query("""
            INSERT INTO conversation {
                id: "casetest",
                title: "UPPERCASE TITLE",
                model: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Search with lowercase
        result = await db.query("""
            SELECT id, title FROM conversation
            WHERE string::lowercase(title) CONTAINS string::lowercase($query);
        """, {"query": "uppercase"})

        assert len(result) == 1
        assert result[0]["title"] == "UPPERCASE TITLE"
