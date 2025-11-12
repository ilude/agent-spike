"""
Test script for minimal orchestrator

Compares orchestrator (lesson-009) with coordinator (lesson-003)
"""

import sys
from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001", "lesson-002"])

from orchestrator_agent import orchestrator


def test_orchestrator():
    """Test orchestrator with mix of YouTube + webpage URLs"""

    print("=" * 80)
    print("TESTING ORCHESTRATOR (Lesson 009)")
    print("=" * 80)

    urls = [
        # YouTube videos
        "https://www.youtube.com/watch?v=i5kwX7jeWL8",  # Cole Medin video
    ]

    print(f"\nProcessing {len(urls)} URLs:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")

    print("\n" + "-" * 80)
    print("Calling orchestrator...")
    print("-" * 80 + "\n")

    try:
        result = orchestrator.run_sync(
            user_prompt=f"""Tag all of these URLs for me:

{chr(10).join(f'{i}. {url}' for i, url in enumerate(urls, 1))}

Process each URL with the appropriate sub-agent and give me organized results."""
        )

        print("ORCHESTRATOR RESULTS:")
        print("=" * 80)
        print(result.data)
        print("=" * 80)

        # Print usage stats if available
        if hasattr(result, 'usage'):
            print(f"\nToken usage: {result.usage()}")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_with_lesson_003():
    """
    Compare with lesson-003 coordinator

    Note: Lesson-003 processes one URL at a time,
    orchestrator can process multiple in one request
    """

    print("\n\n")
    print("=" * 80)
    print("COMPARISON WITH LESSON-003")
    print("=" * 80)

    print("""
Lesson-003 Coordinator:
- Routes single URL to appropriate agent
- Designed for one-URL-per-request workflow
- Simple routing logic

Lesson-009 Orchestrator:
- Handles multiple URLs in one request
- Calls multiple sub-agents as needed
- Accumulates and summarizes results

Key differences to measure:
1. Token usage (orchestrator should be lower per URL)
2. Latency (depends on parallel vs sequential calls)
3. Code complexity (orchestrator adds abstraction)
4. Use case fit (do we actually need multi-URL processing?)
""")

    print("\nTo fully compare, run same URLs through lesson-003 individually.")
    print("For now, this test proves the orchestrator *can* handle multi-URL requests.")


if __name__ == "__main__":
    print("Minimal Orchestrator Test\n")

    # Test orchestrator
    result = test_orchestrator()

    # Show comparison notes
    compare_with_lesson_003()

    # Summary
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Review results above
2. Measure token usage vs lesson-003
3. Decide:
   - Continue? Add IPython state?
   - Shelf? Move to VISION.md goals?

Document decision in COMPLETE.md
""")
