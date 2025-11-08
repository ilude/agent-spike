# Nested Agent Deadlock Issue

**Date**: 2025-11-08
**Discovered In**: Lesson-009
**Status**: ⚠️ CRITICAL - Blocks orchestrator design in `.claude/ideas/orchestrator/`

## TL;DR

**DO NOT call agents-with-tools from within another agent's tool.** This causes event loop deadlocks in Pydantic AI (and likely other async agent frameworks).

## The Problem

### What Causes the Deadlock

When you call an agent that has its own tools from within another agent's tool function, you create nested event loops that deadlock:

```python
# ❌ THIS WILL DEADLOCK
@coordinator.tool
def call_youtube_agent(url: str) -> str:
    # youtube_agent has @agent.tool decorators
    result = youtube_agent.run_sync(f"Tag this: {url}")
    return result.output  # ← Never returns, hangs forever
```

### Why It Happens

1. **Outer agent** (coordinator) calls a tool (`call_youtube_agent`)
2. **Outer event loop** waits for the tool to complete
3. **Inside the tool**, you invoke an inner agent (`youtube_agent.run_sync()`)
4. **Inner agent** decides it needs to call its own tool (`get_transcript`)
5. **Inner agent** tries to execute the tool, which needs an event loop
6. **Deadlock**:
   - Outer event loop is blocked waiting for the tool to return
   - Inner agent is blocked waiting for its tool to execute
   - Inner tool can't execute because the event loop is already occupied
   - Nobody can proceed

### Call Stack When Deadlock Occurs

```
User Request
  └─> Coordinator Agent
      └─> @coordinator.tool call_youtube_agent()
          [Event loop WAITING for tool to complete]
          └─> youtube_agent.run_sync()
              └─> YouTube agent decides to call @agent.tool get_transcript()
                  [Tries to use event loop but it's BLOCKED]
                  └─> DEADLOCK ⚠️
```

## Evidence from Lesson-009

### Failed Approach

**File**: `lessons/lesson-009/orchestrator_agent/tools.py`

```python
# Import full agents with their tools
from youtube_agent.agent import create_agent as create_youtube_agent
from webpage_agent.agent import create_agent as create_webpage_agent

youtube_agent = create_youtube_agent(instrument=False)  # Has tools
webpage_agent = create_webpage_agent(instrument=False)  # Has tools


async def call_subagent(ctx: RunContext, agent_name: str, url: str) -> Dict[str, Any]:
    """Call a specialized sub-agent with a URL."""

    if agent_name == "youtube_tagger":
        # ❌ THIS DEADLOCKS
        result = await youtube_agent.run(
            user_prompt=f"Tag this video: {url}",
            usage=ctx.usage,
        )
        return {"tags": result.output}
```

**Result**: Hung indefinitely when YouTube agent tried to call `get_transcript()`.

### Test Output

```
>>> CALLING SUBAGENT: youtube_tagger with URL: https://www.youtube.com/watch?v=i5kwX7jeWL8
>>> About to call youtube_agent.run...
[HANGS FOREVER - No further output]
```

## Solutions

### Solution 1: Direct Function Calls (Simplest)

Import and call the underlying functions directly, then create a tool-less agent just for LLM reasoning:

**File**: `lessons/lesson-009/orchestrator_agent/tools_simple.py`

```python
# ✅ Import functions, NOT agents
from youtube_agent.tools import get_video_info, get_transcript
from youtube_agent.prompts import TAGGING_SYSTEM_PROMPT


async def call_subagent_simple(ctx: RunContext, agent_name: str, url: str):
    if agent_name == "youtube_tagger":
        # Call functions directly
        video_info = get_video_info(url)
        transcript = get_transcript(url)[:5000]

        # Create tool-less agent just for LLM call
        simple_agent = Agent(
            model=model,
            system_prompt=TAGGING_SYSTEM_PROMPT,
            # NO TOOLS - just reasoning
        )

        result = await simple_agent.run(
            f"Analyze this video and generate tags:\n{video_info}\n{transcript}",
            usage=ctx.usage,
        )

        return {"tags": parse_tags(result.output)}
```

**Pros**:
- ✅ Works immediately (proven in lesson-009)
- ✅ No deadlock risk
- ✅ Straightforward implementation

**Cons**:
- ❌ Hardcoded per sub-agent type
- ❌ Loses modularity
- ❌ Manual coordination of tool calls

**Test Result**: ✅ Successfully processed 2 URLs in parallel, ~7k tokens

### Solution 2: Tool-less Sub-Agents (Best Architecture)

Move ALL tools to the coordinator level. Sub-agents become pure reasoning modules with no tools:

**File**: `lessons/lesson-009/orchestrator_agent/agent_toolless.py`

