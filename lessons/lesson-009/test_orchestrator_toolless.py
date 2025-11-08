"""
Test Option 2: Tool-less Sub-Agents Architecture

Key difference from option 1:
- Coordinator has ALL tools (fetch_youtube_data, fetch_webpage_data, reason_youtube, reason_webpage)
- Sub-agents (youtube_reasoner, webpage_reasoner) have NO tools - pure LLM reasoning
- No nested agent-with-tools calls = no deadlocks
"""
print("TEST START - Option 2: Tool-less Sub-Agents", flush=True)

import asyncio
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.dotenv import load_root_env
load_root_env()

lessons_dir = Path(__file__).parent.parent
sys.path.insert(0, str(lessons_dir))
sys.path.insert(0, str(lessons_dir / "lesson-001"))
sys.path.insert(0, str(lessons_dir / "lesson-002"))

print("Importing coordinator with tool-less sub-agents...", flush=True)
from orchestrator_agent.agent_toolless import coordinator


async def test_toolless_orchestrator():
    """Test coordinator with tool-less sub-agents"""
    print("\nRunning tool-less orchestrator test...", flush=True)

    # Test with 2 URLs (one YouTube, one webpage)
    result = await coordinator.run(
        user_prompt="""Process these URLs for me:
1. https://www.youtube.com/watch?v=i5kwX7jeWL8
2. https://www.anthropic.com/engineering/code-execution-with-mcp

For each URL:
1. Fetch the data using the appropriate fetch tool
2. Generate tags using the appropriate reasoning tool
3. Give me organized results

Use your tools to handle this efficiently."""
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
        result = await test_toolless_orchestrator()
        print("\n[OK] TEST PASSED - No deadlocks with tool-less sub-agents!", flush=True)
        return result
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n" + "="*80, flush=True)
    print("Testing Option 2: Tool-less Sub-Agents Architecture", flush=True)
    print("="*80 + "\n", flush=True)

    print("Architecture:", flush=True)
    print("  - Coordinator has ALL tools (data fetching + reasoning)", flush=True)
    print("  - Sub-agents are pure LLM reasoning (no tools)", flush=True)
    print("  - No nested agent-with-tools calls", flush=True)
    print("  - Expected: NO DEADLOCKS", flush=True)
    print("\nStarting test...\n", flush=True)

    asyncio.run(main())
    print("\nTEST COMPLETE", flush=True)
