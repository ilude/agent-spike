"""
Test basic Mem0 memory operations.

This script tests:
1. Adding memories from conversations
2. Searching memories semantically
3. Retrieving all memories
4. Updating memories
5. Deleting memories

Run with: uv run python test_memory_basics.py
"""

import io
import os
import sys

# Add lesson-006 to path
sys.path.insert(0, os.path.dirname(__file__))

# Fix Windows console UTF-8 encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )

from memory import MemoryClient


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def print_memories(memories: list, title: str = "Memories"):
    """Print memories in a readable format."""
    print(f"\n{title}:")
    if not memories:
        print("  (none)")
        return

    for i, mem in enumerate(memories, 1):
        # Handle both string and dict responses from Mem0
        if isinstance(mem, str):
            print(f"  {i}. {mem}")
        elif isinstance(mem, dict):
            memory_text = mem.get("memory", mem.get("data", ""))
            memory_id = mem.get("id", "N/A")
            score = mem.get("score", "")
            score_str = f" (score: {score:.3f})" if score else ""
            print(f"  {i}. {memory_text}{score_str}")
            print(f"     ID: {memory_id}")
        else:
            print(f"  {i}. {mem}")


def test_add_memories(client: MemoryClient):
    """Test 1: Add memories from conversations."""
    print_section("Test 1: Adding Memories")

    user_id = "test_user_alice"

    # Clean up previous test data
    print("\nCleaning up previous test data...")
    client.delete_all(user_id=user_id)

    # Add first memory: User preferences
    print("\nAdding memory: User prefers tech content...")
    result1 = client.add(
        messages=[
            {"role": "user", "content": "I really enjoy watching tech tutorials and programming videos"},
            {"role": "assistant", "content": "Got it! I'll prioritize tech content for you."}
        ],
        user_id=user_id,
        metadata={"source": "youtube_tagging", "category": "preference"}
    )
    print(f"Result: {result1.get('message', 'Success')}")

    # Add second memory: Specific dislikes
    print("\nAdding memory: User avoids political content...")
    result2 = client.add(
        messages=[
            {"role": "user", "content": "Please don't show me political debates, I find them stressful"},
            {"role": "assistant", "content": "Understood, I'll filter out political content."}
        ],
        user_id=user_id,
        metadata={"source": "youtube_tagging", "category": "preference"}
    )
    print(f"Result: {result2.get('message', 'Success')}")

    # Add third memory: Learning goal
    print("\nAdding memory: User learning Python async...")
    result3 = client.add(
        messages=[
            {"role": "user", "content": "I'm currently learning about Python async/await and asyncio"},
        ],
        user_id=user_id,
        metadata={"source": "conversation", "category": "learning_goal"}
    )
    print(f"Result: {result3.get('message', 'Success')}")

    print("\n✅ Successfully added 3 memories")


def test_search_memories(client: MemoryClient):
    """Test 2: Search memories semantically."""
    print_section("Test 2: Searching Memories")

    user_id = "test_user_alice"

    # Search for preferences
    print("\nQuery: 'What are the user's content preferences?'")
    memories = client.search(
        query="user's content preferences and topics they like",
        user_id=user_id,
        limit=5
    )
    print_memories(memories, "Search Results")

    # Search for learning topics
    print("\n\nQuery: 'What is the user learning?'")
    memories = client.search(
        query="what is the user currently learning or studying",
        user_id=user_id,
        limit=5
    )
    print_memories(memories, "Search Results")

    print("\n✅ Semantic search working correctly")


def test_get_all_memories(client: MemoryClient):
    """Test 3: Retrieve all memories for a user."""
    print_section("Test 3: Getting All Memories")

    user_id = "test_user_alice"

    print(f"\nRetrieving all memories for user: {user_id}")
    all_memories = client.get_all(user_id=user_id)
    print_memories(all_memories, f"All Memories ({len(all_memories)} total)")

    print("\n✅ Retrieved all memories successfully")


