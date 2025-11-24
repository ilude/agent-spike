"""Universal URL ingest API router."""

import asyncio
import csv
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(tags=["ingest"])

# Track active ingests for stats integration
# Format: {video_id: {"started_at": datetime, "step": str}}
_active_ingests: dict[str, dict] = {}

# Track recent completed ingests for activity feed
# Format: [{"type": str, "video_id": str, "status": str, "message": str, "timestamp": str}]
_recent_ingests: list[dict] = []
_MAX_RECENT_INGESTS = 10

# Configuration
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8000")
MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")
QUEUE_BASE = Path(os.getenv("QUEUE_BASE", "/app/src/compose/data/queues"))
ARCHIVE_BASE = Path(os.getenv("ARCHIVE_BASE", "/app/src/compose/data/archive"))


class IngestRequest(BaseModel):
    """Request body for URL ingestion."""

    url: str
    channel_limit: Literal["month", "year", "50", "100", "all"] = "all"


class IngestResponse(BaseModel):
    """Response from ingestion."""

    type: Literal["video", "channel", "article"]
    status: Literal["success", "skipped", "queued", "error"]
    message: str
    details: dict[str, Any] = {}


def detect_url_type(url: str) -> Literal["video", "channel", "article"]:
    """Detect whether URL is a YouTube video, channel, or generic article."""
    url_lower = url.lower()

    # YouTube video patterns
    video_patterns = [
        r"youtube\.com/watch\?v=",
        r"youtu\.be/",
        r"youtube\.com/shorts/",
        r"youtube\.com/live/",
    ]
    for pattern in video_patterns:
        if re.search(pattern, url_lower):
            return "video"

    # YouTube channel patterns
    channel_patterns = [
        r"youtube\.com/@",
        r"youtube\.com/channel/",
        r"youtube\.com/c/",
        r"youtube\.com/user/",
    ]
    for pattern in channel_patterns:
        if re.search(pattern, url_lower):
            return "channel"

    return "article"


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


async def ingest_video(url: str) -> IngestResponse:
    """Ingest a single YouTube video immediately."""
    from compose.services.youtube import get_transcript, extract_video_id as yt_extract
    from compose.services.surrealdb import get_video, upsert_video
    from compose.services.surrealdb import VideoRecord
    from compose.services.archive import (
        create_local_archive_writer,
        ImportMetadata,
        ChannelContext,
    )

    try:
        video_id = yt_extract(url)

        # Check if already in SurrealDB
        existing = await get_video(video_id)
        if existing:
            return IngestResponse(
                type="video",
                status="skipped",
                message=f"Video already cached: {video_id}",
                details={"video_id": video_id},
            )

        transcript = get_transcript(url, cache=None)
        if "ERROR:" in transcript:
            return IngestResponse(
                type="video",
                status="error",
                message=transcript,
                details={"video_id": video_id},
            )

        # Archive to MinIO
        archive_writer = create_local_archive_writer(base_dir=ARCHIVE_BASE)
        import_metadata = ImportMetadata(
            source_type="single_import",
            imported_at=datetime.now(),
            import_method="cli",  # Web UI treated as CLI for now
            channel_context=ChannelContext(is_bulk_import=False),
            recommendation_weight=1.0,
        )
        archive_writer.archive_youtube_video(
            video_id=video_id,
            url=url,
            transcript=transcript,
            metadata={"source": "youtube-transcript-api"},
            import_metadata=import_metadata,
        )

        # Store video metadata in SurrealDB
        video_record = VideoRecord(
            video_id=video_id,
            url=url,
            fetched_at=datetime.now(),
            title="",  # Would need to fetch from YouTube metadata
            channel_id="",
            channel_name="",
            duration_seconds=0,
            view_count=0,
            published_at=None,
            source_type="single_import",
            import_method="cli",
            recommendation_weight=1.0,
            archive_path=f"youtube/{video_id}",
        )
        await upsert_video(video_record)

        return IngestResponse(
            type="video",
            status="success",
            message=f"Ingested video: {video_id} ({len(transcript)} chars)",
            details={"video_id": video_id, "transcript_length": len(transcript)},
        )

    except Exception as e:
        return IngestResponse(
            type="video",
            status="error",
            message=f"Failed to ingest video: {e}",
            details={},
        )


