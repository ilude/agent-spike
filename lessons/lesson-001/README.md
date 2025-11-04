# Lesson 001: YouTube Transcript Categorization Agent

**Status**: Planning Complete ✓
**Difficulty**: Beginner
**Time Estimate**: 60 minutes
**Prerequisites**: Python 3.14, OpenAI or Claude API key

## Overview

Build your first AI agent that analyzes YouTube videos by fetching transcripts and categorizing content. This lesson covers the 4 core components of AI agents based on Cole Medin's video "Learn 90% of Building AI Agents in 30 Minutes".

## What You'll Learn

- Setting up Pydantic AI agent framework
- Designing effective system prompts
- Creating tools for agents to use
- Handling API integrations (YouTube transcripts)
- Building CLI interfaces with Typer
- Basic error handling in agent systems

## What You'll Build

An agent that:
1. Takes YouTube URLs as input
2. Fetches video metadata and transcripts
3. Analyzes content using LLM
4. Returns structured categorization (topics, audience, type)

## Planning Documents

- **[PLAN.md](./PLAN.md)** - Complete lesson plan and objectives
- **[DEPENDENCIES.md](./DEPENDENCIES.md)** - Required packages and setup
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and prompts

## Quick Start

Implementation complete! To use:

```bash
# From project root, ensure dependencies are installed
uv sync --group lesson-001

# Navigate to lesson directory
cd .spec/lessons/lesson-001

# Run the agent
uv run python -m youtube_agent.cli analyze "YOUTUBE_URL"

# Or interactive mode
uv run python -m youtube_agent.cli interactive
```

Note: Uses shared .venv in project root to save disk space.

## Next Steps

1. Review planning documents above
2. Confirm API keys are ready
3. Ask any questions about the approach
4. Begin implementation when ready

## Questions Before Starting?

- Which LLM provider? (OpenAI, Claude, both?)
- Free-form categorization or predefined categories?
- Any specific video types to test?

Let me know when you're ready to start coding!
