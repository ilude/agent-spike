# Data Sources: Video Recommendation System

**Last Updated**: 2025-11-24

## Overview

Multiple data sources feed the recommendation system. Each provides different signals with different reliability.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Sources                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Historical    │    Real-time    │        Discovery            │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ Brave History   │ UI Ratings      │ YouTube API Search          │
│ Google Takeout  │ Mentat Ingest   │ Subscription Feeds          │
│                 │ Watch Signals   │ Related Videos              │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Signal Types

| Signal | Source | Strength | Meaning |
|--------|--------|----------|---------|
| `watched` | Brave, Takeout | Medium | User clicked video (may not have finished) |
| `thumbs_up` | UI | Strong+ | User explicitly liked |
| `thumbs_down` | UI | Strong- | User explicitly disliked |
| `not_interested` | UI | Medium- | User doesn't want to see this |
| `ingested` | Mentat | Strong+ | User cared enough to transcribe |
| `subscribed` | Takeout | Medium+ | User subscribed to channel |
| `searched` | Takeout | Weak+ | User searched for this topic |

## Source 1: Brave Browser History

### What It Contains
- YouTube URLs visited
- Timestamps
- No explicit like/dislike data

### Import Process

```python
async def import_brave_history(file_path: str, user_id: str) -> ImportResult:
    """
    Import YouTube watch history from Brave browser export.

    Steps:
    1. Parse history file (JSON or SQLite)
    2. Filter to youtube.com/watch URLs
    3. Extract video IDs
    4. Deduplicate against existing signals
    5. For new videos: fetch metadata from YouTube API
    6. Create 'watched' signals with source='brave'
    """
    pass
```

### Existing Infrastructure

We already have Brave history sync:
- `compose/cli/brave_history/copy_brave_history.py`
- `make brave-sync` command
- Outputs to `compose/data/queues/brave_history`

**Integration**: Extend existing pipeline to filter YouTube URLs and feed recommendation system.

### Data Location
- Windows: `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\History`
- File format: SQLite database
- Table: `urls` (url, title, visit_count, last_visit_time)

### Parsing

```python
def parse_brave_history(db_path: str) -> list[WatchEvent]:
    """
    Extract YouTube watches from Brave history.

    Query:
    SELECT url, title, last_visit_time
    FROM urls
    WHERE url LIKE '%youtube.com/watch%'
    ORDER BY last_visit_time DESC
    """
    pass
```

## Source 2: Google Takeout

### What It Contains
- Complete watch history with timestamps
- Liked videos
- Subscriptions
- Search history
- Comments

### Export Process
1. Go to takeout.google.com
2. Select "YouTube and YouTube Music"
3. Choose JSON format
4. Download and extract

### File Structure

```
Takeout/
├── YouTube and YouTube Music/
│   ├── history/
│   │   └── watch-history.json
│   ├── subscriptions/
│   │   └── subscriptions.json
│   ├── playlists/
│   │   └── liked-videos.json
│   └── search-history.json
```

### watch-history.json Format

```json
[
  {
    "header": "YouTube",
    "title": "Watched Video Title",
    "titleUrl": "https://www.youtube.com/watch?v=VIDEO_ID",
    "subtitles": [
      {
        "name": "Channel Name",
        "url": "https://www.youtube.com/channel/CHANNEL_ID"
      }
    ],
    "time": "2024-10-15T14:30:00.000Z"
  }
]
```

### Import Process

```python
async def import_google_takeout(
    takeout_dir: str,
    user_id: str,
) -> ImportResult:
    """
    Import from Google Takeout export.

    Steps:
    1. Parse watch-history.json -> 'watched' signals
    2. Parse liked-videos.json -> 'thumbs_up' signals
    3. Parse subscriptions.json -> channel preferences
    4. Deduplicate across sources
    5. Fetch metadata for unknown videos
    """
    pass
```

### Deduplication

Same video may appear in:
- Brave history
- Takeout watch history
- Already in video_rec from API discovery

**Rules**:
1. Video metadata: fetch once, reuse
2. User signals: keep most recent per type
3. Watch count: accumulate from all sources

```python
async def deduplicate_import(
    video_id: str,
    user_id: str,
    signal_type: str,
    source: str,
) -> bool:
    """
    Check if signal already exists.

    Returns True if new (should import), False if duplicate.
    """
    existing = await db.query("""
        SELECT id FROM user_video_signal
        WHERE user_id = $user_id
          AND video_id = $video_id
          AND signal_type = $signal_type
        LIMIT 1
    """, {"user_id": user_id, "video_id": video_id, "signal_type": signal_type})

    return len(existing) == 0
```

## Source 3: Mentat Ingest

