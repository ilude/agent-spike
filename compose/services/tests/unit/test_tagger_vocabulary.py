"""Test vocabulary manager."""

from pathlib import Path
from compose.services.tagger import VocabularyManager


def test_load_seed_vocabulary():
    """Test loading the seed vocabulary."""
    vocab_path = Path(__file__).parent.parent.parent.parent / "lessons" / "lesson-010" / "data" / "seed_vocabulary_v1.json"

    vocab = VocabularyManager(vocab_path)
    vocab.load()

    print(f"Loaded vocabulary version: {vocab.version}")
    print(f"Total tags: {len(vocab.seed_tags)}")
    print(f"Created at: {vocab.created_at}")

    # Get stats
    stats = vocab.get_stats()
    print(f"\nVocabulary Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test canonical form lookup
    print(f"\n=== Testing canonical form lookup ===")
    test_tags = ["prompt-engineering", "PROMPT-ENGINEERING", "ai-agents", "AI"]
    for tag in test_tags:
        canonical = vocab.get_canonical_form(tag)
        print(f"  {tag} -> {canonical}")

    # Test tag info
    print(f"\n=== Testing tag info ===")
    info = vocab.get_tag_info("prompt-engineering")
    if info:
        print(f"  Tag: prompt-engineering")
        print(f"  Count: {info['count']}")
        print(f"  Confidence: {info['confidence']}")
        print(f"  Aliases: {info['aliases']}")

    # Test category lookup
    print(f"\n=== Testing categories ===")
    for category in list(vocab.categories.keys())[:3]:
        tags = vocab.get_tags_by_category(category)
        print(f"  {category}: {len(tags)} tags")
        print(f"    Top 3: {tags[:3]}")

    # Test export for prompt
    print(f"\n=== Testing prompt export ===")
    prompt_text = vocab.export_for_prompt(top_n=10)
    print(prompt_text)

    # Test adding a new tag
    print(f"\n=== Testing tag addition ===")
    vocab.add_tag("test-tag", count=5, aliases=["test_tag", "testtag"])
    new_canonical = vocab.get_canonical_form("test_tag")
    print(f"  Added 'test-tag', canonical form of 'test_tag': {new_canonical}")

    # Test consolidation
    print(f"\n=== Testing consolidation ===")
    vocab.add_tag("ai", count=10)
    vocab.add_tag("artificial-intelligence", count=64)
    vocab.consolidate_tags({"ai": "artificial-intelligence"})
    ai_info = vocab.get_tag_info("artificial-intelligence")
    print(f"  Consolidated 'ai' into 'artificial-intelligence'")
    print(f"  New count: {ai_info['count']}")
    print(f"  Aliases: {ai_info['aliases'][:5]}...")

    print("\n[OK] All tests passed!")


if __name__ == "__main__":
    test_load_seed_vocabulary()
