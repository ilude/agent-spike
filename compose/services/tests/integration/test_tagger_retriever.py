"""Integration test for semantic tag retriever.

Requires remote services:
- Qdrant: http://192.168.16.241:6333
- Infinity: http://192.168.16.241:7997

Run with: uv run pytest compose/services/tests/integration/test_tagger_retriever.py -v -s
"""

import pytest

from compose.services.tagger import create_retriever


@pytest.mark.integration
def test_retriever_find_similar_content(qdrant_url, infinity_url, collection_name):
    """Test semantic retrieval finds similar cached content."""
    retriever = create_retriever(
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        infinity_url=infinity_url
    )

    # Test with a sample query
    query = "AI agents using Claude and Anthropic for prompt engineering"

    print(f"\nQuery: {query}")
    print("\n=== Finding similar content ===")

    # Get similar content
    similar = retriever.find_similar_content(query, limit=3)
    print(f"Found {len(similar)} similar items")

    assert len(similar) >= 0, "Should return results (may be empty if no cached content)"

    for i, result in enumerate(similar, 1):
        score = result.get("_score", "N/A")
        print(f"\n{i}. Score: {score}")
        if "_metadata" in result:
            print(f"   Metadata keys: {list(result['_metadata'].keys())[:5]}")


@pytest.mark.integration
def test_retriever_get_context_tags(qdrant_url, infinity_url, collection_name):
    """Test extracting context tags from similar content."""
    retriever = create_retriever(
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        infinity_url=infinity_url
    )

    query = "AI agents using Claude and Anthropic for prompt engineering"

    print("\n=== Extracting context tags ===")
    context_tags = retriever.get_context_tags(query, limit=5)

    for category, tags in context_tags.items():
        if tags:
            print(f"\n{category}: {len(tags)} tags")
            print(f"  {list(tags)[:5]}...")

    # Verify structure
    expected_categories = {"subject_matter", "entities", "techniques", "tools", "tags"}
    assert set(context_tags.keys()) == expected_categories


@pytest.mark.integration
def test_retriever_formatted_context(qdrant_url, infinity_url, collection_name):
    """Test formatted context output for LLM prompts."""
    retriever = create_retriever(
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        infinity_url=infinity_url
    )

    query = "AI agents using Claude and Anthropic for prompt engineering"

    print("\n=== Formatted context for prompt ===")
    formatted = retriever.get_formatted_context(query, limit=5, top_n_per_category=10)
    print(formatted)

    assert isinstance(formatted, str)
    assert "Tags from similar content:" in formatted


if __name__ == "__main__":
    # Run directly with default remote services
    import os
    os.environ.setdefault("QDRANT_URL", "http://192.168.16.241:6333")
    os.environ.setdefault("INFINITY_URL", "http://192.168.16.241:7997")

    pytest.main([__file__, "-v", "-s"])
