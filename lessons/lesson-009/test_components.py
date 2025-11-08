"""
Unit tests for lesson-009 components

Tests individual pieces to isolate issues:
1. Sub-agents (youtube, webpage)
2. call_subagent tool
3. Orchestrator with minimal input
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from tools.dotenv import load_root_env
load_root_env()

# Add lessons to path
lessons_dir = Path(__file__).parent.parent
sys.path.insert(0, str(lessons_dir))
sys.path.insert(0, str(lessons_dir / "lesson-001"))
sys.path.insert(0, str(lessons_dir / "lesson-002"))


def test_youtube_agent():
    """Test YouTube agent directly"""
    print("\n" + "=" * 80)
    print("TEST 1: YouTube Agent")
    print("=" * 80)

    from youtube_agent.agent import create_agent

    agent = create_agent(instrument=False)
    result = agent.run_sync(
        user_prompt="Tag this video: https://www.youtube.com/watch?v=i5kwX7jeWL8"
    )

    print(f"Result type: {type(result)}")
    print(f"Has output attr: {hasattr(result, 'output')}")
    print(f"Output: {result.output}")
    print("[OK] YouTube agent works\n")

    return result


def test_webpage_agent():
    """Test Webpage agent directly"""
    print("\n" + "=" * 80)
    print("TEST 2: Webpage Agent")
    print("=" * 80)

    from webpage_agent.agent import create_agent

    agent = create_agent(instrument=False)
    result = agent.run_sync(
        user_prompt="Tag this webpage: https://www.anthropic.com"
    )

    print(f"Result type: {type(result)}")
    print(f"Has output attr: {hasattr(result, 'output')}")
    print(f"Output: {result.output}")
    print("[OK] Webpage agent works\n")

    return result


def test_call_subagent_tool():
    """Test call_subagent tool function directly"""
    print("\n" + "=" * 80)
    print("TEST 3: call_subagent Tool")
    print("=" * 80)

    from pydantic_ai import RunContext
    from orchestrator_agent.tools import call_subagent

    # Create a minimal RunContext (we don't actually use it in the tool)
    class MockCtx:
        pass

    ctx = MockCtx()

    # Test YouTube
    print("\n--- Testing youtube_tagger ---")
    result = call_subagent(ctx, "youtube_tagger", "https://www.youtube.com/watch?v=i5kwX7jeWL8")
    print(f"Result: {result}")
    assert result["success"] is True
    assert "tags" in result
    print("[OK] call_subagent works for YouTube\n")

    # Test Webpage
    print("--- Testing webpage_tagger ---")
    result = call_subagent(ctx, "webpage_tagger", "https://www.anthropic.com")
    print(f"Result: {result}")
    assert result["success"] is True
    assert "tags" in result
    print("[OK] call_subagent works for webpage\n")

    return result


def test_orchestrator_simple():
    """Test orchestrator with single URL"""
    print("\n" + "=" * 80)
    print("TEST 4: Orchestrator (Single URL)")
    print("=" * 80)

    from orchestrator_agent import orchestrator

    result = orchestrator.run_sync(
        user_prompt="Tag this URL: https://www.youtube.com/watch?v=i5kwX7jeWL8"
    )

    print(f"\nOrchestrator result:")
    print(f"Type: {type(result)}")
    print(f"Output: {result.output}")
    print("\n[OK] Orchestrator works with single URL\n")

    return result


if __name__ == "__main__":
    print("Lesson-009 Component Tests\n")

    try:
        # Test 1: YouTube agent
        test_youtube_agent()

        # Test 2: Webpage agent
        test_webpage_agent()

        # Test 3: call_subagent tool
        test_call_subagent_tool()

        # Test 4: Orchestrator
        test_orchestrator_simple()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED [OK]")
        print("=" * 80)

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
