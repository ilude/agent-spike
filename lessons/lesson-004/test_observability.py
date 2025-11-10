"""Test observability integration across all agents."""

import asyncio
import os
import sys
from pathlib import Path

# Add paths for all lesson modules
lesson_root = Path(__file__).parent.parent
sys.path.insert(0, str(lesson_root / "lesson-001"))
sys.path.insert(0, str(lesson_root / "lesson-002"))
sys.path.insert(0, str(lesson_root / "lesson-003"))

from tools.env_loader import load_root_env

# Load environment
load_root_env()

# Initialize Logfire before importing agents
from observability import initialize_logfire, get_logfire

# Initialize observability
print("=" * 60)
print("Initializing Pydantic Logfire Observability")
print("=" * 60)
logfire_enabled = initialize_logfire()

if not logfire_enabled:
    print("\nWARNING: Logfire not configured. Running without observability.")
    print("To enable observability:")
    print("  1. Get token from https://logfire.pydantic.dev")
    print("  2. Add to .env: LOGFIRE_TOKEN=your_token")
    print("  3. Re-run this script")
    print("\nContinuing with agent tests (console logging only)...\n")

# Now import agents (after instrumentation is enabled)
from youtube_agent.agent import analyze_video
from webpage_agent.agent import analyze_webpage
from coordinator_agent.agent import analyze_url

# Test URLs
YOUTUBE_URL = "https://www.youtube.com/watch?v=i5kwX7jeWL8"  # Cole Medin's agent video
WEBPAGE_URL = "https://github.com/docling-project/docling"  # Docling GitHub page


async def test_youtube_agent():
    """Test YouTube agent with observability."""
    print("\n" + "=" * 60)
    print("Test 1: YouTube Agent")
    print("=" * 60)
    print(f"URL: {YOUTUBE_URL}")
    print("Analyzing...")

    try:
        result = await analyze_video(YOUTUBE_URL)
        print("\nSUCCESS: YouTube Agent Result:")
        print(result)
        return True
    except Exception as e:
        print(f"\nERROR: YouTube Agent Error: {e}")
        return False


async def test_webpage_agent():
    """Test Webpage agent with observability."""
    print("\n" + "=" * 60)
    print("Test 2: Webpage Agent")
    print("=" * 60)
    print(f"URL: {WEBPAGE_URL}")
    print("Analyzing...")

    try:
        result = await analyze_webpage(WEBPAGE_URL)
        print("\nSUCCESS: Webpage Agent Result:")
        print(result)
        return True
    except Exception as e:
        print(f"\nERROR: Webpage Agent Error: {e}")
        return False


async def test_coordinator_youtube():
    """Test Coordinator with YouTube URL."""
    print("\n" + "=" * 60)
    print("Test 3: Coordinator (YouTube)")
    print("=" * 60)
    print(f"URL: {YOUTUBE_URL}")
    print("Analyzing...")

    try:
        result = await analyze_url(YOUTUBE_URL)
        print("\nSUCCESS: Coordinator Result:")
        print(result)
        return True
    except Exception as e:
        print(f"\nERROR: Coordinator Error: {e}")
        return False


async def test_coordinator_webpage():
    """Test Coordinator with Webpage URL."""
    print("\n" + "=" * 60)
    print("Test 4: Coordinator (Webpage)")
    print("=" * 60)
    print(f"URL: {WEBPAGE_URL}")
    print("Analyzing...")

    try:
        result = await analyze_url(WEBPAGE_URL)
        print("\nSUCCESS: Coordinator Result:")
        print(result)
        return True
    except Exception as e:
        print(f"\nERROR: Coordinator Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n[TEST] Running Observability Tests")
    print("Tests will execute agent operations with Logfire tracing enabled")
    print("Check console output for traces (or Logfire dashboard if configured)\n")

    results = []

    # Test individual agents
    results.append(await test_youtube_agent())
    results.append(await test_webpage_agent())

    # Test coordinator with both URL types
    results.append(await test_coordinator_youtube())
    results.append(await test_coordinator_webpage())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if logfire_enabled:
        print("\n[DASHBOARD] View traces:")
        print("   • Console output above shows detailed traces")
        print("   • Logfire dashboard: https://logfire.pydantic.dev (if token configured)")
        print("\nWhat to look for:")
        print("   • 4 main traces (one per test)")
        print("   • Tool calls (get_video_info, get_transcript, fetch_webpage)")
        print("   • LLM calls with token counts and costs")
        print("   • Latency measurements")
        print("   • Parent/child relationships for coordinator")
    else:
        print("\n[TIP] Enable Logfire cloud dashboard!")
        print("   1. Get free token: https://logfire.pydantic.dev")
        print("   2. Add to lesson-004/.env: LOGFIRE_TOKEN=your_token")
        print("   3. Re-run this script")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
