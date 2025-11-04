# Lesson 003: Multi-Agent Coordinator

A router agent that intelligently coordinates between specialized agents (YouTube and Webpage) to process any URL through a single unified interface.

## What It Does

- Automatically classifies URLs as YouTube videos or webpages
- Routes requests to the appropriate specialized agent
- Provides a single CLI for all URL types
- Returns consistent tag-based analysis regardless of source

## Quick Start

```bash
# Install dependencies
cd .spec/lessons/lesson-003
uv sync --group lesson-003

# Configure API keys (copy from lesson-001 or create new)
cp ../lesson-001/.env .

# Test the router logic
uv run python test_router.py

# Test the full coordinator
uv run python test_coordinator.py
```

## Architecture

```
User Input (URL)
    ↓
URL Router (pattern-based classification)
    ↓
    ├─→ YouTube Agent (if youtube.com/youtu.be)
    │   └─→ Returns tags & summary
    │
    └─→ Webpage Agent (if other URL)
        └─→ Returns tags & summary
```

## Project Structure

```
coordinator_agent/
├── __init__.py
├── router.py         # URL classification logic
├── agent.py          # Coordinator agent
└── cli.py            # Unified CLI interface

test_router.py        # Router unit tests
test_coordinator.py   # Integration tests
```

## Usage Examples

### Analyze Any URL

```bash
# YouTube video
uv run python demo.py "https://youtube.com/watch?v=..."

# Webpage
uv run python demo.py "https://github.com/..."
```

### Interactive Mode

```bash
../../../.venv/Scripts/python.exe -m coordinator_agent.cli interactive
```

Enter any URL and it will automatically route to the correct agent.

## Key Learnings

1. **Router Pattern**: Simple pattern-based routing is faster and more reliable than LLM-based classification
2. **Agent Composition**: Reusing existing agents through imports is simpler than rebuilding
3. **Unified Interface**: A single entry point improves user experience
4. **Path Management**: Python path management across lesson directories requires careful setup

## Dependencies

Lesson 003 depends on:
- All dependencies from lesson-001 (YouTube agent)
- All dependencies from lesson-002 (Webpage agent)

No new dependencies required - just orchestration code.

## Known Issues

- Must use venv Python explicitly (`../../../.venv/Scripts/python.exe`) due to path issues
- CLI commands like `uv run python -m ...` don't work from subdirectories
- Windows/MSYS path resolution can be tricky

## Next Steps

- Lesson 004: Add observability with Langfuse to track multi-agent flows
- Lesson 005: Add guardrails and security checks
- Lesson 006: Add long-term memory with Mem0 for cross-agent learning
