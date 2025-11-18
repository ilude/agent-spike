# Cache Service

Content caching service with semantic search and metadata filtering.

## Purpose

Cache content that's expensive to fetch or compute:
- YouTube video transcripts and metadata
- Webpage content (converted to markdown)
- LLM-generated tags and summaries
- Any data that benefits from fast retrieval

## Design Principles

- **Protocol-first**: Easy to mock and swap implementations
- **Dependency injection**: Configuration passed in, not hard-coded
- **Composition**: Services compose together
- **Semantic search**: Find similar content using vector embeddings
- **Metadata filtering**: Organize and filter by type, source, tags

## Quick Start

```python
from tools.services.cache import create_qdrant_cache

# Use defaults (compose/data/qdrant)
cache = create_qdrant_cache(collection_name="content")

# Cache YouTube video
cache.set(
    "youtube:video:dQw4w9WgXcQ",
    {
        "video_id": "dQw4w9WgXcQ",
        "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "transcript": "...",
        "tags": "music, 80s, meme",
    },
    metadata={
        "type": "youtube_video",
        "source": "youtube-transcript-api",
        "tags": ["music", "80s"],
    }
)

# Exact lookup
result = cache.get("youtube:video:dQw4w9WgXcQ")

# Semantic search
similar = cache.search("80s music videos", limit=5)

# Filter by metadata
youtube_only = cache.filter({"type": "youtube_video"}, limit=100)
```

## Custom Configuration

```python
from pathlib import Path
from tools.services.cache import CacheConfig, QdrantCache

# Custom location and model
config = CacheConfig(
    cache_dir=Path("/custom/cache"),
    collection_name="my_content",
    embedding_model="all-mpnet-base-v2",  # Larger, more accurate
)

cache = QdrantCache(config)
```

## Testing with InMemoryCache

```python
from tools.services.cache import create_in_memory_cache

# For unit tests (no persistence, no Qdrant dependency)
cache = create_in_memory_cache()
cache.set("test", {"data": "value"})
assert cache.get("test") == {"data": "value"}
```

## Integration Example

```python
from tools.services.cache import create_qdrant_cache
from tools.services.archive import create_local_archive_writer

# Composition: Cache + Archive working together
cache = create_qdrant_cache(collection_name="videos")
archive = create_local_archive_writer()

def process_video(url: str):
    video_id = extract_video_id(url)
    cache_key = f"youtube:video:{video_id}"

    # Check cache first
    if cache.exists(cache_key):
        return cache.get(cache_key)

    # Not cached - fetch and archive
    transcript = fetch_transcript(url)
    archive.archive_youtube_video(video_id, url, transcript)

    # Generate tags (expensive)
    tags = generate_tags(transcript)
    archive.add_llm_output(video_id, "tags", tags, "claude-haiku", 0.001)

    # Cache for fast retrieval
    data = {"video_id": video_id, "transcript": transcript, "tags": tags}
    cache.set(cache_key, data, metadata={"type": "youtube_video"})

    return data
```

## File Structure

Cache service is organized as:

```
tools/services/cache/
├── __init__.py           # Exports
├── cache_manager.py      # Protocol (interface)
├── qdrant_cache.py       # Qdrant implementation
├── in_memory_cache.py    # In-memory implementation (testing)
├── models.py             # Pydantic models
├── config.py             # Configuration objects
├── factory.py            # Factory functions
└── README.md             # This file
```

## Testing

```bash
# Run unit tests
uv run pytest tools/tests/unit/test_cache*.py -v

# With coverage
uv run pytest tools/tests/unit/test_cache*.py --cov=tools.services.cache
```

## See Also

- `archive/` - Archive service for storing expensive-to-fetch content
- `protocols.py` - CacheManager protocol definition
- `models.py` - Pydantic data models
- `config.py` - Configuration objects
