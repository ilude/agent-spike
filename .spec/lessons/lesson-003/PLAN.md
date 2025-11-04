# Lesson 003: Multi-Agent Coordinator

## Learning Objectives

- Understand multi-agent system architecture patterns
- Build a router/coordinator agent
- Implement agent-to-agent communication
- Create a unified interface for multiple specialized agents
- Learn URL pattern detection and routing logic

## Project Overview

Build a coordinator agent that:
1. Accepts any URL (YouTube or webpage)
2. Classifies the URL type automatically
3. Routes to the appropriate specialized agent (Lesson 001 or 002)
4. Returns unified, consistent output
5. Provides a single CLI entry point

## Technologies

- **Python 3.14** with shared .venv (root project)
- **uv** - Package manager
- **Pydantic AI** - Agent framework
- **Existing agents** - YouTube agent (Lesson 001), Webpage agent (Lesson 002)
- **Typer** - Unified CLI interface

## Architecture

```
coordinator_agent/
├── __init__.py
├── agent.py          # Main coordinator/router agent
├── router.py         # URL classification logic
├── prompts.py        # System prompts for coordinator
└── cli.py            # Unified CLI interface
```

## Multi-Agent Pattern

### Router Pattern
```
User Input (URL)
    ↓
Coordinator Agent (classify URL)
    ↓
    ├─→ YouTube Agent (if youtube.com/youtu.be)
    │   └─→ Returns tags
    │
    └─→ Webpage Agent (if other URL)
        └─→ Returns tags
```

### Agent Communication
- **Option 1**: Direct Python imports (simple, tight coupling)
- **Option 2**: Agent as orchestrator (Pydantic AI coordination)
- **Going with Option 1** for simplicity and learning

## Implementation Steps

1. **Setup** (~5 min)
   - Create lesson-003 directory structure
   - Add dependency group to root pyproject.toml
   - Create .env file (reuse API keys)

2. **URL Router** (~15 min)
   - Implement URL classification logic
   - Detect YouTube URLs (youtube.com, youtu.be, m.youtube.com)
   - Validate URLs
   - Handle edge cases

3. **Coordinator Agent** (~20 min)
   - Import existing agents from Lessons 001 and 002
   - Create coordinator that routes requests
   - Handle responses from both agents
   - Normalize output format

4. **Unified CLI** (~15 min)
   - Single `analyze` command for any URL
   - Display URL type detection
   - Show which agent is handling the request
   - Pretty output with Rich

5. **Testing** (~10 min)
   - Test with YouTube URLs
   - Test with webpage URLs
   - Test with invalid URLs
   - Test with edge cases (short URLs, redirects)

## Expected Output

```bash
# Unified CLI for any URL
uv run python -m coordinator_agent.cli analyze "https://youtube.com/watch?v=..."

# Output:
URL Type: YouTube Video
Handler: YouTube Agent
Tags: [ai-agents, tutorial, python, langchain, automation]

uv run python -m coordinator_agent.cli analyze "https://github.com/docling-project"

# Output:
URL Type: Webpage
Handler: Webpage Agent
Tags: [document-processing, python, ai, parsing, pdf]
```

## Success Criteria

- ✓ Correctly classifies YouTube vs webpage URLs (100% accuracy on common patterns)
- ✓ Routes to appropriate agent without user intervention
- ✓ Returns consistent output format regardless of agent
- ✓ Handles errors from either agent gracefully
- ✓ Single CLI command for all URL types
- ✓ Code is clean and maintainable (<150 lines)

## Design Decisions

### URL Classification Strategy
- **Pattern-based** (not LLM-based) for speed and reliability
- Regex patterns for YouTube domains
- Fast local classification (no API calls)

### Agent Integration
- **Direct import** of existing agent modules
- Reuse agent.run() methods from Lessons 001 and 002
- No modification to existing agents (composition over modification)

### Error Handling
- If YouTube agent fails → fallback to webpage agent
- If webpage agent fails → return error with details
- Network errors → retry once before failing

### Output Format
- Consistent 3-5 tags regardless of source agent
- Include metadata: URL type, handler used, processing time
- Rich formatting for CLI display

## Dependencies

Lesson 003 depends on:
- All dependencies from lesson-001 (YouTube agent)
- All dependencies from lesson-002 (Webpage agent)

No new dependencies needed - coordinator just orchestrates existing agents.

## Next Steps (Future Lessons)

- Lesson 004: Add observability with Langfuse (track multi-agent flows)
- Lesson 005: Add guardrails and security
- Lesson 006: Add long-term memory with Mem0 (cross-agent learning)

## Notes

- No new API calls needed for routing (pattern-based)
- Reuses existing .env configuration
- Both agent modules must be in same .venv (already done)
- Keep coordinator logic simple - it's just a router
- Focus on learning multi-agent patterns, not complex orchestration
