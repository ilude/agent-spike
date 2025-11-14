# Mentat - AI Research Assistant

Chat interface for your cached content using WebSocket streaming.

## Quick Start

**Prerequisites:**
- Python 3.14 (via `uv`)
- Bun
- `ANTHROPIC_API_KEY` in root `.env` file (already git-crypted)

**First time setup:**
```bash
cd projects/mentat
make install    # Install Python + pnpm dependencies
make            # Start backend + frontend + browser
```

That's it! Mentat will open in your browser at http://localhost:5173

## Daily Usage

```bash
# Start everything
make

# View backend logs (live)
make logs

# Stop everything
make down

# Restart
make restart
```

## Architecture

**Backend (`api/main.py`):**
- FastAPI with WebSocket endpoint at `/ws/chat`
- Streams responses token-by-token
- Health check at `/health` with diagnostics
- Port: 8000

**Frontend (`web/src/App.svelte`):**
- Svelte SPA with WebSocket client
- Real-time message streaming
- Auto-reconnect on disconnect
- Port: 5173

**Services:**
- Uses existing `tools/services/cache` (Qdrant)
- Uses existing `tools/services/archive` (local JSON)

## Project Structure

```
mentat/
├── api/
│   ├── main.py           # FastAPI backend with WebSocket
│   └── __init__.py
├── web/
│   ├── src/
│   │   ├── App.svelte    # Main chat UI
│   │   ├── main.js       # Entry point
│   │   └── app.css       # Global styles
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── logs/
│   └── mentat.log        # Backend logs
├── Makefile              # Development commands
└── README.md             # This file
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make` or `make up` | Start backend + frontend + browser |
| `make down` | Stop all services |
| `make restart` | Restart everything |
| `make start` | Start backend only (daemonized) |
| `make frontend` | Start frontend only |
| `make logs` | Follow backend logs (Ctrl+C to exit) |
| `make dump-logs` | Dump all logs without following |
| `make browser` | Open browser to frontend |
| `make install` | Install all dependencies |
| `make clean` | Remove build artifacts |

## Development Workflow

**Iteration 1 (Current): Spike**
- ✅ WebSocket chat with streaming
- ✅ Basic UI with message history
- ✅ Auto-reconnect
- ✅ Echo response (validates streaming works)

**Iteration 2 (Next): RAG**
- Add semantic search via Qdrant
- Integrate Pydantic AI agent
- Include video transcripts in context
- Display source citations

**Iteration 3 (Later): Tests**
- Backend tests (pytest)
- Frontend tests (Vitest)
- E2E tests (Playwright)

## Troubleshooting

**Port conflicts:**
```
ERROR: Port 8000 is already in use
```
- Another service is using the backend port
- Run `make down` in another Mentat instance
- Or: `netstat -ano | findstr :8000` to find the process

**API key missing:**
```
WARNING: ANTHROPIC_API_KEY not found in environment
```
- Root `.env` file not loaded
- Check if git-crypt is unlocked: `git-crypt status`
- Or set manually: `$env:ANTHROPIC_API_KEY="sk-..."`

**Frontend can't connect:**
```
Connection error. Is the backend running?
```
- Backend not started: `make start`
- Backend crashed: `make logs` to see errors
- Port 8000 blocked by firewall

**Qdrant empty (for Iteration 2+):**
```
No videos found in cache
```
- Need to ingest videos first
- From project root: `uv run python tools/scripts/ingest_video.py "https://youtube.com/watch?v=..."`
- Or use batch ingest: `uv run python tools/scripts/ingest_youtube.py`

## Roadmap

- [x] WebSocket streaming chat
- [x] Basic Svelte UI
- [x] Docker-like Makefile
- [ ] RAG with Qdrant search
- [ ] Pydantic AI agent integration
- [ ] Source citations
- [ ] Video browser panel
- [ ] Multiple chat sessions
- [ ] Conversation history persistence
- [ ] Cost tracking
- [ ] Model selector (Haiku/Sonnet)

## Tech Stack

**Backend:**
- FastAPI 0.109+
- Uvicorn (ASGI server)
- WebSockets
- Python 3.14

**Frontend:**
- Svelte 4.2
- Vite 5.0
- Vanilla CSS (no Tailwind yet)

**Tools:**
- uv (Python package manager)
- Bun (JavaScript runtime & package manager)
- Make (Windows/PowerShell compatible)

## License

Part of the agent-spike learning project.
