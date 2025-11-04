# Lesson 004: Observability with Pydantic Logfire

**Note**: Originally planned for Langfuse, but Langfuse has Python 3.14 compatibility issues (Pydantic V1 dependency). Using Pydantic Logfire instead - official observability platform from the Pydantic team with native Pydantic AI support.

## Learning Objectives

- Understand the importance of observability in multi-agent systems
- Integrate Langfuse for tracking agent behavior
- Monitor tool calls, costs, and latency across all agents
- Track routing decisions in multi-agent coordinator
- View traces in Langfuse dashboard
- Debug agent behavior with detailed trace data

## Project Overview

Add comprehensive observability to all existing agents (YouTube, Webpage, Coordinator) using Langfuse:
1. Track all LLM calls with detailed metadata
2. Monitor tool invocations and their outputs
3. Trace multi-agent routing decisions
4. Calculate costs per request
5. Measure latency at each step
6. View everything in Langfuse dashboard

## Why Observability Matters

**Production challenges without observability:**
- "Why did the agent choose that tool?"
- "How much is this costing per request?"
- "Which agent is slow?"
- "Did the router make the right decision?"
- "What prompt is actually being sent?"

**What we'll track:**
- LLM model, temperature, tokens used
- Tool calls and arguments
- Agent routing decisions
- Response times
- Costs per operation
- Errors and exceptions

## Technologies

- **Python 3.14** with shared .venv
- **uv** - Package manager
- **Langfuse** - Observability platform (cloud or self-hosted)
- **Pydantic AI** - Already supports Langfuse integration
- **Existing agents** - YouTube, Webpage, Coordinator (from lessons 001-003)

## Architecture

### Before (Lesson 003)
```
User → Coordinator → [YouTube Agent | Webpage Agent] → Response
         (black box - no visibility)
```

### After (Lesson 004)
```
User → Coordinator → [YouTube Agent | Webpage Agent] → Response
         ↓              ↓                ↓
    Langfuse       Langfuse          Langfuse
    (routing)      (tools, LLM)      (tools, LLM)
         ↓              ↓                ↓
            Langfuse Dashboard
    (traces, costs, latency, debugging)
```

## Directory Structure

```
lesson-004/
├── observability/
│   ├── __init__.py
│   ├── langfuse_wrapper.py    # Langfuse initialization
│   ├── decorators.py           # Tracing decorators
│   └── config.py               # Langfuse configuration
├── .env                        # Add LANGFUSE_* keys
├── PLAN.md                     # This file
├── README.md                   # Quick reference
├── test_observability.py       # Test script
└── COMPLETE.md                 # Post-completion summary
```

**Note**: We'll modify existing agents in-place rather than duplicating them.

## Implementation Steps

### 1. Setup Langfuse (~10 min)

**Option A: Langfuse Cloud (Recommended)**
- Sign up at https://cloud.langfuse.com
- Create new project
- Get public/secret keys

**Option B: Self-hosted**
- Run Langfuse locally with Docker
- More control but requires setup

**Environment variables:**
```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # or localhost
```

**Install dependency:**
```bash
uv add langfuse --group lesson-004
```

### 2. Create Langfuse Wrapper (~15 min)

**Goals:**
- Initialize Langfuse client with config
- Create trace context manager
- Handle errors gracefully
- Optional: flush traces on exit

**Key functions:**
- `get_langfuse_client()` - Singleton client
- `trace_agent_call()` - Decorator for agent functions
- `trace_tool_call()` - Decorator for tool functions
- `trace_routing_decision()` - Log router decisions

### 3. Instrument Existing Agents (~20 min)

**Lesson 001 (YouTube Agent):**
- Add Langfuse callback to agent initialization
- Tag traces with "youtube-agent"
- Log tool calls (get_transcript, get_video_info)

**Lesson 002 (Webpage Agent):**
- Add Langfuse callback to agent initialization
- Tag traces with "webpage-agent"
- Log tool calls (fetch_webpage)

