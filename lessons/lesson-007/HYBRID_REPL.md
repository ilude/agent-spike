# Hybrid REPL - Background Scheduler + Interactive Ingestion

## Overview

The hybrid REPL combines **background scheduled processing** with **interactive manual ingestion** in a single tool.

**Features:**
- ✅ **Background scheduler** - Processes CSV at 1 video per 15 minutes
- ✅ **Manual ingestion** - Up to 5 videos per 15 minutes
- ✅ **Smart rate limiting** - Auto-appends to CSV if limit exceeded
- ✅ **No quotes needed** - Paste URLs directly
- ✅ **Status tracking** - See rate limits and next scheduled run

## Quick Start

From project root:

```bash
make ingest
```

This starts:
1. Background scheduler processing `projects/video-lists/nate_jones_videos.csv`
2. Interactive REPL for manual URL ingestion

## How It Works

### Two Parallel Streams

**1. Background Scheduler (Automatic)**
- Processes CSV at 1 video per 15 minutes
- Runs independently in background
- Skips already-cached videos
- Respects rate limits

**2. Manual Ingestion (Interactive)**
- Process videos immediately from the REPL
- Rate limit: 5 videos per 15 minutes
- If limit exceeded, URL appended to CSV for scheduler

### Rate Limiting

**Manual ingestion tracking:**
- Tracks last 5 ingestions in rolling 15-minute window
- Shows current status: "3/5 in last 15 min"
- Calculates time until next slot available

**Behavior when limit exceeded:**
- URL added to TOP of CSV queue
- Scheduler will process it next (~15 minutes)
- No error, just queued for later

## Commands

### Status

```
>> status

=== STATUS ===
Rate limit: 3/5 in last 15 min
Manual ingestion: READY (can process immediately)

Scheduler next run: 14:45:23 (in 12m 34s)
Total cached videos: 42
```

Shows:
- Current rate limit status
- When manual ingestion available
- Next scheduled run time
- Total videos cached

### Manual URL Ingestion

Just paste the URL (no quotes):

```
>> https://www.youtube.com/watch?v=VIDEO_ID&t=123s

Processing: https://www.youtube.com/watch?v=VIDEO_ID&t=123s
Rate limit OK (3/5 in last 15 min)
  [1/3] Fetching transcript for video ID: VIDEO_ID...
  [2/3] Generating tags (8234 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached VIDEO_ID (8234 chars)
```

### URL Queued (Rate Limit Hit)

```
>> https://www.youtube.com/watch?v=NEW_VIDEO

Processing: https://www.youtube.com/watch?v=NEW_VIDEO
[RATE LIMIT] Already processed 5 videos in last 15 minutes
Next slot available in: 8 minutes

Appending URL to CSV for scheduled processing...
[OK] URL added to top of CSV queue
     Will be processed by scheduler next (in ~15 minutes)
```

### List Videos

```
>> list

Fetching cached videos...

Found 42 cached videos (showing first 10):
  1. VIDEO_ID1 (12,345 chars)
  2. VIDEO_ID2 (8,234 chars)
  ...
```

### Count Videos

```
>> count

Total cached videos: 42
Rate limit status: 3/5 in last 15 min
```

### Help

```
>> help

Commands:
  - Paste any YouTube URL (no quotes needed)
  - 'status' - Show rate limit status
  - 'list' - Show all cached videos
  - 'count' - Show total cached videos
  - 'quit' or 'exit' - Exit the REPL
  - 'help' - Show this help message
```

### Exit

```
>> quit

Stopping scheduler...
Goodbye!
```

Gracefully stops both scheduler and REPL.

## Example Session

```bash
$ make ingest

Starting Hybrid YouTube Video Ingestion REPL + Scheduler...
Features: Background scheduler + manual ingestion (5 per 15 min)
Press Ctrl+C to stop (progress is saved)

================================================================================
Hybrid YouTube Video Ingestion REPL + Scheduler
================================================================================
Collection: cached_content
CSV File: C:\Projects\working\agent-spike\projects\video-lists\nate_jones_videos.csv

Features:
  - Background scheduler: 1 video per 15 minutes from CSV
  - Manual ingestion: Up to 5 videos per 15 minutes
  - Auto-append to CSV if rate limit would be exceeded

Commands:
  - Paste any YouTube URL (no quotes needed)
  - 'status' - Show rate limit status
  - 'list' - Show all cached videos
  - 'count' - Show total cached videos
  - 'quit' or 'exit' - Exit the REPL
  - 'help' - Show this help message
================================================================================

[OK] Connected to Qdrant collection: cached_content

[SCHEDULER] Starting background scheduler (15 min intervals)

[SCHEDULER] Processing next video:
  Title: The Mental Models of Master Prompters
  URL: https://www.youtube.com/watch?v=GTEz5WWbfiw
  [1/3] Fetching transcript for video ID: GTEz5WWbfiw...
  [2/3] Generating tags (8234 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached GTEz5WWbfiw (8234 chars)
[SCHEDULER] Total processed: 1
[SCHEDULER] Waiting 15 minutes... (next run at 15:00:00)

>> status

=== STATUS ===
Rate limit: 1/5 in last 15 min
Manual ingestion: READY (can process immediately)

Scheduler next run: 15:00:00 (in 14m 32s)
Total cached videos: 8

>> https://www.youtube.com/watch?v=MANUAL_VIDEO

Processing: https://www.youtube.com/watch?v=MANUAL_VIDEO
Rate limit OK (1/5 in last 15 min)
  [1/3] Fetching transcript for video ID: MANUAL_VIDEO...
  [2/3] Generating tags (4567 chars)...
  [3/3] Inserting into Qdrant...
  SUCCESS - Cached MANUAL_VIDEO (4567 chars)

>> count

Total cached videos: 9
Rate limit status: 2/5 in last 15 min

>> quit

Stopping scheduler...
Goodbye!
```

