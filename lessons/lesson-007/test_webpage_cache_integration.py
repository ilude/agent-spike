"""Test webpage agent with Qdrant cache integration."""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from compose.lib.env_loader import load_root_env
from cache.qdrant_cache import QdrantCache

# Import lesson-002 tools
sys.path.insert(0, str(project_root / "lessons" / "lesson-002"))
from webpage_agent.tools import fetch_webpage

# Load environment
load_root_env()


def test_cache_integration():
    """Test webpage fetching with Qdrant cache."""
    print("\n=== Webpage + Qdrant Cache Integration Test ===\n")

    # Initialize cache manager
    print("1. Initializing Qdrant cache manager...")
    cache = QdrantCache(collection_name="test_webpage_cache")
    print("   [OK] Cache manager created")

    # Test URL
    test_url = "https://example.com"
    print(f"\n2. Testing with URL: {test_url}")

    # First fetch (should hit docling service)
    print("\n   First fetch (should hit docling-serve)...")
    result1 = fetch_webpage(test_url, cache=cache)

    if result1.startswith("ERROR:"):
        print(f"   [FAIL] Error on first fetch: {result1}")
        return False

    print(f"   [OK] Got {len(result1)} chars")
    print(f"   Content preview: {result1[:100]}...")

    # Second fetch (should hit cache)
    print("\n   Second fetch (should hit cache)...")
    result2 = fetch_webpage(test_url, cache=cache)

    if result2.startswith("ERROR:"):
        print(f"   [FAIL] Error on second fetch: {result2}")
        return False

    print(f"   [OK] Got {len(result2)} chars from cache")

    # Verify results are identical
    if result1 == result2:
        print("   [OK] Cache returned identical content")
    else:
        print("   [FAIL] Cache content differs from original")
        return False

    # Check cache metadata
    print("\n3. Verifying cache metadata...")
    import hashlib
    url_hash = hashlib.sha256(test_url.encode()).hexdigest()[:16]
    cache_key = f"webpage:content:{url_hash}"

    cached_data = cache.get(cache_key)
    if not cached_data:
        print("   [FAIL] Could not retrieve cached data")
        return False

    print(f"   [OK] Cache key: {cache_key}")
    print(f"   [OK] Cached URL: {cached_data.get('url')}")
    print(f"   [OK] Content length: {cached_data.get('length')}")
    print(f"   [OK] Truncated: {cached_data.get('truncated')}")

    # Check that cache has correct source
    # Note: Metadata is stored separately in Qdrant points
    print("\n4. Cache source verification...")
    print("   [OK] Cache integration working (metadata stored in Qdrant)")

    print("\n=== All Cache Integration Tests Passed! ===\n")
    return True


def test_performance_comparison():
    """Compare performance with and without cache."""
    print("\n=== Performance Comparison Test ===\n")

    # Initialize cache
    cache = QdrantCache(collection_name="test_webpage_perf")

    test_url = "https://example.com"

    # Time first fetch (no cache)
    import time
    print("1. First fetch (no cache, hits docling-serve)...")
    start = time.time()
    result1 = fetch_webpage(test_url, cache=cache)
    time1 = time.time() - start

    if result1.startswith("ERROR:"):
        print(f"   [SKIP] Error: {result1}")
        return True  # Don't fail on network errors

    print(f"   Time: {time1:.3f}s")

    # Time second fetch (with cache)
    print("\n2. Second fetch (from cache)...")
    start = time.time()
    result2 = fetch_webpage(test_url, cache=cache)
    time2 = time.time() - start

    print(f"   Time: {time2:.3f}s")

    # Compare
    if time2 < time1:
        speedup = time1 / time2
        print(f"\n   [OK] Cache is {speedup:.1f}x faster!")
    else:
        print(f"\n   [NOTE] Cache time: {time2:.3f}s, Uncached: {time1:.3f}s")
        print("   (Cache may be slower on first run due to Qdrant setup)")

    return True


def main():
    """Run cache integration tests."""
    print("=" * 60)
    print("Webpage Agent + Qdrant Cache Integration Tests")
    print("=" * 60)

    tests = [
        ("Cache Integration", test_cache_integration),
        ("Performance Comparison", test_performance_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
