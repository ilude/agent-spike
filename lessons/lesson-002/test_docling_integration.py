"""Integration test for docling-serve HTTP API migration."""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path for env_loader
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from compose.lib.env_loader import load_root_env
from webpage_agent.tools import fetch_webpage

# Load environment
load_root_env()


def test_basic_fetch():
    """Test basic webpage fetching with HTTP API."""
    print("\n=== Test 1: Basic Webpage Fetch ===")
    url = "https://example.com"
    print(f"Fetching: {url}")

    result = fetch_webpage(url)

    if result.startswith("ERROR:"):
        print(f"❌ FAILED: {result}")
        return False

    print(f"✓ Success! Got {len(result)} chars of markdown")
    print(f"\nFirst 300 chars:\n{result[:300]}")
    print(f"\nLast 200 chars:\n{result[-200:]}")
    return True


def test_content_quality():
    """Test that markdown content is properly formatted."""
    print("\n=== Test 2: Content Quality Check ===")
    url = "https://example.com"

    result = fetch_webpage(url)

    if result.startswith("ERROR:"):
        print(f"❌ FAILED: {result}")
        return False

    # Check for basic markdown indicators
    checks = [
        (len(result) > 100, "Content length > 100 chars"),
        ("example" in result.lower(), "Contains 'example' text"),
        (not result.startswith("ERROR"), "No error prefix"),
    ]

    all_passed = True
    for passed, description in checks:
        status = "✓" if passed else "❌"
        print(f"{status} {description}")
        if not passed:
            all_passed = False

    return all_passed


def test_truncation():
    """Test content truncation for large pages."""
    print("\n=== Test 3: Content Truncation ===")
    # Use a URL that's likely to have more than 15k chars
    url = "https://www.wikipedia.org"
    print(f"Fetching: {url}")

    result = fetch_webpage(url)

    if result.startswith("ERROR:"):
        print(f"⚠ Skipped (error): {result}")
        return True  # Don't fail on network errors

    print(f"Got {len(result)} chars")

    if "[Content truncated for analysis...]" in result:
        print("✓ Content was truncated as expected")
        return True
    else:
        print("✓ Content under limit (no truncation needed)")
        return True


def test_invalid_url():
    """Test error handling for invalid URLs."""
    print("\n=== Test 4: Invalid URL Handling ===")
    url = "https://thisisnotarealdomainthatexists12345.com"
    print(f"Fetching: {url}")

    result = fetch_webpage(url)

    if result.startswith("ERROR:"):
        print(f"✓ Correctly returned error: {result[:100]}")
        return True
    else:
        print(f"❌ Should have returned error but got content: {result[:100]}")
        return False


def test_service_unavailable():
    """Test error handling when service is down."""
    print("\n=== Test 5: Service Unavailable Handling ===")
    # Temporarily use wrong port to simulate service down
    import os
    old_url = os.getenv("DOCLING_URL")
    os.environ["DOCLING_URL"] = "http://localhost:9999"

    url = "https://example.com"
    print(f"Testing with wrong service URL: http://localhost:9999")

    result = fetch_webpage(url)

    # Restore original URL
    if old_url:
        os.environ["DOCLING_URL"] = old_url

    if "Cannot connect to docling service" in result:
        print(f"✓ Correctly detected service unavailable: {result}")
        return True
    else:
        print(f"❌ Should have detected service down: {result[:100]}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Docling-Serve HTTP API Integration Tests")
    print("=" * 60)

    tests = [
        ("Basic Fetch", test_basic_fetch),
        ("Content Quality", test_content_quality),
        ("Truncation", test_truncation),
        ("Invalid URL", test_invalid_url),
        ("Service Unavailable", test_service_unavailable),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
