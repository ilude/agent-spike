# Agent Spike - Current Status

**Last Updated**: 2025-11-24
**Current Phase**: Personal AI Research Assistant - SurrealDB + MinIO unified data layer

## Current State

- ✅ **9 lessons complete**: YouTube, Webpage, Coordinator, Observability, Security, Memory, Cache Manager, Batch Processing, Orchestrator
- ✅ **Service layer extraction**: Production-ready `compose/services/` structure
- ✅ **SurrealDB migration complete**: All data (videos, conversations, projects) in SurrealDB
- ✅ **Vector search with HNSW indexes**: Native SurrealDB vector similarity search
- **Long-term goal**: Personal AI Research Assistant (see `.claude/VISION.md`)
- **Project structure**:
  - `lessons/`: Progressive agent-building lessons (001-009)
  - `compose/services/`: Microservices (archive, surrealdb, embeddings, chunking, metadata, tagger, youtube)
  - `compose/cli/`: Production CLI scripts (ingestion, search, verification)
  - `compose/data/`: Git-crypt encrypted data storage (archives, browser history)
- **Production features**:
  - **SurrealDB**: Unified data store with native HNSW vector indexes
  - **MinIO**: Object storage for project files (PDFs, docs)
  - **Infinity**: Embedding service (BAAI/bge-m3, gte-large-en-v1.5)
  - Archive-first strategy (all expensive data saved before processing)
  - Queue-based ingestion (pending → processing → completed workflow)
  - Webshare proxy integration (no YouTube API rate limiting)
  - Protocol-first service design (dependency injection)

## Recent Completions

**URL Pattern Analytics SurrealDB Migration (Phase 4)** ✅ COMPLETE (2025-11-24)
- Migrated URL pattern analytics from SQLite to SurrealDB with full async refactor
- Created comprehensive TDD test suite (27 tests) establishing behavioral baseline
- Implemented `AsyncPatternTracker` protocol with SurrealDB backend
- Extracted reusable pattern matching logic to `compose/services/analytics/pattern_matcher.py`
- Converted 3 consumer files to async (`url_filter.py`, `filter_description_urls.py`, `url_filter_status.py`)
- Created migration script: `compose/cli/migrate_url_patterns.py` with dry-run and batch modes
- SurrealDB tables: `pattern_classification`, `pattern_learned`, `pattern_pending_reeval`
- All tests passing, 6 commits pushed

**GitHooks Performance Optimization** ✅ COMPLETE (2025-11-24)
- Optimized pre-commit hook: **1min 15sec → 1-2 seconds** (75-second improvement)
- Pre-commit now only scans staged files instead of all 1,633 encrypted files
- Removed post-checkout and post-merge auto-sync hooks (use `make brave-sync` manually)
- Updated .gitattributes: removed obsolete archive/qdrant/cache encryption
- Removed ~1,500 archive files from git tracking (now stored in MinIO, local files remain)
- Git operations now instant (no 30-second auto-sync delays)

**MinIO Integration Enhancements** ✅ COMPLETE (2025-11-24)
- Worker queue processor uploads completed CSVs to MinIO `completed-queues` bucket
- Created archive-to-MinIO migration CLI: `compose/cli/migrate_archive_to_minio.py`
- Supports dry-run, stats, verify commands for archive migration
- Month-based organization for completed queues and archives

**Frontend Observability Updates** ✅ COMPLETE (2025-11-24)
- Updated OpenTelemetry dependencies to stable v1.x releases
- Added explicit @opentelemetry/api dependency
- Improved compatibility with latest OpenTelemetry SDK

**Dual-Collection Embeddings + Transcript Chunking** ✅ COMPLETE (2025-11-23)
- Migrated from Qdrant to SurrealDB native vector search
- Added HNSW indexes to `video.embedding` (1024-dim, cosine distance)
- Created `video_chunk` table for timestamp-level search
- New `compose/services/embeddings/` - EmbeddingService with Infinity HTTP API
- New `compose/services/chunking/` - Time+token hybrid chunking for YouTube transcripts
- Updated `compose/cli/ingest_video.py` with `--chunks` flag for chunk embeddings
- Renamed `qdrant_indexed` → `vector_indexed` across codebase
- Embedding models: gte-large-en-v1.5 (global) + bge-m3 (chunks)

