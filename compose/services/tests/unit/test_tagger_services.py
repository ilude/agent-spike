"""Unit tests for tagger services: normalizer, retriever, vocabulary.

These tests mock external dependencies and focus on testing the logic
within each module.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime

from compose.services.tagger.vocabulary import VocabularyManager, load_vocabulary
from compose.services.tagger.retriever import SemanticTagRetriever, create_retriever
from compose.services.tagger.normalizer import (
    TagNormalizer,
    create_normalizer,
    _configure_ollama_host,
)
from compose.services.tagger.models import StructuredMetadata, NormalizedMetadata


# =============================================================================
# VocabularyManager Tests
# =============================================================================


class TestVocabularyManager:
    """Test cases for VocabularyManager."""

    @pytest.mark.unit
    def test_init_empty(self):
        """Test creating an empty vocabulary manager."""
        vocab = VocabularyManager()

        assert vocab.version == "v1"
        assert vocab.total_tags == 0
        assert vocab.seed_tags == {}
        assert vocab.categories == {}
        assert vocab.evolution_history == []

    @pytest.mark.unit
    def test_init_with_nonexistent_path(self, temp_dir):
        """Test creating with a path that doesn't exist yet."""
        path = temp_dir / "nonexistent.json"
        vocab = VocabularyManager(vocabulary_path=path)

        # Should not raise, just start empty
        assert vocab.vocabulary_path == path
        assert vocab.total_tags == 0

    @pytest.mark.unit
    def test_load_missing_file_raises(self, temp_dir):
        """Test load raises FileNotFoundError for missing file."""
        vocab = VocabularyManager()
        vocab.vocabulary_path = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            vocab.load()

    @pytest.mark.unit
    def test_load_valid_vocabulary(self, temp_dir):
        """Test loading a valid vocabulary file."""
        vocab_data = {
            "version": "v2",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "total_tags": 2,
            "seed_tags": {
                "ai-agents": {
                    "canonical_form": "ai-agents",
                    "count": 50,
                    "confidence": 1.0,
                    "aliases": ["ai-agent", "artificial-intelligence-agents"],
                },
                "prompt-engineering": {
                    "canonical_form": "prompt-engineering",
                    "count": 30,
                    "confidence": 1.0,
                    "aliases": ["prompt-eng"],
                },
            },
            "categories": {"techniques": ["prompt-engineering"]},
            "evolution_history": [],
        }

        vocab_path = temp_dir / "vocab.json"
        vocab_path.write_text(json.dumps(vocab_data), encoding="utf-8")

        vocab = VocabularyManager(vocabulary_path=vocab_path)

        assert vocab.version == "v2"
        assert vocab.total_tags == 2
        assert "ai-agents" in vocab.seed_tags
        assert "prompt-engineering" in vocab.seed_tags

    @pytest.mark.unit
    def test_save_creates_directory(self, temp_dir):
        """Test save creates parent directories."""
        vocab = VocabularyManager()
        vocab.add_tag("test-tag", count=5)

        save_path = temp_dir / "nested" / "dir" / "vocab.json"
        vocab.save(path=save_path)

        assert save_path.exists()
        data = json.loads(save_path.read_text(encoding="utf-8"))
        assert "test-tag" in data["seed_tags"]

    @pytest.mark.unit
    def test_save_no_path_raises(self):
        """Test save raises ValueError when no path specified."""
        vocab = VocabularyManager()

        with pytest.raises(ValueError, match="No save path"):
            vocab.save()

    @pytest.mark.unit
    def test_get_canonical_form_exact_match(self):
        """Test canonical form lookup with exact match."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "ai-agents": {
                "canonical_form": "ai-agents",
                "count": 10,
                "aliases": ["ai-agent"],
            }
        }

        assert vocab.get_canonical_form("ai-agents") == "ai-agents"
        assert vocab.get_canonical_form("AI-AGENTS") == "ai-agents"
        assert vocab.get_canonical_form("  ai-agents  ") == "ai-agents"

    @pytest.mark.unit
    def test_get_canonical_form_alias_match(self):
        """Test canonical form lookup via alias."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "ai-agents": {
                "canonical_form": "ai-agents",
                "count": 10,
                "aliases": ["ai-agent", "AI Agents"],
            }
        }

        assert vocab.get_canonical_form("ai-agent") == "ai-agents"
        assert vocab.get_canonical_form("AI Agents") == "ai-agents"

    @pytest.mark.unit
    def test_get_canonical_form_not_found(self):
        """Test canonical form returns original when not found."""
        vocab = VocabularyManager()
        vocab.seed_tags = {}

        assert vocab.get_canonical_form("unknown-tag") == "unknown-tag"

    @pytest.mark.unit
    def test_add_tag_new(self):
        """Test adding a new tag."""
        vocab = VocabularyManager()
        vocab.add_tag("new-tag", count=5, aliases=["newtag"], category="tools")

        assert "new-tag" in vocab.seed_tags
        assert vocab.seed_tags["new-tag"]["count"] == 5
        assert vocab.seed_tags["new-tag"]["canonical_form"] == "new-tag"
        assert "newtag" in vocab.seed_tags["new-tag"]["aliases"]
        assert vocab.total_tags == 1
        assert "new-tag" in vocab.categories["tools"]

    @pytest.mark.unit
    def test_add_tag_update_existing(self):
        """Test updating an existing tag."""
        vocab = VocabularyManager()
        vocab.add_tag("test-tag", count=5, aliases=["test1"])
        vocab.add_tag("test-tag", count=3, aliases=["test2"])

        assert vocab.seed_tags["test-tag"]["count"] == 8
        assert "test1" in vocab.seed_tags["test-tag"]["aliases"]
        assert "test2" in vocab.seed_tags["test-tag"]["aliases"]
        assert vocab.total_tags == 1  # Still just one tag

    @pytest.mark.unit
    def test_add_tag_confidence_calculation(self):
        """Test confidence is calculated correctly (capped at 1.0)."""
        vocab = VocabularyManager()
        vocab.add_tag("low-count", count=3)
        vocab.add_tag("high-count", count=100)

        assert vocab.seed_tags["low-count"]["confidence"] == 0.3  # 3/10
        assert vocab.seed_tags["high-count"]["confidence"] == 1.0  # capped

    @pytest.mark.unit
    def test_consolidate_tags_merge(self):
        """Test consolidating tags merges counts and aliases."""
        vocab = VocabularyManager()
        vocab.add_tag("ai", count=10, aliases=["artificial-intelligence"])
        vocab.add_tag("ai-agents", count=20, aliases=["agents"])

        vocab.consolidate_tags({"ai": "ai-agents"})

        assert "ai" not in vocab.seed_tags
        assert vocab.seed_tags["ai-agents"]["count"] == 30  # 10 + 20
        assert "ai" in vocab.seed_tags["ai-agents"]["aliases"]
        assert len(vocab.evolution_history) == 1
        assert vocab.evolution_history[0]["action"] == "consolidate"

    @pytest.mark.unit
    def test_consolidate_tags_creates_canonical(self):
        """Test consolidating into non-existent canonical creates it."""
        vocab = VocabularyManager()
        vocab.add_tag("ai", count=10, aliases=["AI"])

        vocab.consolidate_tags({"ai": "artificial-intelligence"})

        assert "ai" not in vocab.seed_tags
        assert "artificial-intelligence" in vocab.seed_tags
        assert vocab.seed_tags["artificial-intelligence"]["count"] == 10

    @pytest.mark.unit
    def test_consolidate_tags_skip_same(self):
        """Test consolidating tag to itself is skipped."""
        vocab = VocabularyManager()
        vocab.add_tag("ai-agents", count=10)
        initial_count = vocab.seed_tags["ai-agents"]["count"]

        vocab.consolidate_tags({"ai-agents": "ai-agents"})

        assert vocab.seed_tags["ai-agents"]["count"] == initial_count

    @pytest.mark.unit
    def test_bump_version(self):
        """Test version bumping."""
        vocab = VocabularyManager()
        assert vocab.version == "v1"

        new_version = vocab.bump_version(reason="test bump")

        assert new_version == "v2"
        assert vocab.version == "v2"
        assert len(vocab.evolution_history) == 1
        assert vocab.evolution_history[0]["action"] == "version_bump"
        assert vocab.evolution_history[0]["reason"] == "test bump"

    @pytest.mark.unit
    def test_get_tags_by_category(self):
        """Test getting tags by category."""
        vocab = VocabularyManager()
        vocab.categories = {"tools": ["python", "docker"], "concepts": ["rag"]}

        assert vocab.get_tags_by_category("tools") == ["python", "docker"]
        assert vocab.get_tags_by_category("nonexistent") == []

    @pytest.mark.unit
    def test_get_all_tags(self):
        """Test getting all tags."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "tag1": {"canonical_form": "tag1"},
            "tag2": {"canonical_form": "tag2"},
        }

        all_tags = vocab.get_all_tags()
        assert set(all_tags) == {"tag1", "tag2"}

    @pytest.mark.unit
    def test_get_tag_info(self):
        """Test getting tag info."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "ai-agents": {
                "canonical_form": "ai-agents",
                "count": 50,
                "confidence": 1.0,
            }
        }

        info = vocab.get_tag_info("ai-agents")
        assert info is not None
        assert info["count"] == 50

        assert vocab.get_tag_info("nonexistent") is None

    @pytest.mark.unit
    def test_find_similar_tags(self):
        """Test finding similar tags by substring."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "ai-agents": {},
            "ai-models": {},
            "prompt-engineering": {},
            "agent-tools": {},
        }

        similar = vocab.find_similar_tags("ai")
        assert "ai-agents" in similar
        assert "ai-models" in similar
        assert "prompt-engineering" not in similar

    @pytest.mark.unit
    def test_get_stats(self):
        """Test getting vocabulary statistics."""
        vocab = VocabularyManager()
        vocab.version = "v3"
        vocab.seed_tags = {
            "tag1": {"count": 10},
            "tag2": {"count": 20},
        }
        vocab.categories = {"cat1": [], "cat2": []}
        vocab.evolution_history = [{"action": "test"}]

        stats = vocab.get_stats()

        assert stats["version"] == "v3"
        assert stats["total_tags"] == 2
        assert stats["total_occurrences"] == 30
        assert stats["categories"] == 2
        assert stats["evolution_events"] == 1

    @pytest.mark.unit
    def test_export_for_prompt(self):
        """Test exporting vocabulary for prompt."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "high-count": {"count": 100},
            "low-count": {"count": 5},
            "medium-count": {"count": 50},
        }

        export = vocab.export_for_prompt(top_n=2)

        assert "high-count (100)" in export
        assert "medium-count (50)" in export
        assert "low-count" not in export  # Should be cut off

    @pytest.mark.unit
    def test_export_for_prompt_with_category(self):
        """Test exporting vocabulary for prompt with category filter."""
        vocab = VocabularyManager()
        vocab.seed_tags = {
            "python": {"count": 100},
            "docker": {"count": 50},
            "ai-agents": {"count": 80},
        }
        vocab.categories = {"tools": ["python", "docker"]}

        export = vocab.export_for_prompt(category="tools", top_n=10)

        assert "Category: tools" in export
        assert "python (100)" in export
        assert "docker (50)" in export
        assert "ai-agents" not in export

    @pytest.mark.unit
    def test_load_vocabulary_function(self, temp_dir):
        """Test load_vocabulary helper function."""
        vocab_data = {
            "version": "v1",
            "seed_tags": {"test": {"count": 1}},
            "categories": {},
        }
        vocab_path = temp_dir / "vocab.json"
        vocab_path.write_text(json.dumps(vocab_data), encoding="utf-8")

        vocab = load_vocabulary(vocab_path)

        assert vocab.version == "v1"
        assert "test" in vocab.seed_tags


