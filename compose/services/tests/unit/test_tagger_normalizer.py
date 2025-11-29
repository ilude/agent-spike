"""Unit tests for TagNormalizer and integration tests.

These tests mock external dependencies and focus on testing the logic
within the normalizer module and integration between components.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from compose.services.tagger.vocabulary import VocabularyManager
from compose.services.tagger.models import StructuredMetadata


# =============================================================================
# TagNormalizer Tests (SurrealDB-based)
# =============================================================================


class TestTagNormalizer:
    """Test cases for TagNormalizer with SurrealDB retriever."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = MagicMock()
        retriever.get_context_tags.return_value = {
            "subject_matter": {"ai-agents"},
            "entities": set(),
            "techniques": {"rag"},
            "tools": {"python"},
            "tags": set(),
        }
        return retriever

    @pytest.fixture
    def mock_vocabulary(self):
        """Create a mock vocabulary."""
        vocab = MagicMock()
        vocab.get_all_tags.return_value = ["ai-agents", "prompt-engineering", "python"]
        return vocab

    @pytest.mark.unit
    def test_configure_ollama_host_for_ollama_model(self, monkeypatch):
        """Test Ollama host configuration for Ollama models."""
        from compose.services.tagger.normalizer import _configure_ollama_host
        import os

        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.setenv("OLLAMA_URL", "http://test-server:11434")

        _configure_ollama_host("ollama:qwen2.5:7b")

        assert "OLLAMA_BASE_URL" in os.environ
        assert "test-server" in os.environ["OLLAMA_BASE_URL"]

    @pytest.mark.unit
    def test_configure_ollama_host_skips_non_ollama(self, monkeypatch):
        """Test Ollama host config is skipped for non-Ollama models."""
        from compose.services.tagger.normalizer import _configure_ollama_host
        import os

        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

        _configure_ollama_host("claude-3-5-haiku-20241022")

        # Should not set OLLAMA_BASE_URL for Claude models
        assert "OLLAMA_BASE_URL" not in os.environ or "192.168" not in os.environ.get(
            "OLLAMA_BASE_URL", ""
        )

    @pytest.mark.unit
    def test_create_normalizer_factory(self, mock_retriever, mock_vocabulary):
        """Test create_normalizer factory function."""
        from compose.services.tagger.normalizer import create_normalizer

        with patch("compose.services.tagger.normalizer.Agent"):
            normalizer = create_normalizer(
                model="test-model",
                retriever=mock_retriever,
                vocabulary=mock_vocabulary,
            )

        assert normalizer.model == "test-model"
        assert normalizer.retriever is mock_retriever
        assert normalizer.vocabulary is mock_vocabulary

    @pytest.mark.unit
    def test_normalizer_phase1_prompt(self):
        """Test Phase 1 prompt content."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent"):
            normalizer = TagNormalizer(model="test")
            prompt = normalizer._get_phase1_prompt()

        assert "expert content analyzer" in prompt.lower()
        assert "subject matter" in prompt.lower()
        assert "json" in prompt.lower()

    @pytest.mark.unit
    def test_normalizer_phase2_prompt(self):
        """Test Phase 2 prompt content."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent"):
            normalizer = TagNormalizer(model="test")
            prompt = normalizer._get_phase2_prompt()

        assert "normalize" in prompt.lower()
        assert "vocabulary" in prompt.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_raw_metadata(self):
        """Test Phase 1 raw metadata extraction."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = json.dumps(
                {
                    "title": "Test Title",
                    "summary": "Test summary",
                    "subject_matter": ["ai-agents"],
                    "entities": {"people": [], "companies": ["Anthropic"]},
                    "techniques_or_concepts": ["rag"],
                    "tools_or_materials": ["python"],
                    "content_style": "tutorial",
                    "difficulty": "intermediate",
                    "key_points": ["Point 1"],
                    "references": [],
                }
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            normalizer = TagNormalizer(model="test")
            normalizer.phase1_agent = mock_agent

            metadata = await normalizer.extract_raw_metadata("Test transcript")

        assert metadata.title == "Test Title"
        assert "ai-agents" in metadata.subject_matter
        assert "Anthropic" in metadata.entities["companies"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_raw_metadata_strips_markdown(self):
        """Test Phase 1 strips markdown code blocks."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = """```json
{
    "title": "Wrapped Title",
    "summary": "Summary",
    "subject_matter": [],
    "entities": {},
    "techniques_or_concepts": [],
    "tools_or_materials": []
}
```"""
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            normalizer = TagNormalizer(model="test")
            normalizer.phase1_agent = mock_agent

            metadata = await normalizer.extract_raw_metadata("Test")

        assert metadata.title == "Wrapped Title"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_normalize_metadata(self, mock_vocabulary):
        """Test Phase 2 normalization."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = json.dumps(
                {
                    "title": "Normalized Title",
                    "summary": "Normalized summary",
                    "subject_matter": ["ai-agents"],
                    "entities": {"companies": ["Anthropic"]},
                    "techniques_or_concepts": ["retrieval-augmented-generation"],
                    "tools_or_materials": ["python"],
                }
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            normalizer = TagNormalizer(model="test")
            normalizer.phase2_agent = mock_agent

            raw_metadata = StructuredMetadata(
                title="Raw Title",
                summary="Raw summary",
                subject_matter=["ai agents"],
                entities={"companies": ["anthropic"]},
                techniques_or_concepts=["rag"],
                tools_or_materials=["python"],
            )

            normalized = await normalizer.normalize_metadata(
                raw_metadata,
                context_tags={"subject_matter": {"ai-agents"}},
                vocabulary_tags=["ai-agents"],
            )

        assert normalized.title == "Normalized Title"
        assert "retrieval-augmented-generation" in normalized.techniques_or_concepts

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_normalize_from_transcript_full_pipeline(
        self, mock_retriever, mock_vocabulary
    ):
        """Test full two-phase pipeline."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()

            # Phase 1 response
            phase1_result = MagicMock()
            phase1_result.output = json.dumps(
                {
                    "title": "Phase 1 Title",
                    "summary": "Phase 1 summary",
                    "subject_matter": ["ai"],
                    "entities": {},
                    "techniques_or_concepts": ["rag"],
                    "tools_or_materials": ["python"],
                }
            )

            # Phase 2 response
            phase2_result = MagicMock()
            phase2_result.output = json.dumps(
                {
                    "title": "Phase 2 Title",
                    "summary": "Phase 2 summary",
                    "subject_matter": ["ai-agents"],
                    "entities": {},
                    "techniques_or_concepts": ["retrieval-augmented-generation"],
                    "tools_or_materials": ["python"],
                }
            )

            mock_agent.run = AsyncMock(side_effect=[phase1_result, phase2_result])
            MockAgent.return_value = mock_agent

            normalizer = TagNormalizer(
                model="test",
                retriever=mock_retriever,
                vocabulary=mock_vocabulary,
            )
            normalizer.phase1_agent = mock_agent
            normalizer.phase2_agent = mock_agent

            result = await normalizer.normalize_from_transcript(
                "Test transcript",
                use_semantic_context=True,
                use_vocabulary=True,
            )

        assert "raw" in result
        assert "normalized" in result
        assert result["raw"].title == "Phase 1 Title"
        assert result["normalized"].title == "Phase 2 Title"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_normalize_from_transcript_without_context(self):
        """Test pipeline without semantic context or vocabulary."""
        from compose.services.tagger.normalizer import TagNormalizer

        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()

            # Both phases return same structure
            mock_result = MagicMock()
            mock_result.output = json.dumps(
                {
                    "title": "Test",
                    "summary": "",
                    "subject_matter": [],
                    "entities": {},
                    "techniques_or_concepts": [],
                    "tools_or_materials": [],
                }
            )

            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            # No retriever or vocabulary
            normalizer = TagNormalizer(model="test")
            normalizer.phase1_agent = mock_agent
            normalizer.phase2_agent = mock_agent

            result = await normalizer.normalize_from_transcript(
                "Test",
                use_semantic_context=False,
                use_vocabulary=False,
            )

        assert "raw" in result
        assert "normalized" in result


# =============================================================================
# Integration-Style Unit Tests (SurrealDB-based)
# =============================================================================


class TestTaggerIntegration:
    """Integration-style tests that test multiple components together."""

    @pytest.mark.unit
    def test_vocabulary_with_retriever_context(self, temp_dir):
        """Test vocabulary tags can be combined with retriever context."""
        from compose.services.tagger.surrealdb_retriever import SemanticTagRetriever

        # Setup vocabulary
        vocab = VocabularyManager()
        vocab.add_tag("ai-agents", count=50, category="concepts")
        vocab.add_tag("prompt-engineering", count=30, category="techniques")

        # Create retriever with temp archive path
        retriever = SemanticTagRetriever(archive_base_path=temp_dir)

        # Setup archive with test data
        youtube_dir = temp_dir / "youtube" / "2025-01"
        youtube_dir.mkdir(parents=True)
        archive_file = youtube_dir / "test123.json"
        archive_file.write_text(json.dumps({
            "video_id": "test123",
            "structured_metadata": {
                "subject_matter": ["ai-agents", "llm"],
            }
        }), encoding="utf-8")

        # Extract tags from archive
        archive_data = retriever.load_archive_metadata("test123")
        tags = retriever.extract_tags_from_archive(archive_data)
        vocab_tags = vocab.get_all_tags()

        # Both should contribute tags
        assert "ai-agents" in tags["subject_matter"]
        assert "ai-agents" in vocab_tags
        assert "prompt-engineering" in vocab_tags

    @pytest.mark.unit
    def test_vocabulary_canonical_form_normalization(self):
        """Test vocabulary provides canonical forms for normalization."""
        vocab = VocabularyManager()
        vocab.add_tag(
            "artificial-intelligence",
            count=100,
            aliases=["ai", "AI", "A.I."],
        )

        # Various forms should resolve to canonical
        assert vocab.get_canonical_form("ai") == "artificial-intelligence"
        assert vocab.get_canonical_form("AI") == "artificial-intelligence"
        assert vocab.get_canonical_form("A.I.") == "artificial-intelligence"
        assert (
            vocab.get_canonical_form("artificial-intelligence")
            == "artificial-intelligence"
        )

    @pytest.mark.unit
    def test_retriever_format_combined_with_vocabulary(self, temp_dir):
        """Test formatting retriever context alongside vocabulary."""
        from compose.services.tagger.surrealdb_retriever import SemanticTagRetriever

        # Create retriever
        retriever = SemanticTagRetriever(archive_base_path=temp_dir)

        # Create vocabulary
        vocab = VocabularyManager()
        vocab.add_tag("ai-agents", count=50)
        vocab.add_tag("prompt-engineering", count=30)

        # Test context formatting
        context = {
            "subject_matter": {"ai-agents", "llm"},
            "entities": {"Anthropic"},
            "techniques": set(),
            "tools": {"python"},
            "tags": set(),
        }

        formatted = retriever.format_context_for_prompt(context)

        # Should include populated categories
        assert "Subject Matter:" in formatted
        assert "ai-agents" in formatted
        assert "Entities:" in formatted
        assert "Anthropic" in formatted
        assert "Tools:" in formatted
        assert "python" in formatted

        # Vocabulary should provide additional context
        vocab_export = vocab.export_for_prompt(top_n=5)
        assert "ai-agents" in vocab_export