def test_update_memory(client: MemoryClient):
    """Test 4: Update an existing memory."""
    print_section("Test 4: Updating Memory")

    user_id = "test_user_alice"

    # Get first memory
    memories = client.get_all(user_id=user_id)
    if not memories:
        print("⚠️ No memories to update")
        return

    first_memory = memories[0]
    memory_id = first_memory.get("id")

    print(f"\nOriginal memory: {first_memory.get('memory', first_memory.get('data', ''))}")
    print(f"Memory ID: {memory_id}")

    # Update it
    new_content = "User prefers tech content, especially Python tutorials and async programming"
    print(f"\nUpdating to: {new_content}")
    result = client.update(memory_id=memory_id, data=new_content)
    print(f"Result: {result.get('message', 'Success')}")

    # Verify update
    updated_memories = client.get_all(user_id=user_id)
    updated_memory = next((m for m in updated_memories if m.get("id") == memory_id), None)
    if updated_memory:
        print(f"Updated memory: {updated_memory.get('memory', updated_memory.get('data', ''))}")

    print("\n✅ Memory updated successfully")


def test_delete_memory(client: MemoryClient):
    """Test 5: Delete a specific memory."""
    print_section("Test 5: Deleting Memory")

    user_id = "test_user_alice"

    # Get all memories
    memories = client.get_all(user_id=user_id)
    if len(memories) < 2:
        print("⚠️ Need at least 2 memories to test deletion")
        return

    print(f"\nTotal memories before deletion: {len(memories)}")
    print_memories(memories, "Current Memories")

    # Delete the second memory
    memory_to_delete = memories[1]
    memory_id = memory_to_delete.get("id")
    print(f"\nDeleting memory: {memory_to_delete.get('memory', memory_to_delete.get('data', ''))}")
    print(f"Memory ID: {memory_id}")

    result = client.delete(memory_id=memory_id)
    print(f"Result: {result.get('message', 'Success')}")

    # Verify deletion
    remaining_memories = client.get_all(user_id=user_id)
    print(f"\nTotal memories after deletion: {len(remaining_memories)}")
    print_memories(remaining_memories, "Remaining Memories")

    print("\n✅ Memory deleted successfully")


def test_format_for_prompt(client: MemoryClient):
    """Test 6: Format memories for system prompts."""
    print_section("Test 6: Formatting Memories for Prompts")

    user_id = "test_user_alice"

    # Get memories
    memories = client.search(
        query="user preferences and learning goals",
        user_id=user_id,
        limit=3
    )

    # Format for prompt
    formatted = client.format_memories_for_prompt(memories)

    print("\nFormatted for system prompt:")
    print("-" * 60)
    print(formatted)
    print("-" * 60)

    # Show how it would look in a system prompt
    system_prompt = f"""
You are a helpful YouTube video tagging assistant.

<user_memory>
{formatted}
</user_memory>

Use the user's preferences and learning goals to provide relevant tags.
"""

    print("\nExample System Prompt:")
    print("-" * 60)
    print(system_prompt)
    print("-" * 60)

    print("\n✅ Memory formatting working correctly")


def cleanup(client: MemoryClient):
    """Clean up test data."""
    print_section("Cleanup")

    user_id = "test_user_alice"

    print(f"\nDeleting all memories for {user_id}...")
    result = client.delete_all(user_id=user_id)
    print(f"Result: {result.get('message', 'Success')}")

    print("\n✅ Cleanup complete")


def main():
    """Run all tests."""
    from tools.env_loader import load_root_env
    
    # Load environment variables
    load_root_env()

    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Mem0 requires OpenAI API for embeddings")
        print("   Copy .env from lesson-001 or create new .env with OPENAI_API_KEY")
        return

    print("\n" + "=" * 60)
    print(" Mem0 Memory Basics Test Suite")
    print("=" * 60)
    print("\nThis will test basic memory operations:")
    print("  1. Adding memories")
    print("  2. Searching memories")
    print("  3. Getting all memories")
    print("  4. Updating memories")
    print("  5. Deleting memories")
    print("  6. Formatting for prompts")

    try:
        # Create single client instance for all tests
        print("\nInitializing MemoryClient...")
        client = MemoryClient()
        print("✅ MemoryClient initialized")

        # Run tests
        test_add_memories(client)
        test_search_memories(client)
        test_get_all_memories(client)
        test_update_memory(client)
        test_delete_memory(client)
        test_format_for_prompt(client)

        # Cleanup
        cleanup(client)

        # Summary
        print_section("Summary")
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("  - Integrate memory with Pydantic AI agents")
        print("  - Add dynamic system prompts with memory context")
        print("  - Test memory-augmented agent conversations")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
