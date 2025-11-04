# YouTube Tagging Agent

AI agent that automatically generates tags for YouTube videos using transcript analysis.

## Features

- Fetches YouTube video transcripts
- Analyzes content using Claude or GPT models
- Generates 3-5 relevant, reusable tags
- CLI interface with rich output formatting
- Interactive mode for batch processing

## Installation

```bash
# From project root, install lesson-001 dependencies
uv sync --group lesson-001

# Dependencies are shared in root .venv to save disk space
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

## Usage

### Analyze Single Video

```bash
python -m youtube_agent.cli analyze "https://youtube.com/watch?v=VIDEO_ID"
```

### Use Different Model

```bash
python -m youtube_agent.cli analyze "URL" --model gpt-4o-mini
```

### JSON Output

```bash
python -m youtube_agent.cli analyze "URL" --json
```

### Interactive Mode

```bash
python -m youtube_agent.cli interactive
```

## Example Output

```
Analysis Complete!

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field         ┃ Value                                         ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Title         │ Learn 90% of Building AI Agents in 30 Min    │
│ Tags          │ ai-agents, python, tutorial, machine-learning │
│ Summary       │ Comprehensive guide to building AI agents... │
└───────────────┴───────────────────────────────────────────────┘
```

## Architecture

- `agent.py` - Pydantic AI agent configuration
- `tools.py` - YouTube API wrappers
- `prompts.py` - System prompt templates
- `cli.py` - Typer CLI interface

## How It Works

1. User provides YouTube URL
2. Agent calls `get_video_info()` tool to get metadata
3. Agent calls `get_transcript()` tool to fetch transcript
4. LLM analyzes content and generates 3-5 tags
5. Results displayed in terminal or JSON format

## Limitations

- Requires videos to have transcripts enabled
- Only supports English transcripts currently
- No video metadata (title/description) without YouTube Data API
- Rate limited by YouTube transcript API

## Next Steps

- Add support for multiple languages
- Integrate YouTube Data API for full metadata
- Add tag validation/standardization
- Implement caching for repeated videos
- Add observability with Langfuse (Lesson 002)
