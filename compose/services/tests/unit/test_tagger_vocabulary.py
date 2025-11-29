"""Unit tests for VocabularyManager.

These tests mock external dependencies and focus on testing the logic
within the vocabulary module.
"""

import json
import pytest
from pathlib import Path

from compose.services.tagger.vocabulary import VocabularyManager, load_vocabulary


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
