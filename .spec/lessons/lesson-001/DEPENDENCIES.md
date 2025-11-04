# Lesson 001 Dependencies

## Python Packages

```bash
# Core agent framework
pydantic-ai-slim[openai,anthropic]  # Pydantic AI with LLM providers

# CLI
typer[all]                          # Already in main project, but isolated here

# Environment & config
python-dotenv                       # Load .env files

# Optional (for better output formatting)
rich                                # Pretty CLI output
```

## Environment Variables (.env)

```bash
# LLM API Keys (provide at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Default model (optional, can override)
DEFAULT_MODEL=claude-haiku-4-5
# or: DEFAULT_MODEL=gpt-4o-mini
```

## MCP Server Access

**YouTube MCP Server** - Already running in Claude Code environment
- `mcp__MCP_DOCKER__get_video_info`
- `mcp__MCP_DOCKER__get_transcript`
- `mcp__MCP_DOCKER__get_timed_transcript`

**Challenge**: MCP tools are available to Claude Code, but not directly to our Python agent.

## Integration Approach

### Option A: Direct MCP Access (Complex)
- Run MCP server separately
- Connect via stdio/SSE
- Requires MCP client implementation

### Option B: Proxy Pattern (Recommended for Lesson 001)
- Agent uses native Python tools
- Tools call YouTube API directly (youtube-transcript-api)
- Simpler, self-contained
- Learn MCP integration in later lesson

### Option C: Hybrid (Future)
- Build simple MCP client wrapper
- Agent learns to use MCP pattern
- More realistic production setup

## Recommended Stack for Lesson 001

```toml
[project]
name = "youtube-agent"
version = "0.1.0"
requires-python = ">=3.14"

dependencies = [
    "pydantic-ai-slim[openai,anthropic]>=0.0.14",
    "typer[all]>=0.15.0",
    "python-dotenv>=1.0.0",
    "youtube-transcript-api>=0.6.2",  # Direct YouTube access
    "rich>=13.9.0",
]
```

## Installation Commands

```bash
# Create isolated environment for lesson
cd .spec/lessons/lesson-001
python -m venv .venv

# Windows
.venv\Scripts\activate

# Install dependencies
pip install pydantic-ai-slim[openai,anthropic] typer[all] python-dotenv youtube-transcript-api rich

# Or use uv (faster)
uv venv .venv
uv pip install pydantic-ai-slim[openai,anthropic] typer[all] python-dotenv youtube-transcript-api rich
```

## Next Decision

**Choose integration approach:**
- Start with Option B (direct YouTube API) - simpler, self-contained
- Move to Option C in Lesson 003-004 (MCP integration)

**Reason**: Focus on learning agent fundamentals first, not MCP complexity.
