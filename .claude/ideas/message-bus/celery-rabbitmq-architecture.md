# Celery + RabbitMQ Message Bus Architecture

## Overview

A message-driven architecture using Celery (task queue) with RabbitMQ (message broker) to expose the agent-spike Python 3.14 codebase to N8N workflows without dealing with Python version compatibility issues inside N8N.

## Why This Architecture

- **N8N Integration**: Clean HTTP/AMQP boundaries without Python version conflicts
- **Hot Reload Development**: Code changes auto-reload workers (no container rebuilds)
- **Async Processing**: Fire-and-forget pattern perfect for long-running agent tasks
- **Self-Hosted**: Fully local/on-premise deployment
- **Battle-Tested**: Celery + RabbitMQ is a proven production stack

## Core Components

```
N8N → HTTP (Flower) → Celery → RabbitMQ → Worker Processes → Agent Code
     ↘ AMQP (Direct) ↗                  ↘ Result Backend (Redis) ↗
```

## Development Setup

### 1. Infrastructure (docker-compose.dev.yml)

```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"      # AMQP
      - "15672:15672"    # Management UI (admin:admin)
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"      # Result backend

  flower:
    image: mher/flower
    command: celery --broker=amqp://admin:admin@rabbitmq:5672// flower
    ports:
      - "5555:5555"      # HTTP API & Web UI
    depends_on:
      - rabbitmq
```

### 2. Celery Tasks (tasks.py)

```python
from celery import Celery
import sys
from pathlib import Path

# Add lessons to path
sys.path.append(str(Path(__file__).parent / "lessons"))

# Configure Celery
app = Celery('agents',
    broker='amqp://admin:admin@localhost:5672//',
    backend='redis://localhost:6379/0'
)

# Task configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.analyze_youtube': {'queue': 'youtube'},
        'tasks.process_webpage': {'queue': 'webpage'},
        'tasks.cache_search': {'queue': 'cache'},
    }
)

# YouTube Agent Task
@app.task(bind=True, max_retries=3)
def analyze_youtube(self, url):
    try:
        from lesson_001.youtube_agent import YouTubeAgent
        agent = YouTubeAgent()
        return agent.analyze(url)
    except Exception as exc:
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# Webpage Agent Task
@app.task
def process_webpage(url):
    from lesson_002.webpage_agent import WebpageAgent
    return WebpageAgent().process(url)

# Cache Search Task
@app.task
def cache_search(query, limit=5):
    from lesson_007.cache_manager import CacheManager
    cache = CacheManager()
    return cache.search(query, limit=limit)

# Router/Orchestrator Task
@app.task
def route_content(url, process_type="auto"):
    """Smart routing based on URL pattern"""
    if process_type == "auto":
        if "youtube.com" in url or "youtu.be" in url:
            return analyze_youtube.delay(url).id
        elif url.endswith('.pdf'):
            return process_pdf.delay(url).id
        else:
            return process_webpage.delay(url).id
    else:
        task_map = {
            "youtube": analyze_youtube,
            "webpage": process_webpage,
            "cache": cache_search,
        }
        task = task_map.get(process_type, process_webpage)
        return task.delay(url).id
```

### 3. Development Script with Hot Reload

```bash
#!/bin/bash
# dev.sh - Development launcher with auto-reload

# Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# Wait for RabbitMQ to be ready
sleep 5

# Start workers with auto-reload (one per queue for isolation)
celery -A tasks worker -Q youtube --loglevel=info --autoreload --concurrency=2 &
celery -A tasks worker -Q webpage --loglevel=info --autoreload --concurrency=2 &
celery -A tasks worker -Q cache --loglevel=info --autoreload --concurrency=1 &

# Start beat scheduler (for periodic tasks)
# celery -A tasks beat --loglevel=info &

echo "Services running:"
echo "- RabbitMQ Management: http://localhost:15672 (admin:admin)"
echo "- Flower (HTTP API): http://localhost:5555"
echo "- Redis: localhost:6379"
echo ""
echo "Workers auto-reloading on code changes..."
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "docker-compose -f docker-compose.dev.yml down" EXIT
wait
```

## N8N Integration Patterns

### Pattern 1: HTTP via Flower (Simplest)

```javascript
// N8N HTTP Request Node
{
  "method": "POST",
  "url": "http://localhost:5555/api/task/async-apply/tasks.analyze_youtube",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "args": ["https://youtube.com/watch?v=..."]
  }
}
// Returns: {"task-id": "abc-123-def"}

// Poll for result
{
  "method": "GET",
  "url": "http://localhost:5555/api/task/result/abc-123-def"
}
```

### Pattern 2: Direct RabbitMQ (Most Efficient)

```javascript
// N8N RabbitMQ Node
{
  "mode": "publish",
  "exchange": "",
  "routingKey": "youtube",
  "message": {
    "id": "unique-task-id",
    "task": "tasks.analyze_youtube",
    "args": ["https://youtube.com/watch?v=..."]
  }
}
```

### Pattern 3: Webhook Callbacks

