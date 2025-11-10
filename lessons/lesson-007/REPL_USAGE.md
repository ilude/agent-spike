# YouTube Video Ingestion REPL - Usage Guide

## Quick Start

From the project root, run:

```bash
make ingest
```

Or directly:

```bash
uv run python lessons/lesson-007/ingest_repl.py
```

## Features

✅ **No quotes needed** - Paste URLs directly without worrying about PowerShell escaping
✅ **Interactive** - Process multiple videos in one session
✅ **Smart caching** - Detects if video is already cached
✅ **Real-time feedback** - Shows progress as it processes
✅ **Built-in commands** - List, count, and manage cached videos

## Commands

### Ingest a Video

Simply paste the YouTube URL (no quotes needed):

```
>> https://www.youtube.com/watch?v=MuP9ki6Bdtg
```

The REPL will:
1. Fetch the transcript from YouTube
2. Generate AI tags using Claude
3. Insert into Qdrant cache
4. Verify the insertion

### List All Cached Videos

```
>> list
```

Shows all cached videos with:
- Video ID
- Transcript length
- AI-generated tags

### Count Cached Videos

```
>> count
```

Shows total number of videos in the cache.

### Help

```
>> help
```

Shows available commands.

### Exit

```
>> quit
```

or

```
>> exit
```

Exits the REPL.

## Example Session

```
$ make ingest

================================================================================
YouTube Video Ingestion REPL
================================================================================
Collection: cached_content

Commands:
  - Paste any YouTube URL (no quotes needed)
  - 'list' - Show all cached videos
  - 'count' - Show total cached videos
  - 'quit' or 'exit' - Exit the REPL
  - 'help' - Show this help message
================================================================================

[OK] Connected to Qdrant collection: cached_content

>> https://www.youtube.com/watch?v=MuP9ki6Bdtg

Processing: https://www.youtube.com/watch?v=MuP9ki6Bdtg
[1/3] Fetching transcript for video ID: MuP9ki6Bdtg...
[OK] Transcript fetched: 24853 characters
[2/3] Generating tags with AI agent...
[OK] Tags: {"tags": ["rag", "vector-search", "embeddings"]}
[3/3] Inserting into Qdrant...
[SUCCESS] Cached with key: youtube:video:MuP9ki6Bdtg

>> count

Total cached videos: 7

>> quit

Goodbye!
```

## Why Use the REPL?

### Problem with PowerShell

PowerShell treats `&` as a command separator, so URLs like:

```
https://www.youtube.com/watch?v=VIDEO_ID&t=123s
```

Must be quoted:

```bash
uv run python ingest_single_video.py "https://www.youtube.com/watch?v=VIDEO_ID&t=123s"
```

### REPL Solution

The REPL reads URLs as plain input, so you can paste directly:

```
>> https://www.youtube.com/watch?v=VIDEO_ID&t=123s&pp=xyz123
```

No quotes, no escaping, no hassle!

## Advanced Usage

### Use Different Collection

```bash
# Default collection: cached_content
make ingest

# Custom collection
uv run python lessons/lesson-007/ingest_repl.py my_videos
```

### Process Multiple Videos

Just paste multiple URLs one after another:

```
>> https://www.youtube.com/watch?v=VIDEO_1
[Processing...]

>> https://www.youtube.com/watch?v=VIDEO_2
[Processing...]

>> https://www.youtube.com/watch?v=VIDEO_3
[Processing...]

>> list
Found 3 cached videos:
...
```

## Troubleshooting

### "No module named 'cache'"

Make sure you've installed lesson-007 dependencies:

```bash
uv sync --group lesson-007
```

### "Could not extract video ID from URL"

Ensure you're pasting a valid YouTube URL that starts with `http`.

### "Transcript disabled for this video"

Some videos have transcripts disabled by the creator. Nothing we can do about that.

### Script hangs or is slow

Generating tags with AI can take 5-30 seconds depending on transcript length and API response time. Be patient!

## Tips

1. **Keep it running** - Process many videos in one session
2. **Use 'count'** - Quick check without listing everything
3. **Check before adding** - The REPL tells you if video is already cached
4. **Exit with Ctrl+C** - Then type 'quit' to properly exit

## See Also

- `ingest_single_video.py` - One-off script for single videos
- `list_cached_videos.py` - List all cached videos
- `verify_cached_video.py` - Verify specific video with semantic search test
- `scripts/ingest_csv.py` - Batch ingest from CSV file

## Collection Name

Default: `cached_content`

All scripts in lesson-007 use this collection by default. You can specify a different collection as the first argument to any script.