# =============================================================================
# SemanticTagRetriever Tests
# =============================================================================


class TestSemanticTagRetriever:
    """Test cases for SemanticTagRetriever."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock QdrantCache."""
        cache = MagicMock()
        cache.search = MagicMock(return_value=[])
        return cache

    @pytest.mark.unit
    def test_init(self, mock_cache):
        """Test retriever initialization."""
        retriever = SemanticTagRetriever(cache=mock_cache)
        assert retriever.cache is mock_cache

    @pytest.mark.unit
    def test_find_similar_content_empty(self, mock_cache):
        """Test find_similar_content with no results."""
        mock_cache.search.return_value = []
        retriever = SemanticTagRetriever(cache=mock_cache)

        results = retriever.find_similar_content("test query")

        assert results == []
        mock_cache.search.assert_called_once_with("test query", limit=5)

    @pytest.mark.unit
    def test_find_similar_content_with_score_filtering(self, mock_cache):
        """Test find_similar_content filters by score."""
        result_high = MagicMock()
        result_high.score = 0.8

        result_low = MagicMock()
        result_low.score = 0.3

        mock_cache.search.return_value = [result_high, result_low]
        retriever = SemanticTagRetriever(cache=mock_cache)

        results = retriever.find_similar_content("test", min_score=0.5)

        assert len(results) == 2  # Both returned, filter just tags

    @pytest.mark.unit
    def test_find_similar_content_no_score(self, mock_cache):
        """Test find_similar_content includes results without score."""
        result_no_score = MagicMock(spec=[])  # No score attribute

        mock_cache.search.return_value = [result_no_score]
        retriever = SemanticTagRetriever(cache=mock_cache)

        results = retriever.find_similar_content("test")

        assert len(results) == 1

    @pytest.mark.unit
    def test_extract_tags_from_metadata_structured(self, mock_cache):
        """Test extracting tags from structured metadata."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        metadata = {
            "subject_matter": ["ai-agents", "prompt-engineering"],
            "entities": {
                "people": ["John Doe"],
                "companies": ["Anthropic", "OpenAI"],
            },
            "techniques_or_concepts": ["rag", "few-shot"],
            "tools_or_materials": ["python", "langchain"],
            "tags": ["tutorial", "advanced"],
        }

        extracted = retriever.extract_tags_from_metadata(metadata)

        assert "ai-agents" in extracted["subject_matter"]
        assert "prompt-engineering" in extracted["subject_matter"]
        assert "John Doe" in extracted["entities"]
        assert "Anthropic" in extracted["entities"]
        assert "rag" in extracted["techniques"]
        assert "python" in extracted["tools"]
        assert "tutorial" in extracted["tags"]

    @pytest.mark.unit
    def test_extract_tags_from_metadata_empty(self, mock_cache):
        """Test extracting from empty metadata."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        extracted = retriever.extract_tags_from_metadata({})

        assert all(len(v) == 0 for v in extracted.values())

    @pytest.mark.unit
    def test_extract_tags_from_metadata_non_list_values(self, mock_cache):
        """Test extracting handles non-list values gracefully."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        metadata = {
            "subject_matter": "single-tag",  # String instead of list
            "entities": ["not", "a", "dict"],  # List instead of dict
            "techniques_or_concepts": None,
        }

        extracted = retriever.extract_tags_from_metadata(metadata)

        # Should not crash, just skip invalid formats
        assert extracted["subject_matter"] == set()

    @pytest.mark.unit
    def test_extract_tags_from_result_json_tags(self, mock_cache):
        """Test extracting tags from result with JSON tags string."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        result = {
            "tags": json.dumps({"tags": ["ai", "agents", "tutorial"]}),
        }

        extracted = retriever.extract_tags_from_result(result)

        assert "ai" in extracted["tags"]
        assert "agents" in extracted["tags"]
        assert "tutorial" in extracted["tags"]

    @pytest.mark.unit
    def test_extract_tags_from_result_invalid_json(self, mock_cache):
        """Test extracting handles invalid JSON gracefully."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        result = {"tags": "not valid json {"}

        extracted = retriever.extract_tags_from_result(result)

        # Should not crash
        assert extracted["tags"] == set()

    @pytest.mark.unit
    def test_extract_tags_from_result_metadata_field(self, mock_cache):
        """Test extracting from _metadata field."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        result = {
            "_metadata": {
                "subject_matter": ["ai"],
                "tools_or_materials": ["python"],
            }
        }

        extracted = retriever.extract_tags_from_result(result)

        assert "ai" in extracted["subject_matter"]
        assert "python" in extracted["tools"]

    @pytest.mark.unit
    def test_extract_tags_from_result_meta_fields(self, mock_cache):
        """Test extracting from flattened meta_ fields."""
        retriever = SemanticTagRetriever(cache=mock_cache)

        result = {
            "meta_subject_ai_agents": True,
            "meta_tool_python": True,
            "meta_entity_anthropic": "True",
            "meta_technique_rag": True,
            "meta_subject_inactive": False,  # Should be skipped
        }

        extracted = retriever.extract_tags_from_result(result)

        assert "ai-agents" in extracted["subject_matter"]
        assert "python" in extracted["tools"]
        assert "anthropic" in extracted["entities"]
        assert "rag" in extracted["techniques"]
        assert "inactive" not in extracted["subject_matter"]

    @pytest.mark.unit
    def test_get_context_tags(self, mock_cache):
        """Test aggregating tags from similar content."""
        result1 = {
            "_metadata": {
                "subject_matter": ["ai-agents"],
                "tools_or_materials": ["python"],
            }
        }
        result2 = {
            "_metadata": {
                "subject_matter": ["prompt-engineering"],
                "tools_or_materials": ["python", "langchain"],
            }
        }

        mock_cache.search.return_value = [result1, result2]
        retriever = SemanticTagRetriever(cache=mock_cache)

        context = retriever.get_context_tags("test query", limit=5)

        assert "ai-agents" in context["subject_matter"]
        assert "prompt-engineering" in context["subject_matter"]
        assert "python" in context["tools"]
        assert "langchain" in context["tools"]

    @pytest.mark.unit
    def test_format_context_for_prompt(self, mock_cache):
        """Test formatting context tags for LLM prompt."""
        retriever = SemanticTagRetriever(cache=mock_cache)

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
        # Empty categories should not appear
        assert "Entities:" not in formatted

    @pytest.mark.unit
    def test_format_context_for_prompt_limits_tags(self, mock_cache):
        """Test format_context_for_prompt respects top_n limit."""
        retriever = SemanticTagRetriever(cache=mock_cache)

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
        subject_tags = [l for l in lines if l.strip().startswith("- tag")]
        assert len(subject_tags) == 5

    @pytest.mark.unit
    def test_get_formatted_context(self, mock_cache):
        """Test get_formatted_context combines operations."""
        mock_cache.search.return_value = [
            {"_metadata": {"subject_matter": ["ai"]}}
        ]
        retriever = SemanticTagRetriever(cache=mock_cache)

        formatted = retriever.get_formatted_context("query", limit=3, top_n_per_category=5)

        assert "ai" in formatted
        mock_cache.search.assert_called_once()


