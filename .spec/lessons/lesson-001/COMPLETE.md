# Lesson 001 - COMPLETE ✓

## What We Built

A fully functional **YouTube Video Tagging Agent** that analyzes video transcripts and generates 3-5 relevant tags for read-it-later applications.

### Components

1. **Agent Core** (`agent.py`) - Pydantic AI agent with Claude Haiku
2. **Tools** (`tools.py`) - YouTube transcript fetching
3. **System Prompt** (`prompts.py`) - Tagging-focused instructions
4. **CLI** (`cli.py`) - Typer-based interface

### Key Features

- Fetches real YouTube transcripts via `youtube-transcript-api`
- Analyzes content using Claude or GPT models
- Generates 3-5 broad, reusable tags
- Returns structured JSON output with tags + summary
- CLI with single video and interactive modes

## Usage

```bash
# Single video analysis
cd .spec/lessons/lesson-001
uv run python -m youtube_agent.cli analyze "YOUTUBE_URL"

# Interactive mode
uv run python -m youtube_agent.cli interactive
```

## Example Output

```
Analysis Complete!

{
  "video_title": "How to Build AI Agents Simply (First 90%)",
  "tags": [
    "ai-agents",
    "machine-learning",
    "programming",
    "ai-development",
    "software-engineering"
  ],
  "summary": "A comprehensive guide to building AI agents focusing on core
components like language models, system prompts, tools, and memory, emphasizing
simplicity and avoiding over-complication."
}
```

## What We Learned

### 1. The 4 Core Agent Components
- **LLM** - Claude Haiku (fast, cheap for testing)
- **System Prompt** - Tagging expert with clear rules
- **Tools** - `get_video_info()` and `get_transcript()`
- **Memory** - Short-term conversation history (not needed for single analysis)

### 2. Pydantic AI Framework
- Create agent with `Agent(model, system_prompt=...)`
- Decorate tools with `@agent.tool`
- Run with `await agent.run(prompt)`
- Simple, clean API under 100 lines total

### 3. Tool Integration
- YouTube Transcript API: instantiate `YouTubeTranscriptApi()`, call `fetch(video_id)`
- Handle errors gracefully with try/except
- Return simple strings from tools

### 4. Project Structure
- Used shared `.venv` in root (saves 7GB+ per lesson!)
- Dependencies in `[dependency-groups]` in main `pyproject.toml`
- Install with `uv sync --group lesson-001`

## Challenges & Solutions

### Challenge 1: MCP Server Access
**Problem**: MCP tools available to Claude Code, not Python agent
**Solution**: Used `youtube-transcript-api` directly (simpler for learning)
**Future**: Lesson 003-004 will cover MCP integration

### Challenge 2: youtube-transcript-api Changed
**Problem**: API uses instance methods, not static `get_transcript()`
**Solution**: Instantiate `YouTubeTranscriptApi()` then call `fetch(video_id)`
**Learning**: Always check actual library docs, APIs evolve

### Challenge 3: Pydantic AI Result Type
**Problem**: `result.data` doesn't exist
**Solution**: Use `result.output` or `str(result)`
**Learning**: Framework APIs differ from expectations

## Code Stats

- **Total lines**: ~95 lines (excluding docs)
- **Files**: 4 Python files + CLI
- **Dependencies**: 5 packages
- **Cost per analysis**: < $0.01 using Haiku
- **Time per analysis**: 5-10 seconds

## Next Lessons

**Lesson 002**: Add Langfuse for observability
- See what tools agent calls
- Track token usage and costs
- Monitor performance

**Lesson 003**: Security & Guardrails
- Input validation (prevent prompt injection)
- Output filtering with Guardrails AI
- Rate limiting

**Lesson 004**: Multi-Agent System
- Coordinator agent
- Specialized worker agents
- Inter-agent communication

**Lesson 005**: Long-term Memory with Mem0
- Store tag history across sessions
- Learn user preferences
- Context from previous videos

## Resources

- [Cole Medin's Video](https://www.youtube.com/watch?v=i5kwX7jeWL8) - Original inspiration
- [Pydantic AI Docs](https://ai.pydantic.dev/)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)

## Time Spent

- Planning: 10 minutes
- Implementation: 20 minutes
- Debugging API: 15 minutes
- Testing: 10 minutes
- **Total**: ~55 minutes

**Status**: ✅ COMPLETE AND WORKING
