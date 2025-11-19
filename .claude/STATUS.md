# Agent Spike - Current Status

**Last Updated**: 2025-11-18
**Current Phase**: Personal AI Research Assistant - Containerized microservices architecture

## Current State

- ✅ **9 lessons complete**: YouTube, Webpage, Coordinator, Observability, Security, Memory, Cache Manager, Batch Processing, Orchestrator
- ✅ **Service layer extraction**: Production-ready `tools/` structure
- **Long-term goal**: Personal AI Research Assistant (see `.claude/VISION.md`)
- **Project structure**:
  - `lessons/`: Progressive agent-building lessons (001-009)
  - `compose/services/`: Microservices (archive, cache, analytics, metadata, tagger, display, youtube)
  - `compose/cli/`: Production CLI scripts (ingestion, search, verification)
  - `compose/data/`: Git-crypt encrypted data storage (Qdrant, archives, browser history)
- **Production features**:
  - Containerized services (Qdrant, Infinity embeddings, N8N workflows)
  - Archive-first strategy (all expensive data saved before processing)
  - Queue-based ingestion (pending → processing → completed workflow)
  - Webshare proxy integration (no YouTube API rate limiting)
  - Protocol-first service design (dependency injection)
  - Infinity embedding service (BAAI/bge-m3, 1024-dim, 8K context)

## Recent Completions

**Containerized Microservices Migration** ✅ COMPLETE (2025-11-18)
- Migrated from embedded Qdrant to containerized qdrant/qdrant service (ports 6335-6336)
- Added Infinity embedding service (michaelf34/infinity) with BAAI/bge-m3 model
  - 1024-dimension embeddings (vs 384-dim from all-MiniLM-L6-v2)
  - 8,192 token context window (vs 256 tokens)
  - Eliminates 75% transcript truncation issue
- Removed ML dependencies from Docker builds
  - Removed docling>=2.60.0 (use docling-serve container instead)
  - Removed sentence-transformers>=2.2.0 (use Infinity service)
  - Reduced initial build time from 11+ minutes to ~49 seconds
- Updated all ingestion scripts to use Infinity + containerized Qdrant HTTP APIs
- Migrated all data paths from `projects/data/` to `compose/data/`
- Added git-crypt encryption for `compose/data/` directories
- Deleted obsolete `projects/` directory
- Added comprehensive documentation (INFINITY_SETUP.md, embedding_pipeline_spec)
- 12 commits, full test coverage

**Service Layer Extraction** ✅ COMPLETE (2025-11-09)
- Extracted stable patterns from lessons into reusable `tools/` structure
- **tools/services/**: Protocol-first service layer with 3 services
  - `archive/`: LocalArchiveWriter/Reader for expensive data (JSON storage)
  - `cache/`: QdrantCache + InMemoryCache with CacheManager protocol
  - `youtube/`: YouTubeTranscriptService with Webshare proxy support
- **tools/scripts/**: 6 production CLI scripts
  - `ingest_youtube.py`: Queue-based batch REPL (main ingestion tool)
  - `ingest_video.py`: Single video ingestion
  - `list_videos.py`, `verify_video.py`, `search_videos.py`: Cache management
  - `fetch_channel_videos.py`: YouTube Data API channel scraper
- **tools/tests/**: Pytest infrastructure with 19 tests
  - Unit tests for each service
  - Functional tests with real Qdrant
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
- Memory persistence in ~/.mem0/ (Qdrant + SQLite)
- Phase 1 complete (basics), Phase 2-3 deferred (agent integration)
- Time: ~1.5 hours (including Windows debugging)

**Lesson 007: Cache Manager & Content Ingestion** ✅ COMPLETE
- Dependency injection pattern for clean architecture
- CacheManager protocol with QdrantCache implementation
- Semantic search with sentence-transformers embeddings
- Generic CSV ingestion script with progress tracking
- Centralized cache storage in `projects/data/qdrant/`
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
- **Current state**: Infrastructure ready for large-scale ingestion
- **Queue location**: `compose/data/queues/pending/*.csv`
- **Command**: `cd compose && docker compose up -d && cd .. && uv run python compose/cli/ingest_youtube.py`
- **New capabilities**:
  - Infinity embeddings eliminate transcript truncation (8K context vs 256 tokens)
  - Containerized Qdrant for scalable vector storage
  - All data encrypted with git-crypt for multi-machine workflows

**Claude Code Integration with Existing Data** (Next Priority)
- Give Claude Code access to Qdrant cache (transcript data from lesson-007)
- Use Claude Code's YouTube MCP transcript tool to fetch and insert new transcripts
- Workflow:
  1. User asks Claude Code to analyze a YouTube video
  2. Claude Code checks if transcript exists in Qdrant cache
  3. If not cached: Use MCP YouTube tool to fetch transcript
  4. Insert new transcript into Qdrant for future use
  5. Perform analysis (tagging, summarization, etc.)
- Benefits:
  - Leverage existing cached data (49+ videos already cached)
  - Reduce API calls for previously-processed videos
  - Build up knowledge base over time
  - Use MCP tools directly (better than lesson-001's youtube-transcript-api)

**Related files:**
- Cache service: `compose/services/cache/`
- Ingestion scripts: `compose/cli/ingest_*.py`
- Qdrant data: `compose/data/qdrant/` (git-crypt encrypted)
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
13. **Lazy imports**: Qdrant optional dependency (graceful degradation to InMemoryCache)
14. **Containerized services**: Separate embedding/vector services from application container
15. **BAAI/bge-m3 embeddings**: 1024-dim, 8K context for better semantic search
16. **Git-crypt data encryption**: All data in compose/data/ encrypted before push

## File Locations

- Lesson code: `lessons/lesson-XXX/`
- Lesson docs: `lessons/lesson-XXX/{PLAN.md, README.md, COMPLETE.md}`
- Services: `compose/services/{archive,cache,analytics,metadata,tagger,display,youtube}/`
- Scripts: `compose/cli/` (production CLIs)
- Data: `compose/data/{archive,queues,qdrant,browser_history,n8n}/` (git-crypt encrypted)
- Docker: `compose/docker-compose.yml`, `compose/api/Dockerfile`
- Documentation: `compose/INFINITY_SETUP.md`, `.claude/VISION.md`
- This status file: `.claude/STATUS.md`
- Main config: `pyproject.toml` (project root)
- Shared .venv: `.venv/` (project root)

## Git State

- Branch: main
- Recent commits: Containerized services migration (12 commits on 2025-11-18)
- Status: Clean working tree
- All data encrypted with git-crypt before push

**To Resume**: Pull latest, run `git-crypt unlock`, `uv sync --all-groups`, start containers with `cd compose && docker compose up -d`

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
