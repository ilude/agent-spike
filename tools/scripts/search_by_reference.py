#!/usr/bin/env python
"""Search videos by what they reference."""
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from script_base import setup_script_environment
setup_script_environment(load_env=False)

from tools.services.cache import create_qdrant_cache

reference_name = sys.argv[1] if len(sys.argv) > 1 else "Archon"
cache = create_qdrant_cache(collection_name="cached_content")

safe_key = reference_name.replace(" ", "_").replace("-", "_").lower()
results = cache.filter({f"ref_{safe_key}": True}, limit=10)

print(f"\nVideos that reference '{reference_name}':\n")
for video in results:
    print(f"- {video.get('video_id')}: {video.get('metadata', {}).get('title', 'N/A')}")
    
cache.close()
