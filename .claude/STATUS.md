# Agent Spike - Current Status

**Last Updated**: 2025-11-29
**Current Phase**: Personal AI Research Assistant - Production Platform with Full Observability

## Current State

- ✅ **9 lessons complete**: YouTube, Webpage, Coordinator, Observability, Security, Memory, Cache Manager, Batch Processing, Orchestrator
- ✅ **Production platform**: Mentat Chat UI with full-stack architecture
- ✅ **LGTM observability stack**: Loki, Grafana, Tempo, Prometheus with OpenTelemetry instrumentation
- ✅ **SurrealDB migration**: Unified data store replacing Qdrant for primary storage
- **Long-term goal**: Personal AI Research Assistant (see `.claude/VISION.md`)

**Project structure**:
- `lessons/`: Progressive agent-building lessons (001-009)
- `compose/`: Production platform
  - `api/`: FastAPI backend with 16+ routers
  - `frontend/`: SvelteKit chat application
  - `services/`: Microservices layer (20+ services)
  - `worker/`: Queue processor with metrics instrumentation
  - `data/`: Git-crypt encrypted storage
- `infra/ansible/`: GPU server deployment automation

**Production features**:
- Multi-model chat (OpenRouter, OpenAI, Ollama)
- RAG-enabled chat with semantic search
- Conversation history and project management
- File upload with Docling extraction + RAG indexing
- Canvas/artifacts editor
- Queue-based video ingestion with progress tracking
- OpenTelemetry distributed tracing
- Grafana dashboards for API and worker metrics
- Centralized log collection via Grafana Alloy

## Recent Completions

### OpenTelemetry Metrics Instrumentation ✅ COMPLETE (2025-11-29)
- Added comprehensive metrics to queue worker:
  - **Counters**: `worker.jobs.processed`, `worker.jobs.failed`, `worker.videos.processed/skipped/failed`
  - **Histograms**: `worker.job.duration`, `worker.video.duration`
  - **Observable Gauge**: `worker.queue.depth` (pending/processing)
- Updated worker dashboard with PromQL queries instead of log parsing

### Grafana Dashboard Provisioning ✅ COMPLETE (2025-11-29)
- API dashboard: request rate, latency percentiles (p50/p95/p99), error rate, logs
- Worker dashboard: job processing, videos processed/failed/skipped, queue depth, duration histograms
- Dashboards auto-loaded via Grafana provisioning

### Frontend Telemetry ✅ COMPLETE (2025-11-29)
- Fixed OpenTelemetry browser tracing scope bug
- Added OTLP proxy endpoint (`/v1/traces`, `/v1/metrics`) to solve CORS issues
- Auto-instruments fetch API with trace context propagation

### Grafana Alloy Log Collection ✅ COMPLETE (2025-11-28)
- Centralized log collection from all Docker containers
- Ships logs to remote Loki on GPU server (192.168.16.241:3100)
- Extracts metadata from container labels

### Mentat Chat UI ✅ COMPLETE (2025-11-22)
- Built ChatGPT-replacement frontend with SvelteKit
- **Conversations**: Sidebar with search, rename, delete, auto-naming
- **Projects**: File upload with Docling extraction + RAG indexing, custom instructions
- **Canvas/Artifacts**: Right sidebar document editor with auto-save

### SurrealDB Migration ✅ COMPLETE (2025-11-25)
- Migrated from Qdrant to SurrealDB as primary data store
- Native HNSW vector indexes for semantic search
- Repository layer: `compose/services/surrealdb/`
- Tables: conversations, projects, videos, worker_progress

## Service Architecture

### Local Services (Docker Compose)

| Service | Port | Description |
|---------|------|-------------|
| **Traefik** | 80/443 | Reverse proxy + Let's Encrypt SSL |
| **API** | 8000 | FastAPI backend |
| **Queue Worker** | - | Async job processor with metrics |
| **Grafana Alloy** | 12345 | Log collection → Loki |
| **Frontend** | 5173 | SvelteKit (runs locally, not containerized) |

### Remote GPU Server (192.168.16.241)

| Service | Port | Description |
|---------|------|-------------|
| **Infinity** | 7997 | Embeddings (Alibaba-NLP/gte-large-en-v1.5, 1024-dim) |
| **Qdrant** | 6335-6336 | Vector database (legacy) |
| **SurrealDB** | 8000 | Primary database |
| **Loki** | 3100 | Log aggregation |
| **Prometheus** | 9090 | Metrics |
| **Tempo** | 3200 | Distributed tracing |
| **Grafana** | 3000 | Visualization |
| **Ollama** | 11434 | Local LLMs |
| **Docling** | 5001 | Document parsing |
| **MinIO** | 9000 | Object storage |
| **Neo4j** | 7474/7687 | Graph database |
| **n8n** | 5678 | Workflow automation |

## API Endpoints

**Core:**
- `GET /health` - Service health checks (SurrealDB, MinIO, Infinity)
- `POST /v1/traces`, `/v1/metrics` - OTLP proxy for frontend telemetry

**Chat:**
- `GET /chat/models` - List available models
- `WS /chat/ws/chat` - WebSocket chat streaming
- `WS /chat/ws/rag-chat` - RAG-enabled chat

**Content:**
- `POST /youtube/analyze` - Video analysis with archive-first
- `POST /cache/search` - Semantic search
- `POST /ingest` - Content ingestion pipeline

**Data Management:**
- `/conversations` - CRUD + search
- `/projects` - CRUD + file upload + RAG indexing
- `/artifacts` - CRUD for canvas documents

