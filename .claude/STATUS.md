# Agent Spike - Current Status

**Last Updated**: 2025-11-07
**Current Phase**: Personal AI Research Assistant - Building infrastructure

## Current State

- ✅ **8 lessons complete**: YouTube, Webpage, Coordinator, Observability, Security, Memory, Cache Manager, Batch Processing
- 🚧 **Lesson 009 IN PROGRESS**: Orchestrator experiment (testing if orchestrator pattern provides value over simple coordinator)
- **Long-term goal**: Personal AI Research Assistant (see `.claude/VISION.md`)
- **Project structure**:
  - `lessons/`: Progressive agent-building lessons (001-009)
  - `projects/data/`: Centralized data storage (Qdrant cache, brave_history backups)
  - `projects/video-lists/`: CSV files for content ingestion
  - `tools/`: Shared utilities (dotenv.py for centralized environment config)
- All agents instrumented with Pydantic Logfire for tracing
- Security guardrails implemented (input/output validation, rate limiting, PII detection)
- Memory layer integrated with Mem0 (user preferences, semantic search)
- Production-ready patterns: observability, security, memory, caching, batch processing

## Recent Completions

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

### In Progress

**🚧 Lesson 009: Orchestrator Experiment** (Testing Hypothesis)
- Testing if orchestrator pattern provides value over simple coordinator
- Minimal viable orchestrator with call_subagent() tool
- Comparing token usage and efficiency vs lesson-003 coordinator
- Decision point: continue or shelf based on results

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

## File Locations

- Lesson code: `lessons/lesson-XXX/`
- Lesson docs: `lessons/lesson-XXX/{PLAN.md, README.md, COMPLETE.md}`
- This status file: `STATUS.md` (project root)
- Main config: `pyproject.toml` (project root)
- Shared .venv: `.venv/` (project root)

## Git State

- Branch: main
- Recent commits: Lessons 001-004 implementations
- Status: Clean working tree

**To Resume**: Pull latest, run `uv sync --all-groups`, create `.env` files

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
