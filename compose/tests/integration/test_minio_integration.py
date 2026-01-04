"""Integration tests for MinIO operations.

These tests verify MinIO storage operations work correctly
with real object storage.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest

from compose.services.minio.client import MinIOClient


class TestMinIOIntegration:
    """Integration tests for MinIO client operations."""

    def test_put_and_get_text(self, minio_client: MinIOClient):
        """Test storing and retrieving text content."""
        path = "test/note.md"
        content = "# Test Note\n\nThis is test content."

        # Store
        result_path = minio_client.put_text(path, content)
        assert result_path == path

        # Retrieve
        retrieved = minio_client.get_text(path)
        assert retrieved == content

    def test_put_and_get_json(self, minio_client: MinIOClient):
        """Test storing and retrieving JSON content."""
        path = "test/data.json"
        data = {"key": "value", "nested": {"a": 1, "b": 2}}

        # Store
        result_path = minio_client.put_json(path, data)
        assert result_path == path

        # Retrieve
        retrieved = minio_client.get_json(path)
        assert retrieved == data

    def test_exists(self, minio_client: MinIOClient):
        """Test checking object existence."""
        path = "test/exists-check.txt"

        # Should not exist initially
        assert not minio_client.exists(path)

        # Create it
        minio_client.put_text(path, "exists")

        # Should exist now
        assert minio_client.exists(path)

    def test_delete(self, minio_client: MinIOClient):
        """Test deleting objects."""
        path = "test/to-delete.txt"

        # Create
        minio_client.put_text(path, "delete me")
        assert minio_client.exists(path)

        # Delete
        minio_client.delete(path)
        assert not minio_client.exists(path)

    def test_vault_note_path_pattern(self, minio_client: MinIOClient):
        """Test the path pattern used by VaultService for notes."""
        vault_slug = "my-vault"
        note_path = "folder/my-note.md"
        content = "# My Note\n\nContent here."

        # This is the pattern VaultService uses
        minio_path = f"{vault_slug}/notes/{note_path}"

        minio_client.put_text(minio_path, content)
        retrieved = minio_client.get_text(minio_path)

        assert retrieved == content

    def test_nested_paths(self, minio_client: MinIOClient):
        """Test deeply nested paths work correctly."""
        path = "vault/notes/folder/subfolder/deeply/nested/note.md"
        content = "Nested content"

        minio_client.put_text(path, content)
        assert minio_client.exists(path)
        assert minio_client.get_text(path) == content

    def test_unicode_content(self, minio_client: MinIOClient):
        """Test storing content with unicode characters."""
        path = "test/unicode.md"
        content = "# Unicode Test\n\n日本語テスト\nEmoji: 🎉🚀"

        minio_client.put_text(path, content)
        retrieved = minio_client.get_text(path)

        assert retrieved == content

    def test_large_content(self, minio_client: MinIOClient):
        """Test storing larger content."""
        path = "test/large.md"
        # ~100KB of content
        content = "# Large File\n\n" + ("Lorem ipsum dolor sit amet. " * 4000)

        minio_client.put_text(path, content)
        retrieved = minio_client.get_text(path)

        assert retrieved == content
        assert len(retrieved) > 100000
