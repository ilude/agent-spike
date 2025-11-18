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

### Cache Service (`cache/`)

Fast semantic search and metadata filtering with Qdrant.

**Purpose**: Cache processed content for instant retrieval

```python
from compose.services.cache import create_qdrant_cache

cache = create_qdrant_cache(collection_name="content")

# Store with metadata
cache.set(
    "youtube:video:dQw4w9WgXcQ",
    {"transcript": "...", "tags": ["music", "80s"]},
    metadata={"type": "youtube_video", "year": "2024"}
)

# Semantic search
results = cache.search("80s music videos", limit=5)

# Filter by metadata
youtube_only = cache.filter({"type": "youtube_video"})
```

**Key features**:
- Semantic search with sentence-transformers
- Metadata filtering
- In-memory implementation for testing
- Lazy imports (Qdrant optional)

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
from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_writer

# Initialize services
cache = create_qdrant_cache(collection_name="videos")
archive = create_local_archive_writer()

def process_video(url: str):
    video_id = extract_video_id(url)

    # 1. Check cache first (fast path)
    cache_key = f"youtube:video:{video_id}"
    if cache.exists(cache_key):
        return cache.get(cache_key)

    # 2. Fetch transcript (expensive) and archive immediately
    transcript = get_transcript(url)
    archive.archive_youtube_video(video_id, url, transcript)

    # 3. Generate tags (expensive LLM call) and archive
    tags = generate_tags(transcript)  # Your LLM agent
    archive.add_llm_output(video_id, "tags", tags, "claude-haiku", 0.001)

    # 4. Cache result for fast future access
    data = {"video_id": video_id, "transcript": transcript, "tags": tags}
    cache.set(cache_key, data, metadata={"type": "youtube_video"})

    return data
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

**Before (lesson-007)**:
```python
from cache import QdrantCache
cache = QdrantCache(collection_name="content")
```

**After**:
```python
from compose.services.cache import create_qdrant_cache
cache = create_qdrant_cache(collection_name="content")
```

**Backward compatibility**: Lesson modules still work via re-exports, but new code should import directly from `compose.services.*`.

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
