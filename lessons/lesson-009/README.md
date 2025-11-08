# Lesson 009: Minimal Orchestrator Agent

**Experiment**: Test if orchestrator pattern provides value over simple coordinator (lesson-003)

## Quick Start

```bash
cd lessons/lesson-009

# Install dependencies
uv sync --group lesson-009

# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=sk-proj-...
DEFAULT_MODEL=gpt-5-nano
EOF

# Run test
uv run python test_orchestrator.py
```

## What This Tests

**Hypothesis**: Calling sub-agents with isolated contexts is more efficient

**Test case**: Process 3 YouTube + 2 webpage URLs in single request
- Orchestrator calls youtube_tagger and webpage_tagger as needed
- Each sub-agent gets isolated context (no shared history)
- Results accumulated and summarized

**Compare with**: lesson-003 coordinator (routes to single agent per request)

## Architecture

```
orchestrator_agent/
├── agent.py     # Orchestrator (gpt-5-nano)
└── tools.py     # call_subagent() tool

Sub-agents (from other lessons):
- youtube_tagger (lesson-001)
- webpage_tagger (lesson-002)
```

## Success Criteria

- ✅ Handles multi-URL requests elegantly
- ✅ Token usage is lower than lesson-003
- ✅ Code stays simple (<150 lines)
- ✅ Solves real problem

## Files

- `PLAN.md` - Detailed plan and rationale
- `test_orchestrator.py` - Test script with comparison
- `orchestrator_agent/` - Implementation
- `COMPLETE.md` - Findings (after testing)

## Inspiration

Based on MCP code execution research (2025-01-07). See `.claude/ideas/orchestrator/` for full design docs.

This is the **minimal viable version** - testing the core idea before building the full system.
