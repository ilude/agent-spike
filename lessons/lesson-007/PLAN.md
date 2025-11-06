

# Lesson 007: Cache Manager & Content Ingestion

**Status**: In Progress
**Estimated Time**: 90 minutes
**Prerequisites**: Lessons 001-003 (YouTube agent, Webpage agent, Router)

---

## Learning Objectives

By the end of this lesson, you will understand:

1. **Dependency Injection (DI)** - How to design tools that work with or without caching
2. **Protocol-based interfaces** - Using Python's Protocol for structural subtyping
3. **Vector databases** - Qdrant for semantic search and content storage
4. **Batch content ingestion** - Processing large datasets efficiently
5. **Infrastructure patterns** - Building reusable systems that scale

---

## What We're Building

### Core Components

1. **CacheManager Protocol** (`cache/cache_manager.py`)
   - Interface definition for cache implementations
   - Supports get, set, exists, delete, search, filter operations
   - Enables dependency injection pattern

2. **QdrantCache Implementation** (`cache/qdrant_cache.py`)
   - Production-ready cache using Qdrant vector database
   - Automatic embedding generation with sentence-transformers
   - Semantic search capabilities
   - Metadata filtering

3. **CSV Ingestion Script** (`scripts/ingest_csv.py`)
   - Generic tool for ingesting URL lists from CSV files
   - Uses lesson-003 router for content-type detection
   - Fetches content with lessons 001/002 tools
   - Stores in cache with metadata
   - Progress tracking and error handling

4. **Updated Lessons 001/002** (Dependency Injection)
   - Tools now accept optional `cache` parameter
   - Backward compatible (cache is optional)
   - Cache-aware without hard dependencies

---

## Architecture Pattern: Dependency Injection

### The Problem

Traditional approach creates tight coupling:

```python
from cache import QdrantCache

cache = QdrantCache()  # Hard dependency!

def get_transcript(url: str) -> str:
    # Tool is tightly coupled to QdrantCache
    cached = cache.get(url)
    if cached:
        return cached
    # fetch...
```

