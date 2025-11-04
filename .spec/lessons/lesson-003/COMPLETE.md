# Lesson 003: Multi-Agent Coordinator - Complete!

**Status**: ✅ Complete and working
**Time Spent**: ~75 minutes
**Date**: 2025-11-04

## What We Built

A coordinator agent that routes URLs to specialized agents using pattern-based classification:

- **URL Router**: Classifies YouTube vs webpage URLs using regex patterns
- **Coordinator Agent**: Orchestrates calls to YouTube and Webpage agents
- **Unified CLI**: Single interface for all URL types
- **Integration Tests**: Validates routing and agent responses

## Architecture Pattern: Router/Coordinator

```
┌─────────────────────────────────────────────┐
│          Coordinator Agent                   │
│                                              │
│  1. Receive URL                              │
│  2. Classify URL (YouTube/Webpage/Invalid)   │
│  3. Route to appropriate agent               │
│  4. Return normalized response               │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│ YouTube      │        │ Webpage      │
│ Agent        │        │ Agent        │
│ (Lesson 001) │        │ (Lesson 002) │
└──────────────┘        └──────────────┘
```

## Key Components

### 1. URL Router (`router.py`)
- Pattern-based classification (not LLM)
- Regex patterns for YouTube domains
- Fast, deterministic, no API calls
- Handles: youtube.com, youtu.be, m.youtube.com, shorts, embed

### 2. Coordinator Agent (`agent.py`)
- Imports existing agents from lessons 001 & 002
- Routes based on URLRouter classification
- Normalizes responses into CoordinatorResult
- Error handling for invalid URLs and agent failures

### 3. Unified CLI (`cli.py`)
- Single `analyze` command for any URL
- Interactive mode for multiple URLs
- Batch mode for processing lists
- Test command for router validation

## Technical Decisions

### ✅ What Worked Well

1. **Pattern-Based Routing**
   - Faster than LLM classification
   - 100% accurate for common patterns
   - No API costs for routing

2. **Direct Agent Import**
   - Simpler than complex orchestration
   - Reuses existing code without modification
   - Tight coupling acceptable for learning project

3. **Shared Dependencies**
   - All lessons use same .venv
   - Dependency groups manage lesson-specific packages
   - Saves disk space and installation time

### ⚠️ Challenges Encountered

1. **Python Path Management**
   - Subdirectory execution requires explicit venv Python
   - `uv run python -m ...` doesn't work from lesson dirs
   - Solution: Use `../../../.venv/Scripts/python.exe` directly

2. **Dependency Group Syntax**
   - Include-group syntax: `{include-group = "lesson-001"}`
   - Typer not automatically inherited from main dependencies
   - Solution: Add typer explicitly to each lesson group

3. **Windows/MSYS Path Issues**
   - Unicode characters fail in Windows console
   - Path separators inconsistent
   - Solution: Use ASCII characters, absolute venv paths

## What I Learned

### Multi-Agent Patterns

1. **Router Pattern**: Best for clear categorization with known patterns
2. **Coordinator Pattern**: Useful when one agent orchestrates multiple specialists
3. **Composition over Inheritance**: Importing existing agents better than subclassing

### Python Project Structure

1. **Dependency Groups**: Perfect for organizing optional feature sets
2. **Path Management**: Critical for multi-directory projects
3. **Virtual Environments**: Shared venv works well with proper tooling

### Development Process

1. **Test Early**: Router tests caught issues before integration
2. **Incremental Build**: Router → Agent → CLI → Tests
3. **Real-World Testing**: Integration tests with actual APIs validated design

## Code Stats

- **Total Lines**: ~400 lines
- **Files Created**: 8
- **External Dependencies**: 0 new (reuses lesson-001 and lesson-002)
- **Test Coverage**: Router (7 test cases), Integration (2 test cases)

## Validation Results

### Router Tests
```
✓ YouTube standard format
✓ YouTube short URL (youtu.be)
✓ YouTube mobile
✓ Generic webpages
✓ Invalid URLs
✓ Empty strings
```

### Integration Tests
```
✓ YouTube video → Tags generated correctly
✓ Webpage → Tags generated correctly
✓ Routing works transparently
✓ Error handling functional
```

## Performance

- **Router classification**: <1ms (pattern matching)
- **YouTube analysis**: ~10-15s (API + LLM)
- **Webpage analysis**: ~15-20s (fetch + parse + LLM)
- **No performance overhead from coordinator**

## Comparison to Single-Agent Approach

| Aspect | Single Agent | Multi-Agent Coordinator |
|--------|--------------|------------------------|
| Code reuse | Low | High (80%+ reused) |
| Maintainability | Medium | High (separation of concerns) |
| Extensibility | Hard | Easy (add new agent types) |
| Testing | Complex | Simple (test agents independently) |
| Routing logic | LLM-based | Pattern-based (faster) |

## Future Enhancements

### Short-term (Next Lessons)
- [ ] Add observability with Langfuse (track agent selection)
- [ ] Add guardrails for URL validation
- [ ] Implement retry logic for failed agents

### Long-term (Future Exploration)
- [ ] Support for more URL types (PDF, video platforms)
- [ ] Parallel agent execution for batch processing
- [ ] Agent result caching to avoid redundant processing
- [ ] LLM-based routing for ambiguous cases

## Lessons for Next Time

1. **Start with path management**: Set up venv and paths first
2. **Test router separately**: Validate routing before integration
3. **Document CLI usage early**: Helps with testing and debugging
4. **Use simple test scripts**: Better than fighting with CLI tools

## Resources Used

- Cole Medin's video (multi-agent patterns)
- Pydantic AI docs (agent composition)
- Lesson 001 & 002 implementations
- Python pathlib and sys.path documentation

## Time Breakdown

- Planning & design: ~10 minutes
- Router implementation: ~15 minutes
- Coordinator agent: ~20 minutes
- CLI interface: ~15 minutes
- Dependency setup & troubleshooting: ~25 minutes
- Testing & validation: ~10 minutes
- Documentation: ~5 minutes

**Total**: ~75 minutes

## Success Criteria - All Met! ✅

- ✅ Correctly classifies YouTube vs webpage URLs (100% accuracy)
- ✅ Routes to appropriate agent without user intervention
- ✅ Returns consistent output format regardless of agent
- ✅ Handles errors from either agent gracefully
- ✅ Single CLI command for all URL types
- ✅ Code is clean and maintainable (<150 lines per file)

## Final Thoughts

This lesson demonstrated the power of composition in multi-agent systems. Rather than building a monolithic agent that handles all cases, we created specialized agents and a simple coordinator. This approach:

- **Reduces complexity**: Each agent focuses on one task
- **Improves maintainability**: Changes to YouTube logic don't affect webpage processing
- **Enables reusability**: Existing agents work without modification
- **Simplifies testing**: Test each component independently

The router pattern proved ideal for this use case - deterministic, fast, and reliable. For more complex scenarios where categorization isn't pattern-based, an LLM-based router would be appropriate, but would add latency and cost.

**Next**: Lesson 004 will add observability to track how requests flow through the multi-agent system.
