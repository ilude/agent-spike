"""YouTube analysis endpoints."""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models import AnalyzeVideoRequest, AnalyzeVideoResponse
from tools.services.archive import create_archive_manager, ImportMetadata, ChannelContext
from tools.services.youtube import extract_video_id, fetch_video_metadata

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeVideoResponse)
async def analyze_video(request: AnalyzeVideoRequest):
    """
    Analyze a YouTube video.

    This endpoint:
    1. Checks archive for existing data
    2. Fetches metadata from YouTube API only if needed (quota-efficient)
    3. Uses lesson-001 YouTube agent for analysis
    4. Archives results for future use
    """
    try:
        # Extract video ID from URL
        video_id = extract_video_id(str(request.url))
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Initialize archive manager
        archive = create_archive_manager()

        # Check if we have archived data
        cached = False
        metadata = None

        # Load archive if exists
        archive_path = Path(f"projects/data/archive/youtube/{datetime.now().year}-{datetime.now().month:02d}/{video_id}.json")
        if archive_path.exists():
            with open(archive_path) as f:
                archive_data = json.load(f)
                metadata = archive_data.get("youtube_metadata")
                cached = True

        # Fetch metadata if requested or not in archive
        if request.fetch_metadata or not metadata:
            try:
                metadata = fetch_video_metadata(video_id)
                cached = False
            except Exception as e:
                # If fetch fails but we have cached data, use it
                if metadata:
                    cached = True
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch metadata: {str(e)}",
                    )

        # Use lesson-001 agent for analysis
        from lessons.lesson_001.youtube_agent.agent import analyze_video as agent_analyze

        result = await agent_analyze(str(request.url))

        # Archive the results
        if not cached:
            # Update archive with metadata
            archive.update_metadata(
                video_id=video_id,
                url=str(request.url),
                youtube_metadata=metadata,
            )

        # Return response
        return AnalyzeVideoResponse(
            video_id=video_id,
            tags=result.get("tags", []),
            summary=result.get("summary", ""),
            metadata=metadata,
            cached=cached,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/metadata/{video_id}")
async def get_metadata(video_id: str):
    """Get cached metadata for a video from archive."""
    archive_path = Path(f"projects/data/archive/youtube/{datetime.now().year}-{datetime.now().month:02d}/{video_id}.json")

    if not archive_path.exists():
        raise HTTPException(status_code=404, detail="Video not found in archive")

    try:
        with open(archive_path) as f:
            archive_data = json.load(f)
            return {
                "video_id": video_id,
                "metadata": archive_data.get("youtube_metadata"),
                "transcript_available": bool(archive_data.get("raw_transcript")),
                "fetched_at": archive_data.get("fetched_at"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load metadata: {str(e)}")
