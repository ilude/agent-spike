"""Stats API router with SSE for real-time dashboard updates."""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from qdrant_client import QdrantClient

router = APIRouter(tags=["stats"])

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "content")
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")

# Queue paths (container paths - data mounted at /app/src/compose/data)
QUEUE_BASE = Path(os.getenv("QUEUE_BASE", "/app/src/compose/data/queues"))
ARCHIVE_BASE = Path(os.getenv("ARCHIVE_BASE", "/app/src/compose/data/archive"))


def get_queue_stats() -> dict:
    """Get queue directory statistics."""
    pending_dir = QUEUE_BASE / "pending"
    processing_dir = QUEUE_BASE / "processing"
    completed_dir = QUEUE_BASE / "completed"

    pending_files = list(pending_dir.glob("*.csv")) if pending_dir.exists() else []
    processing_files = list(processing_dir.glob("*.csv")) if processing_dir.exists() else []
    completed_files = list(completed_dir.glob("*.csv")) if completed_dir.exists() else []

    # Read progress file if it exists
    progress_file = QUEUE_BASE / ".progress.json"
    current_progress = None
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                current_progress = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "pending_count": len(pending_files),
        "pending_files": [f.name for f in pending_files],
        "processing_count": len(processing_files),
        "processing_files": [f.name for f in processing_files],
        "completed_count": len(completed_files),
        "completed_files": [f.name for f in completed_files[-5:]],  # Last 5
        "current_progress": current_progress,
    }


def get_cache_stats() -> dict:
    """Get Qdrant cache statistics with breakdown by content type."""
    try:
        client = QdrantClient(url=QDRANT_URL)
        collection = client.get_collection(QDRANT_COLLECTION)
        total = collection.points_count

        # Try to get breakdown by type, but don't fail if it doesn't work
        videos_count = 0
        articles_count = 0

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Count videos
            videos_result = client.count(
                collection_name=QDRANT_COLLECTION,
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="youtube_video"))]
                ),
            )
            videos_count = videos_result.count

            # Count articles/webpages
            articles_result = client.count(
                collection_name=QDRANT_COLLECTION,
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="webpage"))]
                ),
            )
            articles_count = articles_result.count
        except Exception:
            # If count filters fail, estimate from total
            videos_count = total
            articles_count = 0

        return {
            "status": "ok",
            "total": total,
            "videos": videos_count,
            "articles": articles_count,
            "collection_name": QDRANT_COLLECTION,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "total": 0,
            "videos": 0,
            "articles": 0,
        }


def get_archive_stats() -> dict:
    """Get archive file statistics."""
    youtube_dir = ARCHIVE_BASE / "youtube"

    if not youtube_dir.exists():
        return {"total_videos": 0, "by_month": {}}

    by_month = {}
    total = 0

    for month_dir in youtube_dir.iterdir():
        if month_dir.is_dir():
            count = len(list(month_dir.glob("*.json")))
            by_month[month_dir.name] = count
            total += count

    return {
        "total_videos": total,
        "by_month": dict(sorted(by_month.items(), reverse=True)),
    }


def is_local_url(url: str) -> bool:
    """Check if URL points to a local service."""
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"]
    # Also treat docker service names as local (same compose network)
    docker_services = ["qdrant", "infinity", "api", "frontend", "docling"]
    for host in local_hosts + docker_services:
        if host in url.lower():
            return True
    return False


async def get_service_health() -> dict:
    """Check health of dependent services."""
    qdrant_ok = False
    infinity_ok = False
    ollama_ok = False
    queue_worker_ok = False

    # Check Qdrant
    try:
        client = QdrantClient(url=QDRANT_URL)
        client.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    # Check Infinity
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{INFINITY_URL}/health")
            infinity_ok = response.status_code == 200
    except Exception:
        pass

    # Check Ollama
    ollama_url = os.getenv("OLLAMA_URL", "http://192.168.16.241:11434")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            ollama_ok = response.status_code == 200
    except Exception:
        pass

    # Check Queue Worker (via progress file or queue activity)
    try:
        progress_file = QUEUE_BASE / ".progress.json"
        processing_dir = QUEUE_BASE / "processing"
        # Worker is "ok" if progress file exists (actively processing) or processing dir has files
        if progress_file.exists():
            queue_worker_ok = True
        elif processing_dir.exists() and list(processing_dir.glob("*.csv")):
            queue_worker_ok = True
        else:
            # Check if worker is idle but healthy (no work to do)
            pending_dir = QUEUE_BASE / "pending"
            if pending_dir.exists():
                queue_worker_ok = True  # Dirs exist = worker is set up
    except Exception:
        pass

    return {
        "qdrant": {"ok": qdrant_ok, "local": is_local_url(QDRANT_URL)},
        "infinity": {"ok": infinity_ok, "local": is_local_url(INFINITY_URL)},
        "ollama": {"ok": ollama_ok, "local": is_local_url(ollama_url)},
        "queue_worker": {"ok": queue_worker_ok, "local": True},  # Always local (same compose)
    }


def get_recent_activity() -> list:
    """Get recent activity from completed queue files and archive."""
    completed_dir = QUEUE_BASE / "completed"
    if not completed_dir.exists():
        return []

    # Get recently modified completed files
    files = sorted(completed_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)

    activity = []
    for f in files[:3]:  # Last 3 files
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        activity.append({
            "type": "queue_completed",
            "file": f.name,
            "timestamp": mtime.isoformat(),
        })

    return activity


async def generate_stats():
    """Generate stats as SSE stream."""
    while True:
        try:
            stats = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "queue": get_queue_stats(),
                "cache": get_cache_stats(),
                "archive": get_archive_stats(),
                "health": await get_service_health(),
                "recent_activity": get_recent_activity(),
            }
            yield f"data: {json.dumps(stats)}\n\n"
        except Exception as e:
            error_data = {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            yield f"data: {json.dumps(error_data)}\n\n"

        await asyncio.sleep(3)  # Update every 3 seconds


@router.get("/stats")
async def get_stats():
    """Get current stats (one-time fetch)."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue": get_queue_stats(),
        "cache": get_cache_stats(),
        "archive": get_archive_stats(),
        "health": await get_service_health(),
        "recent_activity": get_recent_activity(),
    }


@router.get("/stats/stream")
async def stats_stream():
    """SSE endpoint for real-time stats updates."""
    return StreamingResponse(
        generate_stats(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