## Use Cases

### Scenario 1: Opportunistic Ingestion

You're working and come across interesting videos:

```
>> https://youtube.com/watch?v=INTERESTING_VIDEO1
[Processed immediately]

>> https://youtube.com/watch?v=INTERESTING_VIDEO2
[Processed immediately]

>> https://youtube.com/watch?v=INTERESTING_VIDEO3
[Processed immediately]
```

All processed right away (under rate limit).

### Scenario 2: Burst Ingestion

You find 10 videos you want to add:

```
>> https://youtube.com/watch?v=VIDEO1
[Processed - 1/5]

>> https://youtube.com/watch?v=VIDEO2
[Processed - 2/5]

>> https://youtube.com/watch?v=VIDEO3
[Processed - 3/5]

>> https://youtube.com/watch?v=VIDEO4
[Processed - 4/5]

>> https://youtube.com/watch?v=VIDEO5
[Processed - 5/5]

>> https://youtube.com/watch?v=VIDEO6
[RATE LIMIT - Added to CSV queue]

>> https://youtube.com/watch?v=VIDEO7
[RATE LIMIT - Added to CSV queue]
...
```

First 5 processed immediately, rest queued for scheduler.

### Scenario 3: Background Processing

Leave it running while you work:

```bash
# Start in background
make ingest

# Scheduler processes CSV automatically
# Use REPL when you need to add specific videos
# Leave running all day/week
```

## Comparison with Other Tools

### vs. Simple REPL (`ingest_repl.py`)
- ✅ Adds background scheduler
- ✅ Processes CSV automatically
- ✅ Smarter rate limiting
- ✅ Auto-queue when limit exceeded

### vs. Scheduled Script (`scheduled_ingest.py`)
- ✅ Adds interactive manual ingestion
- ✅ Can prioritize specific videos
- ✅ Better for ad-hoc additions
- ⚠️ More complex

### When to use what?

**Use Hybrid REPL (`make ingest`):**
- Want background processing + manual control
- Need to add videos opportunistically
- Want best of both worlds

**Use Scheduled Script (`make ingest-nate`):**
- Just want hands-off background processing
- Don't need manual ingestion
- Simpler if only processing CSV

**Use Simple REPL:**
- Only doing manual ingestion
- No CSV to process
- Don't need background scheduler

## Technical Details

### Rate Limit Tracking

Uses a sliding window algorithm:
- Tracks timestamps of last N ingestions
- Removes timestamps outside 15-minute window
- Allows up to 5 ingestions per window
- Both manual and scheduler count toward limit

### CSV Appending

When rate limit exceeded:
1. Read entire CSV
2. Create new row with minimal data
3. Write back with new row at top (after header)
4. Scheduler picks it up next

### Background Task

Runs as asyncio task:
- Non-blocking (REPL remains responsive)
- Shares rate limiter with manual ingestion
- Communicates next run time to REPL
- Gracefully stops on quit

## Troubleshooting

### "Already running make ingest-nate"

**IMPORTANT**: You **cannot** run both `make ingest` and `make ingest-nate` at the same time!

Qdrant database allows only one connection at a time:
- `make ingest-nate` - Scheduled processing only (no REPL)
- `make ingest` - Hybrid (scheduler + REPL)

**Choose one:**
- If you want manual + scheduled: Use `make ingest` (hybrid)
- If you want scheduled only: Use `make ingest-nate`

If you get "Storage folder is already accessed" error:
1. Stop the other script (Ctrl+C)
2. Start the one you want to use

### Rate limit confusion

Two separate limits:
- **Manual**: 5 per 15 minutes (your manual URLs)
- **Scheduler**: 1 per 15 minutes (CSV processing)

They're independent but both count toward YouTube API limits.

### Scheduler not starting

Check:
1. CSV file exists
2. CSV has 'url' column
3. No syntax errors in CSV

### CSV gets corrupted

The CSV append creates minimal rows. If you see rows with just URLs and "[Manual addition]" titles, that's normal. The scheduler will process them.

## Best Practices

1. **Use status often** - Check rate limits before pasting many URLs
2. **Let scheduler run** - Don't quit too quickly
3. **Monitor in background** - Safe to leave running
4. **Burst carefully** - Remember 5 per 15 min limit
5. **CSV is queue** - Treat it as append-only when using hybrid REPL

## Configuration

Default settings (edit `hybrid_ingest_repl.py`):

- **Max manual ingestions**: 5 per window
- **Window size**: 15 minutes
- **Scheduler interval**: 15 minutes
- **CSV path**: `projects/video-lists/nate_jones_videos.csv`
- **Collection**: `cached_content`

## Notes

- Scheduler and manual ingestion share rate limiter
- CSV acts as persistent queue
- Safe to stop/restart anytime (progress saved)
- Both streams respect YouTube rate limits
- All timestamps in local time

## See Also

- `REPL_USAGE.md` - Simple REPL guide
- `SCHEDULED_INGEST.md` - Scheduled processing guide
- `README.md` - Lesson 007 overview
