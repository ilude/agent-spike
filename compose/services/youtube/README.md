# YouTube Service

Utilities for fetching YouTube video transcripts and metadata.

## Purpose

Provide reusable YouTube functionality:
- Extract video IDs from various URL formats
- Fetch transcripts with proxy support (Webshare)
- Optional caching integration
- Handle errors gracefully

## Quick Start

```python
from compose.services.youtube import extract_video_id, get_transcript

# Extract video ID
video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
print(video_id)  # "dQw4w9WgXcQ"

# Fetch transcript (no caching)
transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")
print(transcript[:100])

# Fetch with caching
from compose.services.cache import create_in_memory_cache

cache = create_in_memory_cache()
transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ", cache=cache)
# Second call uses cache (faster)
transcript2 = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ", cache=cache)
```

## Proxy Support

The transcript service automatically uses Webshare proxy if configured in `.env`:

```bash
WEBSHARE_PROXY_USERNAME=your_username
WEBSHARE_PROXY_PASSWORD=your_password
```

This avoids YouTube rate limiting when fetching many transcripts.

## Integration with Cache Service

```python
from compose.services.youtube import get_transcript
from compose.services.cache import create_qdrant_cache

# Create cache
cache = create_qdrant_cache(collection_name="transcripts")

# Fetch with automatic caching
transcript = get_transcript(
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    cache=cache
)

# Check if cached
video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
cache_key = f"youtube:transcript:{video_id}"
is_cached = cache.exists(cache_key)
```

## Low-Level API

For more control, use `YouTubeTranscriptService` directly:

```python
from compose.services.youtube import YouTubeTranscriptService

service = YouTubeTranscriptService()
transcript, error = service.fetch_transcript_safe("dQw4w9WgXcQ")

if error:
    print(f"Failed: {error}")
else:
    print(f"Success: {transcript[:100]}")
```

## File Structure

```
compose/services/youtube/
├── __init__.py           # Exports
├── utils.py              # High-level functions (extract_video_id, get_transcript)
├── transcript_service.py # Low-level YouTubeTranscriptService class
└── README.md             # This file
```

## Testing

```bash
# Unit tests
uv run pytest compose/tests/unit/test_youtube*.py -v

# Integration test (requires API key)
uv run python -c "
from compose.services.youtube import get_transcript
transcript = get_transcript('https://youtube.com/watch?v=dQw4w9WgXcQ')
print(transcript[:200])
"
```

## See Also

- `archive/` - Archive service for storing fetched transcripts
- `cache/` - Cache service for fast retrieval
- YouTube Transcript API docs: https://github.com/jdepoix/youtube-transcript-api
