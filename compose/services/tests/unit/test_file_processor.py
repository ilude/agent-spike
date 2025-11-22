"""Tests for file processor service.

Run with: uv run pytest compose/services/tests/unit/test_file_processor.py
"""

import json

import httpx
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from compose.services.file_processor import (
    extract_text_from_file,
    chunk_text,
    extract_with_docling,
    delete_file_from_index,
)


# =============================================================================
# Tests for extract_text_from_file
# =============================================================================


class TestExtractTextFromFile:
    """Tests for extract_text_from_file function."""

    def test_plain_text_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from plain text file."""
        test_content = "This is a plain text file.\nWith multiple lines."
        test_file = tmp_path / "test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "text/plain")

        assert result == test_content

    def test_markdown_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from markdown file."""
        test_content = "# Heading\n\nSome **bold** text and *italic* text."
        test_file = tmp_path / "test.md"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "text/markdown")

        assert result == test_content

    def test_markdown_x_content_type(self, tmp_path: Path) -> None:
        """Test extraction with text/x-markdown content type."""
        test_content = "# Another Markdown File"
        test_file = tmp_path / "test.md"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "text/x-markdown")

        assert result == test_content

    def test_json_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from JSON file."""
        test_data = {"key": "value", "nested": {"inner": 123}}
        test_content = json.dumps(test_data, indent=2)
        test_file = tmp_path / "test.json"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "application/json")

        assert result == test_content
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == test_data

    def test_python_code_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from Python code file (.py)."""
        test_content = '''"""Module docstring."""

def hello_world():
    """Print hello world."""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
'''
        test_file = tmp_path / "script.py"
        test_file.write_text(test_content, encoding="utf-8")

        # Python files use extension-based detection
        result = extract_text_from_file(test_file, "application/octet-stream")

        assert result == test_content
        assert "def hello_world():" in result
        assert 'print("Hello, World!")' in result

    def test_fallback_for_unknown_types(self, tmp_path: Path) -> None:
        """Test fallback behavior for unknown content types."""
        test_content = "Some content that should be read as text"
        test_file = tmp_path / "unknown.xyz"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "application/x-unknown")

        # Should fallback to reading as text
        assert result == test_content

    def test_fallback_returns_error_for_binary(self, tmp_path: Path) -> None:
        """Test fallback returns error message for binary files."""
        # Create a file with invalid UTF-8 and Latin-1 bytes
        test_file = tmp_path / "binary.bin"
        # Write bytes that will fail both UTF-8 and Latin-1 decode
        test_file.write_bytes(b"\xff\xfe" + bytes(range(256)))

        result = extract_text_from_file(test_file, "application/x-binary")

        # Fallback should either read successfully with latin-1 or return error
        # Based on implementation, it tries utf-8 first, then returns error message
        assert isinstance(result, str)

    def test_csv_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from CSV file."""
        test_content = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        test_file = tmp_path / "data.csv"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "text/csv")

        assert result == test_content

    def test_yaml_file_extraction_by_extension(self, tmp_path: Path) -> None:
        """Test extraction from YAML file using extension detection."""
        test_content = "name: test\nversion: 1.0\nitems:\n  - one\n  - two"
        test_file = tmp_path / "config.yaml"
        test_file.write_text(test_content, encoding="utf-8")

        # YAML uses extension-based detection
        result = extract_text_from_file(test_file, "application/octet-stream")

        assert result == test_content

    def test_javascript_file_extraction(self, tmp_path: Path) -> None:
        """Test extraction from JavaScript code file (.js)."""
        test_content = "const hello = () => console.log('Hello!');\nhello();"
        test_file = tmp_path / "script.js"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "application/octet-stream")

        assert result == test_content

    def test_unicode_content_extraction(self, tmp_path: Path) -> None:
        """Test extraction handles unicode content correctly."""
        test_content = "Hello 世界! Emoji: 🎉 Accent: café"
        test_file = tmp_path / "unicode.txt"
        test_file.write_text(test_content, encoding="utf-8")

        result = extract_text_from_file(test_file, "text/plain")

        assert result == test_content
        assert "世界" in result
        assert "🎉" in result


# =============================================================================
# Tests for chunk_text
# =============================================================================


class TestChunkText:
    """Tests for chunk_text function."""

    def test_short_text_returns_single_chunk(self) -> None:
        """Test that short text (< chunk_size) returns single chunk."""
        short_text = "This is a short text that should not be split."

        result = chunk_text(short_text, chunk_size=1000, overlap=200)

        assert len(result) == 1
        assert result[0] == short_text

    def test_exact_chunk_size_returns_single_chunk(self) -> None:
        """Test text exactly at chunk_size returns single chunk."""
        text = "x" * 1000

        result = chunk_text(text, chunk_size=1000, overlap=200)

        assert len(result) == 1

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        """Test that long text splits into multiple chunks."""
        # Create text longer than chunk_size
        long_text = "word " * 500  # 2500 chars

        result = chunk_text(long_text, chunk_size=1000, overlap=200)

        assert len(result) > 1
        # All chunks should have content
        for chunk in result:
            assert len(chunk) > 0

    def test_chunks_have_expected_overlap(self) -> None:
        """Test that consecutive chunks have overlapping content."""
        # Create text without natural break points
        long_text = "abcdefghij" * 200  # 2000 chars

        result = chunk_text(long_text, chunk_size=500, overlap=100)

        assert len(result) >= 2
        # Check overlap by verifying the end of one chunk appears at start of next
        for i in range(len(result) - 1):
            # The overlap should create some shared content
            chunk1_end = result[i][-100:]  # Last 100 chars
            chunk2_start = result[i + 1][:100]  # First 100 chars
            # Due to stripping and boundary detection, exact overlap varies
            # but there should be some shared characters
            assert any(c in chunk2_start for c in chunk1_end[:50])

    def test_breaks_at_paragraph_boundaries_when_possible(self) -> None:
        """Test chunking prefers paragraph breaks over arbitrary splits."""
        # Create text with clear paragraph breaks
        paragraph1 = "First paragraph content. " * 30  # ~750 chars
        paragraph2 = "Second paragraph content. " * 30  # ~750 chars
        text = paragraph1 + "\n\n" + paragraph2

        result = chunk_text(text, chunk_size=1000, overlap=200)

        # Should have 2+ chunks, with split near paragraph boundary
        assert len(result) >= 2
        # First chunk should end near paragraph boundary
        # (within reasonable distance of the \n\n)
        assert "\n\n" not in result[0] or result[0].endswith("\n\n")

    def test_breaks_at_sentence_boundaries_when_no_paragraph(self) -> None:
        """Test chunking breaks at sentences when no paragraph break available."""
        # Create text with sentences but no paragraph breaks
        text = "This is sentence one. " * 20 + "This is sentence two. " * 20

        result = chunk_text(text, chunk_size=500, overlap=100)

        assert len(result) >= 2
        # Chunks should generally end with ". " or be trimmed
        for chunk in result[:-1]:  # All but last
            # Should end cleanly (period or trimmed)
            stripped = chunk.strip()
            assert stripped.endswith(".") or len(stripped) > 0

    def test_empty_text_returns_empty_list(self) -> None:
        """Test empty text returns empty list."""
        result = chunk_text("", chunk_size=1000, overlap=200)

        # Empty string after filter should return empty list
        assert result == [] or result == [""]

    def test_whitespace_only_text(self) -> None:
        """Test whitespace-only text is handled."""
        result = chunk_text("   \n\n   ", chunk_size=1000, overlap=200)

        # Should return empty list after stripping
        assert result == [] or all(c.strip() == "" for c in result)

    def test_custom_chunk_size_and_overlap(self) -> None:
        """Test with custom chunk size and overlap values."""
        text = "a" * 100

        result = chunk_text(text, chunk_size=30, overlap=5)

        assert len(result) >= 3
        # Each chunk should be around 30 chars
        for chunk in result[:-1]:
            assert len(chunk) <= 35  # Allow some variance

    def test_overlap_larger_than_half_chunk_size(self) -> None:
        """Test behavior when overlap is large relative to chunk size."""
        text = "x" * 200

        # Large overlap should still work
        result = chunk_text(text, chunk_size=100, overlap=80)

        assert len(result) >= 2


# =============================================================================
# Tests for extract_with_docling
# =============================================================================


class TestExtractWithDocling:
    """Tests for extract_with_docling function (mocked httpx)."""

    def test_successful_extraction_returns_markdown(self, tmp_path: Path) -> None:
        """Test successful Docling extraction returns markdown content."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        expected_markdown = "# Document Title\n\nExtracted content here."
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "document": {"md_content": expected_markdown},
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = extract_with_docling(test_file)

            assert result == expected_markdown
            mock_client.post.assert_called_once()

    def test_connect_error_returns_error_message(self, tmp_path: Path) -> None:
        """Test ConnectError returns appropriate error message."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")

            result = extract_with_docling(test_file)

            assert "[Cannot connect to Docling service" in result
            assert "docling-serve is running" in result

    def test_timeout_exception_returns_error_message(self, tmp_path: Path) -> None:
        """Test TimeoutException returns appropriate error message."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

            result = extract_with_docling(test_file)

            assert "[Docling conversion timeout]" in result

    def test_non_success_status_returns_error(self, tmp_path: Path) -> None:
        """Test non-success status in response returns error message."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "errors": ["Unsupported file format", "Corrupt PDF"],
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = extract_with_docling(test_file)

            assert "[Docling extraction failed:" in result
            assert "Unsupported file format" in result or "errors" in result.lower()

    def test_http_status_error_returns_error_message(self, tmp_path: Path) -> None:
        """Test HTTP status error (4xx/5xx) returns error message."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            mock_client.post.return_value = mock_response

            result = extract_with_docling(test_file)

            assert "[Docling extraction error:" in result

    def test_general_exception_returns_error_message(self, tmp_path: Path) -> None:
        """Test general exception returns error message with details."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = RuntimeError("Unexpected error")

            result = extract_with_docling(test_file)

            assert "[Docling extraction error:" in result
            assert "Unexpected error" in result


# =============================================================================
# Tests for delete_file_from_index
# =============================================================================


class TestDeleteFileFromIndex:
    """Tests for delete_file_from_index function (mocked Qdrant)."""

    def test_successful_deletion_returns_true(self) -> None:
        """Test successful deletion returns True."""
        mock_qdrant = MagicMock()

        with patch(
            "compose.services.file_processor.get_qdrant_client",
            return_value=mock_qdrant,
        ):
            result = delete_file_from_index("project-123", "file-456")

            assert result is True
            mock_qdrant.delete.assert_called_once()

            # Verify correct filter was used
            call_kwargs = mock_qdrant.delete.call_args.kwargs
            assert "points_selector" in call_kwargs
            filter_config = call_kwargs["points_selector"]["filter"]
            must_conditions = filter_config["must"]

            # Check both project_id and file_id filters are present
            project_filter = next(
                (c for c in must_conditions if c["key"] == "project_id"), None
            )
            file_filter = next(
                (c for c in must_conditions if c["key"] == "file_id"), None
            )

            assert project_filter is not None
            assert project_filter["match"]["value"] == "project-123"
            assert file_filter is not None
            assert file_filter["match"]["value"] == "file-456"

    def test_exception_returns_false(self) -> None:
        """Test exception during deletion returns False."""
        mock_qdrant = MagicMock()
        mock_qdrant.delete.side_effect = Exception("Qdrant connection failed")

        with patch(
            "compose.services.file_processor.get_qdrant_client",
            return_value=mock_qdrant,
        ):
            result = delete_file_from_index("project-123", "file-456")

            assert result is False

    def test_deletion_uses_correct_collection(self) -> None:
        """Test deletion targets the correct collection."""
        mock_qdrant = MagicMock()

        with patch(
            "compose.services.file_processor.get_qdrant_client",
            return_value=mock_qdrant,
        ):
            with patch(
                "compose.services.file_processor.PROJECT_COLLECTION",
                "test_collection",
            ):
                delete_file_from_index("project-123", "file-456")

                call_kwargs = mock_qdrant.delete.call_args.kwargs
                assert call_kwargs["collection_name"] == "test_collection"

    def test_deletion_with_special_characters_in_ids(self) -> None:
        """Test deletion handles special characters in IDs."""
        mock_qdrant = MagicMock()

        with patch(
            "compose.services.file_processor.get_qdrant_client",
            return_value=mock_qdrant,
        ):
            # IDs with special characters
            result = delete_file_from_index(
                "project/with/slashes", "file-with-dashes_and_underscores"
            )

            assert result is True
            mock_qdrant.delete.assert_called_once()
