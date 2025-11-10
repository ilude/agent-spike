Communication Style: Be direct and straightforward. No cheerleading phrases like "that's absolutely right" or "great question." Tell me when my ideas are flawed, incomplete, or poorly thought through. Use casual language and occasional profanity when appropriate. Focus on practical problems and realistic solutions rather than being overly positive or encouraging.

Technical Approach: Challenge assumptions, point out potential issues, and ask the hard questions about implementation, scalability, and real-world viability. If something won't work, say so directly and explain why it has problems rather than just dismissing it.

**Development Philosophy**: Experiment-driven, fail-fast approach. Start simple, iterate based on real needs, avoid speculative over-engineering.

**Terminology Note**: This is the **local/project ruleset** (specific to this repository). The **personal ruleset** lives in the user's home directory (`~/.claude/CLAUDE.md`) and applies to all projects. This local ruleset takes precedence over personal preferences for project-specific patterns.

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
- Allows migration between storage systems (Qdrant → Pinecone, etc.)
- Supports reprocessing with different strategies (chunking, embeddings, etc.)

**Archive location:** `projects/data/archive/` (organized by source and month)

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

## Project Overview

**Multi-agent AI learning spike project** for hands-on exploration of building AI agents with Pydantic AI. This is a **learning/experimental repository**, NOT a production application.

**Primary focus**: Progressive lessons in `lessons/` teaching agent development patterns:
- **Lesson 001**: YouTube video tagging agent (YouTube Transcript API + Claude Haiku)
- **Lesson 002**: Webpage content tagging agent (Docling + Claude Haiku)
- **Lesson 003**: Multi-agent coordinator/router (pattern-based URL routing)
- **Lesson 004**: Observability with Logfire (tracing and monitoring)
- **Lesson 005**: Security guardrails (input validation and safety)
- **Lesson 006**: Memory with Mem0 (persistent agent memory)
- **Lesson 007**: Cache Manager with Qdrant (vector database for caching)
- **Lesson 008**: Batch Processing with OpenAI (async batch operations)

**Learning source**: Based on Cole Medin's "Learn 90% of Building AI Agents in 30 Minutes" video (https://www.youtube.com/watch?v=i5kwX7jeWL8).

**Tech stack**:
- Python 3.14
- Pydantic AI framework
- uv package manager (not pip)
- Typer CLIs per lesson
- Claude Haiku for cost-effective prototyping

**Development workflow**:
- Work directly in `lessons/` directories
- Run code with `uv run python` (handles virtual environments automatically)
- Each lesson is self-contained with its own agent, CLI, tests, and documentation

**Directory structure**:
```
lessons/               # Progressive agent-building lessons
├── lesson-001/       # YouTube tagging agent
├── lesson-002/       # Webpage tagging agent
├── lesson-003/       # Multi-agent coordinator
├── lesson-004/       # Observability (Logfire)
├── lesson-005/       # Security guardrails
├── lesson-006/       # Memory (Mem0)
├── lesson-007/       # Cache Manager (Qdrant)
└── lesson-008/       # Batch Processing (OpenAI)
.claude/STATUS.md     # Current progress, known issues, resume instructions
```

**Long-term vision**: This learning project is evolving toward a **Personal AI Research Assistant and Recommendation Engine**. See `.claude/VISION.md` for the full roadmap and architectural plans.

## Quick Start

### First Time in This Codebase?

1. ✅ **Check current state**: `cat .claude/STATUS.md`
2. ✅ **Verify lesson structure**: `ls lessons/`
3. ✅ **Install all dependencies**: `uv sync --all-groups`
4. ✅ **Set up API keys**: Copy `.env` from lesson-001 or create new
   ```bash
   cd lessons/lesson-003
   cp ../lesson-001/.env .
   ```

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

**Loading environment**: Use `tools/dotenv.py` utility in test scripts:
```python
from tools.dotenv import load_root_env
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

# Check what's installed
uv pip list

# Run lesson CLI (if available)
cd lessons/lesson-001
uv run python -m youtube_agent.cli analyze "https://youtube.com/..."
```

### Code Quality (Less Common)

```bash
make format                             # black + isort
make lint                               # ruff
make test                               # pytest
```

### Container Builds (Rarely Needed)

**Note**: Lessons run directly via `uv run python`. Container builds are for the (future) production app in `src/`.

```bash
make build-dev                          # Build devcontainer
make build                              # Build production image
```

For full command reference, see `.devcontainer/Makefile` and root `Makefile`.

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
2. ✅ **Work in `lessons/`** - 9 lessons total, all complete (001-009)
3. ✅ **Check STATUS.md first** - Current state and progress
4. ✅ **Use `uv run python`** - Handles virtual environments automatically
5. ✅ **Install deps with `uv sync --all-groups`** - Before running anything
6. ✅ **Create `.env` in lesson dir** - Add your API keys (see Project-Specific Notes)
7. ✅ **Container/Docker stuff?** - Background info only (see below)
8. ✅ **Questions?** - Read the lesson's README.md and COMPLETE.md

---

## Background: Infrastructure & Architecture

**Note**: This infrastructure exists for potential future production deployment, not for daily lesson development. Work directly on host machine with `uv run python`.

**Container setup**: Multi-stage Dockerfile (base, build-base, production, devcontainer). Two-level Makefile system (root for builds, `.devcontainer/` for dev tasks). Uses uv for fast package management (10-100x faster than pip).

**Current state**: All working code is in `lessons/`. A future `src/` directory would contain production code (doesn't exist yet).

**For lesson work**: The only environment setup you need is API keys in `.env` files and `uv sync --all-groups`.

---

Happy learning!
