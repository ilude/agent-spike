# Agent Spike API

FastAPI service exposing Python 3.14 agents for N8N workflow integration.

## Quick Start

### 1. Install Dependencies

```bash
uv sync --group api
```

### 2. Set Environment Variables

Ensure `.env` file exists in project root with:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
YOUTUBE_API_KEY=AIzaSy...
WEBSHARE_PROXY_USERNAME=...
WEBSHARE_PROXY_PASSWORD=...
```

### 3. Start FastAPI Server

```bash
cd api
./dev.sh
```

The server will start with hot reload at:
- **API**: http://localhost:8000
- **Swagger docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 4. Start N8N (optional)

```bash
docker-compose up -d
```

N8N will be available at:
- **Web UI**: http://localhost:5678 (admin/admin)

## Quick Start with Docker

**Recommended for consistent environment and N8N integration.**

### 1. Ensure .env File Exists

Same as above - `.env` file in project root with API keys.

### 2. Start All Services

```bash
docker-compose up -d
```

This starts:
- **FastAPI**: http://localhost:8000
- **N8N**: http://localhost:5678

### 3. View Logs

```bash
# All services
docker-compose logs -f

# FastAPI only
docker-compose logs -f api

# N8N only
docker-compose logs -f n8n
```

### 4. Stop Services

```bash
docker-compose down
```

### 5. Rebuild After Changes

```bash
# Rebuild API after dependency changes
docker-compose up -d --build api

# Rebuild everything
docker-compose up -d --build
```

### Hot Reload in Docker

Code changes automatically reload! The project directory is mounted into the container, so any changes to `api/` files trigger uvicorn's auto-reload.

## API Endpoints

### YouTube Analysis

**POST /youtube/analyze**

Analyze a YouTube video with archive-first metadata fetching.

Request:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "fetch_metadata": false
}
```

Response:
```json
{
  "video_id": "VIDEO_ID",
  "tags": ["ai", "machine learning"],
  "summary": "Video summary...",
  "metadata": {...},
  "cached": true
}
```

**GET /youtube/metadata/{video_id}**

Get cached metadata from archive.

### Cache Search

**POST /cache/search**

Semantic search of cached content.

Request:
```json
{
  "query": "machine learning tutorials",
  "limit": 5,
  "filters": {}
}
```

Response:
```json
{
  "query": "machine learning tutorials",
  "results": [
    {
      "video_id": "VIDEO_ID",
      "score": 0.95,
      "title": "Video title",
      "summary": "Summary...",
      "tags": ["ml", "tutorial"],
      "url": "https://..."
    }
  ],
  "total_found": 5
}
```

**GET /cache/{key}**

Get specific cached item by key.

### Health Check

**GET /health**

Check service health.

Response:
```json
{
  "status": "ok",
  "checks": {
    "surrealdb": {
      "status": "ok",
      "message": "SurrealDB accessible"
    },
    "minio": {
      "status": "ok",
      "message": "MinIO accessible"
    },
    "infinity": {
      "status": "ok",
      "message": "Infinity embedding service accessible"
    }
  }
}
```

## N8N Integration

### Calling FastAPI from N8N

Use **HTTP Request** node:

**Method**: POST
**URL**:
- **If FastAPI on host**: `http://host.docker.internal:8000/youtube/analyze`
- **If FastAPI in Docker**: `http://api:8000/youtube/analyze`

**Body**:
```json
{
  "url": "{{ $json.youtube_url }}",
  "fetch_metadata": false
}
```

**Note**: When both N8N and FastAPI are in Docker (via docker-compose), use `http://api:8000`. If FastAPI is on host machine, use `host.docker.internal:8000`.

### Example N8N Workflow

1. **Webhook** → Trigger on URL
2. **HTTP Request** → POST to FastAPI `/youtube/analyze`
3. **Code** → Process response
4. **Store** → Save to database/file

## Development

### Hot Reload

Changes to `api/` files will automatically reload the server.

### Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Analyze video
curl -X POST http://localhost:8000/youtube/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Search cache
curl -X POST http://localhost:8000/cache/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI tutorials", "limit": 3}'
```

### Testing with Swagger UI

Open http://localhost:8000/docs for interactive API testing.

## Architecture

```
N8N (Docker) → HTTP → FastAPI (Python 3.14) → Agents
                                             ↓
                                       Archive/Cache
```

**Archive-First Pattern**:
1. Check archive for existing metadata
2. Fetch from YouTube API only if needed (saves quota)
3. Use cached data when available
4. Archive all results for future use

## Quota Management

YouTube Data API quota: **10,000 units/day** (1 unit per video)

**Best practices**:
- Set `fetch_metadata: false` to use archived data
- Only fetch fresh metadata when necessary
- Archive stores all fetched data automatically

## Troubleshooting

**Port already in use**:
```bash
# Change port in dev.sh
uvicorn api.main:app --reload --port 8001
```

**Archive not found**:
```bash
# Ensure archive directory exists
mkdir -p projects/data/archive/youtube
```

**N8N can't reach FastAPI**:
- Use `host.docker.internal:8000` not `localhost:8000`
- Ensure FastAPI is running on `0.0.0.0` not `127.0.0.1`

## Project Structure

```
api/
├── __init__.py
├── main.py              # FastAPI app
├── models.py            # Request/response models
├── dev.sh               # Development server launcher
├── routers/
│   ├── __init__.py
│   ├── health.py        # Health checks
│   ├── youtube.py       # YouTube analysis
│   └── cache.py         # Cache search
└── README.md            # This file
```

## See Also

- Lesson 001: YouTube agent implementation
- Lesson 007: Cache manager with SurrealDB
- Archive service: `compose/services/archive/`
