# Lessons Learned - Message Bus Implementation

## Workflow Tool Selection Insights

### Python Support Varies Widely
- **Native execution**: Windmill, Prefect, Airflow
- **Subprocess only**: Flowise, n8n Python nodes
- **No Python**: SimStudio (TypeScript/Node.js only)

### Licensing Matters
- Windmill: AGPL requires open-sourcing modifications
- Prefect: "Freemium" model with cloud dependency
- Celery: BSD license allows full control

### User Preference: Control > Convenience
When given choice between:
- Simple but limited (Flowise)
- Complex but flexible (Celery + RabbitMQ)
User consistently chose flexibility and control.

## YouTube API Rate Limiting Patterns

### Quota Math
- 10,000 units/day ÷ 1 unit per video = 10,000 videos/day maximum
- Reality: Burst patterns require adaptive limiting
- Solution: Track quota in persistent storage (SQLite)

### Archive-First Saves Quota
```python
# BAD: Re-fetch on every process
def process_video(url):
    data = fetch_youtube_api(url)  # Costs quota!
    return process(data)

# GOOD: Archive once, process many
def ingest_video(url):
    data = fetch_youtube_api(url)  # Costs quota once
    archive.save(data)
    return data

def process_video(url):
    data = archive.load(url)  # Free!
    return process(data)
```

## Integration Architecture Decisions

### Message Queue vs HTTP API
- **HTTP API**: Simple but synchronous, timeout issues
- **Message Queue**: Async, reliable, better for long tasks
- **Hybrid**: HTTP via Flower for N8N, AMQP for direct integration

### Worker Pool Design
```python
# Separate queues prevent blocking
task_routes = {
    'tasks.analyze_youtube': {'queue': 'youtube'},     # CPU-bound
    'tasks.process_webpage': {'queue': 'webpage'},     # I/O-bound
    'tasks.cache_search': {'queue': 'cache'},         # Memory-bound
}
```

### Hot Reload Critical for Development
```bash
# Auto-reload on code changes
celery -A tasks worker --autoreload

# vs Docker rebuild cycle
docker build ... # Slow!
docker-compose restart ... # Lost state!
```

## Common Pitfalls Avoided

### 1. Overengineering Upfront
Started with simple ingestion script, only adding message bus when integration needed.

### 2. Ignoring Rate Limits
YouTube API quota is real constraint - design around it, not against it.

### 3. Losing Expensive Data
Archive everything that costs time/money BEFORE processing.

### 4. Tool Religion
Evaluated multiple options objectively rather than defaulting to familiar tools.

## Key Patterns Emerging

### Dependency Injection Pattern
```python
class YouTubeIngester:
    def __init__(self, archive: ArchiveWriter, cache: CacheManager):
        self.archive = archive  # Inject dependencies
        self.cache = cache
```

### Version Tracking Pattern
```python
# Track processing versions for reprocessing
archive.add_processing_record(
    video_id=video_id,
    version="v2_semantic_chunks",  # Changed chunking strategy
    collection_name="cached_content",
)
```

### Adaptive Rate Limiting Pattern
```python
class AdaptiveLimiter:
    def should_proceed(self) -> bool:
        current_usage = self.get_usage()
        time_remaining = self.time_to_reset()

        if current_usage > 9000:  # 90% used
            return False  # Save for priority

        if time_remaining < 4 and current_usage > 7500:
            return False  # Conserve for end of day

        return True
```

## Architecture Validation

### Why Celery + RabbitMQ Won
1. **Full Python control**: No version conflicts
2. **Production ready**: Battle-tested at scale
3. **Developer friendly**: Hot reload, good debugging
4. **Integration ready**: HTTP and AMQP interfaces
5. **Monitoring built-in**: Flower provides visibility

### Trade-offs Accepted
- More complex setup than SaaS solutions
- Self-hosted infrastructure management
- Manual queue configuration
- No visual workflow designer (use N8N for that)

## Next Architecture Decisions

### Consider Adding
- [ ] Prometheus metrics for queue depths
- [ ] Dead letter queues for failed tasks
- [ ] Circuit breaker for API failures
- [ ] Backup quota from multiple API keys
- [ ] Caching layer for repeat requests

### Avoid Unless Needed
- GraphQL API (REST is sufficient)
- Kubernetes (Docker Compose handles current scale)
- Custom workflow DSL (Celery chains work fine)
- Multi-region deployment (local-first approach)