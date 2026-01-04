"""Integration tests for AuthService against real SurrealDB.

Tests user CRUD, settings, and invite operations.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from surrealdb import AsyncSurreal


class TestUserCRUDIntegration:
    """Integration tests for user CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, clean_tables: AsyncSurreal):
        """Test creating a user with INSERT syntax."""
        db = clean_tables

        result = await db.query("""
            INSERT INTO users {
                id: $id,
                email: $email,
                password_hash: $password_hash,
                display_name: $display_name,
                role: $role,
                oauth_providers: [],
                email_verified: false,
                created_at: time::now(),
                updated_at: time::now()
            };
        """, {
            "id": "user1",
            "email": "test@example.com",
            "password_hash": "$2b$12$hashedpassword",
            "display_name": "Test User",
            "role": "user",
        })

        assert len(result) > 0
        assert result[0]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, clean_tables: AsyncSurreal):
        """Test retrieving user by ID using record syntax."""
        db = clean_tables

        await db.query("""
            INSERT INTO users {
                id: "gettest",
                email: "get@example.com",
                password_hash: "hash",
                display_name: "Get Test",
                role: "user",
                oauth_providers: [],
                email_verified: false,
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("SELECT * FROM users:`gettest`")

        assert len(result) > 0
        assert result[0]["email"] == "get@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, clean_tables: AsyncSurreal):
        """Test retrieving user by email."""
        db = clean_tables

        await db.query("""
            INSERT INTO users {
                id: "emailtest",
                email: "unique@example.com",
                password_hash: "hash",
                display_name: "Email Test",
                role: "user",
                oauth_providers: [],
                email_verified: false,
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("""
            SELECT * FROM users WHERE email = $email;
        """, {"email": "unique@example.com"})

        assert len(result) > 0
        assert result[0]["display_name"] == "Email Test"

    @pytest.mark.asyncio
    async def test_update_user(self, clean_tables: AsyncSurreal):
        """Test updating user profile."""
        db = clean_tables

        await db.query("""
            INSERT INTO users {
                id: "updatetest",
                email: "update@example.com",
                password_hash: "hash",
                display_name: "Original Name",
                role: "user",
                oauth_providers: [],
                email_verified: false,
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("""
            UPDATE users:`updatetest` SET
                display_name = $display_name,
                updated_at = time::now();
        """, {"display_name": "Updated Name"})

        assert len(result) > 0
        assert result[0]["display_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_last_login(self, clean_tables: AsyncSurreal):
        """Test updating last login timestamp."""
        db = clean_tables

        await db.query("""
            INSERT INTO users {
                id: "logintest",
                email: "login@example.com",
                password_hash: "hash",
                display_name: "Login Test",
                role: "user",
                oauth_providers: [],
                email_verified: false,
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("""
            UPDATE users:`logintest` SET last_login_at = time::now();
        """)

        assert len(result) > 0
        assert result[0]["last_login_at"] is not None

    @pytest.mark.asyncio
    async def test_count_users(self, clean_tables: AsyncSurreal):
        """Test counting users for first-user check."""
        db = clean_tables

        # Initially no users
        count_result = await db.query("SELECT count() FROM users GROUP ALL")
        initial_count = count_result[0].get("count", 0) if count_result else 0
        assert initial_count == 0

        # Add users
        await db.query("""
            INSERT INTO users {
                id: "u1", email: "u1@example.com", password_hash: "h",
                display_name: "U1", role: "admin", oauth_providers: [],
                email_verified: false, created_at: time::now(), updated_at: time::now()
            };
        """)
        await db.query("""
            INSERT INTO users {
                id: "u2", email: "u2@example.com", password_hash: "h",
                display_name: "U2", role: "user", oauth_providers: [],
                email_verified: false, created_at: time::now(), updated_at: time::now()
            };
        """)

        count_result = await db.query("SELECT count() FROM users GROUP ALL")
        assert count_result[0]["count"] == 2

    @pytest.mark.asyncio
    async def test_delete_user(self, clean_tables: AsyncSurreal):
        """Test deleting a user."""
        db = clean_tables

        await db.query("""
            INSERT INTO users {
                id: "deltest", email: "del@example.com", password_hash: "h",
                display_name: "Delete", role: "user", oauth_providers: [],
                email_verified: false, created_at: time::now(), updated_at: time::now()
            };
        """)

        # Verify exists
        before = await db.query("SELECT * FROM users:`deltest`")
        assert len(before) > 0

        # Delete
        await db.query("DELETE users:`deltest`")

        # Verify deleted
        after = await db.query("SELECT * FROM users:`deltest`")
        assert len(after) == 0


class TestUserSettingsIntegration:
    """Integration tests for user settings operations."""

    @pytest.mark.asyncio
    async def test_create_user_settings(self, clean_tables: AsyncSurreal):
        """Test creating default user settings."""
        db = clean_tables

        result = await db.query("""
            INSERT INTO user_settings {
                id: $id,
                user_id: $user_id,
                api_keys: {},
                visible_models: [],
                preferences: {},
                created_at: time::now(),
                updated_at: time::now()
            };
        """, {"id": "settings1", "user_id": "user1"})

        assert len(result) > 0
        assert result[0]["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_get_user_settings(self, clean_tables: AsyncSurreal):
        """Test retrieving user settings by user_id."""
        db = clean_tables

        await db.query("""
            INSERT INTO user_settings {
                id: "getsettings",
                user_id: "getuser",
                api_keys: {"openai": "sk-test"},
                visible_models: ["gpt-4"],
                preferences: {"theme": "dark"},
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("""
            SELECT * FROM user_settings WHERE user_id = $user_id;
        """, {"user_id": "getuser"})

        assert len(result) > 0
        assert result[0]["api_keys"]["openai"] == "sk-test"
        assert "gpt-4" in result[0]["visible_models"]

    @pytest.mark.asyncio
    async def test_update_user_settings(self, clean_tables: AsyncSurreal):
        """Test updating user settings."""
        db = clean_tables

        await db.query("""
            INSERT INTO user_settings {
                id: "updsettings",
                user_id: "upduser",
                api_keys: {},
                visible_models: [],
                preferences: {},
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        result = await db.query("""
            UPDATE user_settings SET
                api_keys = $api_keys,
                visible_models = $visible_models,
                updated_at = time::now()
            WHERE user_id = $user_id;
        """, {
            "user_id": "upduser",
            "api_keys": {"anthropic": "sk-ant-test"},
            "visible_models": ["claude-3-opus", "claude-3-sonnet"],
        })

        assert len(result) > 0
        assert result[0]["api_keys"]["anthropic"] == "sk-ant-test"
        assert len(result[0]["visible_models"]) == 2


class TestInviteIntegration:
    """Integration tests for invite operations."""

    @pytest.mark.asyncio
    async def test_create_invite(self, clean_tables: AsyncSurreal):
        """Test creating an invite."""
        db = clean_tables

        # Note: 'token' is a reserved word in SurrealDB, use 'invite_token' instead
        result = await db.query("""
            INSERT INTO invites {
                id: $id,
                invite_token: $invite_token,
                email: $email,
                created_by: $created_by,
                expires_at: $expires_at,
                created_at: time::now()
            };
        """, {
            "id": "invite1",
            "invite_token": "abc123token",
            "email": "invited@example.com",
            "created_by": "admin1",
            "expires_at": "2025-12-31T00:00:00Z",
        })

        assert len(result) > 0
        assert result[0]["invite_token"] == "abc123token"

    @pytest.mark.asyncio
    async def test_validate_invite_by_token(self, clean_tables: AsyncSurreal):
        """Test retrieving invite by token."""
        db = clean_tables

        # Note: 'token' is a reserved word in SurrealDB, use 'invite_token' instead
        await db.query("""
            INSERT INTO invites {
                id: "validateinvite",
                invite_token: "validatetoken",
                email: NONE,
                created_by: "admin",
                expires_at: "2025-12-31T00:00:00Z",
                created_at: time::now()
            };
        """)

        result = await db.query("""
            SELECT * FROM invites WHERE invite_token = $invite_token;
        """, {"invite_token": "validatetoken"})

        assert len(result) > 0
        assert result[0]["created_by"] == "admin"

    @pytest.mark.asyncio
    async def test_use_invite(self, clean_tables: AsyncSurreal):
        """Test marking invite as used."""
        db = clean_tables

        # Note: 'token' is a reserved word in SurrealDB, use 'invite_token' instead
        await db.query("""
            INSERT INTO invites {
                id: "useinvite",
                invite_token: "usetoken",
                email: NONE,
                created_by: "admin",
                expires_at: "2025-12-31T00:00:00Z",
                created_at: time::now()
            };
        """)

        result = await db.query("""
            UPDATE invites SET
                used_at = time::now(),
                used_by = $user_id
            WHERE invite_token = $invite_token;
        """, {"invite_token": "usetoken", "user_id": "newuser"})

        assert len(result) > 0
        assert result[0]["used_by"] == "newuser"
        assert result[0]["used_at"] is not None
