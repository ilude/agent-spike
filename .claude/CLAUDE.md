Communication Style: Be direct and straightforward. No cheerleading phrases like "that's absolutely right" or "great question." Tell me when my ideas are flawed, incomplete, or poorly thought through. Use casual language and occasional profanity when appropriate. Focus on practical problems and realistic solutions rather than being overly positive or encouraging.

Technical Approach: Challenge assumptions, point out potential issues, and ask the hard questions about implementation, scalability, and real-world viability. If something won't work, say so directly and explain why it has problems rather than just dismissing it.

**Development Philosophy**: Experiment-driven, fail-fast approach. Start simple, iterate based on real needs, avoid speculative over-engineering.

**Terminology Note**: This is the **local/project ruleset** (specific to this repository). The **personal ruleset** lives in the user's home directory (`~/.claude/CLAUDE.md`) and applies to all projects. This local ruleset takes precedence over personal preferences for project-specific patterns.

## Session Context Management

enable-session-commits: true

## Data Archiving Strategy

**CRITICAL RULE**: Archive anything that costs time or money to fetch BEFORE processing it.

**What to archive:**
- ✅ External API calls (YouTube transcripts, web scraping, etc.)
- ✅ LLM outputs (tags, summaries, classifications)
- ✅ Rate-limited operations
- ✅ Data that might need reprocessing later

**Why archive first:**
- Enables experimentation without re-fetching (avoid rate limits)
- Protects against data loss (API changes, deleted content)
- Tracks LLM costs over time
- Allows migration between storage systems (SurrealDB, Pinecone, etc.)
- Supports reprocessing with different strategies (chunking, embeddings, etc.)

**Archive location:** `compose/data/archive/` (organized by source and month)

**Note:** The canonical data location has been moved from `projects/data/` to `compose/data/` to align with the Docker Compose service architecture.

**Service pattern:** Use `ArchiveWriter` dependency injection in all ingest pipelines.

**Pipeline order:**
1. Fetch expensive data (transcript, webpage, etc.) → **Archive immediately**
2. Generate LLM outputs (tags, summaries) → **Archive immediately**
3. Process/embed/cache → Derived data (can be rebuilt from archives)

**Implementation:** See `lessons/lesson-007/archive/` for the archive service.

**Example usage:**
```python
from archive import LocalArchiveWriter

archive = LocalArchiveWriter()

# Archive transcript (rate-limited API call)
archive.archive_youtube_video(
    video_id=video_id,
    url=url,
    transcript=transcript,
    metadata={"source": "youtube-transcript-api"},
)

# Archive LLM output (costs money)
archive.add_llm_output(
    video_id=video_id,
    output_type="tags",
    output_value=tags,
    model="claude-3-5-haiku-20241022",
    cost_usd=0.0012,
)

# Track processing versions
archive.add_processing_record(
    video_id=video_id,
    version="v1_full_embed",
    collection_name="cached_content",
)
```

**Future design decisions:** Always ask: "Does this cost time/money to fetch?" → If yes, archive it first.

**Reprocessing archives:** See `~/.claude/skills/archive-reprocessing/` skill for the version-tracked reprocessing system (applies transformations to existing archives with incremental processing).

## Project Overview

**Multi-agent AI learning spike project** for hands-on exploration of building AI agents with Pydantic AI. This is a **learning/experimental repository**, NOT a production application.

**Primary focus**: Progressive lessons in `lessons/` teaching agent development patterns:
- **Lesson 001**: YouTube video tagging agent (YouTube Transcript API + Claude Haiku)
- **Lesson 002**: Webpage content tagging agent (Docling + Claude Haiku)
- **Lesson 003**: Multi-agent coordinator/router (pattern-based URL routing)
- **Lesson 004**: Observability with Logfire (tracing and monitoring)
- **Lesson 005**: Security guardrails (input validation and safety)
- **Lesson 006**: Memory with Mem0 (persistent agent memory)
- **Lesson 007**: Cache Manager (vector database patterns, SurrealDB)
- **Lesson 008**: Batch Processing with OpenAI (async batch operations)
- **Lesson 009**: Agent Orchestrator (multi-agent coordination)
- **Lesson 010**: Semantic Tag Normalization (taxonomy clustering)

