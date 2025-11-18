# Archive Service

Content archiving service for storing expensive-to-fetch data.

## Purpose

Archive anything that costs **time or money** to fetch:
- External API calls (YouTube transcripts, web scraping)
- LLM outputs (tags, summaries, classifications)
- Rate-limited operations
- Data that might need reprocessing later

## Design Principles

- **Protocol-first**: Easy to mock and swap implementations
- **Dependency injection**: Configuration passed in, not hard-coded
- **Composition**: Services compose together
- **Immutable archives**: Write once, update with new records

## Quick Start

```python
from compose.services.archive import create_local_archive_writer

# Use defaults (projects/data/archive)
archive = create_local_archive_writer()

# Archive transcript (rate-limited API call)
archive.archive_youtube_video(
    video_id="dQw4w9WgXcQ",
    url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    transcript="...",
    metadata={"title": "Never Gonna Give You Up"},
)

# Archive LLM output (costs money)
archive.add_llm_output(
    video_id="dQw4w9WgXcQ",
    output_type="tags",
    output_value="music, 80s, meme",
    model="claude-3-5-haiku-20241022",
    cost_usd=0.0012,
)

# Track processing
archive.add_processing_record(
    video_id="dQw4w9WgXcQ",
    version="v1_full_embed",
    collection_name="cached_content",
)
```

## Custom Configuration

```python
from pathlib import Path
from compose.services.archive import ArchiveConfig, LocalArchiveWriter

# Custom location, no month organization
config = ArchiveConfig(
    base_dir=Path("/custom/archive"),
    organize_by_month=False,
)

archive = LocalArchiveWriter(config)
```

## Reprocessing Workflows

```python
from compose.services.archive import create_local_archive_reader

reader = create_local_archive_reader()

# Iterate all archives
for video in reader.iter_youtube_videos():
    print(f"{video.video_id}: {len(video.raw_transcript)} chars")

# Filter by date range
for video in reader.iter_youtube_videos(start_month="2024-10", end_month="2024-11"):
    # Reprocess with new chunking strategy
    chunks = chunk_transcript(video.raw_transcript, size=500)
    # ... cache with new strategy

# Calculate costs
total_cost = reader.get_total_llm_cost()
print(f"Total LLM spend: ${total_cost:.2f}")
```

## File Structure

Archives are stored as JSON files:

```
projects/data/archive/
└── youtube/
    ├── 2024-10/
    │   ├── dQw4w9WgXcQ.json
    │   └── ...
    └── 2024-11/
        └── ...
```

## Testing

```bash
# Run unit tests
uv run pytest compose/tests/unit/test_archive.py -v

# With coverage
uv run pytest compose/tests/unit/test_archive.py --cov=compose.services.archive
```

## See Also

- `protocols.py` - Interface definitions
- `models.py` - Pydantic data models
- `config.py` - Configuration objects
