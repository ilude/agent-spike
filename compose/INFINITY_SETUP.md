# Infinity Embedding Service Setup

## Overview

The Infinity embedding service provides CPU-based embeddings via HTTP API, eliminating the need for heavy PyTorch/CUDA dependencies in the platform-api container.

**Model**: BAAI/bge-m3 (1024-dim embeddings, 8,192 token context)
**Container**: `michaelf34/infinity:latest`
**Port**: 7997
**Model Storage**: Docker named volume `infinity_models`

## Quick Start

### 1. Start the Service

```bash
cd compose
docker compose up -d infinity
```

The first startup will download the bge-m3 model (~2.3GB) to the named volume. This takes several minutes.

### 2. Verify Service Health

```bash
# Check container status
docker ps --filter "name=infinity"

# Test health endpoint
curl http://localhost:7997/health

# Check logs for model loading
docker compose logs infinity
```

### 3. Test Integration

```bash
cd compose
uv run python test_infinity.py
```

This test script verifies:
- Infinity service is accessible
- Embedding generation works
- QdrantCache integration with Infinity
- Embedding dimensions match expected values (1024)

## Volume Portability

### Why Named Volumes?

The bge-m3 model is ~2.3GB. Using a Docker named volume allows you to:
- Preserve models across container rebuilds
- Export/import models between dev machines
- Avoid re-downloading models on each machine

### Export Models for Another Machine

```bash
# Create backup of infinity_models volume
docker run --rm \
  -v compose_infinity_models:/source \
  -v C:/Projects/Personal/agent-spike/compose/data/infinity_backup:/backup \
  alpine tar czf /backup/infinity_models.tar.gz -C /source .
```

Transfer `compose/data/infinity_backup/infinity_models.tar.gz` to the new machine.

### Import Models on New Machine

```bash
# Create the named volume (if it doesn't exist)
docker volume create compose_infinity_models

# Restore from backup
docker run --rm \
  -v compose_infinity_models:/target \
  -v C:/Projects/Personal/agent-spike/compose/data/infinity_backup:/backup \
  alpine tar xzf /backup/infinity_models.tar.gz -C /target
```

Now start the Infinity service - it will use the pre-downloaded models instead of downloading again.

### Check Volume Size

```bash
# Inspect volume
docker volume inspect compose_infinity_models

# Check size (Linux/Mac)
docker run --rm -v compose_infinity_models:/data alpine du -sh /data

# List contents
docker run --rm -v compose_infinity_models:/data alpine ls -lah /data
```

## Model Configuration

The model is configured in `docker-compose.yml`:

```yaml
infinity:
  image: michaelf34/infinity:latest
  container_name: infinity
  ports:
    - "7997:7997"
  volumes:
    - infinity_models:/app/.cache
  environment:
    - MODEL_ID=BAAI/bge-m3
    - PORT=7997
    - BATCH_SIZE=32
    - ENGINE=torch
```

**Model Details:**
- **bge-m3**: Multilingual, 1024-dim, 8,192 token context window
- **Alternative models**: See `embedding_pipeline_spec_for_coding_model.md` for Phase 2 options (gte-large-en-v1.5)

## Integration with QdrantCache

The QdrantCache service automatically uses Infinity when configured:

```python
from compose.services.cache import create_qdrant_cache

cache = create_qdrant_cache(
    collection_name="cached_content",
    qdrant_url="http://localhost:6335",
    infinity_url="http://localhost:7997"  # Use Infinity for embeddings
)

# Set data - triggers embedding generation via Infinity
cache.set(
    "video_123",
    {"transcript": "Long video transcript..."},
    {"type": "youtube_video"}
)
```

The cache now:
1. Sends text to Infinity HTTP API
2. Receives 1024-dim embedding vector
3. Stores in Qdrant with the data

No sentence-transformers or PyTorch needed in the API container!

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker compose logs infinity

# Common issues:
# - Port 7997 already in use: Change port in docker-compose.yml
# - Out of memory: Increase Docker Desktop memory limit
# - Model download failed: Check internet connection, restart container
```

### Embedding Generation Errors

```bash
# Test direct API call
curl -X POST http://localhost:7997/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "BAAI/bge-m3", "input": ["test text"]}'

# Expected response:
# {"data": [{"embedding": [0.123, -0.456, ...]}]}
```

### Volume Issues

```bash
# Remove volume (WARNING: deletes models)
docker volume rm compose_infinity_models

# Recreate volume
docker volume create compose_infinity_models

# Restart service to re-download
docker compose up -d infinity
```

## Performance

**First Request**: ~2-5 seconds (model loading)
**Subsequent Requests**: ~50-200ms per embedding
**Batch Processing**: Use BATCH_SIZE=32 for optimal throughput

**Benchmark** (single embedding):
- Text: ~200 tokens
- Time: ~100ms
- Throughput: ~10 embeddings/sec

## Future Enhancements

See `.claude/VISION.md` - Embedding Architecture section:

**Phase 2**: Add gte-large-en-v1.5 for global embeddings
- Two-model strategy: bge-m3 for chunks, gte-large for global context
- Dual-collection architecture: `content` + `content_chunks`
- Chunk-aware retrieval with parent document lookup

**Phase 3**: Optimize chunking strategy
- Semantic chunking vs fixed-size chunking
- Token-aware chunk boundaries
- Overlap strategies for better context preservation
