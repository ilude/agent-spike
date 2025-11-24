# Streaming Architecture

**Created**: 2025-01-24
**Purpose**: Document the SSE streaming patterns used in this project for real-time progress feedback.

---

## Overview

This document describes the Server-Sent Events (SSE) streaming architecture used for real-time progress updates. The initial implementation supports video ingestion progress, but the pattern is designed to be extensible for future use cases like agent activity monitoring.

## Current Implementation: Ingest Streaming

### Backend Endpoint

**File**: `compose/api/routers/ingest.py`

**Endpoint**: `POST /ingest/stream`

Streams progress events as a video/channel/article is ingested:

```python
@router.post("/ingest/stream")
async def ingest_url_stream(request: IngestRequest):
    """SSE streaming endpoint for URL ingestion with real-time progress."""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
```

### Event Format

Events follow standard SSE format with named events:

```
event: progress
data: {"step": "fetching_transcript", "message": "Fetching transcript from YouTube..."}

event: progress
data: {"step": "transcript_fetched", "message": "Transcript fetched (4,521 chars)", "transcript_length": 4521}

event: progress
data: {"step": "archiving", "message": "Archiving to storage..."}

event: complete
data: {"type": "video", "status": "success", "message": "Ingested video: abc123", "details": {...}}
```

### Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `progress` | Step update during processing | `{step, message, ...extras}` |
| `complete` | Final result (success/error/skipped) | `IngestResponse` model |

### Progress Steps (Video Ingest)

1. `extracting_id` - Parsing URL for video ID
2. `extracted_id` - Video ID extracted
3. `checking_cache` - Checking if already in database
4. `fetching_transcript` - Downloading from YouTube
5. `transcript_fetched` - Transcript received
6. `archiving` - Saving to archive storage
7. `archived` - Archive complete
8. `storing` - Saving to SurrealDB
9. `stored` - Database record created

### Active Ingest Tracking

Active ingests are tracked in memory for stats integration:

```python
# In ingest.py
_active_ingests: dict[str, dict] = {}

def get_active_ingests() -> list[dict]:
    """Get list of active ingests for stats integration."""
    ...

def get_active_ingest_count() -> int:
    """Get count of active ingests."""
    ...
```

The stats endpoint (`/stats/stream`) includes active ingests in its `processing_count`.

### Frontend Client

**File**: `compose/frontend/src/lib/api.js`

```javascript
/**
 * Ingest a URL with real-time progress streaming (SSE)
 * @param {string} url - URL to ingest
 * @param {string} channelLimit - For channels: 'month', 'year', '50', '100', 'all'
 * @param {function} onProgress - Callback for progress events
 * @param {function} onComplete - Callback for completion
 * @param {function} onError - Callback for errors
 */
async ingestUrlStream(url, channelLimit, onProgress, onComplete, onError) {
    const res = await fetch(`${this.baseURL}/ingest/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, channel_limit: channelLimit })
    });

    // Read SSE stream using ReadableStream API
    const reader = res.body.getReader();
    // ... parse events and call callbacks
}
```

---

## Extending for Agent Monitoring

The SSE pattern can be extended for multi-agent activity monitoring. Here's the recommended approach:

### Potential Event Format

```json
{
  "stream": "agent",
  "source_id": "coordinator_abc123",
  "event": "progress",
  "timestamp": "2025-01-24T12:34:56Z",
  "payload": {
    "agent_name": "tagger",
    "status": "running",
    "message": "Processing video 5/10",
    "progress": 0.5
  }
}
```

### Implementation Steps

1. **Create agent activity tracker** (similar to `_active_ingests`):
   ```python
   # compose/services/agents/activity.py
   _agent_activities: dict[str, AgentActivity] = {}

   def register_activity(agent_id: str, activity: AgentActivity): ...
   def update_activity(agent_id: str, status: str, message: str): ...
   def complete_activity(agent_id: str, result: Any): ...
   ```

2. **Create SSE endpoint for agent streams**:
   ```python
   @router.get("/agents/stream")
   async def agent_activity_stream():
       """SSE stream of agent activities."""
       ...
   ```

3. **Integrate with orchestrator**:
   - Agents call `register_activity()` when starting
   - Emit progress events during processing
   - Call `complete_activity()` when done

4. **Frontend subscription**:
   ```javascript
   api.connectAgentStream((activity) => {
       // Update UI with agent status
   });
   ```

### Design Considerations

- **Stateless agents**: Activity tracking should be in-memory with graceful degradation
- **Multiple streams**: Consider using a message broker (Redis pub/sub) for scaling
- **Heartbeats**: Add periodic heartbeat events for connection monitoring
- **Filtering**: Allow clients to subscribe to specific agent types or IDs

---

## Files Reference

| File | Purpose |
|------|---------|
| `compose/api/routers/ingest.py` | SSE streaming endpoint, active ingest tracking |
| `compose/api/routers/stats.py` | Integrates active ingests into stats |
| `compose/frontend/src/lib/api.js` | `ingestUrlStream()` client method |
| `compose/frontend/src/routes/+page.svelte` | Progress UI display |

---

## See Also

- `.claude/VISION.md` - Multi-agent system architecture plans
- `compose/api/routers/stats.py` - Existing SSE stats stream pattern
