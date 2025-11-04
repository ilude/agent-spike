"""Simple demo script to run the coordinator with any URL."""

import asyncio
import sys
from coordinator_agent.agent import analyze_url


async def demo(url: str):
    """Demonstrate the coordinator with a single URL."""
    print("\n" + "=" * 80)
    print("MULTI-AGENT COORDINATOR DEMO")
    print("=" * 80)
    print(f"\nAnalyzing: {url}")
    print("\nProcessing...\n")

    result = await analyze_url(url)

    if result.error:
        print(f"ERROR: {result.error}")
        return False

    print(f"[OK] URL Type: {result.url_type.value}")
    print(f"[OK] Handler: {result.handler}")
    print("\n" + "-" * 80)
    print("RESULT")
    print("-" * 80)
    print(result.result)
    print("=" * 80)

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python demo.py <URL>")
        print("\nExamples:")
        print('  python demo.py "https://www.youtube.com/watch?v=i5kwX7jeWL8"')
        print('  python demo.py "https://github.com/anthropics/claude-code"')
        sys.exit(1)

    url = sys.argv[1]
    success = asyncio.run(demo(url))
    sys.exit(0 if success else 1)
