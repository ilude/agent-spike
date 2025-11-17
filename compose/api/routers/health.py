"""Health check endpoints."""

import os
from pathlib import Path

from fastapi import APIRouter
from compose.api.models import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check overall service health."""
    checks = {
        "archive": await check_archive(),
        "cache": await check_cache(),
    }

    # Determine overall status
    all_ok = all(check["status"] == "ok" for check in checks.values())
    status = "ok" if all_ok else "degraded"

    return HealthCheckResponse(status=status, checks=checks)


async def check_archive() -> dict:
    """Check if archive directory is accessible."""
    try:
        archive_path = Path("platform/data/archive/youtube")
        exists = archive_path.exists()
        writable = os.access(archive_path, os.W_OK) if exists else False

        if not exists:
            return {
                "status": "error",
                "message": "Archive directory does not exist",
                "path": str(archive_path.absolute()),
            }

        if not writable:
            return {
                "status": "error",
                "message": "Archive directory is not writable",
                "path": str(archive_path.absolute()),
            }

        # Count archived videos
        video_count = len(list(archive_path.glob("**/*.json")))

        return {
            "status": "ok",
            "message": f"Archive accessible with {video_count} videos",
            "path": str(archive_path.absolute()),
        }
    except Exception as e:
        return {"status": "error", "message": f"Archive check failed: {str(e)}"}


async def check_cache() -> dict:
    """Check if Qdrant cache is accessible."""
    try:
        from compose.services.cache import create_qdrant_cache

        cache = create_qdrant_cache()

        # Try a simple operation
        cache.exists("test-key")

        return {"status": "ok", "message": "Qdrant cache accessible"}
    except Exception as e:
        return {"status": "error", "message": f"Cache check failed: {str(e)}"}
