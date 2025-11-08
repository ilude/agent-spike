# Lesson 009: Orchestrator Agent - COMPLETE

## Overview

This lesson implemented an orchestrator agent that coordinates multiple sub-agents to handle different URL types in parallel.

## Key Findings

### The Nested Agent Problem

**Discovery**: Calling agents with tools from within another agent's tool causes deadlocks.

**Root Cause**:
- Pydantic AI agents that have tools (like our YouTube and webpage agents) create event loops for handling tool calls
- When called from within another agent's tool, this creates nested event loop conflicts
- The inner agent waits for its tools to complete, but they can't run in the already-running event loop

**Solution**: Created a simplified approach where tools make direct LLM calls instead of using nested agents with their own tools.

### Implementation Details

1. **Original Approach** (`tools.py`):
   - Imported full sub-agents with their tools
   - Called `agent.run()` from within orchestrator's tool
   - Result: Deadlock when sub-agents tried to use their tools

2. **Simplified Approach** (`tools_simple.py`):
   - Import only the raw tool functions (get_transcript, fetch_webpage)
   - Create temporary agents without tools for LLM calls
   - Make direct API calls instead of nested agent invocations
   - Result: Works correctly with parallel execution

### Performance Results

From test run:
- Successfully processed 2 URLs in parallel (YouTube + webpage)
- Total tokens: ~7,010 for both URLs combined
- Execution time: ~26 seconds (mostly API calls)
- Both sub-agents returned appropriate tags

### Architectural Lessons

1. **Tool Nesting Limitations**:
   - Agents with tools should not be called from within other agents' tools
   - Use direct function calls or simple LLM calls instead

2. **Parallel Execution**:
   - Orchestrator correctly makes parallel tool calls when prompted
   - OpenAI models (gpt-5-mini) handle multiple tool calls well

3. **Output Parsing**:
   - Structured output with `output_type` caused validation issues
   - Better to use unstructured text and parse manually for flexibility

## Comparison with Lesson-003

| Aspect | Lesson-003 Router | Lesson-009 Orchestrator |
|--------|------------------|----------------------|
| URL Handling | Single URL per call | Multiple URLs per call |
| Agent Invocation | Direct agent.run() | Tool-based delegation |
| Parallelization | N/A (single URL) | Yes (multiple tools) |
| Complexity | Simple routing | More complex coordination |
| Token Efficiency | Higher (full agent per URL) | Lower (shared orchestrator context) |

## Code Artifacts

### Working Files:
- `orchestrator_agent/agent_simple.py` - Simplified orchestrator
- `orchestrator_agent/tools_simple.py` - Direct LLM call tools
- `test_orchestrator_simple.py` - Working test

### Debug Files:
- `test_components.py` - Component isolation tests
- `test_orchestrator_async.py` - Async pattern experiments
- `debug_hang.py` - Minimal reproduction of hang issue

## Next Steps

Based on findings:

1. **For Production**: Use the simplified pattern (direct LLM calls) when building orchestrators
2. **For Learning**: This lesson demonstrates important limitations of nested agent architectures
3. **For VISION.md Goals**: The orchestrator pattern is valuable but needs careful implementation

## Recommendations

1. **Avoid Nested Agent-with-Tools Calls**: If sub-agents need tools, refactor to:
   - Direct function calls
   - Simple LLM-only agents
   - Separate orchestration from tool execution

2. **Consider Alternatives**:
   - Message queues for agent coordination
   - State machines for complex workflows
   - Direct API composition instead of nested agents

3. **Testing Strategy**:
   - Always test components in isolation first
   - Create minimal reproductions for debugging
   - Use debug logging liberally in async code

## Status: COMPLETE ✓

The orchestrator is functional using the simplified approach. Key learning: nested agent architectures have fundamental limitations that require careful design around event loops and tool execution contexts.