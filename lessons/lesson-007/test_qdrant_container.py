# -*- coding: utf-8 -*-
"""Test Qdrant container integration."""
import os
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from compose.lib.env_loader import load_root_env
load_root_env()

from compose.services.cache import create_qdrant_cache

def test_qdrant_container():
    """Test that QdrantCache can connect to the Qdrant container."""
    # Create cache with Qdrant URL from environment
    qdrant_url = os.getenv("QDRANT_URL")
    print(f"Connecting to Qdrant at: {qdrant_url}")
    
    cache = create_qdrant_cache(
        collection_name="test_container",
        qdrant_url=qdrant_url
    )
    
    # Test basic operations (cache expects dict-like data)
    test_key = "https://example.com/test"
    test_value = {
        "url": "https://example.com/test",
        "markdown": "# Test Content\n\nThis is test content for Qdrant container integration.",
        "title": "Test Page"
    }
    
    print("Setting test value...")
    cache.set(test_key, test_value, metadata={"source": "container_test"})
    
    print("Getting test value...")
    result = cache.get(test_key)
    
    assert result is not None, "Expected result, got None"
    assert result["url"] == test_value["url"], f"URL mismatch"
    print(f"[OK] Retrieved: {result['title']}")
    
    # Test search
    print("Testing search...")
    results = cache.search("test content container", limit=5)
    print(f"[OK] Search found {len(results)} results")
    
    if results:
        first_result = results[0]
        print(f"  - Top result score: {first_result.get('score', 'N/A')}")
        print(f"  - Result data: {first_result.get('data', {}).get('title', 'N/A')}")
    
    print("\n[SUCCESS] All tests passed! Qdrant container integration working correctly.")
    print(f"[INFO] Web UI available at: http://localhost:6335/dashboard")
    print(f"[INFO] Qdrant is running in container mode (not embedded)")

if __name__ == "__main__":
    test_qdrant_container()
