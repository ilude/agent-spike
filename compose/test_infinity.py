"""Test Infinity embedding service integration.

This script tests:
1. Infinity container is running and accessible
2. Embedding generation via HTTP API
3. Model dimensions match expected values
"""

import httpx
import sys

# Fix Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INFINITY_URL = "http://localhost:7997"
MODEL = "BAAI/bge-m3"
EXPECTED_DIM = 1024


def test_infinity_health():
    """Test if Infinity service is accessible."""
    try:
        response = httpx.get(f"{INFINITY_URL}/health", timeout=5.0)
        response.raise_for_status()
        print(f"✓ Infinity service is running")
        return True
    except httpx.HTTPError as e:
        print(f"✗ Infinity service not accessible: {e}")
        return False


def test_embedding_generation():
    """Test embedding generation."""
    try:
        response = httpx.post(
            f"{INFINITY_URL}/embeddings",
            json={
                "model": MODEL,
                "input": ["test text for embedding"]
            },
            timeout=30.0
        )
        response.raise_for_status()

        data = response.json()
        embedding = data["data"][0]["embedding"]

        print(f"✓ Generated embedding with dimension: {len(embedding)}")

        if len(embedding) == EXPECTED_DIM:
            print(f"✓ Dimension matches expected: {EXPECTED_DIM}")
            return True
        else:
            print(f"✗ Unexpected dimension: {len(embedding)} (expected {EXPECTED_DIM})")
            return False

    except httpx.HTTPError as e:
        print(f"✗ Embedding generation failed: {e}")
        return False
    except (KeyError, IndexError) as e:
        print(f"✗ Unexpected response format: {e}")
        return False


def test_cache_integration():
    """Test QdrantCache with Infinity integration."""
    try:
        # Add parent directory to path for imports
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from compose.services.cache import create_qdrant_cache
        from compose.lib.env_loader import load_root_env

        load_root_env()

        # Create cache with Infinity URL
        cache = create_qdrant_cache(
            collection_name="test_infinity",
            qdrant_url="http://localhost:6335",
            infinity_url=INFINITY_URL
        )

        print(f"✓ Cache created with Infinity integration")

        # Test setting a value (triggers embedding generation)
        cache.set(
            "test_key",
            {"content": "This is a test document for Infinity embeddings"},
            {"type": "test"}
        )

        print(f"✓ Cache set with Infinity embedding")

        # Test retrieval
        result = cache.get("test_key")
        if result and result.get("content"):
            print(f"✓ Cache retrieval successful")

        # Cleanup
        cache.delete("test_key")
        cache.close()

        return True

    except Exception as e:
        print(f"✗ Cache integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing Infinity Embedding Service Integration\n")
    print("=" * 50)

    # Test 1: Health check
    print("\n1. Health Check")
    health_ok = test_infinity_health()

    if not health_ok:
        print("\nInfinity service not ready. Start with: cd compose && docker compose up -d infinity")
        sys.exit(1)

    # Test 2: Embedding generation
    print("\n2. Embedding Generation")
    embedding_ok = test_embedding_generation()

    # Test 3: Cache integration
    print("\n3. Cache Integration")
    cache_ok = test_cache_integration()

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Health Check: {'PASS' if health_ok else 'FAIL'}")
    print(f"  Embedding Generation: {'PASS' if embedding_ok else 'FAIL'}")
    print(f"  Cache Integration: {'PASS' if cache_ok else 'FAIL'}")

    if health_ok and embedding_ok and cache_ok:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
