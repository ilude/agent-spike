"""Tests for VaultService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from compose.services.vaults import VaultService, Vault, VaultMeta


# ============ Fixtures ============


@pytest.fixture
def mock_execute_query():
    """Mock SurrealDB execute_query function."""
    with patch("compose.services.vaults.execute_query") as mock:
        yield mock


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client instance with all required methods."""
    mock = MagicMock()
    mock.ensure_bucket.return_value = None
    mock.put_text.return_value = "test-vault/notes/test.md"
    mock.get_text.return_value = "# Test Note\n\nContent"
    mock.exists.return_value = True
    mock.delete.return_value = None
    return mock


@pytest.fixture
def vault_service(mock_minio_client):
    """Create VaultService instance with mocked MinIO client."""
    with patch("compose.services.vaults.MinIOClient") as mock_class:
        mock_class.return_value = mock_minio_client
        service = VaultService()
        return service


@pytest.fixture
def sample_vault_record():
    """Sample vault record from SurrealDB."""
    return {
        "id": "vault:test-123",
        "name": "Test Vault",
        "slug": "test-vault-123",
        "storage_type": "minio",
        "minio_bucket": "mentat-vaults",
        "settings": {},
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


# ============ VaultService Tests ============


class TestVaultServiceCreate:
    """Tests for vault creation."""

    @pytest.mark.asyncio
    async def test_create_vault_success(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test successful vault creation."""
        mock_execute_query.return_value = [sample_vault_record]

        vault = await vault_service.create_vault(name="Test Vault")

        assert vault.name == "Test Vault"
        assert vault.storage_type == "minio"
        assert mock_execute_query.called

    @pytest.mark.asyncio
    async def test_create_vault_with_custom_storage(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test vault creation with custom storage type."""
        sample_vault_record["storage_type"] = "local"
        mock_execute_query.return_value = [sample_vault_record]

        vault = await vault_service.create_vault(
            name="Test Vault", storage_type="local"
        )

        assert vault.storage_type == "local"

    @pytest.mark.asyncio
    async def test_create_vault_generates_slug(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test that vault slug is generated from name."""
        mock_execute_query.return_value = [sample_vault_record]

        await vault_service.create_vault(name="My Test Vault!")

        # Check the CREATE query includes a slug
        call_args = mock_execute_query.call_args
        query = call_args[0][0]
        assert "slug" in query


class TestVaultServiceList:
    """Tests for listing vaults."""

    @pytest.mark.asyncio
    async def test_list_vaults_empty(self, vault_service, mock_execute_query):
        """Test listing when no vaults exist."""
        mock_execute_query.return_value = []

        vaults = await vault_service.list_vaults()

        assert vaults == []

    @pytest.mark.asyncio
    async def test_list_vaults_with_results(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test listing vaults returns VaultMeta objects."""
        sample_vault_record["note_count"] = 5
        mock_execute_query.return_value = [sample_vault_record]

        vaults = await vault_service.list_vaults()

        assert len(vaults) == 1
        assert isinstance(vaults[0], VaultMeta)
        assert vaults[0].name == "Test Vault"
        assert vaults[0].note_count == 5

    @pytest.mark.asyncio
    async def test_list_vaults_handles_none_note_count(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test that None note_count is handled."""
        sample_vault_record["note_count"] = None
        mock_execute_query.return_value = [sample_vault_record]

        vaults = await vault_service.list_vaults()

        assert vaults[0].note_count == 0


class TestVaultServiceGet:
    """Tests for getting individual vaults."""

    @pytest.mark.asyncio
    async def test_get_vault_by_id(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test getting vault by ID."""
        mock_execute_query.return_value = [sample_vault_record]

        vault = await vault_service.get_vault("test-123")

        assert vault is not None
        assert vault.name == "Test Vault"

    @pytest.mark.asyncio
    async def test_get_vault_not_found(self, vault_service, mock_execute_query):
        """Test getting non-existent vault."""
        mock_execute_query.return_value = []

        vault = await vault_service.get_vault("non-existent")

        assert vault is None

    @pytest.mark.asyncio
    async def test_get_vault_by_slug(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test getting vault by slug."""
        mock_execute_query.return_value = [sample_vault_record]

        vault = await vault_service.get_vault_by_slug("test-vault-123")

        assert vault is not None
        assert vault.slug == "test-vault-123"


class TestVaultServiceUpdate:
    """Tests for updating vaults."""

    @pytest.mark.asyncio
    async def test_update_vault_name(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test updating vault name."""
        updated_record = {**sample_vault_record, "name": "Updated Name"}
        mock_execute_query.return_value = [updated_record]

        vault = await vault_service.update_vault("test-123", name="Updated Name")

        assert vault is not None
        assert vault.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_vault_settings(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test updating vault settings."""
        new_settings = {"theme": "dark"}
        updated_record = {**sample_vault_record, "settings": new_settings}
        mock_execute_query.return_value = [updated_record]

        vault = await vault_service.update_vault("test-123", settings=new_settings)

        assert vault.settings == new_settings


class TestVaultServiceDelete:
    """Tests for deleting vaults."""

    @pytest.mark.asyncio
    async def test_delete_vault_success(
        self, vault_service, mock_execute_query, sample_vault_record
    ):
        """Test successful vault deletion.

        delete_vault makes 5 execute_query calls:
        1. Check if vault exists
        2. Delete notes in vault
        3. Delete note_links
        4. Delete entities
        5. Delete the vault
        """
        mock_execute_query.side_effect = [
            [sample_vault_record],  # vault exists
            [],  # delete notes
            [],  # delete links
            [],  # delete entities
            [],  # delete vault
        ]

        result = await vault_service.delete_vault("test-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_vault_not_found(self, vault_service, mock_execute_query):
        """Test deleting non-existent vault."""
        mock_execute_query.return_value = []

        result = await vault_service.delete_vault("non-existent")

        assert result is False


class TestVaultServiceFileTree:
    """Tests for file tree operations."""

    @pytest.mark.asyncio
    async def test_get_file_tree_empty(self, vault_service, mock_execute_query):
        """Test file tree for vault with no notes."""
        mock_execute_query.return_value = []

        tree = await vault_service.get_file_tree("test-123")

        assert tree == []

    @pytest.mark.asyncio
    async def test_get_file_tree_flat_files(self, vault_service, mock_execute_query):
        """Test file tree with flat file structure."""
        mock_execute_query.return_value = [
            {"id": "note:1", "path": "note1.md", "title": "Note 1"},
            {"id": "note:2", "path": "note2.md", "title": "Note 2"},
        ]

        tree = await vault_service.get_file_tree("test-123")

        assert len(tree) == 2
        assert tree[0].name == "note1.md"
        assert tree[0].type == "file"

    @pytest.mark.asyncio
    async def test_get_file_tree_nested_folders(self, vault_service, mock_execute_query):
        """Test file tree with nested folder structure."""
        mock_execute_query.return_value = [
            {"id": "note:1", "path": "folder1/note1.md", "title": "Note 1"},
            {"id": "note:2", "path": "folder1/subfolder/note2.md", "title": "Note 2"},
            {"id": "note:3", "path": "note3.md", "title": "Note 3"},
        ]

        tree = await vault_service.get_file_tree("test-123")

        # Should have folder1 and note3.md at root
        assert len(tree) == 2

        # Find the folder
        folder = next((n for n in tree if n.name == "folder1"), None)
        assert folder is not None
        assert folder.type == "folder"
        assert len(folder.children) == 2  # note1.md and subfolder


# ============ MinIO Integration Tests ============


class TestVaultServiceMinIO:
    """Tests for MinIO operations.

    Note: MinIO methods are sync, not async. They take vault_slug and note_path.
    """

    def test_save_note_content(self, vault_service, mock_minio_client):
        """Test saving note content to MinIO."""
        vault_service.save_note_content(
            vault_slug="test-vault",
            note_path="test.md",
            content="# Test\n\nContent"
        )

        mock_minio_client.put_text.assert_called_once()

    def test_get_note_content(self, vault_service, mock_minio_client):
        """Test getting note content from MinIO."""
        mock_minio_client.exists.return_value = True
        mock_minio_client.get_text.return_value = "# Test Note\n\nContent"

        content = vault_service.get_note_content(
            vault_slug="test-vault",
            note_path="test.md"
        )

        assert content == "# Test Note\n\nContent"
        mock_minio_client.get_text.assert_called_once()

    def test_delete_note_content(self, vault_service, mock_minio_client):
        """Test deleting note content from MinIO."""
        mock_minio_client.exists.return_value = True

        vault_service.delete_note_content(
            vault_slug="test-vault",
            note_path="test.md"
        )

        mock_minio_client.delete.assert_called_once()
