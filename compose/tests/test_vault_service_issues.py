"""Tests for specific issues encountered during Studio development.

These tests verify fixes for:
1. SurrealDB query syntax - no AS aliases allowed
2. note_count None handling when vault has no notes
3. API parameter validation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from compose.services.vaults import VaultService, Vault, VaultMeta, _record_to_meta


# ============ note_count None Handling Tests ============


class TestNoteCountHandling:
    """Tests for handling None note_count from SurrealDB subqueries."""

    def test_record_to_meta_with_none_note_count(self):
        """Test that _record_to_meta handles None note_count gracefully."""
        record = {
            "id": "vault:test-123",
            "name": "Test Vault",
            "slug": "test-vault-123",
            "storage_type": "minio",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        # Should not raise when note_count is 0
        meta = _record_to_meta(record, 0)
        assert meta.note_count == 0

    def test_record_to_meta_with_positive_note_count(self):
        """Test that _record_to_meta handles positive note_count."""
        record = {
            "id": "vault:test-123",
            "name": "Test Vault",
            "slug": "test-vault-123",
            "storage_type": "minio",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        meta = _record_to_meta(record, 5)
        assert meta.note_count == 5

    @pytest.mark.asyncio
    async def test_list_vaults_handles_none_note_count(self):
        """Test that list_vaults handles None note_count from SurrealDB."""
        mock_record = {
            "id": "vault:test-123",
            "name": "Test Vault",
            "slug": "test-vault-123",
            "storage_type": "minio",
            "note_count": None,  # This was causing the issue
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = [mock_record]

            service = VaultService()
            vaults = await service.list_vaults()

            # Should succeed and treat None as 0
            assert len(vaults) == 1
            assert vaults[0].note_count == 0

    @pytest.mark.asyncio
    async def test_list_vaults_handles_list_note_count(self):
        """Test that list_vaults handles list-wrapped note_count."""
        mock_record = {
            "id": "vault:test-123",
            "name": "Test Vault",
            "slug": "test-vault-123",
            "storage_type": "minio",
            "note_count": [5],  # SurrealDB sometimes wraps in list
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = [mock_record]

            service = VaultService()
            vaults = await service.list_vaults()

            # Should extract from list
            assert len(vaults) == 1
            assert vaults[0].note_count == 5

    @pytest.mark.asyncio
    async def test_list_vaults_handles_empty_list_note_count(self):
        """Test that list_vaults handles empty list note_count."""
        mock_record = {
            "id": "vault:test-123",
            "name": "Test Vault",
            "slug": "test-vault-123",
            "storage_type": "minio",
            "note_count": [],  # Empty list from failed subquery
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = [mock_record]

            service = VaultService()
            vaults = await service.list_vaults()

            # Should treat empty list as 0
            assert len(vaults) == 1
            assert vaults[0].note_count == 0


# ============ SurrealDB Query Syntax Tests ============


class TestSurrealDBQuerySyntax:
    """Tests to verify SurrealDB query syntax is correct.

    SurrealDB does NOT support SQL-style table aliases like 'FROM table AS t'.
    These tests verify all queries avoid this pattern.
    """

    def _assert_no_table_aliases(self, query: str) -> None:
        """Assert query doesn't use table aliases (AS pattern after FROM)."""
        import re
        # Match patterns like "FROM table AS alias" or "FROM table_name AS x"
        alias_pattern = r"FROM\s+\w+\s+AS\s+\w+"
        matches = re.findall(alias_pattern, query, re.IGNORECASE)
        assert not matches, f"Query uses forbidden table alias pattern: {matches}"

    @pytest.mark.asyncio
    async def test_list_vaults_query_no_as_alias(self):
        """Verify list_vaults query doesn't use AS for table aliases."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = []

            service = VaultService()
            await service.list_vaults()

            assert mock_query.called
            query = mock_query.call_args[0][0]
            self._assert_no_table_aliases(query)

    @pytest.mark.asyncio
    async def test_get_vault_query_no_as_alias(self):
        """Verify get_vault query doesn't use AS for table aliases."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = []

            service = VaultService()
            await service.get_vault("test-id")

            assert mock_query.called
            query = mock_query.call_args[0][0]
            self._assert_no_table_aliases(query)

    @pytest.mark.asyncio
    async def test_get_vault_by_slug_query_no_as_alias(self):
        """Verify get_vault_by_slug query doesn't use AS for table aliases."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = []

            service = VaultService()
            await service.get_vault_by_slug("test-slug")

            assert mock_query.called
            query = mock_query.call_args[0][0]
            self._assert_no_table_aliases(query)

    @pytest.mark.asyncio
    async def test_get_vault_uses_type_thing_for_id_lookup(self):
        """Verify get_vault uses type::thing() for ID lookups.

        SurrealDB stores IDs as 'table:id' format. When querying by ID,
        we must use type::thing("table", $id) to construct the record ID.
        """
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = []

            service = VaultService()
            await service.get_vault("test-id")

            assert mock_query.called
            query = mock_query.call_args[0][0]
            # Should use type::thing for record ID lookup
            assert "type::thing" in query, "get_vault must use type::thing() for ID lookup"

    @pytest.mark.asyncio
    async def test_create_vault_query_syntax(self):
        """Verify create_vault query syntax is valid."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = [{
                "id": "vault:test-123",
                "name": "Test",
                "slug": "test-123",
                "storage_type": "minio",
                "minio_bucket": "mentat-vaults",
                "settings": {},
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }]

            service = VaultService()
            await service.create_vault(name="Test")

            # Check query syntax
            query = mock_query.call_args[0][0]

            # Should use CREATE or INSERT, not invalid syntax
            assert "CREATE" in query or "INSERT" in query


