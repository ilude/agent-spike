"""Stats API router with SSE for real-time dashboard updates."""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["stats"])

# Configuration
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8000")
MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
WEBSHARE_API_TOKEN = os.getenv("WEBSHARE_API_TOKEN", "")
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

    # Read progress file if it exists (supports both old and new format)
    progress_file = QUEUE_BASE / ".progress.json"
    active_workers = []
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                progress_data = json.load(f)
                # New format: {"workers": [...]}
                if "workers" in progress_data:
                    active_workers = progress_data["workers"]
                # Old format: single object with filename/completed/total
                elif "filename" in progress_data:
                    active_workers = [progress_data]
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "pending_count": len(pending_files),
        "pending_files": [f.name for f in pending_files],
        "processing_count": len(processing_files),
        "processing_files": [f.name for f in processing_files],
        "completed_count": len(completed_files),
        "completed_files": [f.name for f in completed_files[-5:]],  # Last 5
        "active_workers": active_workers,  # List of worker progress objects
    }


async def get_cache_stats() -> dict:
    """Get SurrealDB cache statistics with breakdown by content type."""
    try:
        from compose.services.surrealdb import (
            get_video_count,
        )

        total = await get_video_count()

        # SurrealDB stores all videos; articles are in archive via MinIO
        videos_count = total
        articles_count = 0

        return {
            "status": "ok",
            "total": total,
            "videos": videos_count,
            "articles": articles_count,
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


async def get_webshare_stats() -> dict:
    """Get Webshare proxy bandwidth usage stats."""
    if not WEBSHARE_API_TOKEN:
        return {"status": "unavailable", "message": "API token not configured"}

    headers = {"Authorization": f"Token {WEBSHARE_API_TOKEN}"}
    base_url = "https://proxy.webshare.io/api/v2"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get subscription info for billing period
            sub_resp = await client.get(f"{base_url}/subscription/", headers=headers)
            if sub_resp.status_code != 200:
                return {"status": "error", "message": f"Subscription API error: {sub_resp.status_code}"}
            sub_data = sub_resp.json()

            # Get plan info for bandwidth limit
            plan_resp = await client.get(f"{base_url}/subscription/plan/", headers=headers)
            if plan_resp.status_code != 200:
                return {"status": "error", "message": f"Plan API error: {plan_resp.status_code}"}
            plan_data = plan_resp.json()

            # Get bandwidth limit (0 means unlimited)
            bandwidth_limit_gb = plan_data.get("bandwidth_limit", 0)
            is_unlimited = bandwidth_limit_gb == 0

            # Get billing period start date
            start_date = sub_data.get("start_date", "")
            if start_date:
                # Format: 2024-01-15T00:00:00Z -> use for aggregate query
                start_timestamp = start_date
            else:
                # Fallback: use 30 days ago
                from datetime import timedelta
                start_dt = datetime.now(timezone.utc) - timedelta(days=30)
                start_timestamp = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Get current timestamp for end of range
            now_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Get aggregate bandwidth stats for billing period
            stats_url = f"{base_url}/stats/aggregate/"
            stats_params = {
                "timestamp__gte": start_timestamp,
                "timestamp__lte": now_timestamp,
            }
            stats_resp = await client.get(stats_url, headers=headers, params=stats_params)
            if stats_resp.status_code != 200:
                return {"status": "error", "message": f"Stats API error: {stats_resp.status_code}"}
            stats_data = stats_resp.json()

            # bandwidth_total is in bytes, convert to GB
            bandwidth_bytes = stats_data.get("bandwidth_total", 0)
            used_gb = bandwidth_bytes / (1024**3)

            result = {
                "status": "ok",
                "used_gb": round(used_gb, 3),
                "is_unlimited": is_unlimited,
                "billing_period_start": start_date[:10] if start_date else None,
            }

            if not is_unlimited:
                result["total_gb"] = bandwidth_limit_gb
                result["remaining_gb"] = round(bandwidth_limit_gb - used_gb, 3)
                result["percent_used"] = round((used_gb / bandwidth_limit_gb) * 100, 1) if bandwidth_limit_gb > 0 else 0

            return result

    except httpx.TimeoutException:
        return {"status": "error", "message": "Webshare API timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def is_local_url(url: str) -> bool:
    """Check if URL points to a local service."""
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"]
    # Also treat docker service names as local (same compose network)
    docker_services = ["surrealdb", "minio", "infinity", "api", "frontend", "docling"]
    for host in local_hosts + docker_services:
        if host in url.lower():
            return True
    return False


async def get_service_health() -> dict:
    """Check health of dependent services."""
    surrealdb_ok = False
    minio_ok = False
    infinity_ok = False
    ollama_ok = False
    queue_worker_ok = False
    n8n_ok = False
    docling_ok = False

    # Check SurrealDB
    try:
        from compose.services.surrealdb import verify_connection
        await verify_connection()
        surrealdb_ok = True
    except Exception:
        pass

    # Check MinIO
    try:
        from compose.services.minio import create_minio_client
        client = create_minio_client()
        client.ensure_bucket()
        minio_ok = True
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

    # Check n8n (workflow automation) - remote server
    n8n_url = os.getenv("N8N_URL", "http://192.168.16.241:5678")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{n8n_url}/healthz")
            n8n_ok = response.status_code == 200
    except Exception:
        pass

    # Check Docling (document processing) - remote server
    docling_url = os.getenv("DOCLING_URL", "http://192.168.16.241:5001")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{docling_url}/health")
            docling_ok = response.status_code == 200
    except Exception:
        pass

    return {
        "surrealdb": {"ok": surrealdb_ok, "local": is_local_url(SURREALDB_URL)},
        "minio": {"ok": minio_ok, "local": is_local_url(MINIO_URL)},
        "infinity": {"ok": infinity_ok, "local": is_local_url(INFINITY_URL)},
        "ollama": {"ok": ollama_ok, "local": is_local_url(ollama_url)},
        "queue_worker": {"ok": queue_worker_ok, "local": True},
        "n8n": {"ok": n8n_ok, "local": is_local_url(n8n_url)},
        "docling": {"ok": docling_ok, "local": is_local_url(docling_url)},
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
                "cache": await get_cache_stats(),
                "archive": get_archive_stats(),
                "health": await get_service_health(),
                "recent_activity": get_recent_activity(),
                "webshare": await get_webshare_stats(),
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
        "cache": await get_cache_stats(),
        "archive": get_archive_stats(),
        "health": await get_service_health(),
        "recent_activity": get_recent_activity(),
        "webshare": await get_webshare_stats(),
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