```python
# tasks.py addition for webhooks
@app.task
def analyze_youtube_with_callback(url, callback_url):
    result = analyze_youtube(url)

    # Send result to N8N webhook
    import requests
    requests.post(callback_url, json=result)

    return result
```

## Key Benefits for Agent-Spike Project

1. **Python 3.14 Isolation**: Workers run in your controlled environment
2. **Hot Reload**: Change agent code → workers auto-restart (no Docker rebuilds)
3. **Queue Separation**: YouTube, webpage, cache tasks in separate queues
4. **Monitoring**: Flower provides web UI + HTTP API for task management
5. **Reliability**: Automatic retries, dead letter queues, persistent messages
6. **Scalability**: Add workers per queue as needed

## Production Considerations

```python
# celeryconfig.py for production
broker_connection_retry = True
broker_connection_retry_on_startup = True
worker_prefetch_multiplier = 4
worker_max_tasks_per_child = 1000  # Restart workers after N tasks (memory leaks)

# Result backend optimization
result_expires = 3600  # Results expire after 1 hour
result_compression = 'gzip'  # Compress large results

# Task time limits
task_soft_time_limit = 300  # 5 minute soft limit
task_time_limit = 600  # 10 minute hard limit

# Error handling
task_acks_late = True  # Acknowledge after completion (safer)
worker_cancel_long_running_tasks_on_connection_loss = True
```

## Directory Structure

```
agent-spike/
├── message_bus/
│   ├── tasks.py              # Celery task definitions
│   ├── celeryconfig.py       # Celery configuration
│   ├── docker-compose.dev.yml # Infrastructure
│   ├── dev.sh                # Development launcher
│   └── requirements.txt      # celery[amqp], flower, redis
├── lessons/                  # Existing agent code
│   ├── lesson-001/          # YouTube agent
│   ├── lesson-002/          # Webpage agent
│   └── lesson-007/          # Cache manager
└── .env                      # API keys
```

## Quick Start Commands

```bash
# Install dependencies
uv pip install celery[amqp] flower redis

# Start everything
./dev.sh

# Submit a task via curl
curl -X POST http://localhost:5555/api/task/async-apply/tasks.analyze_youtube \
  -H "Content-Type: application/json" \
  -d '{"args": ["https://youtube.com/watch?v=abc123"]}'

# View task status
curl http://localhost:5555/api/task/result/{task-id}

# Scale a specific queue
celery -A tasks worker -Q youtube --autoreload --concurrency=4
```

## Why This Over Alternatives

- **vs FastAPI**: True async with queue persistence, better for long-running tasks
- **vs OpenFaaS**: Simpler setup, better dev experience, hot reload
- **vs Ray Serve**: More mature ecosystem, better N8N integration options
- **vs Plain RabbitMQ**: Celery adds retries, routing, monitoring out of the box

## YouTube API Rate Limiting Implementation

### SQLite Quota Tracker

```python
# rate_limiter.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

class YouTubeQuotaTracker:
    """Persistent quota tracking across container restarts"""

    def __init__(self, db_path="quota.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quota_usage (
                    date TEXT PRIMARY KEY,
                    units_used INTEGER DEFAULT 0,
                    last_reset TIMESTAMP,
                    priority_reserved INTEGER DEFAULT 1000
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    video_id TEXT,
                    units_consumed INTEGER,
                    priority BOOLEAN
                )
            """)

    def can_proceed(self, units=1, priority=False) -> bool:
        """Check if we have quota available"""
        today = datetime.now().date().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT units_used, priority_reserved FROM quota_usage WHERE date = ?",
                (today,)
            ).fetchone()

            if not row:
                # First request of the day
                conn.execute(
                    "INSERT INTO quota_usage (date, units_used) VALUES (?, ?)",
                    (today, 0)
                )
                return True

            units_used, reserved = row
            available = 10000 - units_used

            if priority:
                return available >= units

            # Non-priority requests can't use reserved quota
            return available - reserved >= units

    def consume_quota(self, video_id: str, units=1, priority=False):
        """Record quota consumption"""
        today = datetime.now().date().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE quota_usage SET units_used = units_used + ? WHERE date = ?",
                (units, today)
            )
            conn.execute(
                "INSERT INTO request_log (timestamp, video_id, units_consumed, priority) VALUES (?, ?, ?, ?)",
                (datetime.now(), video_id, units, priority)
            )
```

### Adaptive Burst Limiter

```python
# tasks.py addition
from celery import Task
from rate_limiter import YouTubeQuotaTracker

class YouTubeRateLimitedTask(Task):
    """Base task with YouTube API rate limiting"""

    def __init__(self):
        super().__init__()
        self.quota_tracker = YouTubeQuotaTracker()

    def before_start(self, task_id, args, kwargs):
        """Check quota before starting task"""
        url = args[0] if args else kwargs.get('url')
        video_id = extract_video_id(url)
        priority = kwargs.get('priority', False)

        if not self.quota_tracker.can_proceed(priority=priority):
            # Reschedule for next day or return cached version
            if priority:
                # Priority tasks wait
                raise self.retry(countdown=3600)  # Try again in 1 hour
            else:
                # Non-priority tasks use cache
                from lesson_007.cache_manager import CacheManager
                cache = CacheManager()
                cached = cache.get_by_url(url)
                if cached:
                    return {"source": "cache", "data": cached}
                raise Exception("YouTube API quota exceeded, no cache available")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Record quota usage after successful API call"""
        if status == "SUCCESS" and retval.get("source") != "cache":
            url = args[0] if args else kwargs.get('url')
            video_id = extract_video_id(url)
            self.quota_tracker.consume_quota(video_id)

@app.task(base=YouTubeRateLimitedTask, bind=True)
def analyze_youtube_with_quota(self, url, priority=False):
    """YouTube analysis with automatic rate limiting"""
    from lesson_001.youtube_agent import YouTubeAgent
    agent = YouTubeAgent()
    result = agent.analyze(url)
    return {"source": "api", "data": result}
```