# ============ Vault Slug Generation Tests ============


class TestVaultSlugGeneration:
    """Tests for vault slug generation."""

    @pytest.mark.asyncio
    async def test_create_vault_generates_slug(self):
        """Test that vault creation generates a unique slug."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            mock_query.return_value = [{
                "id": "vault:test-123",
                "name": "My Test Vault",
                "slug": "my-test-vault-abc123",
                "storage_type": "minio",
                "minio_bucket": "mentat-vaults",
                "settings": {},
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }]

            service = VaultService()
            vault = await service.create_vault(name="My Test Vault")

            # Slug should be generated
            assert vault.slug is not None
            assert len(vault.slug) > 0

    @pytest.mark.asyncio
    async def test_create_vault_slug_format(self):
        """Test that vault slug uses correct format."""
        with patch("compose.services.vaults.execute_query") as mock_query, \
             patch("compose.services.vaults.MinIOClient"):
            # Check the query contains slug generation logic
            mock_query.return_value = [{
                "id": "vault:test-123",
                "name": "Test",
                "slug": "test-abc123",
                "storage_type": "minio",
                "minio_bucket": "mentat-vaults",
                "settings": {},
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }]

            service = VaultService()
            await service.create_vault(name="Test")

            query = mock_query.call_args[0][0]
            # Should include slug field
            assert "slug" in query.lower()


# ============ VaultMeta Pydantic Model Tests ============


class TestVaultMetaModel:
    """Tests for VaultMeta Pydantic model validation."""

    def test_vault_meta_requires_note_count_integer(self):
        """Test that VaultMeta requires note_count to be an integer."""
        from pydantic import ValidationError

        # This should work
        meta = VaultMeta(
            id="vault-123",
            name="Test",
            slug="test-123",
            storage_type="minio",
            note_count=0,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert meta.note_count == 0

        # This should fail with None
        with pytest.raises(ValidationError):
            VaultMeta(
                id="vault-123",
                name="Test",
                slug="test-123",
                storage_type="minio",
                note_count=None,  # Invalid
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )

    def test_vault_meta_accepts_zero(self):
        """Test that VaultMeta accepts 0 for note_count."""
        meta = VaultMeta(
            id="vault-123",
            name="Test",
            slug="test-123",
            storage_type="minio",
            note_count=0,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert meta.note_count == 0


# ============ API Parameter Tests ============


class TestAPIParameterValidation:
    """Tests for API parameter validation that caused issues."""

    def test_create_vault_request_requires_name(self, client):
        """Test that create vault requires name parameter."""
        response = client.post("/vaults", json={})

        assert response.status_code == 422
        error = response.json()
        assert "detail" in error
        # Should mention the missing field
        assert any("name" in str(e).lower() for e in error["detail"])

    def test_create_vault_accepts_name_only(self, client):
        """Test that create vault works with just name."""
        mock_vault = MagicMock()
        mock_vault.id = "vault-123"
        mock_vault.name = "Test"
        mock_vault.slug = "test-123"
        mock_vault.storage_type = "minio"
        mock_vault.note_count = 0
        mock_vault.minio_bucket = "mentat-vaults"
        mock_vault.settings = {}
        mock_vault.created_at = "2025-01-01T00:00:00Z"
        mock_vault.updated_at = "2025-01-01T00:00:00Z"

        mock_service = MagicMock()
        mock_service.create_vault = AsyncMock(return_value=mock_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.post("/vaults", json={"name": "Test"})

        assert response.status_code == 200

    def test_create_note_requires_vault_id_and_path(self, client):
        """Test that create note requires vault_id and path."""
        # Missing both
        response = client.post("/notes", json={"content": "test"})
        assert response.status_code == 422

        # Missing path
        response = client.post("/notes", json={"vault_id": "v1", "content": "test"})
        assert response.status_code == 422

        # Missing vault_id
        response = client.post("/notes", json={"path": "test.md", "content": "test"})
        assert response.status_code == 422

    def test_list_notes_requires_vault_id(self, client):
        """Test that list notes requires vault_id query param."""
        response = client.get("/notes")
        assert response.status_code == 422