```python
# ✅ Coordinator has ALL the tools
@coordinator.tool
async def fetch_youtube_data(url: str) -> Dict[str, Any]:
    """Fetch YouTube data - coordinator controls all data fetching"""
    video_info = get_video_info(url)
    transcript = get_transcript(url)
    return {"url": url, "title": video_info["title"], "transcript": transcript}


@coordinator.tool
async def reason_youtube(data: Dict[str, Any]) -> Dict[str, Any]:
    """Use YouTube reasoner - tool-less agent, just LLM reasoning"""

    # ✅ Call tool-less sub-agent (NO deadlock risk)
    result = await youtube_reasoner.run(
        f"Analyze this video and generate tags:\n{data}",
        usage=ctx.usage,
    )

    return {"tags": parse_tags(result.output)}


# ✅ Sub-agents have NO tools - pure reasoning
youtube_reasoner = Agent(
    model="openai:gpt-5-nano",
    system_prompt=YOUTUBE_TAGGING_PROMPT,
    # NO @agent.tool decorators
)
```

**Workflow**:
1. Coordinator fetches data with its own tools
2. Coordinator stores data (in memory, IPython, database, etc.)
3. Coordinator calls tool-less sub-agent for specialized reasoning
4. Sub-agent returns result (no tools to call, no deadlock)

**Pros**:
- ✅ No deadlock risk
- ✅ Clean separation: coordinator controls data, sub-agents provide reasoning
- ✅ Scalable architecture
- ✅ Can still have multiple specialized "agents"
- ✅ Testable: can test reasoning independently

**Cons**:
- ❌ Requires redesigning existing agents
- ❌ Coordinator has more responsibility

**Test Result**: ✅ Successfully processed 2 URLs in parallel, ~20k tokens

### Solution 3: Message Queue / Task System (Overkill)

Run sub-agents in separate processes with their own event loops, communicate via message queues.

**Don't use this** for learning projects. It's massive architectural overhead for marginal benefit.

## Impact on `.claude/ideas/orchestrator/`

### Current Orchestrator Design Will Fail

**File**: `.claude/ideas/orchestrator/ARCHITECTURE.md` (lines 202-233)

```python
SUBAGENT_REGISTRY = {
    'youtube_tagger': youtube_tagger_agent,  # ← Has tools
    'webpage_tagger': webpage_tagger_agent,  # ← Has tools
}


@coordinator.tool
def call_subagent(agent_name: str, variable_name: str) -> str:
    # Get sub-agent
    subagent = SUBAGENT_REGISTRY.get(agent_name)

    # ❌ THIS WILL DEADLOCK
    result = subagent.run_sync(
        user_prompt=f"Process this {variable_name}",
        message_history=[],
        deps=deps,
    )

    return result.data
```

**This is the exact pattern that failed in lesson-009.**

The note about "fresh context" doesn't help—the issue isn't memory or history, it's nested event loops.

### Required Changes to Orchestrator Design

**Option A: Use Solution 1 Pattern**

```python
@coordinator.tool
def call_subagent(agent_name: str, variable_name: str) -> str:
    data = kernel.user_ns.get(variable_name)

    if agent_name == 'youtube_tagger':
        # Import functions, not agent
        from youtube_agent.tools import get_transcript
        transcript = get_transcript(data)

        # Tool-less agent for reasoning
        temp_agent = Agent(model, system_prompt=YOUTUBE_PROMPT)
        result = temp_agent.run_sync(transcript)
        return result.output
```

**Option B: Use Solution 2 Pattern** (Recommended)

```python
# Coordinator has ALL tools
@coordinator.tool
def fetch_youtube_transcript(url: str) -> str:
    return get_transcript_impl(url)


@coordinator.tool
def reason_youtube_tags(transcript: str) -> list[str]:
    # youtube_reasoner has NO tools
    result = youtube_reasoner.run_sync(transcript)
    return parse_tags(result.output)


# Tool-less sub-agents
youtube_reasoner = Agent(
    model='openai:gpt-5-nano',
    system_prompt=YOUTUBE_PROMPT,
    # NO TOOLS
)
```

**Workflow**:
1. Coordinator executes `execute_python("transcript = fetch_youtube_transcript(url)")`
2. Transcript stored in IPython
3. Coordinator executes `execute_python("tags = reason_youtube_tags(transcript)")`
4. Tags stored in IPython
5. No nested agent-with-tools calls

## Architectural Principles

### Rule 1: No Nested Agent-with-Tools Calls

**Never** call an agent that has `@agent.tool` decorators from within another agent's tool.

```python
# ❌ BAD
@outer_agent.tool
def my_tool():
    result = inner_agent_with_tools.run_sync(...)  # DEADLOCK
    return result.data

# ✅ GOOD
@outer_agent.tool
def my_tool():
    result = inner_agent_no_tools.run_sync(...)  # Safe
    return result.data
```

