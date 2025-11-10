# Scheduled Video Ingestion - Rate-Limited Batch Processing

## Overview

Process large CSV files of YouTube videos with automatic rate limiting to avoid hitting YouTube API limits.

**Features:**
- ✅ Processes **1 video every 15 minutes** (configurable)
- ✅ **Automatically skips** already-cached videos
- ✅ **Exits gracefully** on rate limit detection
- ✅ **Progress saved** - resume anytime
- ✅ **Interruptible** - Ctrl+C to stop safely

## Quick Start

### Process Nate Jones Videos

From project root:

```bash
make ingest-nate
```

This will start processing `projects/video-lists/nate_jones_videos.csv` at 1 video per 15 minutes.

### Manual Usage

```bash
# Basic usage (15 minute intervals)
uv run python lessons/lesson-007/scheduled_ingest.py projects/video-lists/nate_jones_videos.csv

# Custom collection
uv run python lessons/lesson-007/scheduled_ingest.py videos.csv my_collection

# Custom interval (in minutes)
uv run python lessons/lesson-007/scheduled_ingest.py videos.csv cached_content 30

# Faster for testing (1 minute intervals)
uv run python lessons/lesson-007/scheduled_ingest.py videos.csv cached_content 1
```

## How It Works

### CSV Format

CSV must have a `url` column:

```csv
title,url,upload_date,view_count,duration,description
"Video Title",https://www.youtube.com/watch?v=VIDEO_ID,2025-01-01,1000,10:00,"Description..."
```

### Processing Flow

For each video in the CSV:

1. **Check cache** - Skip if already processed
2. **Fetch transcript** - Get from YouTube API
3. **Check for rate limits** - Exit if rate limited
4. **Generate tags** - Use Claude to create tags
5. **Store in Qdrant** - Cache for future use
6. **Wait 15 minutes** - Before next video

### Rate Limit Detection

If YouTube returns a rate limit error (429 or "Too Many Requests"), the script:
- Prints the rate limit message
- Shows how many videos were processed
- Exits cleanly
- **Resume later** - all progress is saved

### Progress Tracking

The script shows real-time progress:

```
[42/1949] Processing video:
  Title: The Mental Models of Master Prompters
  URL: https://www.youtube.com/watch?v=GTEz5WWbfiw
  [1/3] Fetching transcript for video ID: GTEz5WWbfiw...
  [2/3] Generating tags (12345 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached GTEz5WWbfiw (12345 chars)

  Progress: 35 processed, 7 skipped, 0 failed
  Waiting 15 minutes... (next video at 14:45:00)
```

## Example Session

```bash
$ make ingest-nate

Starting scheduled ingestion of Nate Jones videos...
Rate limit: 1 video every 15 minutes
Press Ctrl+C to stop (progress is saved)

================================================================================
Scheduled YouTube Video Ingestion
================================================================================
CSV File: projects/video-lists/nate_jones_videos.csv
Collection: cached_content
Interval: 15 minutes between videos
Started: 2025-11-09 14:30:00
================================================================================

[OK] Connected to Qdrant collection: cached_content

[INFO] Found 1949 videos in CSV

[1/1949] Processing video:
  Title: The Mental Models of Master Prompters: 10 Techniques for...
  URL: https://www.youtube.com/watch?v=GTEz5WWbfiw
  [1/3] Fetching transcript for video ID: GTEz5WWbfiw...
  [2/3] Generating tags (8234 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached GTEz5WWbfiw (8234 chars)

  Progress: 1 processed, 0 skipped, 0 failed
  Waiting 15 minutes... (next video at 14:45:00)

[2/1949] Processing video:
  Title: Why tool augmented AI beats autonomous agents!
  URL: https://www.youtube.com/watch?v=uR7sC68Eazk
  SKIPPED - Already cached (ID: uR7sC68Eazk)

  Progress: 1 processed, 1 skipped, 0 failed

[3/1949] Processing video:
  Title: Send this to your manager: AI budget crisis
  URL: https://www.youtube.com/watch?v=3C2oZpoQ8ro
  [1/3] Fetching transcript for video ID: 3C2oZpoQ8ro...
  [2/3] Generating tags (4567 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached 3C2oZpoQ8ro (4567 chars)

  Progress: 2 processed, 1 skipped, 0 failed
  Waiting 15 minutes... (next video at 15:00:00)

^C
[INTERRUPTED] Stopped by user (Ctrl+C)
You can resume later - progress is saved in Qdrant cache
```

