# Product Requirements Document: Mentat UI

**Status**: Archived / Superseded
**Last Updated**: 2025-11-18
**Original Development Period**: November 2025

## Executive Summary

Mentat UI was a proposed **chat-based web interface** for interacting with cached content (YouTube transcripts, webpages) stored in the agent-spike project's Qdrant vector database. The project was explored during early development but was **abandoned in favor of a CLI-first, microservices architecture** and the broader "Personal AI Research Assistant" vision.

This PRD documents the original design discussions, technical architecture, and lessons learned for historical reference and potential future web UI development.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Target Users](#target-users)
4. [Technical Architecture](#technical-architecture)
5. [Feature Requirements](#feature-requirements)
6. [User Experience Design](#user-experience-design)
7. [Integration Points](#integration-points)
8. [Security & Privacy](#security--privacy)
9. [Open Questions & Decisions](#open-questions--decisions)
10. [Why It Was Abandoned](#why-it-was-abandoned)
11. [What Survived](#what-survived)
12. [Lessons Learned](#lessons-learned)

---

## 1. Project Overview

### Vision

Create a lightweight, localhost-only chat interface where users can ask questions about their cached research materials (YouTube videos, articles, etc.) and receive AI-generated responses with relevant source citations.

### Goals

- **Accessibility**: Make cached content searchable through natural language
- **Real-time interaction**: Stream AI responses token-by-token for perceived speed
- **Context-aware**: Use RAG (Retrieval-Augmented Generation) to ground responses in actual cached content
- **Privacy-first**: Run entirely on localhost with no external data sharing

### Non-Goals

- Public deployment or multi-user support
- Mobile app or responsive design (desktop-focused)
- Advanced chat features (history, threads, sharing)
- Production-grade security or authentication

---

## 2. Problem Statement

### User Pain Points

1. **Scattered research materials**: YouTube transcripts and saved webpages are hard to search manually
2. **No semantic search**: File names and tags aren't enough to find relevant content
3. **Context switching**: Jumping between browser tabs to find information is inefficient
4. **No synthesis**: Want AI to connect ideas across multiple sources

### Proposed Solution

A chat interface that:
- Queries the Qdrant vector database for semantically relevant content
- Uses LLM to synthesize answers from retrieved sources
- Streams responses in real-time for better UX
- Provides source citations for fact-checking

---

## 3. Target Users

### Primary User Persona

**"Developer Researcher"**
- Software engineer learning new technologies
- Saves YouTube tutorials and articles to Qdrant
- Works primarily in terminal/IDE but wants quick web access
- Values privacy and localhost-only tools

### User Scenarios

1. **Quick lookup**: "What did that video say about Docker networking?"
2. **Cross-source synthesis**: "Summarize all my saved content about AI agents"
3. **Fact-checking**: "Which videos mentioned Pydantic AI's memory features?"

---

## 4. Technical Architecture

### 4.1 Backend (FastAPI)

**Location**: `projects/mentat/api/main.py` (no longer exists)

#### Core Technologies

- **Framework**: FastAPI (async Python web framework)
- **WebSockets**: For real-time streaming chat
- **LLM Provider**: OpenRouter (multi-model proxy)
- **Vector DB**: Qdrant (semantic search over cached content)
- **Package Manager**: uv (fast Python dependency management)

#### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check with diagnostics |
| `/ws/chat` | WebSocket | Streaming chat interface |

#### WebSocket Protocol

**Client → Server**:
```json
{
  "message": "user question here"
}
```

**Server → Client (streaming)**:
```json
{"type": "token", "content": "word"}
{"type": "token", "content": "by"}
{"type": "token", "content": "word"}
{"type": "done", "sources": [{"title": "...", "url": "..."}]}
```

#### Environment Configuration

```bash
# Required environment variables
OPENROUTER_API_KEY=sk-or-v1-...  # LLM access
# Qdrant runs on localhost:6333 (Docker container)
```

#### Security Model

```python
# CORS restricted to localhost only
allowed_origins = [
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",
]
```

#### Error Handling

- **Empty messages**: `{"error": "Message cannot be empty"}`
- **Too long messages**: Max 10,000 characters
- **API key missing**: Fails on startup with clear error
- **Connection failures**: WebSocket sends `{"type": "error", ...}`

### 4.2 Frontend (Planned but Not Implemented)

**Expected Location**: `projects/mentat/web/`

#### Proposed Tech Stack

- **Build Tool**: Vite (dev server on port 5173)
- **Framework**: React or Vue (not decided)
- **Styling**: Likely Tailwind CSS + shadcn/ui
- **WebSocket Client**: Native browser WebSocket API

#### Expected File Structure

```
projects/mentat/web/
├── package.json
├── vite.config.js
├── index.html
└── src/
    ├── App.jsx
    ├── components/
    │   ├── ChatWindow.jsx
    │   ├── MessageInput.jsx
    │   └── SourceCitation.jsx
    └── hooks/
        └── useWebSocket.js
```

**Note**: No actual frontend code was implemented.

### 4.3 Infrastructure

#### Development Environment

```bash
# Backend startup
cd projects/mentat
uv run uvicorn api.main:app --reload --port 8001

# Frontend startup (planned)
cd projects/mentat/web
npm run dev  # Vite dev server on port 5173
```

#### Project Structure

```
projects/mentat/
├── api/
│   ├── __init__.py
│   └── main.py          # FastAPI app
├── web/                 # Frontend (never implemented)
├── tests/               # Test suite
├── logs/                # Application logs
├── Makefile             # Build automation
└── README.md            # Documentation
```

#### Docker/Containerization

**Not containerized** in initial implementation. Would have run via:
- Backend: `uv run uvicorn`
- Frontend: `npm run dev`
- Qdrant: Existing Docker container (`compose/docker-compose.yml`)

---

## 5. Feature Requirements

### 5.1 MVP Features (What Was Implemented)

#### ✅ Health Check Endpoint

```python
GET /health
Response: {
    "status": "ok",
    "timestamp": "2025-11-18T12:00:00",
    "api_key_configured": true
}
```

**Purpose**: Verify backend is running and API keys are loaded

#### ✅ WebSocket Chat (Basic)

```python
WS /ws/chat
- Accepts user messages
- Streams LLM responses token-by-token
- No RAG (just passes message to OpenRouter)
```

**Limitations**: "This is the minimal spike implementation. **Iteration 2 will add RAG**."

### 5.2 Planned Features (Never Implemented)

#### ❌ RAG (Retrieval-Augmented Generation)

**Design**:
1. User sends message via WebSocket
2. Backend queries Qdrant for top 5 relevant chunks
3. Constructs prompt: `"Context: {retrieved_content}\n\nQuestion: {user_message}"`
4. LLM generates response using context
5. Returns response + source citations

**Why not implemented**: Project abandoned before Iteration 2

#### ❌ Chat History

**Design**: Store conversations in local SQLite database

**Schema**:
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP,
    messages JSON  -- Array of {role, content, sources}
);
```

**Why not implemented**: Ephemeral sessions deemed sufficient for MVP

#### ❌ Source Citations UI

**Design**: Show source cards below each AI response

**Mockup**:
```
AI: Based on your cached content, Docker networking...

Sources:
┌───────────────────────────────────┐
│ 🎥 Docker Networking Basics       │
│ youtu.be/abc123 • 12:34          │
└───────────────────────────────────┘
┌───────────────────────────────────┐
│ 📄 Container Networking Guide     │
│ example.com/article • Saved Nov 1│
└───────────────────────────────────┘
```

**Why not implemented**: No frontend built

---

## 6. User Experience Design

### 6.1 Interface Layout

**Planned Design** (never implemented):

```
┌─────────────────────────────────────────────┐
│ Mentat Chat                          [━][□][✕]│
├─────────────────────────────────────────────┤
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ AI: How can I help you search      │    │
│  │     your cached content?            │    │
│  └────────────────────────────────────┘    │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ You: What did I save about agents? │    │
│  └────────────────────────────────────┘    │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ AI: You have 3 videos about agents...│ │
│  │ [Source citations here]             │    │
│  └────────────────────────────────────┘    │
│                                             │
├─────────────────────────────────────────────┤
│ Type your question...            [Send]    │
└─────────────────────────────────────────────┘
```

### 6.2 Interaction Patterns

#### Real-Time Streaming

**Visual feedback**:
- Blinking cursor while waiting for first token
- Words appear as they're generated (typewriter effect)
- "Thinking..." indicator during retrieval phase

#### Error States

| Error | User Message | Technical Detail |
|-------|--------------|------------------|
| Empty message | "Please type a message" | Client-side validation |
| Too long | "Message too long (max 10K chars)" | Server-side validation |
| Connection lost | "Connection lost. Reconnecting..." | WebSocket disconnect |
| API error | "Something went wrong. Try again." | Generic server error |

### 6.3 Performance Requirements

- **First token latency**: < 2 seconds (depends on OpenRouter)
- **Streaming speed**: Real-time as tokens arrive
- **UI responsiveness**: < 100ms for user input

### 6.4 Accessibility

**Not explicitly designed** in chat history. For future reference:
- Keyboard navigation (Tab, Enter to send)
- Screen reader support (ARIA labels)
- High contrast mode (respect system preferences)

---

## 7. Integration Points

### 7.1 OpenRouter API

**Purpose**: LLM proxy supporting multiple models

**Configuration**:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
```

**Why OpenRouter?**
- Model flexibility (Claude, GPT, Llama, etc.)
- Single API for multiple providers
- Streaming support

**Trade-offs**:
- Additional latency vs. direct Anthropic/OpenAI
- Requires separate API key
- Third-party dependency

### 7.2 Qdrant Vector Database

**Purpose**: Semantic search over cached content

**Connection** (planned):
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Search for relevant content
results = client.search(
    collection_name="cached_content",
    query_vector=embed_query(user_message),
    limit=5,
)
```

**Why not implemented**: Project abandoned before RAG iteration

### 7.3 Environment Management

**Uses centralized environment loader**:
```python
from tools.env_loader import load_root_env

load_root_env()  # Loads .env from git root
```

**Benefits**:
- Single source of truth for API keys
- Git-crypt encryption for secrets
- Shared across all project services

### 7.4 Data Flow Diagram

```
┌──────────┐
│ Frontend │ (never built)
│ (Vite)   │
└────┬─────┘
     │ WebSocket (localhost:8001/ws/chat)
     ▼
┌──────────────────┐
│ FastAPI Backend  │
│ (uvicorn)        │
└────┬────────┬────┘
     │        │
     │        └──► Qdrant (localhost:6333)
     │             [semantic search - planned]
     │
     └──► OpenRouter API
          (https://openrouter.ai/api/v1)
          [LLM responses]
```

---

## 8. Security & Privacy

### 8.1 Threat Model

**Assumptions**:
- Single user on trusted localhost machine
- No public internet exposure
- User controls all data (personal research materials)

**Out of Scope**:
- Multi-user authentication
- Public deployment
- API rate limiting
- Malicious input sanitization (beyond basic validation)

### 8.2 Security Measures

#### CORS Restrictions

```python
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

**Purpose**: Prevent cross-origin requests from other websites

#### Input Validation

```python
# Max message length
MAX_MESSAGE_LENGTH = 10_000

# Empty message check
if not message.strip():
    raise ValueError("Empty message")
```

**Purpose**: Prevent DoS via extremely long messages

#### API Key Protection

- Stored in `.env` (git-crypt encrypted)
- Never logged or exposed in responses
- Validated on startup (fail-fast if missing)

### 8.3 Privacy Considerations

**Data Storage**:
- No chat history persisted (ephemeral WebSocket sessions)
- All user data stays on localhost
- Qdrant database is local (not cloud-hosted)

**Third-Party Data Sharing**:
- OpenRouter receives user messages and LLM responses
  - **Privacy risk**: User queries sent to third party
  - **Mitigation**: Use direct Anthropic/OpenAI APIs instead (not implemented)

---

## 9. Open Questions & Decisions

### 9.1 Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Frontend framework?** | Likely React/Vue (not confirmed) | Vite dev server suggests modern framework |
| **LLM provider?** | OpenRouter | Model flexibility vs. vendor lock-in |
| **Streaming approach?** | WebSocket | Better than SSE for bidirectional chat |
| **Security model?** | Localhost-only | Single-user tool, no auth needed |
| **Port allocation?** | Backend: 8001, Frontend: 5173 | Avoid conflicts with other services |
| **Package manager?** | uv | Consistency with rest of project |

### 9.2 Unresolved Questions

#### Why OpenRouter Instead of Direct APIs?

**Pros**:
- Model flexibility (switch between Claude, GPT, etc.)
- Single API client for multiple providers
- Cost transparency (OpenRouter shows per-model pricing)

**Cons**:
- Additional latency (proxy overhead)
- Privacy concerns (third-party sees all messages)
- Extra API key to manage

**Alternative**: Use direct Anthropic/OpenAI clients (current project uses this approach)

#### What Happened to the Mentat Directory?

**Evidence**:
- Chat logs reference `projects/mentat/api/main.py`
- Directory no longer exists in current codebase
- No git history of deletion (likely manual cleanup)

**Hypothesis**:
- Merged into `compose/` microservices architecture
- Abandoned in favor of CLI-first tools
- Code possibly lost or uncommitted

---

## 10. Why It Was Abandoned

### 10.1 Evidence from Project Evolution

**Before Mentat**:
```
lessons/lesson-007/  # Cache Manager with Qdrant
└── Cache interactions via Python CLI
```

**During Mentat Exploration**:
```
projects/mentat/
├── api/main.py      # WebSocket chat backend
└── web/             # Planned but never built
```

**After Mentat (Current State)**:
```
compose/
├── services/        # Microservices (archive, cache, youtube)
├── cli/             # Production CLI tools
└── docker-compose.yml
```

### 10.2 Inferred Reasons for Abandonment

#### 1. Scope Mismatch

**Original assumption**: "Users want a chat interface to query cached content"

**Reality**: Core value is in **content ingestion and recommendations**, not chat UI

**Evidence**: `.claude/VISION.md` shifted focus to:
> "Personal AI Research Assistant and Recommendation Engine"

#### 2. Complexity vs. Value

**Web UI costs**:
- Frontend framework setup (React/Vue)
- WebSocket state management
- UI design and testing
- Cross-browser compatibility

**Alternative**: CLI tools are simpler and align with developer workflow

**Evidence**: `compose/cli/ingest_youtube.py` provides same functionality without web overhead

#### 3. Better Architectural Fit

**Mentat model**: Monolithic FastAPI app with embedded chat logic

**Current model**: Microservices (`compose/services/`) with clear separation of concerns

**Benefits of current approach**:
- Archive service: Handles data persistence independently
- Cache service: Manages Qdrant interactions
- CLI: Thin layer over services (no web UI needed)

#### 4. Privacy Concerns

**OpenRouter requirement**: All user queries sent to third-party proxy

**Alternative**: Direct Anthropic/OpenAI APIs (current project uses this)

**Evidence**: Lesson 008 uses OpenAI batch API directly, no proxy

### 10.3 Timeline of Abandonment

| Date | Event |
|------|-------|
| Early Nov 2025 | Mentat UI explored (chat logs show initial design) |
| Mid Nov 2025 | FastAPI backend implemented (`api/main.py`) |
| Mid Nov 2025 | Frontend planned but never started |
| Late Nov 2025 | Focus shifted to `compose/` microservices |
| Current | `projects/mentat/` directory no longer exists |

---

## 11. What Survived

### 11.1 Architectural Patterns

#### WebSocket Streaming

**From Mentat**:
```python
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    async for chunk in stream_response():
        await websocket.send_json({"type": "token", "content": chunk})
```

**Survived in**: Streaming patterns used in current LLM integrations (not WebSocket, but async streaming)

#### Health Check Endpoint

**From Mentat**:
```python
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now()}
```

**Survived in**: Standard pattern for all microservices (archive, cache, etc.)

#### Environment Loading

**From Mentat**:
```python
from tools.env_loader import load_root_env
load_root_env()
```

**Survived in**: Still used across all services (`compose/lib/env_loader.py`)

### 11.2 Technical Learnings

| Learning | Where It's Applied Now |
|----------|------------------------|
| **Async Python patterns** | All current services use `asyncio` |
| **Vector search integration** | `compose/services/cache/` uses Qdrant |
| **LLM streaming** | OpenAI batch API (Lesson 008) |
| **Localhost-first security** | Docker services bound to localhost |
| **Centralized config** | `.env` + `env_loader.py` pattern |

---

## 12. Lessons Learned

### 12.1 Technical Insights

#### 1. CLI > Web UI for Developer Tools

**Lesson**: For personal productivity tools, CLI is often faster to build and use

**Evidence**:
- `compose/cli/ingest_youtube.py` does same job as Mentat without web overhead
- Integrates into terminal workflow (no context switching)
- Easier to automate (shell scripts, cron jobs)

#### 2. Direct API Clients > Proxies

**Lesson**: OpenRouter added latency and privacy concerns

**Current approach**: Direct Anthropic/OpenAI clients

**Benefits**:
- Lower latency
- Better privacy
- Simpler debugging

#### 3. Microservices > Monoliths (for learning projects)

**Lesson**: Clear service boundaries make iteration easier

**Evidence**:
```
compose/services/
├── archive/      # Write-once, read-many
├── cache/        # Qdrant interactions
├── youtube/      # Transcript fetching
└── tagger/       # LLM tagging
```

**Benefits**:
- Test services in isolation
- Swap implementations without breaking dependents
- Clear data flow

### 12.2 Product Insights

#### 1. Validate Assumptions Early

**Original assumption**: "I need a chat UI to query cached content"

**Reality**: CLI tools + proactive recommendations are more valuable

**Lesson**: Build smallest possible spike to test core hypothesis before investing in UI

#### 2. Follow the Data

**Mentat focus**: Query interface

**Actual bottleneck**: Content ingestion and tagging

**Lesson**: Focus on data pipeline first, presentation layer second

**Current priority**:
1. ✅ Ingest content (YouTube, webpages)
2. ✅ Tag and embed (LLM + vector DB)
3. 🚧 Generate recommendations (next phase)
4. ❓ UI layer (TBD - maybe CLI is enough)

#### 3. Avoid Sunk Cost Fallacy

**Mentat situation**: Backend built, frontend not started

**Decision**: Abandon instead of "finishing" a tool that doesn't solve the right problem

**Outcome**: Freed up energy to build better architecture (`compose/` microservices)

### 12.3 Future Considerations

#### If Building a Web UI Again

**Checklist**:
- [ ] Validate with non-UI prototype first (CLI, Jupyter notebook)
- [ ] Start with static mockups (Figma, HTML+CSS)
- [ ] Build API-first (test with `curl` before building frontend)
- [ ] Use framework with good SSR (Next.js, SvelteKit) for SEO/performance
- [ ] Plan for auth from day 1 (even if single-user, makes multi-user easier later)

**Tech stack recommendations**:
- **Framework**: Next.js (React) or SvelteKit (Svelte)
- **Styling**: Tailwind CSS + shadcn/ui
- **API**: tRPC (type-safe API without OpenAPI spec)
- **WebSocket**: Socket.io (easier than raw WebSocket)
- **Deployment**: Vercel (if public) or Docker (if localhost)

---

## Appendix: Code Artifacts

### A.1 FastAPI Backend (Reconstructed)

**File**: `projects/mentat/api/main.py` (no longer exists)

```python
"""
Mentat Chat API - Minimal spike implementation.

This is a WebSocket-based chat interface for querying cached content.
Iteration 2 will add RAG (Retrieval-Augmented Generation) with Qdrant.
"""

import os
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

from tools.env_loader import load_root_env

# Load environment variables
load_root_env()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment")

MAX_MESSAGE_LENGTH = 10_000

# Initialize OpenRouter client
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Initialize FastAPI app
app = FastAPI(title="Mentat Chat API")

# CORS configuration (localhost-only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(OPENROUTER_API_KEY),
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Client sends: {"message": "user question"}
    Server streams: {"type": "token", "content": "word"}
    Server finishes: {"type": "done", "sources": []}
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "").strip()

            # Validate message
            if not message:
                await websocket.send_json({"type": "error", "error": "Message cannot be empty"})
                continue

            if len(message) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Message too long (max {MAX_MESSAGE_LENGTH} chars)"
                })
                continue

            # Stream LLM response
            try:
                async for token in stream_llm_response(message):
                    await websocket.send_json({"type": "token", "content": token})

                # Send completion signal
                await websocket.send_json({
                    "type": "done",
                    "sources": [],  # TODO: Add sources from RAG in Iteration 2
                })

            except Exception as e:
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        pass  # Client disconnected


async def stream_llm_response(message: str) -> AsyncIterator[str]:
    """
    Stream LLM response token by token.

    TODO Iteration 2: Add RAG here
    1. Query Qdrant for relevant cached content
    2. Construct prompt with context
    3. Stream response with sources
    """
    response = await client.chat.completions.create(
        model="anthropic/claude-3-haiku",  # Via OpenRouter
        messages=[{"role": "user", "content": message}],
        stream=True,
    )

    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### A.2 Expected Frontend Structure

**File**: `projects/mentat/web/src/App.jsx` (never implemented)

```jsx
// Expected structure (not actual code)

import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import ChatWindow from './components/ChatWindow';
import MessageInput from './components/MessageInput';

function App() {
  const [messages, setMessages] = useState([]);
  const { sendMessage, isConnected } = useWebSocket('ws://localhost:8001/ws/chat');

  const handleSend = (text) => {
    sendMessage({ message: text });
    setMessages([...messages, { role: 'user', content: text }]);
  };

  useEffect(() => {
    // Handle incoming messages
    // Update messages state with streaming tokens
  }, []);

  return (
    <div className="app">
      <ChatWindow messages={messages} />
      <MessageInput onSend={handleSend} disabled={!isConnected} />
    </div>
  );
}

export default App;
```

### A.3 Directory Structure (Reconstructed)

```
projects/mentat/
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI app (see A.1)
├── web/                     # Never implemented
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx          # Main component (see A.2)
│       ├── components/
│       │   ├── ChatWindow.jsx
│       │   ├── MessageInput.jsx
│       │   └── SourceCitation.jsx
│       └── hooks/
│           └── useWebSocket.js
├── tests/
│   ├── test_health.py
│   └── test_websocket.py
├── logs/
│   └── .gitkeep
├── Makefile                 # Build and run commands
└── README.md                # Project documentation
```

---

## References

1. **Chat History**: `~/.claude/projects/C--Projects-Personal-agent-spike-projects-mentat/`
2. **Current Vision**: `.claude/VISION.md` (Personal AI Research Assistant)
3. **Microservices Architecture**: `compose/services/` directory
4. **Lesson 007**: Cache Manager with Qdrant (foundation for Mentat's RAG)
5. **Lesson 008**: OpenAI Batch Processing (current LLM integration approach)

---

**Document Status**: Complete
**Source**: Chat history analysis from `~/.claude/projects/C--Projects-Personal-agent-spike-projects-mentat/`
**Author**: Claude (agent-spike project assistant)
**Date**: 2025-11-18
