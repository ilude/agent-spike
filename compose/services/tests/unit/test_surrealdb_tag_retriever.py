"""Unit tests for SurrealDB tag retriever.

Tests tag retrieval using SurrealDB vector search instead of Qdrant.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from compose.services.tagger.surrealdb_retriever import (
    SurrealDBTagRetriever,
    create_surrealdb_retriever,
)


@pytest.fixture
def mock_embedding():
    """Mock embedding vector."""
    return [0.1] * 1024


@pytest.fixture
def mock_search_results():
    """Mock search results from SurrealDB."""
    from compose.services.surrealdb.models import VectorSearchResult

    return [
        VectorSearchResult(
            video_id="vid1",
            title="AI Agents Tutorial",
            url="https://youtube.com/vid1",
            similarity_score=0.95,
            channel_name="AI Channel",
            archive_path="youtube/2024-11/vid1",
        ),
        VectorSearchResult(
            video_id="vid2",
            title="Prompt Engineering",
            url="https://youtube.com/vid2",
            similarity_score=0.85,
            channel_name="ML Channel",
            archive_path="youtube/2024-11/vid2",
        ),
    ]


@pytest.fixture
def mock_archive_metadata():
    """Mock metadata from archive."""
    return {
        "subject_matter": ["ai-agents", "prompt-engineering"],
        "entities": {
            "people": ["Cole Medin"],
            "companies": ["anthropic"],
        },
        "techniques_or_concepts": ["few-shot-prompting", "chain-of-thought"],
        "tools_or_materials": ["claude-api", "langchain"],
        "tags": ["ai", "llm"],
    }


@pytest.mark.unit
def test_create_surrealdb_retriever():
    """Test factory function."""
    retriever = create_surrealdb_retriever(
        infinity_url="http://test:7997",
        infinity_model="test-model",
    )

    assert isinstance(retriever, SurrealDBTagRetriever)
    assert retriever.infinity_url == "http://test:7997"
    assert retriever.infinity_model == "test-model"


@pytest.mark.unit
def test_create_surrealdb_retriever_defaults():
    """Test factory with environment defaults."""
    import os

    os.environ["INFINITY_URL"] = "http://env:7997"

    retriever = create_surrealdb_retriever()

    assert retriever.infinity_url == "http://env:7997"


@pytest.mark.unit
def test_extract_tags_from_metadata(mock_archive_metadata):
    """Test extracting tags from metadata dict."""
    retriever = SurrealDBTagRetriever()

    tags = retriever.extract_tags_from_metadata(mock_archive_metadata)

    assert "ai-agents" in tags["subject_matter"]
    assert "prompt-engineering" in tags["subject_matter"]
    assert "Cole Medin" in tags["entities"]
    assert "anthropic" in tags["entities"]
    assert "few-shot-prompting" in tags["techniques"]
    assert "claude-api" in tags["tools"]
    assert "ai" in tags["tags"]


@pytest.mark.unit
def test_extract_tags_from_metadata_empty():
    """Test extraction with empty metadata."""
    retriever = SurrealDBTagRetriever()

    tags = retriever.extract_tags_from_metadata({})

    assert len(tags["subject_matter"]) == 0
    assert len(tags["entities"]) == 0
    assert len(tags["techniques"]) == 0
    assert len(tags["tools"]) == 0


@pytest.mark.unit
@patch("compose.services.tagger.surrealdb_retriever.get_embedding_sync")
@patch("asyncio.run")
def test_find_similar_content(
    mock_search, mock_embed, mock_embedding, mock_search_results
):
    """Test finding similar content via SurrealDB vector search."""
    # Setup mocks
    mock_embed.return_value = mock_embedding

    # Mock async function
    mock_search.return_value = mock_search_results

    retriever = SurrealDBTagRetriever(infinity_url="http://test:7997")

    results = retriever.find_similar_content("test query", limit=5, min_score=0.5)

    # Verify embedding call
    mock_embed.assert_called_once()
    assert mock_embed.call_args[0][0] == "test query"

    # Verify results
    assert len(results) == 2
    assert results[0]["video_id"] == "vid1"
    assert results[0]["similarity_score"] == 0.95
    assert results[1]["video_id"] == "vid2"


@pytest.mark.unit
@patch("compose.services.tagger.surrealdb_retriever.get_embedding_sync")
@patch("asyncio.run")
def test_find_similar_content_filters_low_scores(
    mock_search, mock_embed, mock_embedding, mock_search_results
):
    """Test that low-scoring results are filtered out."""
    mock_embed.return_value = mock_embedding

    # Mock with one low-score result
    from compose.services.surrealdb.models import VectorSearchResult

    low_score_results = [
        VectorSearchResult(
            video_id="vid1",
            title="High Score",
            url="https://youtube.com/vid1",
            similarity_score=0.95,
            archive_path="youtube/2024-11/vid1",
        ),
        VectorSearchResult(
            video_id="vid2",
            title="Low Score",
            url="https://youtube.com/vid2",
            similarity_score=0.3,  # Below threshold
            archive_path="youtube/2024-11/vid2",
        ),
    ]

    mock_search.return_value = low_score_results

    retriever = SurrealDBTagRetriever()

    results = retriever.find_similar_content("test", limit=5, min_score=0.5)

    # Only high-score result should be returned
    assert len(results) == 1
    assert results[0]["video_id"] == "vid1"


@pytest.mark.unit
@patch("compose.services.tagger.surrealdb_retriever.get_embedding_sync")
@patch("asyncio.run")
def test_find_similar_content_empty_embedding(mock_search, mock_embed):
    """Test handling of empty embedding."""
    mock_embed.return_value = None

    retriever = SurrealDBTagRetriever()

    results = retriever.find_similar_content("test")

    # Should return empty list if embedding fails
    assert len(results) == 0
    mock_search.assert_not_called()


@pytest.mark.unit
def test_format_context_for_prompt():
    """Test formatting tags for LLM prompt."""
    retriever = SurrealDBTagRetriever()

    context_tags = {
        "subject_matter": {"ai-agents", "prompt-engineering", "llm"},
        "entities": {"anthropic", "openai"},
        "techniques": {"few-shot-prompting"},
        "tools": {"claude-api", "langchain"},
        "tags": set(),
    }

    formatted = retriever.format_context_for_prompt(context_tags, top_n_per_category=10)

    assert "Tags from similar content:" in formatted
    assert "Subject Matter:" in formatted
    assert "ai-agents" in formatted
    assert "Entities:" in formatted
    assert "anthropic" in formatted


@pytest.mark.unit
def test_format_context_for_prompt_limits_tags():
    """Test that formatting respects top_n limit."""
    retriever = SurrealDBTagRetriever()

    # Create many tags
    many_tags = {f"tag-{i}" for i in range(20)}

    context_tags = {
        "subject_matter": many_tags,
        "entities": set(),
        "techniques": set(),
        "tools": set(),
        "tags": set(),
    }

    formatted = retriever.format_context_for_prompt(context_tags, top_n_per_category=5)

    # Count number of tag lines (should be 5, not 20)
    tag_lines = [line for line in formatted.split("\n") if line.startswith("  - tag-")]
    assert len(tag_lines) == 5


@pytest.mark.unit
@patch("builtins.open", create=True)
@patch("pathlib.Path.exists")
@patch("compose.services.archive.create_local_archive_writer")
def test_extract_tags_from_archive(
    mock_writer_fn, mock_exists, mock_open, mock_archive_metadata
):
    """Test extracting tags from archive file."""
    import json
    from pathlib import Path

    # Mock file exists
    mock_exists.return_value = True

    # Mock archive writer with config
    mock_config = Mock()
    mock_config.base_dir = Path("/fake/archive")

    mock_writer = Mock()
    mock_writer.config = mock_config
    mock_writer_fn.return_value = mock_writer

    # Mock file open
    mock_file = Mock()
    mock_file.__enter__ = Mock(return_value=mock_file)
    mock_file.__exit__ = Mock(return_value=False)
    mock_file.read = Mock(return_value=json.dumps(mock_archive_metadata))
    mock_open.return_value = mock_file

    retriever = SurrealDBTagRetriever()

    tags = retriever.extract_tags_from_archive("youtube/2024-11/vid1")

    assert "ai-agents" in tags["subject_matter"]
    assert "few-shot-prompting" in tags["techniques"]


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("compose.services.archive.create_local_archive_writer")
def test_extract_tags_from_archive_missing(mock_writer_fn, mock_exists):
    """Test extraction with missing archive file."""
    from pathlib import Path

    # Mock archive writer with config
    mock_config = Mock()
    mock_config.base_dir = Path("/fake/archive")

    mock_writer = Mock()
    mock_writer.config = mock_config
    mock_writer_fn.return_value = mock_writer

    mock_exists.return_value = False

    retriever = SurrealDBTagRetriever()

    tags = retriever.extract_tags_from_archive("youtube/2024-11/missing")

    # Should return empty sets
    assert len(tags["subject_matter"]) == 0
    assert len(tags["techniques"]) == 0


@pytest.mark.unit
def test_extract_tags_from_archive_no_path():
    """Test extraction with None archive path."""
    retriever = SurrealDBTagRetriever()

    tags = retriever.extract_tags_from_archive(None)

    assert len(tags["subject_matter"]) == 0


@pytest.mark.unit
@patch("compose.services.tagger.surrealdb_retriever.get_embedding_sync")
@patch("asyncio.run")
def test_get_formatted_context(mock_search, mock_embed, mock_embedding):
    """Test end-to-end formatted context retrieval."""
    from compose.services.surrealdb.models import VectorSearchResult

    mock_embed.return_value = mock_embedding

    # Mock search results
    results = [
        VectorSearchResult(
            video_id="vid1",
            title="Test",
            url="https://youtube.com/vid1",
            similarity_score=0.95,
            archive_path=None,  # No archive for this test
        )
    ]

    mock_search.return_value = results

    retriever = SurrealDBTagRetriever()

    formatted = retriever.get_formatted_context("test query")

    assert isinstance(formatted, str)
    assert "Tags from similar content:" in formatted