### What It Is
When a user pastes a YouTube URL into Mentat chat for transcription, that's a strong positive signal.

### Integration Point

The existing ingest endpoint:
- `POST /ingest` with YouTube URL
- Fetches transcript
- Stores in cache

**Enhancement**: Also create `ingested` signal in video_rec system.

```python
# In ingest handler
async def handle_youtube_ingest(url: str, user_id: str):
    video_id = extract_video_id(url)

    # Existing: fetch and cache transcript
    transcript = await fetch_transcript(video_id)
    await cache_transcript(video_id, transcript)

    # NEW: record as positive signal for recommendations
    await recommendation_service.record_signal(
        user_id=user_id,
        video_id=video_id,
        signal_type="ingested",
        source="mentat",
    )
```

## Source 4: YouTube API Discovery

### Purpose
Find NEW videos the user hasn't seen but might like.

### API Endpoints Used

| Endpoint | Quota Cost | Purpose |
|----------|------------|---------|
| search.list | ~100 units | Find videos by query |
| videos.list | ~1 unit/video | Get metadata |
| channels.list | ~1 unit/channel | Get channel info |

### Discovery Strategies

**1. Query-based**
Search for topics matching user categories:
```python
queries = ["ESP32 projects", "home automation DIY", "woodworking beginner"]
for query in queries:
    results = youtube.search(query, max_results=10)
```

**2. Channel-based**
Fetch recent uploads from liked channels:
```python
for channel_id in user_top_channels[:10]:
    uploads = youtube.channel_uploads(channel_id, max_results=5)
```

**3. Related videos** (v2)
Get recommendations from YouTube for liked videos:
```python
for video_id in recent_thumbs_up[:5]:
    related = youtube.related_videos(video_id, max_results=5)
```

### Quota Management

Daily limit: 10,000 units (free tier)

**Budget allocation**:
- Scheduled batch (daily): ~2,000 units
- On-demand discovery: ~500 units
- Buffer: ~7,500 units

**Tracking**:
```python
class QuotaTracker:
    async def use(self, units: int) -> bool:
        """Use quota, return False if would exceed limit."""
        pass

    async def get_remaining(self) -> int:
        """Get remaining quota for today."""
        pass

    async def reset_at(self) -> datetime:
        """When does quota reset (midnight PT)."""
        pass
```

### Scheduled Batch Job

```python
class DailyDiscoveryJob:
    """
    Run 1-2x daily to discover new content.

    Process:
    1. Get user's active categories
    2. Build search queries from category keywords
    3. Search YouTube (respecting quota)
    4. Filter out already-known videos
    5. Fetch metadata for new videos
    6. Queue transcript fetching
    7. Extract features
    """
    pass
```

## Source 5: UI Ratings

### Real-time Signals

User interactions in the /videos UI:

```typescript
// Frontend events
async function rateVideo(videoId: string, rating: 'up' | 'down') {
  await api.post(`/videos/${videoId}/rate`, { rating });
  // Optimistic UI update
  updateLocalState(videoId, rating);
}

async function markNotInterested(videoId: string) {
  await api.post(`/videos/${videoId}/rate`, { rating: 'not_interested' });
  // Remove from view
  hideVideo(videoId);
}
```

### Signal Recording

```python
async def record_rating(
    user_id: str,
    video_id: str,
    rating: str,
) -> None:
    """
    Record UI rating as signal.

    Also updates:
    - Channel preference (affinity score)
    - Category associations
    - Triggers retrain check
    """
    signal_type = {
        'up': 'thumbs_up',
        'down': 'thumbs_down',
        'not_interested': 'not_interested',
    }[rating]

    await db.query("""
        INSERT INTO user_video_signal {
            user_id: $user_id,
            video_id: $video_id,
            signal_type: $signal_type,
            source: 'ui',
            timestamp: time::now()
        }
    """, {...})

    # Update channel preference
    await update_channel_affinity(user_id, video_id, rating)

    # Check if model needs retraining
    if await should_retrain(user_id):
        await queue_retrain_job(user_id)
```

## Import Pipeline

### Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Parse Source │ ──► │ Deduplicate  │ ──► │ Fetch Meta   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Update Model │ ◄── │ Store Signal │ ◄── │Extract Feats │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Error Handling

| Error | Action |
|-------|--------|
| Video deleted/private | Skip, log warning |
| Quota exceeded | Stop discovery, use cached |
| Rate limited | Exponential backoff |
| Invalid URL | Skip, count in errors |
| Transcript unavailable | Store video without transcript |

### Import Result

```python
@dataclass
class ImportResult:
    source: str
    total_processed: int
    new_videos: int
    new_signals: int
    duplicates_skipped: int
    errors: int
    error_details: list[str]
    quota_used: int
```