## Archive-First Pattern Integration

### Pipeline with Archiving

```python
# tasks.py enhanced pipeline
@app.task
def ingest_youtube_video(url, priority=False):
    """Complete ingestion pipeline with archive-first approach"""

    from archive import LocalArchiveWriter
    from lesson_007.cache_manager import CacheManager

    archive = LocalArchiveWriter()
    cache = CacheManager()
    video_id = extract_video_id(url)

    # Step 1: Check if already archived
    existing = archive.get_video(video_id)
    if existing and not priority:
        return {"status": "already_archived", "video_id": video_id}

    # Step 2: Fetch with rate limiting
    task = analyze_youtube_with_quota.delay(url, priority=priority)
    result = task.get(timeout=300)

    if result["source"] == "cache":
        return {"status": "quota_exceeded_using_cache", "data": result["data"]}

    # Step 3: Archive immediately (before any processing)
    archive.archive_youtube_video(
        video_id=video_id,
        url=url,
        transcript=result["data"]["transcript"],
        metadata=result["data"]["metadata"],
        api_response=result["data"]  # Full API response
    )

    # Step 4: Generate enrichments (LLM calls)
    enrichment_task = enrich_video_metadata.delay(video_id)
    enrichments = enrichment_task.get(timeout=120)

    # Step 5: Archive enrichments
    archive.add_llm_output(
        video_id=video_id,
        output_type="enrichments",
        output_value=enrichments,
        model="claude-3-5-haiku-20241022",
        cost_usd=enrichments.get("cost", 0.001)
    )

    # Step 6: Update cache
    cache.add_content({
        "video_id": video_id,
        "url": url,
        **result["data"],
        **enrichments
    })

    return {"status": "success", "video_id": video_id}
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
```bash
# Directory structure
message_bus/
├── __init__.py
├── tasks.py              # Celery task definitions
├── celeryconfig.py       # Configuration
├── rate_limiter.py       # YouTube quota management
├── docker-compose.dev.yml
├── dev.sh               # Hot reload launcher
├── requirements.txt
└── tests/
    ├── test_tasks.py
    └── test_rate_limiter.py
```

### Phase 2: Agent Integration (Week 2)
- Wrap lesson-001 (YouTube agent)
- Wrap lesson-002 (Webpage agent)
- Wrap lesson-007 (Cache manager)
- Create smart router task

### Phase 3: Rate Limiting (Week 3)
- Implement SQLite quota tracker
- Add priority queue system
- Create monitoring dashboard
- Test burst scenarios

### Phase 4: N8N Workflows (Week 4)
- Document Flower HTTP API
- Create example workflows
- Implement webhook callbacks
- Add error handling

## Monitoring & Observability

### Quota Dashboard

```python
# monitoring.py
from flask import Flask, jsonify
from rate_limiter import YouTubeQuotaTracker

app = Flask(__name__)
tracker = YouTubeQuotaTracker()

@app.route('/api/quota/status')
def quota_status():
    """Real-time quota status for monitoring"""
    return jsonify({
        "date": datetime.now().date().isoformat(),
        "units_used": tracker.get_usage_today(),
        "units_remaining": 10000 - tracker.get_usage_today(),
        "priority_reserved": 1000,
        "percentage_used": (tracker.get_usage_today() / 10000) * 100
    })

@app.route('/api/quota/forecast')
def quota_forecast():
    """Predict when quota will be exhausted"""
    current_rate = tracker.get_hourly_rate()
    remaining = 10000 - tracker.get_usage_today()
    hours_until_exhausted = remaining / current_rate if current_rate > 0 else float('inf')

    return jsonify({
        "current_rate_per_hour": current_rate,
        "hours_until_exhausted": hours_until_exhausted,
        "estimated_exhaustion_time": (
            datetime.now() + timedelta(hours=hours_until_exhausted)
        ).isoformat() if hours_until_exhausted < 24 else None
    })
```

## Next Steps

1. Set up basic Celery + RabbitMQ infrastructure
2. Implement YouTubeQuotaTracker with SQLite
3. Wrap existing agent lessons as Celery tasks
4. Test hot reload during development
5. Create N8N workflow using HTTP/RabbitMQ nodes
6. Add monitoring/alerting via Flower API
7. Deploy quota dashboard for visibility
8. Consider adding Celery Beat for scheduled tasks (cache warming, quota reset notifications)