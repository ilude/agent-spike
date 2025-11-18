# Development & Interactive Tools

This directory contains development and interactive tools for analysis and experimentation with the agent-spike project.

## Purpose

These tools are designed for:
- **Interactive exploration** of cached data and vector stores
- **Development workflows** like batch processing and testing
- **Analysis and comparison** of different models and approaches
- **Experimentation** with tagging, embeddings, and retrieval strategies

## Tools

### analyze_youtube.py
Analyze YouTube videos from the cache, retrieve metadata, and explore stored content.

### check_titles.py
Verify and check video titles in the cache.

### compare_models.py
Compare different LLM models for tagging and analysis tasks.

### list_gpt5_models.py
List available GPT-5 models from OpenAI.

### tag_videos.py
Interactive tool for tagging videos with various strategies.

### youtube_cache.py
Direct cache operations and exploration for YouTube content.

## Usage

All tools should be run with `uv run python`:

```bash
cd compose/tools
uv run python analyze_youtube.py
uv run python tag_videos.py
# etc.
```

## Environment

These tools use the project's shared `.env` file at the repository root for API keys and configuration.