**SurrealDB Backup Service** ✅ COMPLETE (2025-11-23)
- Fixed backup service for SurrealDB data to MinIO storage
- **Root cause**: SurrealDB record ID syntax requires backticks for UUIDs with dashes
  - Wrong: `CREATE backup SET id = $id` (creates field, not record ID)
  - Right: `CREATE backup:`{uuid}`` (creates record with specific ID)
- **Fix**: Updated all CRUD queries in `compose/services/backup.py` to use backtick syntax
- **Also fixed**: `RecordID` object → string conversion for Pydantic validation
- Backup now completes successfully: status transitions pending → in_progress → completed
- Frontend "Create Backup" button working
- Cleaned up 15 orphaned pending backup records from failed attempts

**Mentat Chat UI - Projects & Canvas** ✅ COMPLETE (2025-11-22)
- Built ChatGPT-replacement frontend with conversation history, projects, and canvas
- **Phase 1 - Conversations**: Sidebar with search, rename, delete, auto-naming
- **Phase 2 - Projects**:
  - Project grouping for conversations
  - File upload with Docling text extraction (PDF, DOCX, etc.)
  - RAG indexing via SurrealDB for semantic search
  - Custom instructions injected into chat context
- **Phase 3 - Canvas/Artifacts**:
  - Right sidebar with document editor
  - Artifacts browser tab
  - Auto-save with 2-second debounce
  - Artifacts linked to conversations/projects

**New files created:**
- `compose/services/projects.py` - Project storage with file management
- `compose/services/artifacts.py` - Artifact storage service
- `compose/services/file_processor.py` - Docling extraction + SurrealDB indexing
- `compose/api/routers/projects.py` - Projects REST API
- `compose/api/routers/artifacts.py` - Artifacts REST API
- Frontend: Canvas UI, artifact API methods, project selector

**Required services** (must be running for full functionality):
- SurrealDB: `docker compose up surrealdb` (port 8001)
- MinIO: `docker compose up minio` (ports 9000/9001)
- Infinity embeddings: `docker compose up infinity` (port 7997)
- Docling: `docker compose up docling` (port 5001) - for PDF/DOCX processing
- FastAPI backend: `uv run uvicorn compose.api.main:app --reload`
- Frontend: `cd compose/frontend && bun run dev`

**API Endpoints added:**
- `GET/POST /projects` - List/create projects
- `GET/PUT/DELETE /projects/{id}` - Project CRUD
- `POST /projects/{id}/files` - File upload with background RAG processing
- `POST /projects/{id}/search` - Semantic search project files
- `GET/POST /artifacts` - List/create artifacts
- `GET/PUT/DELETE /artifacts/{id}` - Artifact CRUD

**Containerized Microservices Migration** ✅ COMPLETE (2025-11-18, updated 2025-11-23)
- **Data store**: SurrealDB with native HNSW vector indexes (replaced Qdrant)
- **Object storage**: MinIO for project files (PDFs, docs)
- **Embeddings**: Infinity service (michaelf34/infinity) with dual models:
  - BAAI/bge-m3: 1024-dim chunk embeddings (8K context)
  - gte-large-en-v1.5: 1024-dim global embeddings
- Removed ML dependencies from Docker builds
  - Removed docling>=2.60.0 (use docling-serve container instead)
  - Removed sentence-transformers>=2.2.0 (use Infinity service)
  - Reduced initial build time from 11+ minutes to ~49 seconds
- Migrated all data paths from `projects/data/` to `compose/data/`
- Added git-crypt encryption for `compose/data/` directories
- Deleted obsolete `projects/` directory
- Added comprehensive documentation (INFINITY_SETUP.md, embedding_pipeline_spec)

