# Lesson 009: Minimal Orchestrator Agent

**Status**: In Progress
**Model**: gpt-5-nano (for cost-effective testing)

## Goal

Test if an orchestrator pattern provides value over the simple coordinator in lesson-003.

**Hypothesis**: Calling sub-agents with isolated contexts is more efficient than routing to single agents.

## Inspiration

Based on today's research (2025-01-07):
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Data Analytics Agent](https://github.com/agency-ai-solutions/data-analytics-agent)

See comprehensive design docs in `.claude/ideas/orchestrator/`

## What We're Building (MVP)

**Minimal viable orchestrator** - NOT the full 2679-line design!

### Core Components

1. **Orchestrator Agent** (gpt-5-nano)
   - Coordinates multiple sub-agent calls
   - Accumulates results
   - Returns summarized output

2. **call_subagent() Tool**
   - Takes: agent_name (youtube_tagger/webpage_tagger), url
   - Calls appropriate sub-agent with isolated context
   - Returns results

3. **Test Harness**
   - Process 3 YouTube + 2 webpage URLs in one request
   - Compare with lesson-003 coordinator
   - Measure: token usage, time, quality

## What We're NOT Building (Yet)

- ❌ IPython persistent state
- ❌ Progressive tool discovery
- ❌ Code generation
- ❌ Self-evolution
- ❌ Complex sandboxing

**Reason**: Prove basic pattern first, add complexity only if needed.

## Success Criteria

**Orchestrator wins if**:
- Handles multi-URL requests better than lesson-003
- Token usage is demonstrably lower
- Code remains simple (<150 lines total)
- Solves a real problem

**Orchestrator loses if**:
- Just adds complexity with no benefit
- Lesson-003 works fine for actual use cases
- Can't justify the extra abstraction

## Test Plan

1. **Implement orchestrator** (~1 hour)
   - agent.py (orchestrator)
   - tools.py (call_subagent)

2. **Test with real URLs** (~30 min)
   - 3 YouTube videos
   - 2 web articles
   - Process all in one request

3. **Compare with lesson-003** (~30 min)
   - Same URLs through coordinator
   - Measure differences
   - Document findings

4. **Decision** (~15 min)
   - Continue? Add IPython state?
   - Shelf? Move to VISION.md goals?
   - Document rationale in COMPLETE.md

## Timeline

- **Start**: 2025-01-07 evening
- **Expected completion**: 2 hours
- **Decision point**: After comparison with lesson-003

## Next Steps (If Orchestrator Wins)

- Add IPython kernel for persistent state
- Test with larger batches (10+ URLs)
- Measure token savings quantitatively
- Consider progressive tool discovery

## Next Steps (If Orchestrator Loses)

- Document why in COMPLETE.md
- Archive design docs for future reference
- Focus on VISION.md recommendation engine goals
- Revisit when we have proven orchestration need
