# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Terminology Note**: This is the **local/project ruleset** (specific to this repository). The **personal ruleset** lives in the user's home directory (`~/.claude/CLAUDE.md`) and applies to all projects. This local ruleset takes precedence over personal preferences for project-specific patterns.

## Project Overview

**Multi-agent AI learning spike project** for hands-on exploration of building AI agents with Pydantic AI. This is a **learning/experimental repository**, NOT a production application.

**Primary focus**: Progressive lessons in `lessons/` teaching agent development patterns:
- **Lesson 001**: YouTube video tagging agent (YouTube Transcript API + Claude Haiku)
- **Lesson 002**: Webpage content tagging agent (Docling + Claude Haiku)
- **Lesson 003**: Multi-agent coordinator/router (pattern-based URL routing)

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
└── ...
STATUS.md             # Current progress, known issues, resume instructions
src/                  # (Future) Production code would go here (currently empty)
```

**Long-term vision**: This learning project is evolving toward a **Personal AI Research Assistant and Recommendation Engine**. See `.claude/VISION.md` for the full roadmap and architectural plans.

## Quick Start

### First Time in This Codebase?

1. ✅ **Check current state**: `cat STATUS.md`
2. ✅ **Verify lesson structure**: `ls lessons/`
3. ✅ **Install all dependencies**: `uv sync --all-groups`
4. ✅ **Set up API keys**: Copy `.env` from lesson-001 or create new
   ```bash
   cd lessons/lesson-003
   cp ../lesson-001/.env .
   ```

### Resuming Work?

1. ✅ **Check git status**: `git status`
2. ✅ **Read STATUS.md**: `STATUS.md`
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

**See `multi-agent-ai-projects` skill for detailed lesson patterns.** That skill auto-activates when working with `lessons/` or `STATUS.md`.

### Relationship with STATUS.md

**IMPORTANT**: This CLAUDE.md file provides **static patterns and architectural guidance**.
For **dynamic state, current progress, and next steps**, always check `STATUS.md` first.

- **CLAUDE.md** (this file): How lessons are structured, best practices, commands
- **STATUS.md**: Which lessons are complete, current phase, known issues, resume instructions

### Lessons Structure

Each lesson is a self-contained module in `lessons/lesson-XXX/`:

```
lesson-XXX/
├── <name>_agent/          # Agent implementation package
│   ├── __init__.py
│   ├── agent.py           # Pydantic AI agent setup
│   ├── tools.py           # Tool implementations
│   ├── prompts.py         # System prompts
│   └── cli.py             # Typer CLI (optional)
├── .env                   # API keys (gitignored, never commit!)
├── PLAN.md                # Lesson plan and learning objectives
├── README.md              # Quick reference for the lesson
├── COMPLETE.md            # Summary of learnings after completion
└── test_*.py              # Test scripts and demos
```

**See `lessons/lesson-001/` or any existing lesson for concrete examples.**

### Dependency Management

**Important**: `pyproject.toml` has a **dual structure** due to migration. Always use **`[dependency-groups]`** (lines 67-81) - these have up-to-date versions and proper uv syntax. Ignore `[project.optional-dependencies]` (legacy format).

**Install lesson dependencies:**
```bash
uv sync --group lesson-001      # Single lesson
uv sync --all-groups            # All lessons (recommended)
```

**Dependency composition**: Lesson 003 includes lessons 001+002 via `{include-group = "..."}`.

### Python & Virtual Environments

**The golden rule**: Always use `uv run python` - it handles virtual environment detection automatically. FYI: This project has a hybrid .venv structure (lesson-001 has its own, others share root .venv) for historical reasons, but `uv run` handles it transparently.

**See `python-workflow` skill for general Python patterns.** Quick reference for this project:
```bash
cd lessons/lesson-XXX
uv run python test_script.py           # Run test scripts
uv run python demo.py "URL"            # Run demos
uv run python -m agent_name.cli        # Run CLI (if available)
```

### API Keys and Environment Variables

Each lesson needs `.env` file with API keys (gitignored, never commit):

```bash
# Copy from existing lesson
cd lessons/lesson-003
cp ../lesson-001/.env .

# Or create new
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
DEFAULT_MODEL=claude-3-5-haiku-20241022
EOF
```

**Model selection**: Defaults to Claude Haiku (cheap, fast). Override via `DEFAULT_MODEL` in `.env` or `--model` CLI flag.

### Best Practices for Lesson Work

1. ✅ **Always use `uv run python`** for execution (not `python` or manual venv paths)
2. ✅ **Read STATUS.md first** when resuming work
3. ✅ **Update STATUS.md** after completing a lesson
4. ✅ **Install dependencies before running** - `uv sync --group lesson-XXX`
5. ✅ **Copy API keys** from existing lessons or create new `.env`
6. ✅ **Run tests first** to verify environment setup
7. ✅ **Don't reference `.venv` manually** - let uv handle it
8. ✅ **Keep lessons self-contained** - avoid cross-lesson imports (except lesson-003 coordinator)

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
2. ✅ **Work in `lessons/`** - Each lesson is self-contained
3. ✅ **Check STATUS.md first** - Current state and progress
4. ✅ **Use `uv run python`** - Handles virtual environments automatically
5. ✅ **Install deps with `uv sync --all-groups`** - Before running anything
6. ✅ **Copy `.env` from lesson-001** - API keys needed for each lesson
7. ✅ **Container/Docker stuff?** - Background info only (see below)
8. ✅ **Questions?** - Read the lesson's README.md and COMPLETE.md

---

## Background: Infrastructure & Architecture

**Note**: This infrastructure exists for potential future production deployment, not for daily lesson development. Work directly on host machine with `uv run python`.

**Container setup**: Multi-stage Dockerfile (base, build-base, production, devcontainer). Two-level Makefile system (root for builds, `.devcontainer/` for dev tasks). Uses uv for fast package management (10-100x faster than pip).

**Current state**: `src/` directory is empty. All working code is in `lessons/`. The `src/app/cli.py` would become the production CLI entry point (`agent-spike` command) if this project moves to production.

**For lesson work**: The only environment setup you need is API keys in `.env` files and `uv sync --all-groups`.

---

Happy learning!
