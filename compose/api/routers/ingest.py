"""Universal URL ingest API router."""

import csv
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["ingest"])

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "content")
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
    from compose.services.cache import create_qdrant_cache
    from compose.services.archive import (
        create_local_archive_writer,
        ImportMetadata,
        ChannelContext,
    )

    cache = None
    try:
        cache = create_qdrant_cache(
            collection_name=QDRANT_COLLECTION,
            qdrant_url=QDRANT_URL,
            infinity_url=INFINITY_URL,
        )

        video_id = yt_extract(url)
        cache_key = f"youtube:video:{video_id}"

        if cache.exists(cache_key):
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

        # Archive
        archive_writer = create_local_archive_writer(base_dir=ARCHIVE_BASE)
        import_metadata = ImportMetadata(
            source_type="web_ingest",
            imported_at=datetime.now(),
            import_method="api",
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

        # Cache
        cache_data = {
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "transcript_length": len(transcript),
        }
        metadata = {
            "type": "youtube_video",
            "source": "web_ingest",
            "video_id": video_id,
            "imported_at": datetime.now().isoformat(),
        }
        cache.set(cache_key, cache_data, metadata=metadata)

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
    finally:
        if cache:
            cache.close()


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
    """Ingest a webpage/article using Docling."""
    import hashlib
    from compose.services.webpage import fetch_webpage
    from compose.services.cache import create_qdrant_cache

    cache = None
    try:
        cache = create_qdrant_cache(
            collection_name=QDRANT_COLLECTION,
            qdrant_url=QDRANT_URL,
            infinity_url=INFINITY_URL,
        )

        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_key = f"webpage:content:{url_hash}"

        if cache.exists(cache_key):
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

        # Cache the content
        cache_data = {
            "markdown": markdown,
            "url": url,
            "length": len(markdown),
        }
        metadata = {
            "type": "webpage",
            "source": "docling",
            "url_hash": url_hash,
            "imported_at": datetime.now().isoformat(),
        }
        cache.set(cache_key, cache_data, metadata=metadata)

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
    finally:
        if cache:
            cache.close()


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
