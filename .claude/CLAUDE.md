# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Style

Be direct and straightforward. Challenge assumptions, point out issues, ask hard questions. No cheerleading. Use casual language. Focus on practical problems and realistic solutions.

enable-session-commits: true

## Project Overview

**Multi-agent AI learning spike** evolving into a **Personal AI Research Assistant**. See `.claude/STATUS.md` for current state and `.claude/VISION.md` for long-term roadmap.

**Two main areas:**
1. `lessons/` - Progressive agent-building lessons (001-010 complete)
2. `compose/` - Production platform (Mentat Chat UI with full-stack architecture)

**Tech stack:** Python 3.14, Pydantic AI, uv package manager, FastAPI, SvelteKit, SurrealDB, OpenTelemetry

## Quick Start

```bash
# First time
git-crypt unlock                     # Decrypt .env (API keys)
uv sync --all-groups                 # Install all dependencies

# Resume work
cat .claude/STATUS.md                # Check current state
git status                           # Check uncommitted changes

# Start platform
cd compose && docker compose up -d   # Start API, Traefik, worker
cd compose/frontend && bun run dev   # Start frontend (separate terminal)
```

## Essential Commands

```bash
# Python execution (ALWAYS use uv run)
uv run python script.py              # Run any script
uv run python -m pytest              # Run tests

# Code quality
make test                            # Run all tests
make lint                            # ruff check
make format                          # black + isort

# GPU server (192.168.16.241 - runs heavy AI services)
make gpu-deploy                      # Deploy compose stack
make gpu-update                      # Pull images + restart
```

## Architecture

### Local Services (Docker Compose in `compose/`)

| Service | Port | Notes |
|---------|------|-------|
| Traefik | 80/443 | Reverse proxy + Let's Encrypt |
| API | 8000 | FastAPI backend |
| Queue Worker | - | Async job processor |
| Alloy | 12345 | Log collection → Loki |
| Frontend | 5173 | Runs locally (not containerized) |

### Remote GPU Server (192.168.16.241)

| Service | Port | Purpose |
|---------|------|---------|
| SurrealDB | 8000 | Primary database |
| Infinity | 7997 | Embeddings (gte-large-en-v1.5) |
| Loki/Prometheus/Tempo/Grafana | various | LGTM observability stack |
| Ollama | 11434 | Local LLMs |
| MinIO | 9000 | Object storage |

### Key URLs

- `https://mentat.local.ilude.com` → Frontend
- `https://api.local.ilude.com` → FastAPI backend
- `http://192.168.16.241:3000` → Grafana dashboards

## Code Organization

```
compose/
├── api/routers/     # FastAPI routers (20+ endpoints)
├── services/        # Business logic (20+ services)
├── frontend/        # SvelteKit chat application
├── worker/          # Queue processor with metrics
├── lib/             # Shared utilities (telemetry, env_loader)
└── data/            # Git-crypt encrypted storage

lessons/             # Progressive agent lessons (001-010)
infra/ansible/       # GPU server deployment automation
```

## Critical Rules

### Archive-First Pattern
**Archive anything that costs time/money BEFORE processing:**
1. Fetch expensive data (transcript, webpage) → Archive immediately
2. Generate LLM outputs (tags, summaries) → Archive immediately
3. Process/embed/cache → Derived data (can rebuild from archives)

Location: `compose/data/archive/` (organized by source and month)

### Environment
- **Single shared `.venv` at project root** - UV workspace configuration
- **Always `uv run python`** - Never reference `.venv/Scripts/python.exe`
- **Root `.env` encrypted** - Use `git-crypt unlock` or set vars manually

### Loading API Keys
```python
from compose.lib.env_loader import load_root_env
load_root_env()  # Finds git root, loads .env automatically
```

## Dependency Groups

Each lesson and service has its own group in `pyproject.toml`:
```bash
uv sync --group lesson-007           # Single lesson
uv sync --group platform-api         # Platform API service
uv sync --all-groups                 # Everything (recommended)
```

## Design Decisions

1. **SurrealDB as primary store** - Unified database with native vector indexes
2. **Remote GPU server** - Heavy services (embeddings, LGTM stack) on dedicated hardware
3. **Frontend runs locally** - Windows hot reload issues with containerized Vite
4. **Protocol-first services** - `typing.Protocol` for dependency injection
5. **OTLP proxy** - Solves browser CORS for frontend telemetry
