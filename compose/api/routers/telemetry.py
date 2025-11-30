"""OTLP proxy endpoint for frontend telemetry."""

import os

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["telemetry"])

OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://192.168.16.241:4318")


@router.post("/v1/traces")
async def proxy_traces(request: Request):
    """Proxy OTLP traces from browser to collector.

    The frontend sends traces to this endpoint, which forwards them
    to the OTEL collector. This avoids CORS issues with direct
    browser-to-collector communication.
    """
    body = await request.body()
    content_type = request.headers.get("Content-Type", "application/x-protobuf")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{OTLP_ENDPOINT}/v1/traces",
                content=body,
                headers={"Content-Type": content_type},
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.RequestError as e:
            return Response(
                content=f"Failed to forward traces: {e}".encode(),
                status_code=502,
            )


@router.post("/v1/metrics")
async def proxy_metrics(request: Request):
    """Proxy OTLP metrics from browser to collector."""
    body = await request.body()
    content_type = request.headers.get("Content-Type", "application/x-protobuf")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{OTLP_ENDPOINT}/v1/metrics",
                content=body,
                headers={"Content-Type": content_type},
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.RequestError as e:
            return Response(
                content=f"Failed to forward metrics: {e}".encode(),
                status_code=502,
            )
