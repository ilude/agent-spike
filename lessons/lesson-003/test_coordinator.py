"""Test script for the coordinator agent with real URLs."""

import asyncio
import sys
from coordinator_agent.agent import analyze_url


async def test_youtube():
    """Test with a YouTube URL."""
    print("\n" + "=" * 80)
    print("TEST 1: YouTube Video")
    print("=" * 80)

    url = "https://www.youtube.com/watch?v=i5kwX7jeWL8"
    print(f"URL: {url}")
    print("Processing...\n")

    result = await analyze_url(url)

    if result.error:
        print(f"ERROR: {result.error}")
        return False

    print(f"URL Type: {result.url_type.value}")
    print(f"Handler: {result.handler}")
    print(f"\nResult:\n{result.result}")

    return True


async def test_webpage():
    """Test with a webpage URL."""
    print("\n" + "=" * 80)
    print("TEST 2: Webpage")
    print("=" * 80)

    url = "https://github.com/docling-project/docling"
    print(f"URL: {url}")
    print("Processing...\n")

    result = await analyze_url(url)

    if result.error:
        print(f"ERROR: {result.error}")
        return False

    print(f"URL Type: {result.url_type.value}")
    print(f"Handler: {result.handler}")
    print(f"\nResult:\n{result.result}")

    return True


async def main():
    """Run all tests."""
    print("Testing Multi-Agent Coordinator")

    # Test YouTube
    youtube_success = await test_youtube()

    # Test Webpage
    webpage_success = await test_webpage()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"YouTube test: {'PASSED' if youtube_success else 'FAILED'}")
    print(f"Webpage test: {'PASSED' if webpage_success else 'FAILED'}")

    return youtube_success and webpage_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
