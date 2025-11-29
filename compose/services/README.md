# Services Architecture

Centralized, reusable services extracted from lesson experiments.

## Design Principles

1. **Protocol-first**: Define interfaces using Python `Protocol` for easy mocking
2. **Dependency injection**: Pass configuration in, don't hard-code paths
3. **Composition over inheritance**: Services compose together cleanly
4. **Factory functions**: Provide sensible defaults while allowing customization
5. **Optional dependencies**: Graceful degradation when deps not installed

## Available Services

### Archive Service (`archive/`)

Store expensive-to-fetch content for future reprocessing.

**Purpose**: Archive anything that costs time or money (transcripts, LLM outputs, API calls)

```python
from compose.services.archive import create_local_archive_writer

archive = create_local_archive_writer()

# Archive YouTube transcript
archive.archive_youtube_video(
    video_id="dQw4w9WgXcQ",
    url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    transcript="transcript text...",
    metadata={"source": "youtube-transcript-api"}
)

# Archive LLM output
archive.add_llm_output(
    video_id="dQw4w9WgXcQ",
    output_type="tags",
    output_value=["AI", "tutorial"],
    model="claude-haiku",
    cost_usd=0.001
)
```

**Key features**:
- JSON storage organized by month (YYYY-MM/)
- Immutable archives (append-only)
- Track LLM costs and processing versions
- Enables reprocessing without re-fetching

### SurrealDB Service (`surrealdb/`)

Video metadata storage and semantic search with SurrealDB + Infinity embeddings.

**Purpose**: Store video records with embeddings for semantic search

```python
from compose.services.surrealdb import get_video, upsert_video, search_videos_by_text

# Get video by ID
video = await get_video("dQw4w9WgXcQ")

# Semantic search
results = await search_videos_by_text("80s music videos", limit=5)

# Get all videos
from compose.services.surrealdb import get_all_videos
videos = await get_all_videos(limit=100)
```

**Key features**:
- Vector search with SurrealDB HNSW indexes
- Infinity API for embedding generation
- Pipeline state tracking for reprocessing
- Channel and topic relationships

### Cache Service (`cache/`) - DEPRECATED

> **⚠️ DEPRECATED**: Replaced by SurrealDB service. See `surrealdb/` above.

Legacy cache service using Qdrant. Kept for reference only.

### YouTube Service (`youtube/`)

Fetch video transcripts and metadata with proxy support.

**Purpose**: Reusable YouTube utilities across all lessons

```python
from compose.services.youtube import extract_video_id, get_transcript

# Extract video ID
video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")

# Fetch transcript (with optional caching)
transcript = get_transcript(
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    cache=cache  # Optional
)
```

**Key features**:
- Webshare proxy support (avoid rate limits)
- Multiple URL format support
- Optional cache integration
- Error handling with descriptive messages

## Service Composition

Services are designed to work together:

```python
from compose.services.youtube import extract_video_id, get_transcript
from compose.services.surrealdb import get_video, upsert_video
from compose.services.surrealdb.models import VideoRecord
from compose.services.archive import create_local_archive_writer

# Initialize services
archive = create_local_archive_writer()

async def process_video(url: str):
    video_id = extract_video_id(url)

    # 1. Check SurrealDB first (fast path)
    existing = await get_video(video_id)
    if existing:
        return existing

    # 2. Fetch transcript (expensive) and archive immediately
    transcript = get_transcript(url)
    archive.archive_youtube_video(video_id, url, transcript)

    # 3. Generate tags (expensive LLM call) and archive
    tags = generate_tags(transcript)  # Your LLM agent
    archive.add_llm_output(video_id, "tags", tags, "claude-haiku", 0.001)

    # 4. Store in SurrealDB with embedding
    video = VideoRecord(
        video_id=video_id,
        url=url,
        title="...",
        pipeline_state={"tags": tags},
    )
    await upsert_video(video)

    return video
```

## Directory Structure

```
compose/services/
├── README.md              # This file
├── archive/               # Archive service
│   ├── __init__.py
│   ├── models.py
│   ├── protocols.py
│   ├── config.py
│   ├── local_writer.py
│   ├── local_reader.py
│   ├── factory.py
│   └── README.md
├── cache/                 # Cache service
│   ├── __init__.py
│   ├── models.py
│   ├── cache_manager.py   # Protocol
│   ├── qdrant_cache.py
│   ├── in_memory_cache.py
│   ├── config.py
│   ├── factory.py
│   └── README.md
└── youtube/               # YouTube service
    ├── __init__.py
    ├── utils.py
    ├── transcript_service.py
    └── README.md
```

## Testing

All services have comprehensive pytest test suites:

```bash
# Run all service tests
uv run pytest compose/tests/unit/ -v

# Run specific service tests
uv run pytest compose/tests/unit/test_archive*.py -v
uv run pytest compose/tests/unit/test_cache*.py -v
uv run pytest compose/tests/unit/test_youtube*.py -v

# With coverage
uv run pytest compose/tests/unit/ --cov=compose.services
```

## Migration from Lessons

Lessons now import from centralized services:

**Before (lesson-007 with Qdrant)**:
```python
from cache import QdrantCache
cache = QdrantCache(collection_name="content")
```

**After (SurrealDB)**:
```python
from compose.services.surrealdb import get_video, upsert_video, search_videos_by_text

# Get video
video = await get_video("video_id")

# Search
results = await search_videos_by_text("query", limit=10)
```

**Note**: The Qdrant-based cache service is deprecated. All new code should use `compose.services.surrealdb`.

## Adding New Services

When extracting code from lessons:

1. **Create service directory**: `compose/services/your_service/`
2. **Define protocol**: Interface for dependency injection
3. **Create models**: Pydantic models for data structures
4. **Implement service**: Concrete implementation(s)
5. **Add factory functions**: Sensible defaults + customization
6. **Write tests**: Unit tests with pytest
7. **Document**: README with examples
8. **Update lessons**: Use factory functions from service

See existing services for patterns to follow.

## Future Services

Candidates for extraction:

- **LLM Agent Service**: Pydantic AI agent creation with observability
- **Web Scraping Service**: Docling-based webpage fetching
- **Embedding Service**: Sentence-transformers wrapper
- **Batch Processing Service**: OpenAI batch API utilities

Extract when patterns stabilize across 2+ lessons.
