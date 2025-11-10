"""Test two-phase tag normalizer."""

import asyncio
from pathlib import Path

from tag_normalizer.normalizer import create_normalizer
from tag_normalizer.retriever import create_retriever
from tag_normalizer.vocabulary import load_vocabulary


async def test_normalizer():
    """Test tag normalization."""
    print("=== Setting up normalizer ===")

    # Load vocabulary
    vocab_path = Path(__file__).parent / "data" / "seed_vocabulary_v1.json"
    vocabulary = load_vocabulary(vocab_path)
    print(f"Loaded vocabulary: {len(vocabulary.seed_tags)} tags")

    # Create retriever
    retriever = create_retriever()
    print("Created semantic retriever")

    # Create normalizer
    normalizer = create_normalizer(
        retriever=retriever,
        vocabulary=vocabulary
    )
    print("Created normalizer\n")

    # Test transcript
    transcript = """
    In this video, we'll explore how to build AI agents using Claude and the Anthropic API.
    We'll cover prompt engineering techniques, including few-shot prompting and chain-of-thought reasoning.
    You'll learn how to use LangChain to orchestrate multiple agents, and we'll implement
    retrieval augmented generation (RAG) using a vector database like Qdrant or Pinecone.
    This is an intermediate tutorial for developers who want to build production AI systems.
    """

    print("=== Phase 1: Raw Extraction ===")
    raw = await normalizer.extract_raw_metadata(transcript)
    print(f"Title: {raw.title}")
    print(f"Summary: {raw.summary}")
    print(f"Subject Matter: {raw.subject_matter}")
    print(f"Techniques: {raw.techniques_or_concepts}")
    print(f"Tools: {raw.tools_or_materials}")
    print(f"Difficulty: {raw.difficulty}")
    print(f"Content Style: {raw.content_style}")

    print("\n=== Getting Semantic Context ===")
    context = retriever.get_context_tags(transcript[:1000], limit=5)
    for category, tags in context.items():
        if tags:
            print(f"{category}: {list(tags)[:5]}")

    print("\n=== Phase 2: Normalization ===")
    normalized = await normalizer.normalize_metadata(
        raw,
        context_tags=context,
        vocabulary_tags=vocabulary.get_all_tags()
    )
    print(f"Title: {normalized.title}")
    print(f"Subject Matter: {normalized.subject_matter}")
    print(f"Techniques: {normalized.techniques_or_concepts}")
    print(f"Tools: {normalized.tools_or_materials}")

    print("\n=== Comparison ===")
    print("Raw vs Normalized Subject Matter:")
    print(f"  Raw:        {raw.subject_matter}")
    print(f"  Normalized: {normalized.subject_matter}")

    print("\nRaw vs Normalized Techniques:")
    print(f"  Raw:        {raw.techniques_or_concepts}")
    print(f"  Normalized: {normalized.techniques_or_concepts}")

    print("\n=== Full Pipeline Test ===")
    result = await normalizer.normalize_from_transcript(
        transcript,
        use_semantic_context=True,
        use_vocabulary=True
    )
    print(f"Raw subject_matter:        {result['raw'].subject_matter}")
    print(f"Normalized subject_matter: {result['normalized'].subject_matter}")

    print("\n[OK] Normalizer test complete!")


if __name__ == "__main__":
    asyncio.run(test_normalizer())
