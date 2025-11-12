"""
Test orchestrator with proper async pattern
"""
print("TEST START", flush=True)

import asyncio
import sys
from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001", "lesson-002"])

print("Importing orchestrator...", flush=True)
from orchestrator_agent import orchestrator


async def test_orchestrator():
    """Test orchestrator with async pattern"""
    print("Running orchestrator...", flush=True)

    result = await orchestrator.run(
        user_prompt="Tag this YouTube URL: https://www.youtube.com/watch?v=i5kwX7jeWL8"
    )

    print(f"\n=== RESULT ===", flush=True)
    print(f"Type: {type(result)}", flush=True)
    print(f"Output: {result.output}", flush=True)

    return result


async def main():
    """Main async function"""
    try:
        result = await test_orchestrator()
        print("\n✅ TEST PASSED", flush=True)
        return result
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Starting async test...", flush=True)
    asyncio.run(main())
    print("DONE", flush=True)