**Lesson 003 (Coordinator):**
- Log routing decisions (YouTube vs Webpage)
- Create parent trace for entire flow
- Child traces for delegated agent calls
- Tag with URL pattern matched

### 4. Test & Validate (~10 min)

**Test scenarios:**
1. Single YouTube video analysis
2. Single webpage analysis
3. Coordinator routing both types
4. Error cases (invalid URL, API failure)

**Validation:**
- All traces appear in Langfuse dashboard
- Parent/child relationships correct
- Tool calls visible
- Costs calculated
- Latency measurements present

### 5. Dashboard Exploration (~5 min)

**Explore Langfuse UI:**
- Traces view (detailed execution flow)
- Sessions (group related requests)
- Costs over time
- Latency distribution
- Model usage statistics
- Error rates

## Expected Output

### CLI (unchanged)
```bash
cd lessons/lesson-003
uv run python test_coordinator.py

# Same output as before, but...
# Behind the scenes: traces sent to Langfuse
```

### Langfuse Dashboard
```
Trace: YouTube Video Analysis
├─ Span: Router Decision [0.2ms]
│  └─ Decision: youtube, Pattern: youtube.com
├─ Span: YouTube Agent [12.4s]
│  ├─ Tool: get_video_info [1.2s]
│  ├─ Tool: get_transcript [8.3s]
│  └─ LLM Call: claude-3-5-haiku [2.9s]
│     ├─ Input: 1,245 tokens ($0.0015)
│     ├─ Output: 156 tokens ($0.0019)
│     └─ Total Cost: $0.0034
└─ Total: 12.6s, $0.0034
```

## Pydantic AI Integration

**Good news**: Pydantic AI has built-in Langfuse support!

```python
from pydantic_ai import Agent
from langfuse import Langfuse

langfuse = Langfuse()

agent = Agent(
    model="claude-3-5-haiku-20241022",
    system_prompt="...",
    # Automatic Langfuse tracing!
)

# Or manual:
result = await agent.run(
    "Analyze this video",
    message_history=[],
    # Langfuse will auto-capture this
)
```

## Success Criteria

- ✅ Langfuse successfully tracks all agent calls
- ✅ Routing decisions visible in traces
- ✅ Tool calls logged with arguments and outputs
- ✅ Cost tracking works for all LLM calls
- ✅ Parent/child trace relationships correct
- ✅ Dashboard shows end-to-end flow
- ✅ No performance degradation (<50ms overhead)
- ✅ Errors logged and visible in dashboard

## Cost Considerations

**Langfuse Pricing:**
- Cloud free tier: 50k traces/month
- Our usage: ~1 trace per analysis = plenty for learning
- Self-hosted: Free, unlimited

**LLM Costs (unchanged):**
- YouTube/Webpage: ~$0.003-0.005 per analysis
- Now we can SEE these costs in real-time!

## Advanced Features (Optional)

### Tagging & Metadata
- User ID tracking
- Session grouping
- Custom tags (url_type, content_category)
- Environment tags (dev, staging, prod)

### Prompt Management
- Version prompts in Langfuse
- A/B test different prompts
- Compare performance metrics

### Evaluation
- Score trace quality (manual or automated)
- Track accuracy over time
- Identify failure patterns

## Next Steps (Future Lessons)

After understanding observability:
- **Lesson 005**: Security & Guardrails (see where prompts need protection)
- **Lesson 006**: Long-term Memory (track what agent remembers)
- **Lesson 013**: Cost Optimization (use Langfuse data to optimize)

## Questions Before Starting

1. Langfuse Cloud or self-hosted? (Cloud recommended for speed)
2. Want to explore advanced features (tagging, sessions)?
3. Any specific metrics you want to track?

## Resources

- [Langfuse Docs](https://langfuse.com/docs)
- [Pydantic AI + Langfuse Integration](https://ai.pydantic.dev/logfire/)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)

## Notes

- Observability adds ~20-50ms overhead (negligible for our use case)
- Traces are async - don't block agent execution
- Can disable in production if needed via environment variable
- Langfuse stores traces for 30 days (free tier)
