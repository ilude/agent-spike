"""Integration test for two-phase tag normalizer using Ollama.

Requires remote services:
- Ollama: http://192.168.16.241:11434 (qwen2.5:7b model)
- Qdrant: http://192.168.16.241:6333 (for semantic context)
- Infinity: http://192.168.16.241:7997 (for embeddings)

Run with: uv run pytest compose/services/tests/integration/test_tagger_normalizer.py -v -s
"""

import asyncio
from pathlib import Path

import pytest

from compose.services.tagger import (
    create_normalizer,
    create_retriever,
    VocabularyManager,
)


# Sample transcript for testing
SAMPLE_TRANSCRIPT = """
In this video, we'll explore how to build AI agents using Claude and the Anthropic API.
We'll cover prompt engineering techniques, including few-shot prompting and chain-of-thought reasoning.
You'll learn how to use LangChain to orchestrate multiple agents, and we'll implement
retrieval augmented generation (RAG) using a vector database like Qdrant or Pinecone.
This is an intermediate tutorial for developers who want to build production AI systems.
"""


@pytest.fixture
def vocabulary():
    """Load vocabulary from lesson-010 data."""
    # Path from repo root
    vocab_path = Path(__file__).parent.parent.parent.parent.parent / "lessons" / "lesson-010" / "data" / "seed_vocabulary_v1.json"

    if not vocab_path.exists():
        pytest.skip(f"Vocabulary file not found: {vocab_path}")

    vocab = VocabularyManager(vocab_path)
    vocab.load()
    return vocab


@pytest.fixture
def retriever(qdrant_url, infinity_url, collection_name):
    """Create retriever using remote services."""
    return create_retriever(
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        infinity_url=infinity_url
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_normalizer_extract_raw_metadata(ollama_url):
    """Test Phase 1: Raw metadata extraction using Ollama."""
    import os
    os.environ["OLLAMA_URL"] = ollama_url

    normalizer = create_normalizer(model="ollama:qwen2.5:7b")

    print("\n=== Phase 1: Raw Extraction ===")
    raw = await normalizer.extract_raw_metadata(SAMPLE_TRANSCRIPT)

    print(f"Title: {raw.title}")
    print(f"Summary: {raw.summary}")
    print(f"Subject Matter: {raw.subject_matter}")
    print(f"Techniques: {raw.techniques_or_concepts}")
    print(f"Tools: {raw.tools_or_materials}")
    print(f"Difficulty: {raw.difficulty}")
    print(f"Content Style: {raw.content_style}")

    # Basic assertions
    assert raw.title is not None
    assert raw.summary is not None
    assert len(raw.subject_matter) > 0, "Should extract subject matter"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_normalizer_with_semantic_context(ollama_url, retriever):
    """Test Phase 2: Normalization with semantic context from Qdrant."""
    import os
    os.environ["OLLAMA_URL"] = ollama_url

    normalizer = create_normalizer(
        model="ollama:qwen2.5:7b",
        retriever=retriever
    )

    print("\n=== Getting Semantic Context ===")
    context = retriever.get_context_tags(SAMPLE_TRANSCRIPT[:1000], limit=5)
    for category, tags in context.items():
        if tags:
            print(f"{category}: {list(tags)[:5]}")

    print("\n=== Phase 1: Extract Raw ===")
    raw = await normalizer.extract_raw_metadata(SAMPLE_TRANSCRIPT)
    print(f"Raw Subject Matter: {raw.subject_matter}")

    print("\n=== Phase 2: Normalize ===")
    normalized = await normalizer.normalize_metadata(
        raw,
        context_tags=context
    )
    print(f"Normalized Subject Matter: {normalized.subject_matter}")

    assert normalized.title is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_normalizer_with_vocabulary(ollama_url, vocabulary):
    """Test normalization with vocabulary constraints."""
    import os
    os.environ["OLLAMA_URL"] = ollama_url

    normalizer = create_normalizer(
        model="ollama:qwen2.5:7b",
        vocabulary=vocabulary
    )

    print(f"\n=== Vocabulary: {len(vocabulary.seed_tags)} tags loaded ===")

    raw = await normalizer.extract_raw_metadata(SAMPLE_TRANSCRIPT)

    normalized = await normalizer.normalize_metadata(
        raw,
        vocabulary_tags=vocabulary.get_all_tags()
    )

    print("\n=== Comparison ===")
    print(f"Raw Subject Matter:        {raw.subject_matter}")
    print(f"Normalized Subject Matter: {normalized.subject_matter}")

    assert normalized.subject_matter is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_normalizer_full_pipeline(ollama_url, retriever, vocabulary):
    """Test full normalize_from_transcript pipeline."""
    import os
    os.environ["OLLAMA_URL"] = ollama_url

    normalizer = create_normalizer(
        model="ollama:qwen2.5:7b",
        retriever=retriever,
        vocabulary=vocabulary
    )

    print("\n=== Full Pipeline Test ===")
    result = await normalizer.normalize_from_transcript(
        SAMPLE_TRANSCRIPT,
        use_semantic_context=True,
        use_vocabulary=True
    )

    print(f"Raw subject_matter:        {result['raw'].subject_matter}")
    print(f"Normalized subject_matter: {result['normalized'].subject_matter}")

    assert "raw" in result
    assert "normalized" in result
    assert result["normalized"].title is not None

    print("\n[OK] Full pipeline test complete!")


if __name__ == "__main__":
    # Run directly with default remote services
    import os
    os.environ.setdefault("QDRANT_URL", "http://192.168.16.241:6333")
    os.environ.setdefault("INFINITY_URL", "http://192.168.16.241:7997")
    os.environ.setdefault("OLLAMA_URL", "http://192.168.16.241:11434")

    pytest.main([__file__, "-v", "-s"])
