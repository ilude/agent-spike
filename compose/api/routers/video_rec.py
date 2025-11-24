"""Video recommendation endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from compose.services.surrealdb.driver import get_db

router = APIRouter()


class VideoRecResponse(BaseModel):
    """Video recommendation response."""

    video_id: str
    url: str
    title: str
    channel_id: str
    channel_name: str
    thumbnail_url: str
    duration_seconds: int
    view_count: int
    upload_date: str
    tags: list[str]
    categories: list[str]


class VideosListResponse(BaseModel):
    """List of videos response."""

    videos: list[VideoRecResponse]
    total: int
    limit: int
    offset: int


@router.get("/videos", response_model=VideosListResponse)
async def list_videos(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="upload_date", regex="^(upload_date|view_count|title)$"),
    hide_watched: bool = Query(default=False),
):
    """
    List video recommendations.

    Args:
        limit: Maximum number of videos to return (1-100)
        offset: Number of videos to skip
        sort_by: Sort field (upload_date, view_count, title)
        hide_watched: Hide videos marked as watched

    Returns:
        List of videos with pagination info
    """
    try:
        db = await get_db()

        # Build query
        query = f"""
        SELECT * FROM video_rec
        ORDER BY {sort_by} DESC
        LIMIT $limit
        START $offset
        """

        result = await db.query(query, {"limit": limit, "offset": offset})

        # Extract videos from result
        videos = []
        if result and len(result) > 0:
            videos_data = result[0].get("result", [])
            for video in videos_data:
                videos.append(
                    VideoRecResponse(
                        video_id=video.get("video_id", ""),
                        url=video.get("url", ""),
                        title=video.get("title", ""),
                        channel_id=video.get("channel_id", ""),
                        channel_name=video.get("channel_name", ""),
                        thumbnail_url=video.get("thumbnail_url", ""),
                        duration_seconds=video.get("duration_seconds", 0),
                        view_count=video.get("view_count", 0),
                        upload_date=str(video.get("upload_date", "")),
                        tags=video.get("tags", []),
                        categories=video.get("categories", []),
                    )
                )

        # Get total count
        count_query = "SELECT count() as total FROM video_rec GROUP ALL"
        count_result = await db.query(count_query)
        total = 0
        if count_result and len(count_result) > 0:
            count_data = count_result[0].get("result", [])
            if count_data and len(count_data) > 0:
                total = count_data[0].get("total", 0)

        return VideosListResponse(
            videos=videos,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch videos: {str(e)}"
        )


@router.get("/videos/{video_id}", response_model=VideoRecResponse)
async def get_video(video_id: str):
    """Get single video by ID."""
    try:
        db = await get_db()

        query = "SELECT * FROM video_rec WHERE video_id = $video_id LIMIT 1"
        result = await db.query(query, {"video_id": video_id})

        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

        videos = result[0].get("result", [])
        if not videos or len(videos) == 0:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

        video = videos[0]
        return VideoRecResponse(
            video_id=video.get("video_id", ""),
            url=video.get("url", ""),
            title=video.get("title", ""),
            channel_id=video.get("channel_id", ""),
            channel_name=video.get("channel_name", ""),
            thumbnail_url=video.get("thumbnail_url", ""),
            duration_seconds=video.get("duration_seconds", 0),
            view_count=video.get("view_count", 0),
            upload_date=str(video.get("upload_date", "")),
            tags=video.get("tags", []),
            categories=video.get("categories", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch video: {str(e)}"
        )