# =============================================================================
# TagNormalizer Tests
# =============================================================================


class TestTagNormalizer:
    """Test cases for TagNormalizer."""

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
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.setenv("OLLAMA_URL", "http://test-server:11434")

        import os

        _configure_ollama_host("ollama:qwen2.5:7b")

        assert "OLLAMA_BASE_URL" in os.environ
        assert "test-server" in os.environ["OLLAMA_BASE_URL"]

    @pytest.mark.unit
    def test_configure_ollama_host_skips_non_ollama(self, monkeypatch):
        """Test Ollama host config is skipped for non-Ollama models."""
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

        _configure_ollama_host("claude-3-5-haiku-20241022")

        import os

        # Should not set OLLAMA_BASE_URL for Claude models
        assert "OLLAMA_BASE_URL" not in os.environ or "192.168" not in os.environ.get(
            "OLLAMA_BASE_URL", ""
        )

    @pytest.mark.unit
    def test_create_normalizer_factory(self, mock_retriever, mock_vocabulary):
        """Test create_normalizer factory function."""
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
        with patch("compose.services.tagger.normalizer.Agent"):
            normalizer = TagNormalizer(model="test")
            prompt = normalizer._get_phase1_prompt()

        assert "expert content analyzer" in prompt.lower()
        assert "subject matter" in prompt.lower()
        assert "json" in prompt.lower()

    @pytest.mark.unit
    def test_normalizer_phase2_prompt(self):
        """Test Phase 2 prompt content."""
        with patch("compose.services.tagger.normalizer.Agent"):
            normalizer = TagNormalizer(model="test")
            prompt = normalizer._get_phase2_prompt()

        assert "normalize" in prompt.lower()
        assert "vocabulary" in prompt.lower()
        assert "consolidate" in prompt.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_raw_metadata(self):
        """Test Phase 1 raw metadata extraction."""
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
    async def test_normalize_metadata_handles_capitalized_keys(self, mock_vocabulary):
        """Test Phase 2 handles LLM returning capitalized keys."""
        with patch("compose.services.tagger.normalizer.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            # Simulate LLM returning capitalized keys
            mock_result.output = json.dumps(
                {
                    "Title": "Test Title",
                    "Summary": "Test summary",
                    "Subject Matter": ["ai"],
                    "Entities": {},
                    "Techniques Or Concepts": [],
                    "Tools Or Materials": [],
                }
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            normalizer = TagNormalizer(model="test")
            normalizer.phase2_agent = mock_agent

            raw = StructuredMetadata(
                title="Raw",
                summary="",
                subject_matter=[],
                entities={},
                techniques_or_concepts=[],
                tools_or_materials=[],
            )

            normalized = await normalizer.normalize_metadata(raw)

        assert normalized.title == "Test Title"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_normalize_from_transcript_full_pipeline(
        self, mock_retriever, mock_vocabulary
    ):
        """Test full two-phase pipeline."""
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
# Integration-Style Unit Tests (with mocked dependencies)
# =============================================================================


class TestTaggerIntegration:
    """Integration-style tests that test multiple components together."""

    @pytest.mark.unit
    def test_vocabulary_to_retriever_flow(self, temp_dir):
        """Test vocabulary tags can be used in retriever context."""
        # Setup vocabulary
        vocab = VocabularyManager()
        vocab.add_tag("ai-agents", count=50, category="concepts")
        vocab.add_tag("prompt-engineering", count=30, category="techniques")

        # Mock cache for retriever
        mock_cache = MagicMock()
        mock_cache.search.return_value = [
            {"_metadata": {"subject_matter": ["ai-agents"]}}
        ]

        retriever = SemanticTagRetriever(cache=mock_cache)

        # Get context and combine with vocabulary
        context = retriever.get_context_tags("test query")
        vocab_tags = vocab.get_all_tags()

        # Both should contribute tags
        assert "ai-agents" in context["subject_matter"]
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