**Learning source**: Based on Cole Medin's "Learn 90% of Building AI Agents in 30 Minutes" video (https://www.youtube.com/watch?v=i5kwX7jeWL8).

**Tech stack**:
- Python 3.14 (pinned via `.python-version`)
- Pydantic AI framework
- uv package manager (not pip)
- Typer CLIs per lesson
- Claude Haiku for cost-effective prototyping
- **SurrealDB**: Unified data store with native HNSW vector search
- **MinIO**: Object storage for binary files
- **Infinity**: Embedding service (bge-m3, gte-large)

**Virtual environment setup**:
- **Single shared `.venv` at project root** (configured as UV workspace)
- All lessons use the same virtual environment (saves ~7GB per lesson)
- UV automatically finds the root venv from any subdirectory
- **NEVER** manually reference `.venv/Scripts/python.exe` paths

**Development workflow**:
- Work directly in `lessons/` directories
- **Always use `uv run python`** (finds root venv automatically from any subdirectory)
- Each lesson is self-contained with its own agent, CLI, tests, and documentation
- Run commands from lesson directory: `cd lessons/lesson-XXX && uv run python script.py`

**Directory structure**:
```
lessons/               # Progressive agent-building lessons
├── lesson-001/       # YouTube tagging agent
├── lesson-002/       # Webpage tagging agent
├── lesson-003/       # Multi-agent coordinator
├── lesson-004/       # Observability (Logfire)
├── lesson-005/       # Security guardrails
├── lesson-006/       # Memory (Mem0)
├── lesson-007/       # Cache Manager (SurrealDB)
├── lesson-008/       # Batch Processing (OpenAI)
├── lesson-009/       # Agent Orchestrator
└── lesson-010/       # Semantic Tag Normalization
.claude/STATUS.md     # Current progress, known issues, resume instructions
```

**Long-term vision**: This learning project is evolving toward a **Personal AI Research Assistant and Recommendation Engine**. See `.claude/VISION.md` for the full roadmap and architectural plans.

## Quick Start

### First Time in This Codebase?

1. ✅ **Check current state**: `cat .claude/STATUS.md`
2. ✅ **Verify lesson structure**: `ls lessons/`
3. ✅ **Install all dependencies**: `uv sync --all-groups`
4. ✅ **Unlock secrets**: `git-crypt unlock` (root `.env` is encrypted)

### Resuming Work?

1. ✅ **Check git status**: `git status`
2. ✅ **Read STATUS.md**: `.claude/STATUS.md`
3. ✅ **Sync dependencies**: `uv sync --group lesson-XXX`
4. ✅ **Run existing tests**: Verify environment
   ```bash
   cd lessons/lesson-003
   uv run python test_router.py
   ```

### Working on Lessons?

- ✅ **Always use `uv run python`** to execute scripts (not `python` directly)
- ✅ Each lesson is in `lessons/lesson-XXX/`
- ✅ See "Multi-Agent Learning Lessons" section below for patterns

## Multi-Agent Learning Lessons

**CRITICAL: Read STATUS.md first** for current lesson state and progress.

**See `multi-agent-ai-projects` skill for detailed lesson patterns** (lesson structure, dependency management, API key setup, best practices). That skill auto-activates when working with `lessons/` or `STATUS.md`.

### Project-Specific Notes

**Dependency groups**: Located in `pyproject.toml` lines 77-120. Each lesson has its own dependency group. Install with:
```bash
uv sync --group lesson-XXX      # Single lesson
uv sync --all-groups            # All lessons (recommended)
```

**Python execution**: Always use `uv run python` (handles virtual environment automatically):
```bash
cd lessons/lesson-XXX
uv run python test_script.py
uv run python -m agent_name.cli
```

**API keys**: This project uses centralized environment management:

**Root `.env` file** (encrypted with git-crypt):
- Located at project root
- Contains ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
- Encrypted with git-crypt (must unlock repo to read)

**Loading environment**: Use `compose/lib/env_loader.py` utility in test scripts:
```python
from compose.lib.env_loader import load_root_env
load_root_env()  # Finds git root, loads .env automatically
```

**If `.env` encrypted**: Either unlock repo or set environment variables:
```bash
git-crypt unlock                    # Decrypt .env
# OR
export OPENAI_API_KEY="sk-proj-..."  # Set manually
```