**Service Layer Extraction** ✅ COMPLETE (2025-11-09)
- Extracted stable patterns from lessons into reusable `tools/` structure
- **tools/services/**: Protocol-first service layer with 3 services
  - `archive/`: LocalArchiveWriter/Reader for expensive data (JSON storage)
  - `cache/`: Cache with CacheManager protocol (migrated from Qdrant to SurrealDB)
  - `youtube/`: YouTubeTranscriptService with Webshare proxy support
- **tools/scripts/**: 6 production CLI scripts
  - `ingest_youtube.py`: Queue-based batch REPL (main ingestion tool)
  - `ingest_video.py`: Single video ingestion
  - `list_videos.py`, `verify_video.py`, `search_videos.py`: Cache management
  - `fetch_channel_videos.py`: YouTube Data API channel scraper
- **tools/tests/**: Pytest infrastructure with 19 tests
  - Unit tests for each service
  - Functional tests with SurrealDB
  - Shared fixtures and conftest.py
  - Coverage reporting enabled
- **All lessons updated**: Now import from centralized services
- **Key patterns**: Dependency injection, composition over inheritance, lazy imports
- **Time**: ~4 hours (5-phase refactoring)

**Lesson 009: Orchestrator Agent** ✅ COMPLETE (2025-11-08)
- Built orchestrator that coordinates multiple sub-agents in parallel
- **Key Learning**: Nested agent-with-tools calls cause deadlocks
- Solution: Created simplified pattern using direct LLM calls instead of nested agents
- Successfully processes multiple URLs in parallel with reduced token usage
- Orchestrator provides value for multi-URL batch processing scenarios
- Time: ~3 hours (including extensive debugging of nested agent issues)

**Lesson 005: Security & Guardrails** ✅ COMPLETE
- Built practical security validators using Python stdlib
- Input validation: URL safety, prompt injection detection, SQL injection patterns
- Output validation: PII detection/redaction, XSS filtering
- Rate limiting: In-memory request throttling with cooldowns
- 86% URL attack detection, 75% prompt injection detection, 100% PII detection
- Time: ~45 minutes

**Lesson 006: Memory with Mem0 (Phase 1)** ✅ COMPLETE
- Mem0 wrapper with simplified API for memory management
- Semantic search for relevant memories (no exact matches needed)
- User isolation and metadata support
- Memory persistence in ~/.mem0/ (Mem0 library uses Qdrant internally + SQLite)
- Phase 1 complete (basics), Phase 2-3 deferred (agent integration)
- Time: ~1.5 hours (including Windows debugging)

**Lesson 007: Cache Manager & Content Ingestion** ✅ COMPLETE
- Dependency injection pattern for clean architecture
- CacheManager protocol (migrated from Qdrant to SurrealDB)
- Semantic search with sentence-transformers embeddings
- Generic CSV ingestion script with progress tracking
- Centralized cache storage with SurrealDB native vector search
- Successfully cached 49+ items from video lists

**Lesson 008: Batch Processing with OpenAI** ✅ COMPLETE
- OpenAI Batch API integration for 50% cost savings
- JSONL batch input preparation from cache
- Batch job submission, monitoring, and result processing
- 4 CLI scripts (prepare, submit, check, process)
- Ready to tag all cached content at scale

## What's Next

### Immediate Next Steps

**Video Ingestion Queue Processing** (Ready to Resume)
- **Current state**: Infrastructure ready for large-scale ingestion with SurrealDB
- **Queue location**: `compose/data/queues/pending/*.csv`
- **Command**: `cd compose && docker compose up -d && cd .. && uv run python compose/cli/ingest_video.py <url> --chunks`
- **New capabilities**:
  - SurrealDB with HNSW vector indexes for semantic search
  - Dual embeddings: global (recommendations) + chunks (timestamp search)
  - Infinity embeddings eliminate transcript truncation (8K context)
  - All data encrypted with git-crypt for multi-machine workflows

**Claude Code Integration with Existing Data** (Next Priority)
- Give Claude Code access to SurrealDB cache (transcript data)
- Use Claude Code's YouTube MCP transcript tool to fetch and insert new transcripts
- Workflow:
  1. User asks Claude Code to analyze a YouTube video
  2. Claude Code checks if transcript exists in SurrealDB
  3. If not cached: Use MCP YouTube tool to fetch transcript
  4. Insert new transcript into SurrealDB for future use
  5. Perform analysis (tagging, summarization, etc.)
- Benefits:
  - Leverage existing cached data (49+ videos already cached)
  - Reduce API calls for previously-processed videos
  - Build up knowledge base over time
  - Chunk-level search: "find where they discussed X"

**Related files:**
- SurrealDB repository: `compose/services/surrealdb/`
- Embedding service: `compose/services/embeddings/`
- Chunking service: `compose/services/chunking/`
- Ingestion scripts: `compose/cli/ingest_*.py`
- Archive data: `compose/data/archive/` (git-crypt encrypted)

### Future Capabilities (As Needs Emerge)

#### Core Patterns
- **Streaming Responses** - Real-time output for long operations
- **Parallel Agent Execution** - Process multiple URLs concurrently
- **Structured Output & Validation** - Type-safe responses with Pydantic
- **RAG (Retrieval Augmented Generation)** - Knowledge base with semantic search

#### Production & Resilience
- **Error Handling & Retry Strategies** - Exponential backoff, circuit breaker
- **Human-in-the-Loop** - Approval workflows and confidence scoring
- **Cost Optimization** - Model selection, caching strategies

#### Advanced Multi-Agent Patterns
- **Sequential Workflows** - Multi-step agent chains
- **Planning Agent** - Task decomposition with ReAct pattern
- **Agent Collaboration** - Multiple agents with voting/consensus
- **Conditional Routing** - LLM-based routing and state machines

#### Evaluation & Testing
- **Agent Evaluation Framework** - Golden datasets and metrics
- **Prompt Engineering & Iteration** - Systematic optimization

#### Deployment & Integration
- **FastAPI Service** - REST API with async endpoints
- **Browser Extension Integration** - Chrome extension for real-time tagging

**Note**: These capabilities will be built as needs emerge, following the experiment-driven philosophy in `.claude/development-philosophy.md`. No prescriptive roadmap - focus on solving real problems.

## Project Setup (Resume on New Machine)

### Prerequisites
- Python 3.14
- Git
- uv package manager

### Quick Start
```bash
# Clone repo
git clone <repo-url>
cd agent-spike

# Install uv if not present
python -m pip install uv

# Sync all dependencies
uv sync --all-groups

# Copy environment variables
# Create .env files in lesson directories with:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-proj-...
# DEFAULT_MODEL=claude-3-5-haiku-20241022

# Test Lesson 001
cd lessons/lesson-001
uv run python -m youtube_agent.cli analyze "https://www.youtube.com/watch?v=i5kwX7jeWL8"

# Test Lesson 002
cd lessons/lesson-002
uv run python -m webpage_agent.cli analyze "https://github.com/docling-project/docling"

# Test Lesson 003 (Coordinator)
cd lessons/lesson-003
uv run python test_coordinator.py

# Test Lesson 004 (Observability)
cd lessons/lesson-004
uv run python test_observability.py
```

## Quick Commands Reference

```bash
# Install lesson dependencies
uv sync --group lesson-001
uv sync --group lesson-002
uv sync --group lesson-003
uv sync --group lesson-004
uv sync --all-groups            # All lessons at once

# Run agents
cd lessons/lesson-001 && uv run python -m youtube_agent.cli analyze "URL"
cd lessons/lesson-002 && uv run python -m webpage_agent.cli analyze "URL"

# Run coordinator (routes automatically)
cd lessons/lesson-003 && uv run python test_coordinator.py

# Test router
cd lessons/lesson-003 && uv run python test_router.py

# Test observability (all agents with tracing)
cd lessons/lesson-004 && uv run python test_observability.py

# Interactive mode
cd lessons/lesson-001 && uv run python -m youtube_agent.cli interactive
cd lessons/lesson-002 && uv run python -m webpage_agent.cli interactive

# Check dependencies
uv pip list | grep -E "(pydantic-ai|docling|youtube-transcript|logfire)"
```

## Known Issues

- Some JavaScript-heavy websites fail with Docling (returns 404)
  - Example: https://simonwillison.net/... (dynamic routing)
  - Works fine with: GitHub, example.com, static sites
- Docling includes some navigation in output (handled via prompt instructions)
- ~~Lesson 003: Path issues~~ - **RESOLVED**: Use `uv run python` from any directory

## Design Decisions Made

1. **Shared .venv**: All lessons use root .venv (saves disk space)
2. **Dependency groups**: Each lesson = separate dependency group in `pyproject.toml`
3. **15k char limit**: Webpage content truncated for cost control
4. **HTML only**: Lesson 002 doesn't handle PDFs yet (could add later)
5. **Claude Haiku default**: Cheap and fast for prototyping
6. **Pattern-based routing** (Lesson 003): Regex for URL classification (not LLM)
7. **Direct agent import** (Lesson 003): Composition over complex orchestration
8. **Pydantic Logfire over Langfuse** (Lesson 004): Langfuse has Python 3.14 compatibility issues, Logfire is native to Pydantic ecosystem
9. **Archive-first strategy**: All expensive data (transcripts, LLM outputs) saved before processing
10. **Protocol-first services**: typing.Protocol for dependency injection and testability
11. **Queue-based ingestion**: CSV workflow (pending → processing → completed) for resumable batch processing
12. **Webshare proxy**: YouTube Transcript API proxy to eliminate rate limiting
13. **SurrealDB as unified data store**: Single database for videos, conversations, projects with native vector search
14. **HNSW vector indexes**: SurrealDB native cosine similarity search (no separate vector DB needed)
15. **Dual embedding models**: gte-large for global/recommendation, bge-m3 for chunk/search
16. **MinIO object storage**: Binary files (PDFs, docs) separate from structured data
17. **Git-crypt data encryption**: All data in compose/data/ encrypted before push

## File Locations

- Lesson code: `lessons/lesson-XXX/`
- Lesson docs: `lessons/lesson-XXX/{PLAN.md, README.md, COMPLETE.md}`
- Services: `compose/services/{archive,surrealdb,embeddings,chunking,metadata,tagger,youtube}/`
- Scripts: `compose/cli/` (production CLIs)
- Data: `compose/data/{archive,queues}/` (git-crypt encrypted)
- Docker: `compose/docker-compose.yml`, `compose/api/Dockerfile`
- Documentation: `compose/INFINITY_SETUP.md`, `.claude/VISION.md`
- This status file: `.claude/STATUS.md`
- Main config: `pyproject.toml` (project root)
- Shared .venv: `.venv/` (project root)

## Git State

- Branch: main
- Recent commits (2025-11-24):
  - 5418aaa - docs: add proactive memory system design
  - 65ca4b8 - feat: add archive-to-MinIO migration script
  - 16d5329 - feat: upload completed queue files to MinIO
  - 2769894 - build: update OpenTelemetry dependencies
  - d3cf26c - chore: complete githook cleanup
  - bd020a2 - perf: optimize githooks (75-second improvement)
  - 21ba237 - feat: add migration script and async URL filter (Phase 4)
  - be11316 - test: add TDD test suite for pattern tracker
  - d70f597 - feat: add SurrealDB PatternTracker implementation
  - f10f6d4 - feat: implement SurrealDB repository for analytics
- Status: Clean working tree, all changes pushed
- All data encrypted with git-crypt before push

**To Resume**: Pull latest, run `git-crypt unlock`, `uv sync --all-groups`, start containers with `cd compose && docker compose up -d` (starts SurrealDB, MinIO, Infinity)

---

## Completed Lessons (Detailed)

### ✅ Lesson 001: YouTube Video Tagging Agent
- **Location**: `lessons/lesson-001/`
- **Status**: Complete and working
- **Tech**: Pydantic AI, youtube-transcript-api, Claude Haiku
- **What it does**: Analyzes YouTube video transcripts and generates 3-5 tags
- **Run**: `cd lessons/lesson-001 && uv run python -m youtube_agent.cli analyze "YOUTUBE_URL"`
- **Key files**: `youtube_agent/{agent.py, tools.py, prompts.py, cli.py}`
- **Time**: ~55 minutes to build

### ✅ Lesson 002: Webpage Content Tagging Agent
- **Location**: `lessons/lesson-002/`
- **Status**: Complete and working
- **Tech**: Pydantic AI, Docling, Claude Haiku
- **What it does**: Fetches webpages, converts to Markdown, generates 3-5 tags
- **Run**: `cd lessons/lesson-002 && uv run python -m webpage_agent.cli analyze "WEBPAGE_URL"`
- **Key files**: `webpage_agent/{agent.py, tools.py, prompts.py, cli.py}`
- **Code reuse**: 80% from Lesson 001
- **Time**: ~60 minutes to build

### ✅ Lesson 003: Multi-Agent Coordinator
- **Location**: `lessons/lesson-003/`
- **Status**: Complete and working
- **Tech**: Pattern-based routing, agent composition
- **What it does**: Routes any URL to appropriate agent (YouTube or Webpage)
- **Run**: `cd lessons/lesson-003 && uv run python test_coordinator.py`
- **Key files**: `coordinator_agent/{router.py, agent.py, cli.py}`
- **Pattern**: Router/Coordinator multi-agent pattern
- **Code reuse**: 100% reuse of existing agents
- **Time**: ~75 minutes to build

### ✅ Lesson 004: Observability with Pydantic Logfire
- **Location**: `lessons/lesson-004/`
- **Status**: Complete and working
- **Tech**: Pydantic Logfire, OpenTelemetry, console tracing
- **What it does**: Adds comprehensive observability to all agents (YouTube, Webpage, Coordinator)
- **Run**: `cd lessons/lesson-004 && uv run python test_observability.py`
- **Key files**: `observability/{config.py, logfire_wrapper.py}`, instrumented agents
- **Pattern**: Global instrumentation with per-agent opt-in
- **What's tracked**: Tool calls, LLM calls, token counts, costs, latency, parent/child traces
- **Note**: Originally planned for Langfuse, switched to Logfire due to Python 3.14 compatibility
- **Time**: ~80 minutes to build (including Langfuse detour)

### ✅ Lesson 009: Orchestrator Agent
- **Location**: `lessons/lesson-009/`
- **Status**: Complete and working (with simplified approach)
- **Tech**: Pydantic AI agents with tool-based delegation
- **What it does**: Orchestrates multiple sub-agents to process multiple URLs in parallel
- **Run**: `cd lessons/lesson-009 && uv run python test_orchestrator_simple.py`
- **Key files**: `orchestrator_agent/{agent_simple.py, tools_simple.py}`
- **Pattern**: Direct LLM calls instead of nested agents (avoids deadlocks)
- **Key Learning**: Nested agent-with-tools calls create event loop conflicts
- **Time**: ~3 hours to build (including debugging nested agent issues)

## Dependencies

All dependencies are in root `pyproject.toml` using dependency groups:

### lesson-001 group
- pydantic-ai
- python-dotenv
- rich
- youtube-transcript-api

### lesson-002 group
- docling (+ all its deps: torch, transformers, scipy, numpy, pandas, etc.)
- Everything from lesson-001

### lesson-003 group
- Everything from lesson-001 and lesson-002

### lesson-004 group
- Everything from lesson-003
- logfire (for observability)

### lesson-005 group
- Everything from lesson-004
- (No additional dependencies - uses Python stdlib)

### lesson-006 group
- Everything from lesson-005
- mem0ai (for memory/preferences)

### lesson-007 group
- Everything from lesson-003 (router, YouTube, webpage tools)
- qdrant-client (vector database)
- sentence-transformers (embeddings)
- tqdm (progress bars)

### lesson-008 group
- Everything from lesson-007 (cache manager)
- openai (OpenAI Python SDK for Batch API)

### lesson-009 group
- Everything from lesson-003 (router, YouTube, webpage tools)
- openai (for GPT-5 models)

**Note**: `.venv` is in project root (shared across lessons to save ~7GB per lesson)

## Architecture Pattern

All lessons follow the same structure:
```
lesson-XXX/
├── <name>_agent/          # Agent implementation package
│   ├── __init__.py
│   ├── agent.py           # Pydantic AI agent setup
│   ├── tools.py           # Tool implementations
│   ├── prompts.py         # System prompts
│   └── cli.py             # Typer CLI interface
├── .env                   # API keys (gitignored, never commit!)
├── PLAN.md                # Lesson plan and learning objectives
├── README.md              # Quick reference for the lesson
├── COMPLETE.md            # Summary of learnings after completion
└── test_*.py              # Test scripts and demos
```

## API Keys Required

All lessons use the same API keys (configured in `.env` files):
- `ANTHROPIC_API_KEY` - For Claude models
- `OPENAI_API_KEY` - For GPT models
- `DEFAULT_MODEL` - Optional, defaults to `claude-3-5-haiku-20241022`

**Security**: `.env` files are gitignored, must be created manually on each machine

## Learning Source

All lessons based on Cole Medin's video:
- **Video**: "Learn 90% of Building AI Agents in 30 Minutes"
- **URL**: https://www.youtube.com/watch?v=i5kwX7jeWL8
- **Concepts**: 4 core components (LLM, System Prompt, Tools, Memory)
