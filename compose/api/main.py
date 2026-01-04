"""FastAPI application for exposing Python agents and chat interface."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compose.api.middleware import CorrelationMiddleware, HTTPServerMetricsMiddleware
from compose.api.routers import health, youtube, cache, chat, stats, ingest, conversations, projects, artifacts, styles, memory, websearch, sandbox, imagegen, auth, settings, backup, telemetry, vaults, studio_notes, graph
from compose.lib.telemetry import setup_telemetry

# Setup telemetry BEFORE creating app so meter provider is available for middleware
TELEMETRY_ENABLED = bool(os.getenv("OTLP_ENDPOINT") or os.getenv("ENABLE_TELEMETRY", "").lower() == "true")
if TELEMETRY_ENABLED:
    setup_telemetry("agent-spike-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield


# Create FastAPI app
app = FastAPI(
    title="Agent Spike API",
    description="FastAPI service with chat interface and agent integration",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS configuration for frontend and N8N
CORS_ORIGINS = [
    "http://localhost:5173",    # Vite dev server
    "http://127.0.0.1:5173",
    "http://frontend:5173",     # Docker container
    "http://localhost:8000",
    "*",                        # N8N and other integrations
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID middleware for request tracking
app.add_middleware(CorrelationMiddleware)

# HTTP server metrics middleware (only if telemetry enabled)
if TELEMETRY_ENABLED:
    app.add_middleware(HTTPServerMetricsMiddleware, service_name="agent-spike-api")

# Include routers
app.include_router(health.router)
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(cache.router, prefix="/cache", tags=["cache"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(stats.router, tags=["stats"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(conversations.router, tags=["conversations"])
app.include_router(projects.router, tags=["projects"])
app.include_router(artifacts.router, tags=["artifacts"])
app.include_router(styles.router, tags=["styles"])
app.include_router(memory.router, tags=["memory"])
app.include_router(websearch.router, tags=["search"])
app.include_router(sandbox.router, tags=["sandbox"])
app.include_router(imagegen.router, tags=["imagegen"])
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(backup.router)
app.include_router(telemetry.router)

# Mentat Studio routers
app.include_router(vaults.router, tags=["studio"])
app.include_router(studio_notes.router, tags=["studio"])
app.include_router(graph.router, tags=["studio"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agent Spike API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "youtube_analyze": "POST /youtube/analyze",
            "cache_search": "POST /cache/search",
            "chat_models": "GET /chat/models",
            "chat_random": "GET /chat/random-question",
            "chat_ws": "WS /chat/ws/chat",
            "chat_rag_ws": "WS /chat/ws/rag-chat",
            "ingest": "POST /ingest",
            "ingest_detect": "GET /ingest/detect",
            "conversations_list": "GET /conversations",
            "conversations_create": "POST /conversations",
            "conversations_get": "GET /conversations/{id}",
            "conversations_search": "GET /conversations/search?q=",
            "projects_list": "GET /projects",
            "projects_create": "POST /projects",
            "projects_get": "GET /projects/{id}",
            "projects_files": "POST /projects/{id}/files",
            "artifacts_list": "GET /artifacts",
            "artifacts_create": "POST /artifacts",
            "artifacts_get": "GET /artifacts/{id}",
            "styles_list": "GET /styles",
            "styles_get": "GET /styles/{id}",
            "memory_list": "GET /memory",
            "memory_add": "POST /memory",
            "memory_search": "GET /memory/search?q=",
            "memory_get": "GET /memory/{id}",
            "memory_update": "PUT /memory/{id}",
            "memory_delete": "DELETE /memory/{id}",
            "memory_clear": "DELETE /memory",
            "websearch": "GET /search?q=",
            "freedium_check": "GET /search/freedium?url=",
            "freedium_fetch": "POST /search/freedium",
            "sandbox_languages": "GET /sandbox/languages",
            "sandbox_execute": "POST /sandbox/execute",
            "sandbox_validate": "POST /sandbox/validate",
            "imagegen_options": "GET /imagegen/options",
            "imagegen_generate": "POST /imagegen/generate",
            "imagegen_list": "GET /imagegen/images",
        },
    }