### Rule 2: Separation of Data and Reasoning

**Good architecture**: Separate data fetching from reasoning.

- **Coordinator**: Controls all data fetching (has data tools)
- **Sub-agents**: Pure reasoning modules (no data tools)

```python
# ✅ Clean separation
@coordinator.tool
def fetch_data(source: str) -> dict:
    """Coordinator fetches data"""
    return fetch_impl(source)


@coordinator.tool
def analyze_data(data: dict) -> str:
    """Coordinator delegates reasoning to tool-less agent"""
    return analyzer_agent.run_sync(data)  # analyzer_agent has NO tools


# Tool-less reasoning agent
analyzer_agent = Agent(
    model='openai:gpt-5-nano',
    system_prompt="Analyze this data...",
    # NO TOOLS
)
```

### Rule 3: Use Direct Functions When Needed

If you need to call existing agents' functionality, import their underlying functions:

```python
# ✅ Import functions, not agents
from youtube_agent.tools import get_transcript, get_video_info
from webpage_agent.tools import fetch_webpage

# Call directly
transcript = get_transcript(url)
webpage = fetch_webpage(url)
```

## Token Efficiency Comparison

From lesson-009 tests:

| Approach | URLs | Tokens | Notes |
|----------|------|--------|-------|
| **Solution 1: Direct Calls** | 2 | ~7,010 | Lower tokens, simpler output |
| **Solution 2: Tool-less** | 2 | ~20,575 | Higher tokens, richer output |

**Note**: Token difference due to output verbosity, not architecture. Both approaches work without deadlocks.

## Recommendations

### For New Projects

**Use Solution 2 (Tool-less Sub-Agents)**:
- Clean architecture
- Scalable to many sub-agents
- No deadlock risk
- Clear separation of concerns

### For Quick Prototypes

**Use Solution 1 (Direct Calls)**:
- Fast to implement
- Works with existing agents
- Proven pattern

### For Production

**Use Solution 2** with additional hardening:
- Error handling
- Retry logic
- Observability
- Rate limiting

## Related Files

### Lesson-009 Implementations

- ✅ **Working**: `lessons/lesson-009/orchestrator_agent/tools_simple.py` (Solution 1)
- ✅ **Working**: `lessons/lesson-009/orchestrator_agent/agent_toolless.py` (Solution 2)
- ❌ **Broken**: `lessons/lesson-009/orchestrator_agent/tools.py` (Original nested approach)

### Tests

- ✅ **Passing**: `lessons/lesson-009/test_orchestrator_simple.py` (Solution 1)
- ✅ **Passing**: `lessons/lesson-009/test_orchestrator_toolless.py` (Solution 2)
- ❌ **Hangs**: `lessons/lesson-009/test_orchestrator_async.py` (Original approach)

### Documentation

- `lessons/lesson-009/COMPLETE.md` - Detailed findings from debugging
- `.claude/ideas/orchestrator/ARCHITECTURE.md` - Original design (needs updates)
- `.claude/ideas/orchestrator/DECISIONS.md` - Design decisions (needs updates)

## Action Items

### Before Implementing Orchestrator

- [ ] Update `.claude/ideas/orchestrator/ARCHITECTURE.md` with Solution 2 pattern
- [ ] Revise `call_subagent()` implementation (lines 202-233)
- [ ] Update all examples in `EXAMPLES.md` to use tool-less sub-agents
- [ ] Add architectural principle: "No nested agent-with-tools calls"
- [ ] Add to `DECISIONS.md`: Decision about tool-less sub-agents

### When Building

- [ ] Start with Solution 2 architecture
- [ ] Make all sub-agents tool-less (pure reasoning)
- [ ] Put all data-fetching tools at coordinator level
- [ ] Test with component tests before integration
- [ ] Add debug logging for tool calls

## References

- [Lesson-009 COMPLETE.md](../../lessons/lesson-009/COMPLETE.md)
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare: Code Mode](https://blog.cloudflare.com/code-mode/)

## Appendix: Why Async Doesn't Help

Some might think using `async`/`await` differently would solve this. It doesn't.

**The problem is structural**, not about how you call the functions:

```python
# ❌ Still deadlocks
@coordinator.tool
async def my_tool():
    result = await inner_agent_with_tools.run(...)  # DEADLOCK
    return result.output

# ❌ Still deadlocks
@coordinator.tool
def my_tool():
    result = inner_agent_with_tools.run_sync(...)  # DEADLOCK
    return result.output
```

**The only solution**: Don't call agents-with-tools from within another agent's tool.

---

**Last Updated**: 2025-11-08
**Validated**: Lesson-009 tests (both solutions working)
**Status**: ✅ Solutions proven and documented
