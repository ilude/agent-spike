# Lesson 004: Observability with Pydantic Logfire

Add comprehensive observability to all existing agents using Pydantic Logfire.

**Note**: Originally planned for Langfuse, but switched to Pydantic Logfire due to Python 3.14 compatibility issues with Langfuse's Pydantic V1 dependency.

## What This Lesson Teaches

- Setting up Pydantic Logfire for agent tracing
- Instrumenting Pydantic AI agents with built-in observability
- Tracking tool calls, costs, and latency
- Monitoring multi-agent routing decisions
- Viewing traces in console or Logfire dashboard

## Prerequisites

- Lessons 001-003 completed
- (Optional) Logfire account for cloud dashboard: https://logfire.pydantic.dev
- API keys for Claude or OpenAI

## Quick Start

### 1. Install Dependencies

```bash
uv sync --group lesson-004
```

### 2. Configure Environment

```bash
cd lessons/lesson-004
cp .env.template .env
# Edit .env with your API keys
# LOGFIRE_TOKEN is optional - will work in console-only mode without it
```

### 3. Run Instrumented Agents

```bash
# Run full test suite
uv run python test_observability.py

# Traces will appear in console output!
```

## What Gets Tracked

### YouTube Agent (Lesson 001)
- LLM calls (model, tokens, cost)
- Tool calls: `get_video_info`, `get_transcript`
- Response time
- Tags: `youtube-agent`, `video-tagging`

### Webpage Agent (Lesson 002)
- LLM calls
- Tool calls: `fetch_webpage`
- Content parsing time
- Tags: `webpage-agent`, `content-tagging`

### Coordinator (Lesson 003)
- Routing decisions (YouTube vs Webpage)
- Parent/child trace relationships
- End-to-end latency
- Agent selection reasoning
- Tags: `coordinator`, `multi-agent`

## Directory Structure

```
lesson-004/
├── observability/
│   ├── __init__.py
│   ├── config.py              # Logfire configuration
│   └── logfire_wrapper.py     # Initialization & helpers
├── .env                       # Your credentials (gitignored)
├── .env.template              # Template for setup
├── test_observability.py      # Test all agents with tracing
├── PLAN.md                    # Detailed lesson plan
├── README.md                  # This file
└── COMPLETE.md                # Completion summary
```

## How It Works

### Pydantic AI + Logfire Integration

```python
from pydantic_ai import Agent
from observability import initialize_logfire

# Initialize Logfire (call once at startup)
initialize_logfire()

# Create agent with instrumentation enabled
agent = Agent(
    model="claude-3-5-haiku-20241022",
    system_prompt="...",
    instrument=True  # Enable tracing!
)

# All agent calls now automatically traced
result = await agent.run("Analyze this...")
```

### Console Output Example

```
[Observability] Logfire running in local/console mode
[Observability] Pydantic AI instrumentation enabled

Test 1: YouTube Agent
URL: https://www.youtube.com/watch?v=...
Analyzing...

14:16:29.392 running tool: get_video_info
             │ tool_arguments={
             │     'url': 'https://www.youtube.com/watch?v=...',
             │ }
             │ tool_response=None
             │ gen_ai.tool.name='get_video_info'

14:16:31.147 running tool: get_transcript
             │ tool_arguments={
             │     'url': 'https://www.youtube.com/watch?v=...',
             │ }
             │ tool_response=None
             │ gen_ai.tool.name='get_transcript'

14:16:32.157 chat claude-3-5-haiku-20241022
             │ model_request_parameters={...}

SUCCESS: YouTube Agent Result:
{tags: [...], summary: "..."}
```

**Note**: Verbose mode shows:
- Tool names and arguments
- Tool call IDs
- Model parameters
- Timestamps for each operation

## Cloud Dashboard (Optional)

To send traces to Logfire cloud dashboard:

1. Sign up at https://logfire.pydantic.dev (free tier)
2. Get your token
3. Add to `.env`:
   ```
   LOGFIRE_TOKEN=your_token_here
   ```
4. Re-run tests - traces will appear in dashboard!

## Testing

```bash
# Test all agents with observability
cd lessons/lesson-004
uv run python test_observability.py

# Output will show:
# - 4 tests (YouTube, Webpage, Coordinator x2)
# - Detailed traces for each operation
# - Success/failure status
```

## Troubleshooting

### "Logfire not configured"
- This is normal! Logfire works in console-only mode by default
- To enable cloud dashboard, add LOGFIRE_TOKEN to `.env`

### Agent creation fails
- Verify dependencies: `uv sync --group lesson-004`
- Check Python version: `python --version` (should be 3.14+)
- Verify logfire installed: `uv pip list | grep logfire`

### Traces not showing
- Logfire uses console output - check terminal
- For cloud dashboard, verify LOGFIRE_TOKEN is set
- Make sure `instrument=True` when creating agents

## Why Logfire Instead of Langfuse?

**Original Plan**: Langfuse (open-source LLM observability)
**Reality**: Langfuse depends on Pydantic V1, which is not compatible with Python 3.14

**Solution**: Pydantic Logfire
- Made by the Pydantic team (same as Pydantic AI)
- Native Python 3.14 support
- Built-in Pydantic AI integration
- Console-first approach (works without cloud signup)
- Free tier with cloud dashboard available

## Cost

**Logfire:**
- Console mode: FREE
- Cloud tier: FREE for 50k traces/month

**LLM Calls:** Same as before (~$0.003-0.005 per analysis)

## Next Steps

After understanding observability:
- **Lesson 005**: Security & Guardrails
- **Lesson 006**: Long-term Memory with Mem0
- **Lesson 007**: Streaming Responses
- **Lesson 013**: Cost Optimization (using Logfire data!)

## Resources

- [Pydantic Logfire Docs](https://logfire.pydantic.dev/docs/)
- [Pydantic AI Docs](https://ai.pydantic.dev/)
- [Pydantic AI + Logfire Integration](https://ai.pydantic.dev/logfire/)
