"""Test semantic tag retriever."""

from tools.services.tagger import create_retriever


def test_retriever():
    """Test semantic tag retrieval."""
    print("Creating retriever...")
    retriever = create_retriever()

    # Test with a sample query
    query = "AI agents using Claude and Anthropic for prompt engineering"

    print(f"\nQuery: {query}")
    print("\n=== Finding similar content ===")

    # Get similar content
    similar = retriever.find_similar_content(query, limit=3)
    print(f"Found {len(similar)} similar items")

    for i, result in enumerate(similar, 1):
        print(f"\n{i}. Score: {getattr(result, 'score', 'N/A')}")
        if hasattr(result, 'payload'):
            video_id = result.payload.get('key', 'unknown')
            print(f"   ID: {video_id}")

            # Show some metadata fields
            meta_fields = [k for k in result.payload.keys() if k.startswith('meta_')][:5]
            if meta_fields:
                print(f"   Sample metadata fields: {meta_fields}")

    # Get context tags
    print("\n=== Extracting context tags ===")
    context_tags = retriever.get_context_tags(query, limit=5)

    for category, tags in context_tags.items():
        if tags:
            print(f"\n{category}: {len(tags)} tags")
            print(f"  {list(tags)[:5]}...")

    # Get formatted context
    print("\n=== Formatted context for prompt ===")
    formatted = retriever.get_formatted_context(query, limit=5, top_n_per_category=10)
    print(formatted)

    print("\n[OK] Retriever test complete!")


if __name__ == "__main__":
    test_retriever()