**Other:** `/stats`, `/settings`, `/auth`, `/backup`, `/websearch`, `/imagegen`

## Quick Start

### Start Platform
```bash
# Start backend services
cd compose && docker compose up -d

# Start frontend (separate terminal)
cd compose/frontend && bun run dev
```

### Key URLs
- Frontend: `https://mentat.local.ilude.com`
- API: `https://api.local.ilude.com`
- Traefik: `https://traefik.local.ilude.com`
- Grafana: `http://192.168.16.241:3000`

### Check Status
```bash
cd compose && docker compose ps
docker compose logs api -f
docker compose logs queue-worker -f
```

## Git State

- **Branch**: main
- **Recent commits**:
  - `b900a99` - feat: add OpenTelemetry metrics instrumentation to queue worker
  - `aec6578` - feat: add Grafana dashboard provisioning for API and worker
  - `543925d` - fix: frontend telemetry provider scope bug
  - `0fd5fad` - feat: add OTLP proxy endpoint for frontend telemetry
  - `ee1836e` - feat: add Grafana Alloy for centralized log collection
- **Status**: Clean working tree

## What's Next

### Immediate Priorities

1. **Video Ingestion at Scale**
   - Queue location: `compose/data/queues/pending/*.csv`
   - Command: `uv run python compose/cli/ingest_youtube.py`
   - Progress tracked in SurrealDB

2. **Agent Self-Monitoring**
   - LGTM client (`compose/services/observability/lgtm_client.py`) enables agents to query their own performance
   - Use for calibration decisions, error pattern detection

3. **Recommendation Engine**
   - See `.claude/VISION.md` for ego prompt ideas
   - Leverage accumulated video/content data

## File Locations

| Category | Location |
|----------|----------|
| Lessons | `lessons/lesson-XXX/` |
| API Routers | `compose/api/routers/` |
| Services | `compose/services/` |
| Frontend | `compose/frontend/src/` |
| Queue Worker | `compose/worker/` |
| Dashboards | `infra/ansible/files/observability/dashboards/` |
| Alloy Config | `compose/alloy-config.alloy` |
| Telemetry | `compose/lib/telemetry.py` |
| Docker | `compose/docker-compose.yml` |
| Data | `compose/data/` (git-crypt encrypted) |

## Design Decisions

1. **SurrealDB as primary store** - Unified database with native vector indexes
2. **Remote GPU server** - Heavy services (Infinity, Qdrant, LGTM stack) on 192.168.16.241
3. **OTLP proxy** - Solves browser CORS issues for frontend telemetry
4. **Grafana Alloy** - Lightweight log collector vs full Promtail
5. **Frontend runs locally** - Windows hot reload issues with containerized Vite
6. **Archive-first strategy** - All expensive data saved before processing
7. **Queue-based ingestion** - CSV workflow with SurrealDB progress tracking
8. **Protocol-first services** - typing.Protocol for dependency injection

## Observability Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │    │     API     │    │   Worker    │
│  (Browser)  │    │  (FastAPI)  │    │  (Queue)    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │ OTLP/HTTP        │ OTLP/HTTP        │ OTLP/HTTP
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────┐
│              GPU Server (192.168.16.241)            │
├─────────────┬─────────────┬─────────────┬──────────┤
│    Tempo    │ Prometheus  │    Loki     │ Grafana  │
│  (traces)   │  (metrics)  │   (logs)    │  (viz)   │
└─────────────┴─────────────┴─────────────┴──────────┘
```

**Instrumentation:**
- Backend: `opentelemetry-instrumentation-fastapi`, `-httpx`, `-logging`
- Frontend: `@opentelemetry/sdk-trace-web`, auto-instrumented fetch
- Worker: Custom metrics (counters, histograms, gauges)
- Logs: Grafana Alloy collects from Docker socket

---

## Completed Lessons (Reference)

### ✅ Lesson 001: YouTube Video Tagging Agent
- **Tech**: Pydantic AI, youtube-transcript-api, Claude Haiku
- **Run**: `cd lessons/lesson-001 && uv run python -m youtube_agent.cli analyze "URL"`

### ✅ Lesson 002: Webpage Content Tagging Agent
- **Tech**: Pydantic AI, Docling, Claude Haiku
- **Run**: `cd lessons/lesson-002 && uv run python -m webpage_agent.cli analyze "URL"`

### ✅ Lesson 003: Multi-Agent Coordinator
- **Tech**: Pattern-based routing, agent composition
- **Run**: `cd lessons/lesson-003 && uv run python test_coordinator.py`

### ✅ Lesson 004: Observability with Logfire
- **Tech**: Pydantic Logfire, OpenTelemetry
- **Run**: `cd lessons/lesson-004 && uv run python test_observability.py`

### ✅ Lesson 005: Security & Guardrails
- **Tech**: Python stdlib validators (URL, PII, XSS)

### ✅ Lesson 006: Memory with Mem0
- **Tech**: Mem0 wrapper, semantic search

### ✅ Lesson 007: Cache Manager & Ingestion
- **Tech**: Qdrant, sentence-transformers

### ✅ Lesson 008: Batch Processing
- **Tech**: OpenAI Batch API

### ✅ Lesson 009: Orchestrator Agent
- **Tech**: Parallel sub-agent coordination

---

**To Resume**: `git pull && git-crypt unlock && uv sync --all-groups && cd compose && docker compose up -d`
