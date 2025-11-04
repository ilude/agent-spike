# Agent Spike - Current Status

**Last Updated**: 2025-11-04
**Current Phase**: Multi-agent learning - 3 lessons complete

## Completed Lessons

### ✅ Lesson 001: YouTube Video Tagging Agent
- **Location**: `.spec/lessons/lesson-001/`
- **Status**: Complete and working
- **Tech**: Pydantic AI, youtube-transcript-api, Claude Haiku
- **What it does**: Analyzes YouTube video transcripts and generates 3-5 tags
- **Run**: `cd .spec/lessons/lesson-001 && uv run python -m youtube_agent.cli analyze "YOUTUBE_URL"`
- **Key files**: `youtube_agent/{agent.py, tools.py, prompts.py, cli.py}`
- **Time**: ~55 minutes to build

### ✅ Lesson 002: Webpage Content Tagging Agent
- **Location**: `.spec/lessons/lesson-002/`
- **Status**: Complete and working
- **Tech**: Pydantic AI, Docling, Claude Haiku
- **What it does**: Fetches webpages, converts to Markdown, generates 3-5 tags
- **Run**: `cd .spec/lessons/lesson-002 && uv run python -m webpage_agent.cli analyze "WEBPAGE_URL"`
- **Key files**: `webpage_agent/{agent.py, tools.py, prompts.py, cli.py}`
- **Code reuse**: 80% from Lesson 001
- **Time**: ~60 minutes to build

### ✅ Lesson 003: Multi-Agent Coordinator
- **Location**: `.spec/lessons/lesson-003/`
- **Status**: Complete and working
- **Tech**: Pattern-based routing, agent composition
- **What it does**: Routes any URL to appropriate agent (YouTube or Webpage)
- **Run**: `cd .spec/lessons/lesson-003 && ../../../.venv/Scripts/python.exe test_coordinator.py`
- **Key files**: `coordinator_agent/{router.py, agent.py, cli.py}`
- **Pattern**: Router/Coordinator multi-agent pattern
- **Code reuse**: 100% reuse of existing agents
- **Time**: ~75 minutes to build

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
uv sync --group lesson-001 --group lesson-002 --group lesson-003

# Copy environment variables
# Create .env files in lesson directories with:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-proj-...
# DEFAULT_MODEL=claude-3-5-haiku-20241022

# Test Lesson 001
cd .spec/lessons/lesson-001
uv run python -m youtube_agent.cli analyze "https://www.youtube.com/watch?v=i5kwX7jeWL8"

# Test Lesson 002
cd .spec/lessons/lesson-002
uv run python -m webpage_agent.cli analyze "https://github.com/docling-project/docling"

# Test Lesson 003 (Coordinator)
cd .spec/lessons/lesson-003
uv run python test_coordinator.py
```

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

**Note**: `.venv` is in project root (shared across lessons to save ~7GB per lesson)

## Architecture Pattern

Both lessons follow the same structure:
```
lesson-XXX/
├── <name>_agent/
│   ├── __init__.py
│   ├── agent.py       # Pydantic AI agent setup
│   ├── tools.py       # Tool implementations
│   ├── prompts.py     # System prompts
│   └── cli.py         # Typer CLI interface
├── .env               # API keys
├── PLAN.md           # Lesson plan
├── ARCHITECTURE.md   # Design docs
├── README.md         # Quick reference
└── COMPLETE.md       # Summary of learnings
```

## API Keys Required

Both lessons use the same API keys (configured in `.env` files):
- `ANTHROPIC_API_KEY` - For Claude models
- `OPENAI_API_KEY` - For GPT models
- `DEFAULT_MODEL` - Optional, defaults to `claude-3-5-haiku-20241022`

**Security**: `.env` files are gitignored, must be created manually on each machine

## Learning Source

All lessons based on Cole Medin's video:
- **Video**: "Learn 90% of Building AI Agents in 30 Minutes"
- **URL**: https://www.youtube.com/watch?v=i5kwX7jeWL8
- **Concepts**: 4 core components (LLM, System Prompt, Tools, Memory)

## What's Next

### Planned Future Lessons

**Lesson 004: Observability with Langfuse** (Next up)
- Add observability to all three agents
- Track routing decisions and agent selection
- Monitor tool calls, costs, latency across multi-agent flows
- Debugging and monitoring dashboard
- Estimated time: 60 minutes

**Lesson 005: Security & Guardrails**
- Guardrails AI integration
- Input/output validation
- Rate limiting
- Estimated time: 45 minutes

**Lesson 006: Long-term Memory with Mem0**
- Tag standardization
- User preference learning
- Cross-session context
- Estimated time: 60 minutes

## Notes for Resume

### Current State
- 3 agents working: YouTube, Webpage, and Coordinator
- All tested and functional
- Coordinator successfully routes to specialized agents
- All use same dependencies (shared .venv)
- Ready for observability layer (Lesson 004)

### Known Issues
- Some JavaScript-heavy websites fail with Docling (returns 404)
  - Example: https://simonwillison.net/... (dynamic routing)
  - Works fine with: GitHub, example.com, static sites
- Docling includes some navigation in output (handled via prompt instructions)
- ~~Lesson 003: Path issues~~ - **RESOLVED**: Use `uv run python` from any directory

### Design Decisions Made
1. **Shared .venv**: All lessons use root .venv (saves disk space)
2. **Dependency groups**: Each lesson = separate dependency group in `pyproject.toml`
3. **15k char limit**: Webpage content truncated for cost control
4. **HTML only**: Lesson 002 doesn't handle PDFs yet (could add later)
5. **Claude Haiku default**: Cheap and fast for prototyping
6. **Pattern-based routing** (Lesson 003): Regex for URL classification (not LLM)
7. **Direct agent import** (Lesson 003): Composition over complex orchestration

### File Locations
- Planning docs: `.spec/lessons/lesson-XXX/*.md`
- Source code: `.spec/lessons/lesson-XXX/<name>_agent/`
- This status file: `.spec/STATUS.md`
- Main pyproject.toml: `./pyproject.toml`
- Shared .venv: `./.venv/`

## Quick Commands Reference

```bash
# Install lesson dependencies
uv sync --group lesson-001
uv sync --group lesson-002
uv sync --group lesson-003

# Run agents
cd .spec/lessons/lesson-001 && uv run python -m youtube_agent.cli analyze "URL"
cd .spec/lessons/lesson-002 && uv run python -m webpage_agent.cli analyze "URL"

# Run coordinator (routes automatically)
cd .spec/lessons/lesson-003 && uv run python test_coordinator.py

# Test router
cd .spec/lessons/lesson-003 && uv run python test_router.py

# Interactive mode
cd .spec/lessons/lesson-001 && uv run python -m youtube_agent.cli interactive
cd .spec/lessons/lesson-002 && uv run python -m webpage_agent.cli interactive

# Check dependencies
uv pip list | grep -E "(pydantic-ai|docling|youtube-transcript)"
```

## Git State

- Branch: main
- Recent commits: Lessons 001, 002, and 003 implementations
- Uncommitted: Status file updates

**To Resume**: Pull latest, run `uv sync --all-groups`, create `.env` files
