"""
Test the simplified orchestrator
"""
print("TEST START", flush=True)

import asyncio
import sys
from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001", "lesson-002"])

print("Importing simplified orchestrator...", flush=True)
from orchestrator_agent.agent_simple import orchestrator


async def test_orchestrator():
    """Test simplified orchestrator"""
    print("Running simplified orchestrator...", flush=True)

    # Test with 2 URLs
    result = await orchestrator.run(
        user_prompt="""Tag these URLs for me:
1. https://www.youtube.com/watch?v=i5kwX7jeWL8
2. https://www.anthropic.com/engineering/code-execution-with-mcp

Process each URL and give me the tags."""
    )

    print(f"\n=== RESULT ===", flush=True)
    print(f"Type: {type(result)}", flush=True)
    print(f"Output:\n{result.output}", flush=True)

    # Check usage stats
    if hasattr(result, 'usage'):
        usage = result.usage()
        print(f"\n=== USAGE ===", flush=True)
        print(f"Total tokens: {usage.total_tokens if usage else 'N/A'}", flush=True)

    return result


async def main():
    """Main async function"""
    try:
        result = await test_orchestrator()
        print("\n[OK] TEST PASSED", flush=True)
        return result
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Starting simplified orchestrator test...", flush=True)
    asyncio.run(main())
    print("\nTEST COMPLETE", flush=True)