## Time Estimates

### Full Nate Jones Collection

- **Total videos**: ~1,949
- **Already cached**: 7
- **Remaining**: ~1,942
- **Time per video**: 15 minutes + processing (~2-5 mins)
- **Estimated time**: ~20,000 minutes = **~14 days** of continuous running

### Strategies

**Option 1: Run continuously**
```bash
# Start and leave running
make ingest-nate

# Or in background (PowerShell)
Start-Job { make ingest-nate }
```

**Option 2: Run in batches**
```bash
# Process 10 videos (~3 hours)
# Stop with Ctrl+C after 10 videos
# Resume later (skips already-cached videos)
make ingest-nate
```

**Option 3: Faster intervals (risky)**
```bash
# 5 minute intervals (3x faster, higher rate limit risk)
uv run python lessons/lesson-007/scheduled_ingest.py \
  projects/video-lists/nate_jones_videos.csv \
  cached_content \
  5
```

## Resuming After Stop

Just run the command again:

```bash
make ingest-nate
```

The script will:
- Check each video against the cache
- Skip already-processed videos (instant)
- Continue processing new ones

## Rate Limit Handling

### What Triggers Rate Limits?

- Too many requests in short time
- YouTube API quotas
- IP-based throttling

### What Happens?

```
[42/1949] Processing video:
  [1/3] Fetching transcript for video ID: ABC123...
  ERROR - Too Many Requests (429)

[RATE LIMIT DETECTED]
Message: RATE_LIMIT - ERROR: Too Many Requests
Exiting to avoid further rate limit issues.
Resume later - already processed 41/1949 videos
```

### Recovery

1. **Wait** - Give it 1-2 hours
2. **Resume** - Run the command again
3. **Consider increasing interval** - Use 30 minutes instead of 15

## Monitoring Progress

### Check Cache Count

```bash
uv run python lessons/lesson-007/list_cached_videos.py | grep "Found"
```

### View Recent Videos

```bash
uv run python lessons/lesson-007/list_cached_videos.py | head -20
```

### Search for Specific Video

```bash
uv run python lessons/lesson-007/verify_cached_video.py VIDEO_ID
```

## Troubleshooting

### Script stops immediately

Make sure dependencies are installed:
```bash
uv sync --group lesson-007
```

### "CSV must have 'url' column"

Check your CSV format. First line should have headers including `url`.

### High failure rate

- Check your API keys in `.env`
- Verify internet connection
- Consider increasing interval

### Want to run faster?

**Development/Testing:**
```bash
# 1 minute intervals (for testing only!)
uv run python lessons/lesson-007/scheduled_ingest.py videos.csv cached_content 1
```

**Production:**
Keep 15 minutes or increase to 30 minutes to be safe.

## Best Practices

1. **Start small** - Test with 10-20 videos first
2. **Monitor closely** - Watch first few iterations
3. **Be patient** - 15 minutes is slow but safe
4. **Use logging** - Redirect output to file:
   ```bash
   make ingest-nate 2>&1 | tee ingest.log
   ```
5. **Resume often** - Don't worry about stopping/starting

## Related Tools

- **ingest_repl.py** - Interactive REPL for manual video ingestion
- **ingest_single_video.py** - One-off video ingestion
- **list_cached_videos.py** - View all cached videos
- **verify_cached_video.py** - Check specific video

## Configuration

Edit the script to customize:

- **Line 136**: Default interval (currently 15 minutes)
- **Line 95**: Transcript truncation (currently 15,000 chars)
- **Line 86**: Cache collection name

## Notes

- Progress is saved automatically (in Qdrant cache)
- Safe to interrupt at any time (Ctrl+C)
- Script checks cache before processing (no duplicate work)
- Rate limit detection exits gracefully
- All timestamps in local time

## See Also

- `REPL_USAGE.md` - Interactive REPL guide
- `README.md` - Lesson 007 overview
- `.claude/STATUS.md` - Project status