**Current status**: Lessons 001-006 complete, see .claude/STATUS.md for next steps.

## Common Development Commands

### Most Common (Lesson Work)

```bash
# Run any Python script in lesson context
uv run python <script>.py

# Install dependencies
uv sync --group lesson-001              # Single lesson
uv sync --all-groups                    # All lessons

# Run lesson CLI (if available)
cd lessons/lesson-001
uv run python -m youtube_agent.cli analyze "https://youtube.com/..."
```

### Platform (API + Worker)

```bash
make up                                 # Start backend (traefik, api, worker)
make down                               # Stop all services
make logs                               # View all service logs
make logs-api                           # View specific service logs
make status                             # Show service status
make rebuild                            # Rebuild and restart all
make rebuild-api                        # Rebuild specific service
```

Frontend runs locally (not in container):
```bash
cd compose/frontend && bun run dev      # Start frontend dev server
```

### Code Quality

```bash
make format                             # black + isort
make lint                               # ruff
make test                               # pytest (backend + frontend)
```

### GPU Server Management

Remote GPU server at `192.168.16.241` runs AI services (Infinity, Ollama, Docling). Managed via Ansible in `infra/ansible/`.

```bash
make gpu-deploy                         # Deploy compose stack + secrets
make gpu-update                         # Pull latest images + restart
make gpu-backup                         # Fetch current remote config
make gpu-shell                          # Interactive Ansible shell
```

## Python Configuration

Code quality standards (applies to production code in `src/`):

- **Line length**: 88 characters (black standard)
- **Target version**: Python 3.14
- **Type checking**: mypy with strict mode enabled
- **Linting**: ruff with E, F, W, I, UP rules
- **Import sorting**: isort with black profile

**For lesson code**: These are guidelines, not strict requirements. Focus on learning!

## Summary for New Claude Sessions

1. ✅ **This is a learning project** - Multi-agent AI spike, not production app
2. ✅ **Work in `lessons/`** - 10 lessons total, all complete (001-010)
3. ✅ **Check STATUS.md first** - Current state and progress
4. ✅ **Use `uv run python`** - Handles virtual environments automatically
5. ✅ **Install deps with `uv sync --all-groups`** - Before running anything
6. ✅ **Unlock secrets with `git-crypt unlock`** - Root `.env` is encrypted
7. ✅ **GPU server?** - Use `make gpu-deploy` (see `infra/ansible/`)
8. ✅ **Questions?** - Read the lesson's README.md and COMPLETE.md

---

## Background: Infrastructure & Architecture

**Note**: Infrastructure is for the platform (API, worker, frontend). Lessons run directly on host with `uv run python`.

**Compose files** (in `compose/`):
- `docker-compose.yml` - Main services (traefik, api, worker)
- `docker-compose.override.yml` - Local dev overrides (routes frontend to localhost)
- `docker-compose.production.yml` - Containerized frontend (NOT for local dev)

**Current state**: All working code is in `lessons/`. Platform code is in `compose/`.

**For lesson work**: Just need API keys in `.env` and `uv sync --all-groups`.

## Local Development Architecture

**Starting the platform:**
```bash
make up                              # Start backend (traefik, api, worker)
cd compose/frontend && bun run dev   # Start frontend locally
```

**Services:**
- **API + Worker**: Run in containers via `make up`
- **Frontend**: Runs LOCALLY (hot reload broken in container on Windows)

**URLs (HTTPS via Traefik):**
- `https://mentat.local.ilude.com` → Frontend (local dev server) - **ALWAYS USE THIS**
- `https://api.local.ilude.com` → API container
- `https://traefik.local.ilude.com` → Traefik dashboard
- **Never use `localhost:5173`** - different origin = separate localStorage/auth state

**Environment Files:**
- **Single `.env` at project root ONLY** - git-crypt encrypted
- **NO subdirectory `.env` files** - they cause override issues

**Common Issues:**
- **Traefik 404s**: Docker socket connection broken → Restart Docker Desktop
- **API unhealthy after code changes**: `make rebuild-api`
- **Mixed content errors**: Use traefik HTTPS routes, not localhost

---

Happy learning!
