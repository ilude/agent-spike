"""Unit tests for SemanticTagRetriever.

These tests mock external dependencies and focus on testing the logic
within the retriever module.
"""

import json
import pytest
from pathlib import Path


# =============================================================================
# SemanticTagRetriever Tests (SurrealDB-based)
# =============================================================================


class TestSemanticTagRetriever:
    """Test cases for SurrealDB-based SemanticTagRetriever."""

    @pytest.fixture
    def retriever(self, temp_dir):
        """Create a retriever with temp archive path."""
        from compose.services.tagger.surrealdb_retriever import SemanticTagRetriever
        return SemanticTagRetriever(archive_base_path=temp_dir)

    @pytest.fixture
    def sample_archive_data(self):
        """Sample archive data structure."""
        return {
            "video_id": "test123",
            "youtube_metadata": {
                "tags": ["AI", "Machine Learning", "Tutorial"],
            },
            "llm_outputs": [
                {
                    "output_type": "tags",
                    "output_value": json.dumps({
                        "tags": ["ai-agents", "prompt-engineering"]
                    }),
                }
            ],
            "structured_metadata": {
                "subject_matter": ["ai-agents", "llm"],
                "entities": {
                    "people": ["Sam Altman"],
                    "companies": ["OpenAI", "Anthropic"],
                },
                "techniques_or_concepts": ["rag", "few-shot"],
                "tools_or_materials": ["python", "langchain"],
            },
        }

    @pytest.mark.unit
    def test_init_default_path(self):
        """Test retriever initialization with default path."""
        from compose.services.tagger.surrealdb_retriever import SemanticTagRetriever
        retriever = SemanticTagRetriever()
        assert retriever.archive_base_path.name == "archive"

    @pytest.mark.unit
    def test_init_custom_path(self, temp_dir):
        """Test retriever initialization with custom path."""
        from compose.services.tagger.surrealdb_retriever import SemanticTagRetriever
        retriever = SemanticTagRetriever(archive_base_path=temp_dir)
        assert retriever.archive_base_path == temp_dir

    @pytest.mark.unit
    def test_extract_tags_from_archive_empty(self, retriever):
        """Test extracting tags from empty archive data."""
        result = retriever.extract_tags_from_archive({})

        assert result["subject_matter"] == set()
        assert result["entities"] == set()
        assert result["techniques"] == set()
        assert result["tools"] == set()
        assert result["tags"] == set()

    @pytest.mark.unit
    def test_extract_tags_from_archive_youtube_tags(self, retriever):
        """Test extracting tags from youtube_metadata.tags."""
        archive_data = {
            "youtube_metadata": {
                "tags": ["AI", "Machine Learning", "Tutorial"],
            }
        }

        result = retriever.extract_tags_from_archive(archive_data)

        assert "ai" in result["tags"]
        assert "machine learning" in result["tags"]
        assert "tutorial" in result["tags"]

    @pytest.mark.unit
    def test_extract_tags_from_archive_llm_outputs(self, retriever):
        """Test extracting tags from llm_outputs."""
        archive_data = {
            "llm_outputs": [
                {
                    "output_type": "tags",
                    "output_value": json.dumps({
                        "tags": ["ai-agents", "prompt-engineering"]
                    }),
                }
            ]
        }

        result = retriever.extract_tags_from_archive(archive_data)

        assert "ai-agents" in result["tags"]
        assert "prompt-engineering" in result["tags"]

    @pytest.mark.unit
    def test_extract_tags_from_archive_structured_metadata(self, retriever, sample_archive_data):
        """Test extracting tags from structured_metadata."""
        result = retriever.extract_tags_from_archive(sample_archive_data)

        assert "ai-agents" in result["subject_matter"]
        assert "llm" in result["subject_matter"]
        assert "Sam Altman" in result["entities"]
        assert "OpenAI" in result["entities"]
        assert "rag" in result["techniques"]
        assert "python" in result["tools"]

    @pytest.mark.unit
    def test_extract_tags_from_archive_invalid_llm_json(self, retriever):
        """Test handling invalid JSON in llm_outputs."""
        archive_data = {
            "llm_outputs": [
                {
                    "output_type": "tags",
                    "output_value": "not valid json {",
                }
            ]
        }

        # Should not raise
        result = retriever.extract_tags_from_archive(archive_data)
        assert result["tags"] == set()

    @pytest.mark.unit
    def test_load_archive_metadata_not_found(self, retriever, temp_dir):
        """Test loading archive for non-existent video."""
        # Create youtube directory structure
        youtube_dir = temp_dir / "youtube" / "2025-01"
        youtube_dir.mkdir(parents=True)

        result = retriever.load_archive_metadata("nonexistent")
        assert result is None

    @pytest.mark.unit
    def test_load_archive_metadata_found(self, retriever, temp_dir, sample_archive_data):
        """Test loading archive for existing video."""
        # Create youtube directory structure and file
        youtube_dir = temp_dir / "youtube" / "2025-01"
        youtube_dir.mkdir(parents=True)

        archive_file = youtube_dir / "test123.json"
        archive_file.write_text(json.dumps(sample_archive_data), encoding="utf-8")

        result = retriever.load_archive_metadata("test123")
        assert result is not None
        assert result["video_id"] == "test123"

    @pytest.mark.unit
    def test_format_context_for_prompt_empty(self, retriever):
        """Test formatting empty context."""
        context = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        formatted = retriever.format_context_for_prompt(context)

        assert "Tags from similar content:" in formatted
        # No categories should be listed for empty context
        assert "Subject Matter:" not in formatted

    @pytest.mark.unit
    def test_format_context_for_prompt_with_tags(self, retriever):
        """Test formatting context with tags."""
        context = {
            "subject_matter": {"ai-agents", "prompt-engineering"},
            "entities": set(),
            "techniques": {"rag"},
            "tools": {"python", "langchain"},
            "tags": set(),
        }

        formatted = retriever.format_context_for_prompt(context)

        assert "Tags from similar content:" in formatted
        assert "Subject Matter:" in formatted
        assert "ai-agents" in formatted
        assert "Techniques:" in formatted
        assert "rag" in formatted
        assert "Tools:" in formatted
        assert "python" in formatted
        # Empty categories should not appear
        assert "Entities:" not in formatted

    @pytest.mark.unit
    def test_format_context_for_prompt_limits_tags(self, retriever):
        """Test format_context_for_prompt respects top_n limit."""
        context = {
            "subject_matter": {f"tag{i}" for i in range(20)},
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        formatted = retriever.format_context_for_prompt(context, top_n_per_category=5)

        # Count how many tags appear under Subject Matter
        lines = formatted.split("\n")
        subject_tags = [line for line in lines if line.strip().startswith("- tag")]
        assert len(subject_tags) == 5