**Issues:**
- Can't use the tool without Qdrant installed
- Hard to test (can't inject mock cache)
- Can't swap cache backends
- Violates separation of concerns

### The Solution: Protocol + Optional Injection

```python
from typing import Optional, Protocol

class CacheManager(Protocol):
    def get(self, key: str) -> Optional[dict]: ...
    def set(self, key: str, value: dict): ...

def get_transcript(url: str, cache: Optional[CacheManager] = None) -> str:
    # Tool works with ANY cache implementation
    # Or works without cache at all!
    if cache:
        cached = cache.get(url)
        if cached:
            return cached["transcript"]

    # fetch...

    if cache:
        cache.set(url, {"transcript": result})

    return result
```

**Benefits:**
- ✅ Works with or without cache
- ✅ Can use ANY cache implementation
- ✅ Easy to test (inject mock)
- ✅ Clean separation of concerns
- ✅ Backward compatible

---

## Key Concepts

### 1. Protocol-Based Interfaces

Python's `Protocol` from `typing` enables **structural subtyping** (duck typing with type checking):

```python
from typing import Protocol

class CacheManager(Protocol):
    def get(self, key: str) -> Optional[dict]: ...
    def set(self, key: str, value: dict): ...

# Any class with these methods is compatible!
class QdrantCache:  # No inheritance needed
    def get(self, key: str) -> Optional[dict]:
        # implementation

    def set(self, key: str, value: dict):
        # implementation

# Type checker knows this works:
def use_cache(cache: CacheManager):
    cache.get("key")  # ✓ OK
```

This is different from traditional inheritance - **no base class needed**, just matching methods.

### 2. Vector Databases & Embeddings

**Qdrant** stores data as vectors (embeddings) for semantic search:

```python
# Text → Vector (embedding)
"AI agents tutorial" → [0.23, -0.45, 0.67, ...]  # 384 dimensions

# Search: "artificial intelligence agents"
query_vector = [0.21, -0.43, 0.65, ...]  # Similar vector!

# Qdrant finds similar vectors (cosine similarity)
results = qdrant.search(query_vector, limit=10)
# Returns: documents about AI agents, even without exact wording
```

**Why embeddings?**
- Find content by **meaning**, not just keywords
- "multi-agent systems" matches "agent orchestration"
- Works across synonyms, paraphrasing

**SentenceTransformers** generates embeddings:
- Model: `all-MiniLM-L6-v2` (fast, good quality)
- 384-dimensional vectors
- Trained on semantic similarity

### 3. Metadata Filtering

Store structured metadata alongside embeddings:

```python
cache.set(
    "youtube:video123",
    {"transcript": "..."},
    metadata={
        "type": "youtube_video",
        "source": "Nate Jones",
        "upload_date": "2024-10-15",
        "tags": ["ai", "agents"]
    }
)

# Later: Semantic search + metadata filter
results = cache.search(
    "agent patterns",
    filters={"type": "youtube_video", "source": "Nate Jones"}
)
```

---

## Implementation Steps

### Step 1: Update Lessons 001/002 (30 min)

Add dependency injection to existing tools:

1. Import Protocol and define CacheManager interface
2. Add optional `cache` parameter to tools
3. Check cache before fetching
4. Store in cache after fetching
5. Test backward compatibility

**Files modified:**
- `lessons/lesson-001/youtube_agent/tools.py`
- `lessons/lesson-002/webpage_agent/tools.py`

### Step 2: Implement Cache Infrastructure (40 min)

Build the cache system:

1. Create `CacheManager` protocol
2. Create `QdrantCache` implementation
3. Add data models for type safety
4. Test basic operations (get, set, exists, delete)
5. Test semantic search

**Files created:**
- `cache/cache_manager.py` - Protocol definition
- `cache/qdrant_cache.py` - Qdrant implementation
- `cache/models.py` - Data models
- `cache/__init__.py` - Module exports

### Step 3: Build CSV Ingestion Script (20 min)

Create generic ingestion tool:

1. Parse CSV with validation
2. Route URLs using lesson-003 router
3. Fetch content with cache injection
4. Store with metadata from CSV columns
5. Add progress tracking and error handling

**Files created:**
- `scripts/ingest_csv.py` - Main ingestion script

---

## Testing Plan

### Unit Tests (`test_cache.py`)

1. **CacheManager Protocol**
   - Test get/set/exists/delete operations
   - Test with mock implementation

2. **QdrantCache**
   - Test basic operations
   - Test semantic search
   - Test metadata filtering
   - Test cache persistence

3. **CSV Ingestion**
   - Test with sample CSV
   - Test error handling
   - Test skip-existing logic

### Integration Tests

1. **End-to-End with Real Data**
   - Ingest Nate Jones videos CSV
   - Verify all 169 videos cached
   - Test semantic search on corpus
   - Test metadata filtering

---

## Usage Examples

### Example 1: Basic Caching

```python
from cache import QdrantCache

# Initialize cache
cache = QdrantCache(collection_name="content")

# Store data
cache.set(
    "youtube:video123",
    {"transcript": "Learn about AI agents..."},
    metadata={"type": "youtube_video"}
)

# Retrieve data
data = cache.get("youtube:video123")
print(data["transcript"])
```

### Example 2: Using with Existing Tools

```python
from cache import QdrantCache
from lessons.lesson001.youtube_agent.tools import get_transcript

# Create cache
cache = QdrantCache()

# First call: fetches from YouTube API
transcript1 = get_transcript("https://youtube.com/watch?v=...", cache=cache)

# Second call: loads from cache (instant!)
transcript2 = get_transcript("https://youtube.com/watch?v=...", cache=cache)
```

### Example 3: Semantic Search

```python
from cache import QdrantCache

cache = QdrantCache(collection_name="content")

# Search by meaning
results = cache.search(
    "how to build multi-agent systems",
    limit=10,
    filters={"type": "youtube_video"}
)

for item in results:
    print(f"Score: {item['_score']:.2f} - {item.get('title', 'N/A')}")
```

### Example 4: CSV Ingestion

```bash
# Ingest all Nate Jones videos
cd lessons/lesson-007
python scripts/ingest_csv.py \
  --csv ../../projects/video-lists/nate_jones_videos.csv \
  --collection nate_content

# Output:
# Reading CSV: ../../projects/video-lists/nate_jones_videos.csv
# Initializing cache (collection: nate_content)...
# Cache initialized. Current count: 0
# Ingesting content: 100%|███████| 169/169 [15:23<00:00,  5.46s/it]
#
# Ingestion Complete!
# ┏━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
# ┃ Metric           ┃ Count ┃
# ┡━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
# │ Total rows       │ 169   │
# │ Processed        │ 165   │
# │ Skipped (cached) │ 0     │
# │ Errors           │ 4     │
# │ YouTube videos   │ 165   │
# │ Cache total      │ 165   │
# └──────────────────┴───────┘
```

---

## Dependencies

New packages required for lesson-007:

- `qdrant-client` - Qdrant vector database client
- `sentence-transformers` - Embedding generation
- `tqdm` - Progress bars
- `rich` - Beautiful console output

These will be added to `pyproject.toml` as `lesson-007` dependency group.

---

## Success Criteria

✅ Lesson-001 tools work with and without cache
✅ Lesson-002 tools work with and without cache
✅ QdrantCache implements CacheManager protocol
✅ Can ingest Nate Jones videos CSV (169 videos)
✅ Semantic search finds relevant content
✅ Metadata filtering works
✅ Cache persists across runs

---

## Next Steps

After completing this lesson:

1. **Lesson 008: Batch Processing** - Use OpenAI Batch API to tag all cached content
2. **Recommendation Engine** - Build content discovery based on preferences
3. **Application Suggester** - Connect learnings to active projects

---

## Notes

### Design Decisions

1. **Why Qdrant?**
   - Already installed (Mem0 dependency from lesson-006)
   - Excellent semantic search
   - Local-first (no external services)
   - Production-ready

2. **Why sentence-transformers?**
   - High-quality embeddings
   - Fast inference
   - Model: all-MiniLM-L6-v2 (384D, ~120MB)
   - Widely used, well-documented

3. **Why generic CSV ingestion?**
   - Works with any URL list
   - Reusable across projects
   - Clean separation of data and logic

4. **Why dependency injection?**
   - Clean architecture
   - Testable
   - Flexible (swap backends)
   - Backward compatible

### Common Pitfalls

1. **Forgetting to pass cache** - Tools default to no cache, make sure to inject!
2. **Cache key mismatches** - Use consistent key format (e.g., `youtube:transcript:{video_id}`)
3. **Embedding model download** - First run downloads ~120MB model
4. **CSV encoding** - Make sure CSV is UTF-8 encoded

---

**Estimated completion time: 90 minutes**

Ready to build a production-grade caching system! 🚀
