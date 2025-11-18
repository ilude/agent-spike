# Scripts

Reusable command-line scripts built on top of the service layer.

## Quick Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `ingest_youtube.py` | Batch REPL ingestion | `make ingest` |
| `ingest_video.py` | Single video ingestion | `uv run python compose/cli/ingest_video.py "URL"` |
| `list_videos.py` | List cached videos | `uv run python compose/cli/list_videos.py` |
| `verify_video.py` | Check specific video | `uv run python compose/cli/verify_video.py VIDEO_ID` |
| `search_videos.py` | Semantic search | `uv run python compose/cli/search_videos.py "query"` |
| `fetch_channel_videos.py` | Get channel videos → CSV | `uv run python compose/cli/fetch_channel_videos.py "@channel"` |

## Available Scripts

### `ingest_youtube.py`

Fast YouTube video ingestion with background batch processing (REPL).

**Usage:**
```bash
# Via make (recommended)
make ingest

# Direct invocation
uv run python compose/cli/ingest_youtube.py [csv_path] [collection_name]
```

**Features:**
- Background batch processor (entire CSV on startup)
- Manual URL ingestion (instant, no rate limit)
- Webshare proxy support (no YouTube rate limiting)
- Archive-first pipeline (all expensive data saved)
- Interactive REPL for manual URLs

**See also:** `lessons/lesson-007/INGEST_FAST.md`

---

### `ingest_video.py`

Ingest a single YouTube video (non-interactive).

**Usage:**
```bash
# Single video
uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..."

# Custom collection
uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..." my_collection

# Dry run (show what would happen)
uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..." --dry-run
```

**Features:**
- Simple single-video ingestion
- Archive + cache pipeline
- Dry run mode for testing
- Detailed progress output

---

### `list_videos.py`

List all cached YouTube videos.

**Usage:**
```bash
# Default collection
uv run python compose/cli/list_videos.py

# Custom collection
uv run python compose/cli/list_videos.py my_collection

# Limit results
uv run python compose/cli/list_videos.py cached_content 20
```

**Features:**
- Shows video ID, URL, transcript length, tags
- Configurable result limit
- Clean formatted output

---

### `verify_video.py`

Verify a specific video is cached and show its data.

**Usage:**
```bash
# Check if video is cached
uv run python compose/cli/verify_video.py dQw4w9WgXcQ

# Custom collection
uv run python compose/cli/verify_video.py dQw4w9WgXcQ my_collection
```

**Features:**
- Check if video exists in cache
- Show full video data
- Display transcript snippet
- Test semantic search with video's tags

---

### `search_videos.py`

Semantic search for cached videos.

**Usage:**
```bash
# Search default collection
uv run python compose/cli/search_videos.py "machine learning tutorial"

# Custom collection
uv run python compose/cli/search_videos.py "AI agents" my_collection

# More results
uv run python compose/cli/search_videos.py "python coding" cached_content 20
```

**Features:**
- Semantic similarity search using embeddings
- Relevance scoring
- Context snippets showing query matches
- Configurable result limit

---

### `fetch_channel_videos.py`

Fetch all videos from a YouTube channel and export to CSV.

**Usage:**
```bash
# Fetch channel videos
uv run python compose/cli/fetch_channel_videos.py "https://www.youtube.com/@NateBJones"

# Specify output file
uv run python compose/cli/fetch_channel_videos.py "https://www.youtube.com/@NateBJones" output.csv
```

**Features:**
- Uses YouTube Data API v3 (requires `YOUTUBE_API_KEY` in `.env`)
- Fetches video metadata (title, URL, description, stats)
- Exports to CSV format
- Useful for creating video lists to feed into `ingest_youtube.py`

**Requirements:**
- Set `YOUTUBE_API_KEY` in your `.env` file
- Install: `uv add google-api-python-client` (if not already installed)

## Design Philosophy

Scripts in this directory:
1. **Build on services** - Use `compose.services.*` for business logic
2. **CLI-focused** - Provide user-friendly command-line interfaces
3. **Self-contained** - Can be run directly or via make targets
4. **Well-documented** - Clear help text and examples
5. **Error handling** - Graceful exits and helpful error messages

## Adding New Scripts

When creating a script:

1. **Use services** - Don't duplicate business logic
2. **Accept arguments** - Use `sys.argv` or argparse/click
3. **Provide defaults** - Sensible defaults for common use cases
4. **Handle errors** - Clean exit on Ctrl+C and exceptions
5. **Document it** - Add to this README with usage examples
6. **Add make target** - Create a make shortcut if useful

Example structure:
```python
#!/usr/bin/env python
"""Brief description of what this script does."""

from compose.cli.base import setup_script_environment

# Setup environment
setup_script_environment()

# Import from services
from compose.services.your_service import your_function

async def main():
    """Main entry point."""
    try:
        # Your script logic here
        pass
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Clean exit - already handled in main()
```

## Future Scripts

Candidates for extraction from lessons:
- **export_cache.py** - Export Qdrant cache to archive or other formats
- **batch_tag.py** - Batch re-tagging of videos with different LLM
- **compare_models.py** - Compare different LLM models for tagging
- **archive_stats.py** - Show statistics from archive (costs, counts, etc.)
- **dedupe_cache.py** - Remove duplicate videos from cache

Extract when patterns stabilize and scripts are useful standalone.
