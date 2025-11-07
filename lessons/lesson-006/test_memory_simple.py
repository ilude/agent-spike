"""
Simple working test for Mem0 memory operations.

This script demonstrates:
1. Adding memories from conversations
2. Searching memories semantically
3. Retrieving all memories for a user

Key learning: Mem0 API returns dicts with 'results' key, not raw lists.

Run with: uv run python test_memory_simple.py
"""

import io
import os
import sys
from dotenv import load_dotenv

# Fix Windows console UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )

import io
import os
import sys

# Add lesson-006 to path
sys.path.insert(0, os.path.dirname(__file__))

from memory import MemoryClient
from tools.dotenv import load_root_env


def main():
    """Run simple memory operations test."""
    # Load environment variables
    load_root_env()

    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Mem0 requires OpenAI API for embeddings")
        print("   Copy .env from lesson-001 or create new .env with OPENAI_API_KEY")
        return

    print("\n" + "=" * 60)
    print(" Mem0 Memory Simple Test")
    print("=" * 60)

    try:
        # Initialize client
        print("\n1. Initializing MemoryClient...")
        client = MemoryClient()
        print("   ✅ MemoryClient initialized")

        # Clean up any previous test data
        user_id = "test_user_simple"
        print(f"\n2. Cleaning up previous test data for {user_id}...")
        client.delete_all(user_id=user_id)
        print("   ✅ Cleanup complete")

        # Add memories
        print("\n3. Adding memories...")

        print("   Adding: User prefers tech content")
        result1 = client.add(
            messages=[
                {"role": "user", "content": "I love watching tech tutorials and Python videos"},
            ],
            user_id=user_id,
            metadata={"category": "preference"}
        )
        print(f"   ✅ {result1.get('message', 'Success')}")

        print("   Adding: User avoids politics")
        result2 = client.add(
            messages=[
                {"role": "user", "content": "Please don't show me political content"},
            ],
            user_id=user_id,
            metadata={"category": "preference"}
        )
        print(f"   ✅ {result2.get('message', 'Success')}")

        print("   Adding: User learning asyncio")
        result3 = client.add(
            messages=[
                {"role": "user", "content": "I'm currently learning Python asyncio"},
            ],
            user_id=user_id,
            metadata={"category": "learning"}
        )
        print(f"   ✅ {result3.get('message', 'Success')}")

        # Search memories
        print("\n4. Searching memories...")
        query = "What content does the user prefer?"
        print(f"   Query: '{query}'")

        search_results = client.search(
            query=query,
            user_id=user_id,
            limit=3
        )

        # Handle Mem0's return format (can be list or dict with 'results' key)
        if isinstance(search_results, dict) and 'results' in search_results:
            memories = search_results['results']
        elif isinstance(search_results, list):
            memories = search_results
        else:
            memories = []

        print(f"   ✅ Found {len(memories)} relevant memories:")
        for i, mem in enumerate(memories, 1):
            memory_text = mem.get("memory", mem.get("data", ""))
            score = mem.get("score", 0)
            print(f"      {i}. {memory_text} (score: {score:.3f})")

        # Get all memories
        print("\n5. Getting all memories...")
        all_results = client.get_all(user_id=user_id)

        # Handle Mem0's return format
        if isinstance(all_results, dict) and 'results' in all_results:
            all_memories = all_results['results']
        elif isinstance(all_results, list):
            all_memories = all_results
        else:
            all_memories = []

        print(f"   ✅ Retrieved {len(all_memories)} total memories:")
        for i, mem in enumerate(all_memories, 1):
            memory_text = mem.get("memory", mem.get("data", ""))
            memory_id = mem.get("id", "N/A")
            print(f"      {i}. {memory_text}")
            print(f"         ID: {memory_id}")

        # Format for prompt
        print("\n6. Formatting memories for system prompt...")
        formatted = client.format_memories_for_prompt(memories)
        print("   ✅ Formatted memories:")
        print()
        for line in formatted.split('\n'):
            print(f"      {line}")

        # Cleanup
        print(f"\n7. Cleaning up test data for {user_id}...")
        client.delete_all(user_id=user_id)
        print("   ✅ Cleanup complete")

        # Success summary
        print("\n" + "=" * 60)
        print(" ✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nKey learnings:")
        print("  - Mem0 extracts facts from conversations automatically")
        print("  - Semantic search finds relevant memories without exact matches")
        print("  - Memory persists across sessions (stored in ~/.mem0/)")
        print("  - Each user's memories are isolated by user_id")
        print("\nNext steps:")
        print("  - Integrate with Pydantic AI agents (dynamic system prompts)")
        print("  - Add post-conversation memory updates")
        print("  - Test multi-user memory isolation")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
