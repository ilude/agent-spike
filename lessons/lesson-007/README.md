# Lesson 007: Cache Manager & Content Ingestion

**Quick Reference Guide**

## What This Lesson Teaches

- Dependency injection pattern for clean architecture
- Protocol-based interfaces in Python
- Qdrant vector database for semantic search
- Batch content ingestion from CSV files

## Quick Start

### 1. Install Dependencies

```bash
uv sync --group lesson-007
```

### 2. Set Up Environment

```bash
# Copy API keys from lesson-001
cp ../lesson-001/.env .
```

### 3. Test Basic Cache Operations

```bash
uv run python test_cache.py
```

### 4. Ingest Nate Jones Videos

```bash
cd scripts
uv run python ingest_csv.py \
  --csv ../../../projects/video-lists/nate_jones_videos.csv \
  --collection nate_content
```

## Core Components

### CacheManager Protocol

Interface for dependency injection - any class implementing these methods works:

```python
from cache import CacheManager

class MyCacheManager:
    def get(self, key: str) -> Optional[dict]: ...
    def set(self, key: str, value: dict, metadata: dict = None): ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def search(self, query: str, limit: int = 10, filters: dict = None) -> list: ...
    def filter(self, conditions: dict, limit: int = 100) -> list: ...
```

### QdrantCache

Production-ready implementation with semantic search:

```python
from cache import QdrantCache

# Initialize
cache = QdrantCache(collection_name="content")

# Store
cache.set(
    "youtube:video123",
    {"transcript": "..."},
    metadata={"type": "youtube_video", "source": "Nate Jones"}
)

# Retrieve
data = cache.get("youtube:video123")

# Semantic search
results = cache.search("multi-agent systems", limit=10)
```

### CSV Ingestion Script

Generic tool for batch content ingestion:

```bash
# Basic usage
python ingest_csv.py --csv path/to/urls.csv

# With options
python ingest_csv.py \
  --csv path/to/urls.csv \
  --collection my_content \
  --limit 50 \
  --no-skip
```

## Usage Examples

### Example 1: Use Existing Tools with Cache

```python
from cache import QdrantCache
from lessons.lesson001.youtube_agent.tools import get_transcript

cache = QdrantCache()

# First call: fetches from YouTube
transcript = get_transcript("https://youtube.com/watch?v=xyz", cache=cache)

# Second call: instant (from cache)
transcript = get_transcript("https://youtube.com/watch?v=xyz", cache=cache)
```

### Example 2: Search Cached Content

```python
from cache import QdrantCache

cache = QdrantCache(collection_name="nate_content")

# Semantic search
results = cache.search(
    "how to coordinate multiple agents",
    limit=5,
    filters={"type": "youtube_video"}
)

for result in results:
    print(f"{result['title']} (score: {result['_score']:.2f})")
```

### Example 3: Filter by Metadata

```python
from cache import QdrantCache

cache = QdrantCache(collection_name="nate_content")

# Get all videos from 2024
videos_2024 = cache.filter(
    {"type": "youtube_video"},
    limit=100
)

# Filter in Python for more complex logic
recent = [v for v in videos_2024 if v.get("upload_date", "").startswith("2024")]
```

## File Structure

```
lesson-007/
├── cache/
│   ├── __init__.py              # Module exports
│   ├── cache_manager.py         # Protocol definition
│   ├── qdrant_cache.py          # Qdrant implementation
│   └── models.py                # Data models
├── scripts/
│   └── ingest_csv.py            # CSV ingestion tool
├── PLAN.md                      # Detailed learning plan
├── README.md                    # This file
├── test_cache.py                # Test suite
└── .env                         # API keys (gitignored)
```

## Common Commands

```bash
# Run tests
uv run python test_cache.py

# Interactive REPL (no quotes needed for URLs!)
make ingest                                      # From project root
uv run python lessons/lesson-007/ingest_repl.py # From anywhere

# Scheduled ingestion (rate-limited, 1 video per 15 minutes)
make ingest-nate                                 # Process Nate Jones videos
uv run python scheduled_ingest.py videos.csv     # Custom CSV

# Ingest single video
uv run python ingest_single_video.py "https://youtube.com/watch?v=VIDEO_ID"

# List cached videos
uv run python list_cached_videos.py

# Verify specific video
uv run python verify_cached_video.py VIDEO_ID

# Ingest CSV (batch, no rate limiting - legacy)
uv run python scripts/ingest_csv.py --csv path/to/file.csv

# Ingest with limit (for testing)
uv run python scripts/ingest_csv.py --csv file.csv --limit 10

# Check cache contents (interactive Python)
uv run python
>>> from cache import QdrantCache
>>> cache = QdrantCache(collection_name="content")
>>> cache.count()
165
```

## Key Concepts

**Dependency Injection**: Tools accept optional cache parameter, work with or without it

**Protocols**: Structural typing - no inheritance needed, just matching methods

**Vector Search**: Embeddings enable semantic search (meaning-based, not keyword-based)

**Metadata Filtering**: Combine semantic search with structured filters

## Troubleshooting

**"Collection not found"**
→ Cache is empty or collection name mismatch. Check collection name.

**"Model download failed"**
→ First run downloads ~120MB embedding model. Check internet connection.

**"CSV must have 'url' column"**
→ CSV must have a column named `url`. Check CSV headers.

**"No module named 'cache'"**
→ Run from lesson-007 directory or fix Python path.

## Next Steps

After completing this lesson:

1. Review `PLAN.md` for detailed implementation guide
2. Read `COMPLETE.md` (after completing lesson) for learnings
3. Move to Lesson 008: Batch Processing with OpenAI

## Dependencies

- `qdrant-client` - Vector database client
- `sentence-transformers` - Embedding generation
- `tqdm` - Progress bars
- `rich` - Console output

(All installed via `uv sync --group lesson-007`)

---

For detailed learning objectives and implementation steps, see `PLAN.md`.