async def ingest_channel(
    url: str, limit: Literal["month", "year", "50", "100", "all"]
) -> IngestResponse:
    """Fetch channel videos and queue as CSV."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return IngestResponse(
            type="channel",
            status="error",
            message="YOUTUBE_API_KEY not configured",
            details={},
        )

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        # Extract username from URL
        username_match = re.search(r"@([^/]+)", url)
        if not username_match:
            return IngestResponse(
                type="channel",
                status="error",
                message="Could not extract channel username from URL",
                details={"url": url},
            )
        username = username_match.group(1)

        # Get channel ID
        search_response = youtube.search().list(
            part="snippet", q=username, type="channel", maxResults=1
        ).execute()

        if not search_response.get("items"):
            return IngestResponse(
                type="channel",
                status="error",
                message=f"Channel not found: {username}",
                details={},
            )

        channel_id = search_response["items"][0]["snippet"]["channelId"]
        channel_name = search_response["items"][0]["snippet"]["title"]

        # Calculate cutoff date based on limit
        if limit == "month":
            cutoff_date = datetime.now() - timedelta(days=30)
            max_videos = None
        elif limit == "year":
            cutoff_date = datetime.now() - timedelta(days=365)
            max_videos = None
        elif limit == "50":
            cutoff_date = datetime.now() - timedelta(days=365 * 10)
            max_videos = 50
        elif limit == "100":
            cutoff_date = datetime.now() - timedelta(days=365 * 10)
            max_videos = 100
        else:  # all
            cutoff_date = datetime.now() - timedelta(days=365 * 10)
            max_videos = None

        # Get uploads playlist
        channel_response = youtube.channels().list(
            part="contentDetails", id=channel_id
        ).execute()

        if not channel_response.get("items"):
            return IngestResponse(
                type="channel",
                status="error",
                message="Could not get channel details",
                details={},
            )

        uploads_playlist_id = channel_response["items"][0]["contentDetails"][
            "relatedPlaylists"
        ]["uploads"]

        # Fetch videos
        videos = []
        next_page_token = None

        while True:
            playlist_response = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            ).execute()

            video_ids = []
            video_dates = {}

            for item in playlist_response.get("items", []):
                video_id = item["contentDetails"]["videoId"]
                published_at = datetime.strptime(
                    item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                )

                if published_at >= cutoff_date:
                    video_ids.append(video_id)
                    video_dates[video_id] = published_at
                else:
                    break

            if not video_ids:
                break

            # Get video details
            videos_response = youtube.videos().list(
                part="snippet,statistics,contentDetails", id=",".join(video_ids)
            ).execute()

            for video in videos_response.get("items", []):
                vid = video["id"]
                snippet = video["snippet"]
                statistics = video.get("statistics", {})

                videos.append({
                    "title": snippet["title"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "upload_date": video_dates[vid].strftime("%Y-%m-%d"),
                    "view_count": statistics.get("viewCount", "0"),
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                })

                if max_videos and len(videos) >= max_videos:
                    break

            if max_videos and len(videos) >= max_videos:
                break

            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break

        if not videos:
            return IngestResponse(
                type="channel",
                status="error",
                message="No videos found in specified time range",
                details={"channel_id": channel_id},
            )

        # Save to CSV
        pending_dir = QUEUE_BASE / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{username.lower().replace('-', '_')}_videos.csv"
        csv_path = pending_dir / filename

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "url", "upload_date", "view_count", "channel_id", "channel_name"],
            )
            writer.writeheader()
            writer.writerows(videos)

        return IngestResponse(
            type="channel",
            status="queued",
            message=f"Queued {len(videos)} videos from {channel_name}",
            details={
                "filename": filename,
                "video_count": len(videos),
                "channel_id": channel_id,
                "channel_name": channel_name,
            },
        )

    except HttpError as e:
        return IngestResponse(
            type="channel",
            status="error",
            message=f"YouTube API error: {e}",
            details={},
        )
    except Exception as e:
        return IngestResponse(
            type="channel",
            status="error",
            message=f"Failed to fetch channel: {e}",
            details={},
        )


async def ingest_article(url: str) -> IngestResponse:
    """Ingest a webpage/article using Docling and store in MinIO."""
    import hashlib
    from compose.services.webpage import fetch_webpage
    from compose.services.minio import create_minio_client

    try:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        content_path = f"articles/{url_hash}.md"

        # Check if already in MinIO
        client = create_minio_client()
        if client.exists(content_path):
            return IngestResponse(
                type="article",
                status="skipped",
                message=f"Article already cached: {url[:50]}...",
                details={"url_hash": url_hash},
            )

        markdown = fetch_webpage(url)
        if markdown.startswith("ERROR:"):
            return IngestResponse(
                type="article",
                status="error",
                message=markdown,
                details={"url": url},
            )

        # Store the content in MinIO
        client.put_text(content_path, markdown)

        return IngestResponse(
            type="article",
            status="success",
            message=f"Ingested article ({len(markdown)} chars)",
            details={"url_hash": url_hash, "content_length": len(markdown)},
        )

    except Exception as e:
        return IngestResponse(
            type="article",
            status="error",
            message=f"Failed to ingest article: {e}",
            details={},
        )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_url(request: IngestRequest) -> IngestResponse:
    """Universal URL ingestion endpoint.

    Automatically detects URL type and processes accordingly:
    - YouTube videos: Immediate ingestion (transcript + cache)
    - YouTube channels: Fetch video list → CSV queue
    - Articles/webpages: Docling extraction → cache
    """
    url_type = detect_url_type(request.url)

    if url_type == "video":
        return await ingest_video(request.url)
    elif url_type == "channel":
        return await ingest_channel(request.url, request.channel_limit)
    else:
        return await ingest_article(request.url)


@router.get("/ingest/detect")
async def detect_url(url: str) -> dict[str, str]:
    """Detect URL type without ingesting."""
    return {"url": url, "type": detect_url_type(url)}


# =============================================================================
# SSE Streaming Ingest
# =============================================================================


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def get_active_ingests() -> list[dict]:
    """Get list of active ingests for stats integration."""
    return [
        {
            "video_id": vid,
            "started_at": info["started_at"].isoformat(),
            "step": info["step"],
        }
        for vid, info in _active_ingests.items()
    ]


def get_active_ingest_count() -> int:
    """Get count of active ingests."""
    return len(_active_ingests)


def _record_completed_ingest(
    content_type: str,
    status: str,
    message: str,
    video_id: str | None = None,
    url_hash: str | None = None,
) -> None:
    """Record a completed ingest for the activity feed."""
    global _recent_ingests
    _recent_ingests.insert(0, {
        "type": f"ingest_{status}",
        "content_type": content_type,
        "video_id": video_id,
        "url_hash": url_hash,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep only the most recent
    _recent_ingests = _recent_ingests[:_MAX_RECENT_INGESTS]


def get_recent_ingests() -> list[dict]:
    """Get list of recent completed ingests for activity feed."""
    return _recent_ingests.copy()


async def _stream_video_ingest(url: str) -> AsyncGenerator[str, None]:
    """Stream video ingest progress as SSE events."""
    from compose.services.youtube import get_transcript, extract_video_id as yt_extract
    from compose.services.surrealdb import get_video, upsert_video
    from compose.services.surrealdb import VideoRecord
    from compose.services.archive import (
        create_local_archive_writer,
        ImportMetadata,
        ChannelContext,
    )

    video_id = None
    try:
        # Step 1: Extract video ID
        yield _sse_event("progress", {"step": "extracting_id", "message": "Extracting video ID..."})
        video_id = yt_extract(url)

        # Track this ingest
        _active_ingests[video_id] = {"started_at": datetime.now(), "step": "checking_cache"}

        yield _sse_event("progress", {"step": "extracted_id", "message": f"Video ID: {video_id}", "video_id": video_id})

        # Step 2: Check cache
        yield _sse_event("progress", {"step": "checking_cache", "message": "Checking if already cached..."})
        _active_ingests[video_id]["step"] = "checking_cache"

        existing = await get_video(video_id)
        if existing:
            result = IngestResponse(
                type="video",
                status="skipped",
                message=f"Video already cached: {video_id}",
                details={"video_id": video_id},
            )
            yield _sse_event("complete", result.model_dump())
            return

        # Step 3: Fetch transcript
        yield _sse_event("progress", {"step": "fetching_transcript", "message": "Fetching transcript from YouTube..."})
        _active_ingests[video_id]["step"] = "fetching_transcript"

        # Run sync transcript fetch in thread pool to not block
        transcript = await asyncio.to_thread(get_transcript, url, None)

        if "ERROR:" in transcript:
            result = IngestResponse(
                type="video",
                status="error",
                message=transcript,
                details={"video_id": video_id},
            )
            yield _sse_event("complete", result.model_dump())
            return

        yield _sse_event("progress", {
            "step": "transcript_fetched",
            "message": f"Transcript fetched ({len(transcript):,} chars)",
            "transcript_length": len(transcript),
        })

        # Step 4: Archive to MinIO
        yield _sse_event("progress", {"step": "archiving", "message": "Archiving to storage..."})
        _active_ingests[video_id]["step"] = "archiving"

        archive_writer = create_local_archive_writer(base_dir=ARCHIVE_BASE)
        import_metadata = ImportMetadata(
            source_type="single_import",
            imported_at=datetime.now(),
            import_method="cli",  # Web UI treated as CLI for now
            channel_context=ChannelContext(is_bulk_import=False),
            recommendation_weight=1.0,
        )
        archive_writer.archive_youtube_video(
            video_id=video_id,
            url=url,
            transcript=transcript,
            metadata={"source": "youtube-transcript-api"},
            import_metadata=import_metadata,
        )

        yield _sse_event("progress", {"step": "archived", "message": "Archived successfully"})

        # Step 5: Store in SurrealDB
        yield _sse_event("progress", {"step": "storing", "message": "Storing in database..."})
        _active_ingests[video_id]["step"] = "storing"

        video_record = VideoRecord(
            video_id=video_id,
            url=url,
            fetched_at=datetime.now(),
            title="",
            channel_id="",
            channel_name="",
            duration_seconds=0,
            view_count=0,
            published_at=None,
            source_type="single_import",
            import_method="cli",
            recommendation_weight=1.0,
            archive_path=f"youtube/{video_id}",
        )
        await upsert_video(video_record)

        yield _sse_event("progress", {"step": "stored", "message": "Stored in database"})

        # Complete
        result = IngestResponse(
            type="video",
            status="success",
            message=f"Ingested video: {video_id} ({len(transcript):,} chars)",
            details={"video_id": video_id, "transcript_length": len(transcript)},
        )
        _record_completed_ingest("video", "success", result.message, video_id=video_id)
        yield _sse_event("complete", result.model_dump())

    except Exception as e:
        result = IngestResponse(
            type="video",
            status="error",
            message=f"Failed to ingest video: {e}",
            details={"video_id": video_id} if video_id else {},
        )
        _record_completed_ingest("video", "error", result.message, video_id=video_id)
        yield _sse_event("complete", result.model_dump())

    finally:
        # Clean up active ingest tracking
        if video_id and video_id in _active_ingests:
            del _active_ingests[video_id]


async def _stream_channel_ingest(
    url: str, limit: Literal["month", "year", "50", "100", "all"]
) -> AsyncGenerator[str, None]:
    """Stream channel ingest progress as SSE events."""
    # Channel ingests are quick (just creates CSV), use existing logic
    yield _sse_event("progress", {"step": "fetching_channel", "message": "Fetching channel information..."})

    result = await ingest_channel(url, limit)

    _record_completed_ingest("channel", result.status, result.message)
    yield _sse_event("complete", result.model_dump())


async def _stream_article_ingest(url: str) -> AsyncGenerator[str, None]:
    """Stream article ingest progress as SSE events."""
    yield _sse_event("progress", {"step": "fetching_article", "message": "Fetching article content..."})

    result = await ingest_article(url)

    url_hash = result.details.get("url_hash") if result.details else None
    _record_completed_ingest("article", result.status, result.message, url_hash=url_hash)
    yield _sse_event("complete", result.model_dump())


@router.post("/ingest/stream")
async def ingest_url_stream(request: IngestRequest):
    """SSE streaming endpoint for URL ingestion with real-time progress.

    Streams progress events as the ingestion proceeds:
    - event: progress - Step updates with message
    - event: complete - Final result (IngestResponse)

    Example events:
        event: progress
        data: {"step": "fetching_transcript", "message": "Fetching transcript from YouTube..."}

        event: complete
        data: {"type": "video", "status": "success", "message": "...", "details": {...}}
    """
    url_type = detect_url_type(request.url)

    if url_type == "video":
        generator = _stream_video_ingest(request.url)
    elif url_type == "channel":
        generator = _stream_channel_ingest(request.url, request.channel_limit)
    else:
        generator = _stream_article_ingest(request.url)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
