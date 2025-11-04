# Lesson 001: YouTube Transcript Categorization Agent

## Learning Objectives

- Understand the 4 core components of AI agents (LLM, System Prompt, Tools, Memory)
- Build a simple agent using Pydantic AI framework
- Integrate MCP server tools into an agent
- Design effective system prompts for specific tasks
- Implement CLI-based agent interaction

## Project Overview

Build an AI agent that can:
1. Accept YouTube video URLs
2. Fetch video transcripts using MCP YouTube tools
3. Categorize transcripts by topic/content type
4. Provide structured output with categorization results

## Technologies

- **Python 3.14** with shared .venv (root project)
- **uv** - Package manager (not pip)
- **Pydantic AI** - Agent framework
- **OpenAI/Claude APIs** - LLM backend
- **YouTube Transcript API** - Direct YouTube access
- **Typer** - CLI interface (already in project)

## Architecture

```
youtube_agent/
├── __init__.py
├── agent.py          # Core agent with Pydantic AI
├── tools.py          # MCP tool wrappers
├── prompts.py        # System prompts
└── cli.py            # Typer CLI interface
```

## Agent Components

### 1. System Prompt
- Persona: YouTube content analyst
- Goal: Categorize video content accurately
- Instructions: How to analyze transcripts
- Output format: Structured categorization (JSON/dict)

### 2. Tools
- `get_video_info(url)` - Fetch video metadata
- `get_transcript(url)` - Fetch full transcript
- (MCP tools already available in Claude Code environment)

### 3. LLM Choice
- Start with: Claude Haiku 4.5 (cheap, fast for testing)
- Alternative: GPT-4o-mini
- Use environment variable for easy switching

### 4. Memory
- Short-term: Conversation history for CLI
- No long-term memory needed for Lesson 001

## Implementation Steps

1. **Setup** (~5 min)
   - Use root project .venv (shared across all lessons)
   - Install with: `uv sync --group lesson-001`
   - Create .env file in lesson-001 directory

2. **MCP Integration** (~15 min)
   - Test YouTube MCP tools directly
   - Create wrapper functions to call MCP from Python
   - Handle MCP tool responses

3. **Agent Core** (~20 min)
   - Define system prompt for categorization
   - Create Pydantic AI agent
   - Wire up MCP tool wrappers
   - Test with single video

4. **CLI Interface** (~10 min)
   - Simple Typer CLI
   - Accept URL as argument
   - Display categorization results
   - Interactive mode for multiple videos

5. **Testing & Iteration** (~10 min)
   - Test with various video types
   - Refine system prompt based on results
   - Handle edge cases (no transcript, errors)

## Expected Output

```bash
# Single video analysis
uv run python -m youtube_agent.cli analyze "https://youtube.com/watch?v=..."

# Result:
Video: "Learn 90% of Building AI Agents"
Duration: 29 minutes
Category: Educational/Technical
Topics: [AI Agents, Python, LangChain, System Design]
Content Type: Tutorial
Audience: Developers/Intermediate
Summary: Comprehensive guide to building AI agents...
```

## Success Criteria

- ✓ Agent successfully fetches video transcripts
- ✓ Categorizes content into meaningful categories
- ✓ Returns structured, consistent output
- ✓ Handles errors gracefully
- ✓ Code is <100 lines (keeping it simple!)

## Next Steps (Future Lessons)

- Lesson 002: Add observability with Langfuse
- Lesson 003: Add guardrails and security
- Lesson 004: Multi-agent system (coordinator + workers)
- Lesson 005: Long-term memory with Mem0

## Questions Before Starting

1. Which LLM API key do you have ready? (OpenAI, Claude, both?)
2. Should categorization be free-form or use predefined categories?
3. Any specific video types you want to test with?

## Notes

- Using .venv locally (not devcontainer) as requested
- CLI-only interface for now
- Skipping Langfuse/Guardrails for simplicity
- Can run alongside main agent-spike CLI without conflicts
