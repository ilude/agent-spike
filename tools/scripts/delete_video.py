#!/usr/bin/env python
"""Delete a video from cache."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.cache import create_qdrant_cache

video_id = sys.argv[1]
cache_key = f"youtube:video:{video_id}"

cache = create_qdrant_cache(collection_name="cached_content")
result = cache.delete(cache_key)
cache.close()

print(f"Deleted {cache_key}: {result}")
