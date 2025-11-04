# How to Run Lesson 003: Multi-Agent Coordinator

## Prerequisites

Make sure all dependencies are installed:

```bash
cd C:\Projects\Personal\agent-spike
uv sync --all-groups
```

## Option 1: Quick Demo (Recommended for First-Time Use)

Analyze any URL with a simple command:

```bash
cd .spec/lessons/lesson-003
uv run python demo.py "YOUR_URL_HERE"
```

### Examples:

**Analyze a YouTube video:**
```bash
uv run python demo.py "https://www.youtube.com/watch?v=i5kwX7jeWL8"
```

**Analyze a webpage:**
```bash
uv run python demo.py "https://github.com/anthropics/anthropic-sdk-python"
```

**Output:**
```
================================================================================
MULTI-AGENT COORDINATOR DEMO
================================================================================

Analyzing: https://github.com/anthropics/anthropic-sdk-python

Processing...

[OK] URL Type: webpage
[OK] Handler: Webpage Agent

--------------------------------------------------------------------------------
RESULT
--------------------------------------------------------------------------------
{
  "page_title": "Anthropic Python SDK",
  "tags": ["python-sdk", "ai-tools", "machine-learning", "api-library", "claude-ai"],
  "summary": "Official Python SDK for interacting with Anthropic's AI API..."
}
================================================================================
```

## Option 2: Run Unit Tests (Router Only)

Test the URL classification logic without making API calls:

```bash
cd .spec/lessons/lesson-003
uv run python test_router.py
```

**Output:**
```
Testing URL Router
================================================================================
PASS https://www.youtube.com/watch?v=i5kwX7jeWL8        | Expected: youtube    | Got: youtube
PASS https://youtu.be/i5kwX7jeWL8                       | Expected: youtube    | Got: youtube
PASS https://m.youtube.com/watch?v=test                 | Expected: youtube    | Got: youtube
PASS https://github.com/docling-project/docling         | Expected: webpage    | Got: webpage
PASS https://example.com                                | Expected: webpage    | Got: webpage
PASS not-a-url                                          | Expected: invalid    | Got: invalid
PASS (empty)                                            | Expected: invalid    | Got: invalid
================================================================================
All tests PASSED!
```

## Option 3: Run Integration Tests

Test the full coordinator with both YouTube and webpage agents:

```bash
cd .spec/lessons/lesson-003
uv run python test_coordinator.py
```

This will:
1. Test with a YouTube video URL
2. Test with a webpage URL
3. Show full output from both agents
4. Report pass/fail for each test

**Expected runtime:** ~30-40 seconds (makes real API calls)

## Option 4: Use as a Python Module

You can also import and use the coordinator in your own scripts:

```python
import asyncio
from coordinator_agent.agent import analyze_url

async def main():
    # Analyze any URL
    result = await analyze_url("https://www.youtube.com/watch?v=...")

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Type: {result.url_type.value}")
        print(f"Handler: {result.handler}")
        print(f"Result: {result.result}")

asyncio.run(main())
```

## Understanding the Output

The coordinator automatically:

1. **Classifies the URL** - Determines if it's YouTube, webpage, or invalid
2. **Routes to the correct agent** - Sends to YouTube Agent or Webpage Agent
3. **Returns unified results** - Consistent format regardless of source

### URL Classification Examples:

| URL | Classification | Handler |
|-----|---------------|---------|
| `https://youtube.com/watch?v=xyz` | youtube | YouTube Agent |
| `https://youtu.be/xyz` | youtube | YouTube Agent |
| `https://m.youtube.com/watch?v=xyz` | youtube | YouTube Agent |
| `https://github.com/...` | webpage | Webpage Agent |
| `https://example.com` | webpage | Webpage Agent |
| `not-a-url` | invalid | None (error) |

## Troubleshooting

### Issue: ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'pydantic_ai'`

**Solution:**
```bash
cd C:\Projects\Personal\agent-spike
uv sync --all-groups
```

### Issue: API Key Not Found

**Error:** `ANTHROPIC_API_KEY not found`

**Solution:** Copy the `.env` file from lesson-001:
```bash
cd .spec/lessons/lesson-003
cp ../lesson-001/.env .
```

Then edit `.env` and add your API keys:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
DEFAULT_MODEL=claude-3-5-haiku-20241022
```

### Issue: Unicode/Character Encoding Errors

**Error:** `UnicodeEncodeError: 'charmap' codec can't encode...`

**Solution:** This is a Windows console limitation. The scripts have been updated to use ASCII characters only.

## Performance Notes

- **Router classification:** <1ms (pattern matching, no API calls)
- **YouTube analysis:** ~10-15 seconds (API + LLM processing)
- **Webpage analysis:** ~15-20 seconds (fetch + parse + LLM processing)
- **Coordinator overhead:** Negligible (<1ms)

## Cost Notes

Each analysis makes 2-3 API calls to Claude Haiku:
- YouTube: ~2-3 API calls (~$0.002 per video)
- Webpage: ~3-4 API calls (~$0.003 per page)

Using Claude Haiku keeps costs very low for testing and development.

## Next Steps

After running Lesson 003, you're ready for:
- **Lesson 004:** Add observability with Langfuse to track multi-agent flows
- **Lesson 005:** Add security guardrails
- **Lesson 006:** Add long-term memory with Mem0
