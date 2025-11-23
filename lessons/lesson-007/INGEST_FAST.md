# Fast YouTube Ingestion (No Rate Limiting)

**New workflow using Webshare proxy - processes entire CSV on startup!**

## Quick Start

```bash
make ingest
```

## What Changed

### Before (Rate Limited)
- **15 minute delays** between videos
- Manual rate limit tracking (5 per 15 min)
- CSV processed slowly over hours/days
- Complex scheduler logic

### After (Fast with Proxy)
- **No rate limiting** - Webshare proxy handles it
- Entire CSV processed on startup
- Manual URLs processed instantly
- Simple background batch processor

## Features

1. **Background Batch Processing**
   - Processes entire `projects/video-lists/nate_jones_videos.csv` on startup
   - No rate limiting (Webshare proxy handles YouTube rate limits)
   - Runs in background while REPL is available

2. **Manual URL Processing**
   - Paste any YouTube URL for instant processing
   - No rate limit delays
   - Results saved to both archive and cache

3. **Archive-First Pipeline**
   - All transcripts archived before caching
   - All LLM outputs archived with cost tracking
   - Enables future reprocessing without re-fetching

## Architecture

```
User starts REPL
    ↓
Background task starts → Processes entire CSV
    ↓                           ↓
REPL ready            [Video 1] → Fetch transcript (via Webshare proxy)
    ↓                           ↓
Accept URLs           [Video 1] → Archive transcript
    ↓                           ↓
Process instantly     [Video 1] → Generate tags (LLM)
                                ↓
                      [Video 1] → Archive LLM output
                                ↓
                      [Video 1] → Cache in Qdrant
                                ↓
                      [Video 2] → (repeat...)
```

## Pipeline Steps

For each video:

1. **Check cache** - Skip if already processed
2. **Fetch transcript** - Via Webshare proxy (no rate limit)
3. **Archive transcript** - Save to `compose/data/archive/` (JSON)
4. **Generate tags** - Claude Haiku LLM
5. **Archive LLM output** - Save with cost tracking
6. **Cache result** - Store in Qdrant for semantic search

## Commands

While REPL is running:

- **Paste URL** - Process any YouTube URL instantly
- **`list`** - Show cached videos (first 20)
- **`count`** - Total cached videos
- **`quit`** / **`exit`** - Stop gracefully
- **`help`** - Show commands

## Exit Behavior

Ctrl+C produces clean output:
```
Keyboard Interrupt Received... Exiting!
Goodbye!
```

No stack traces, no errors - just clean shutdown.

## Proxy Configuration

Webshare proxy enabled via `.env`:
```bash
WEBSHARE_PROXY_USERNAME=your_username
WEBSHARE_PROXY_PASSWORD=your_password
```

This eliminates YouTube rate limiting completely.

## Data Storage

**Archive** (Expensive data):
- `compose/data/archive/YYYY-MM/video_id.json`
- Immutable JSON files
- Contains: transcript, LLM outputs, metadata, costs

**Cache** (Fast retrieval):
- `compose/data/qdrant/`
- Semantic search enabled
- Can be rebuilt from archive if needed

## Comparison with Old Workflow

| Feature | Old (Rate Limited) | New (Fast) |
|---------|-------------------|-----------|
| CSV Processing | 15 min per video | Batch on startup |
| Manual URLs | 5 per 15 min | Instant, unlimited |
| Proxy Support | No | Yes (Webshare) |
| Archive Pipeline | No | Yes |
| Exit Handling | Stack trace | Clean message |
| Total Time (100 videos) | ~25 hours | ~10-20 minutes |

## Old Workflow (Still Available)

If you need the old rate-limited version:
```bash
make ingest-old
```

But there's no reason to use it now that we have proxy support!

## Next Steps

1. Run `make ingest`
2. Let it process the CSV in background
3. Use REPL for manual URLs as needed
4. Check archive: `ls compose/data/archive/`
5. Search cache: Use `list` or `count` commands
