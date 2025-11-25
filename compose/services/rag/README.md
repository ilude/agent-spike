# SurrealDB RAG Service

Clean RAG (Retrieval Augmented Generation) implementation using SurrealDB vector search and MinIO transcript storage.

## Features

- **SurrealDB Vector Search**: HNSW cosine similarity search on 1,390 videos
- **MinIO Transcript Storage**: Retrieves full transcripts for context
- **No Qdrant Dependencies**: Clean migration from Qdrant
- **Configurable Limits**: Result limits, score thresholds, transcript truncation
- **Channel Filtering**: Filter results by channel name
- **Error Handling**: Graceful fallbacks for service unavailability

## Architecture

```
User Query
    ↓
SurrealDB RAG Service
    ↓
search_videos_by_text() → Infinity API → Embedding
    ↓
SurrealDB Vector Search (HNSW)
    ↓
Results + MinIO Transcript Fetch
    ↓
Formatted Context for LLM
```

## Usage

### Basic Context Retrieval

```python
from compose.services.rag import SurrealDBRAG

# Initialize RAG service
rag = SurrealDBRAG()

# Retrieve context
results = await rag.retrieve_context(
    query="How to build AI agents?",
    limit=5
)

# Format for LLM prompt
context = await rag.format_context_for_llm(
    query="How to build AI agents?",
    limit=5
)
```

### With Channel Filter

```python
rag = SurrealDBRAG()

results = await rag.retrieve_context(
    query="machine learning tutorials",
    limit=10,
    channel_filter="AI Explained"
)
```

### With Score Threshold

```python
# Only return results with similarity >= 0.7
rag = SurrealDBRAG(min_score=0.7)

results = await rag.retrieve_context(query="AI agents")
```

### Extract Source Citations

```python
rag = SurrealDBRAG()

results = await rag.retrieve_context(query="AI agents")
sources = rag.extract_sources(results)

for source in sources:
    print(f"{source['title']} - {source['url']}")
```

### Convenience Method

```python
# Get both context and sources in one call
context, sources = await rag.get_context_and_sources(
    query="How to build AI agents?",
    limit=5
)
```

## Configuration

### Constructor Parameters

- `default_limit` (int): Default number of results (default: 5)
- `min_score` (float): Minimum similarity score 0.0-1.0 (default: 0.0)
- `max_transcript_chars` (int): Max characters per transcript (default: 4000)

### Environment Variables

Configured via `compose.services.surrealdb.repository`:

- `INFINITY_URL`: Embedding service URL (default: `http://192.168.16.241:7997`)
- `INFINITY_MODEL`: Embedding model (default: `Alibaba-NLP/gte-large-en-v1.5`)

## Integration with Existing Code

The RAG service is a drop-in replacement for Qdrant-based RAG. Current usage in `compose/api/routers/chat.py`:

```python
# OLD: Qdrant-based search (lines 514-554)
query_vector = await get_embedding(message)
search_results = await semantic_search(query_vector, limit=5)

# NEW: SurrealDB RAG service
from compose.services.rag import SurrealDBRAG

rag = SurrealDBRAG()
context, sources = await rag.get_context_and_sources(
    query=message,
    limit=5
)
```

## Context Format

The service formats context as:

```
[Video: "Introduction to AI Agents"]
Channel: AI Explained
Relevance: 0.920

Transcript:
This is a sample transcript about AI agents...

---

[Video: "Building Multi-Agent Systems"]
Channel: Tech Tutorial
Relevance: 0.880

Transcript:
We'll discuss how to build and coordinate multiple agents...
```

## Error Handling

- **SurrealDB unavailable**: Raises `ConnectionError`
- **Infinity API unavailable**: Raises `Exception` with "embedding" in message
- **MinIO unavailable**: Continues with "(Transcript not available)" message
- **Empty query**: Raises `ValueError`
- **Invalid limit**: Raises `ValueError`

## Testing

```bash
# Run all RAG tests
uv run pytest compose/services/tests/unit/test_rag_surrealdb.py -v

# Run specific test class
uv run pytest compose/services/tests/unit/test_rag_surrealdb.py::TestContextRetrieval -v
```

## Migration Notes

### From Qdrant to SurrealDB

1. **No Qdrant imports**: Service is completely independent
2. **Same API surface**: `retrieve_context()`, `format_context_for_llm()`, `extract_sources()`
3. **Better integration**: Uses existing `search_videos_by_text()` from SurrealDB repository
4. **Simpler dependencies**: No Qdrant client, uses existing infrastructure

### Existing Qdrant Code (Phase 4)

The following files still use Qdrant and will be handled in Phase 4 (Qdrant removal):

- `compose/services/cache/qdrant_cache.py` - Old cache implementation
- `compose/services/tagger/retriever.py` - Tag retrieval for normalization
- `compose/api/routers/chat.py` (lines 514-554) - RAG search in WebSocket endpoint

## Performance

- **Vector search**: HNSW index on 1024-dim embeddings (gte-large-en-v1.5)
- **Typical query time**: ~50-200ms for 5 results
- **Transcript fetch**: ~10-50ms per video from MinIO
- **Total RAG flow**: ~100-500ms depending on result count

## Future Enhancements

- [ ] Chunk-level search (use `semantic_search_chunks()` for timestamp-level retrieval)
- [ ] Date range filtering (add `min_date`/`max_date` to `retrieve_context()`)
- [ ] Multi-query expansion (generate multiple search queries for better recall)
- [ ] Hybrid search (combine vector search with BM25 keyword search)
- [ ] Result re-ranking (use cross-encoder for better relevance)
- [ ] Caching (cache frequent queries to reduce latency)
