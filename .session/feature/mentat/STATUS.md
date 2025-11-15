# Status Log

---

## 2025-01-13 09:00 - Initial setup
✅ Ingested 2 YouTube videos (qw4fDU18RcU, p0mrXfwAbCg)
✅ Created projects/mentat/ monorepo structure (api/ + web/)
Next: Build FastAPI backend with WebSocket

---

## 2025-01-13 09:30 - Backend + Frontend created
✅ FastAPI backend with WebSocket streaming (echo test)
✅ Svelte 4 + Vite frontend with chat UI
✅ Makefile with Docker-like commands (up/down/logs)
✅ Bun for package management
Next: Integrate OpenRouter

---

## 2025-01-13 10:00 - OpenRouter integration
✅ Added AsyncOpenAI client with OpenRouter base URL
✅ Configured moonshotai/kimi-k2:free model
✅ Replaced echo with real LLM streaming
✅ Used tools/env_loader.py for .env loading
Next: Test and fix Makefile issues

---

## 2025-01-13 10:15 - Makefile fixes
✅ Fixed Windows CMD → PowerShell conversion
✅ Fixed variable escaping ($$var → \$$var) for Git Bash
✅ All commands now work cross-platform
❌ Port 8000 blocked by ghost processes from Git Bash testing
Next: Change to port 8001

---

## 2025-01-13 10:30 - Port conflict resolved
✅ Changed BACKEND_PORT from 8000 → 8001
✅ PID files gitignored
✅ Iteration 1 spike complete
Next: User testing via `make up` in PowerShell

---

## 2025-11-13 20:30 - SvelteKit Migration Complete
✅ Migrated from plain Svelte to SvelteKit with adapter-node
✅ Docker Compose working with hot reload
✅ Fixed VITE_API_URL environment variable (localhost:8001)
❌ OpenRouter model blocked by data policy settings
Next: Configure OpenRouter or switch model, then test chat flow
Blocker: moonshotai/kimi-k2:free requires "Free model publication" data policy enabled

Files:
- frontend/src/routes/+layout.svelte (global styles)
- frontend/src/routes/+page.svelte (landing page with health check)
- frontend/src/routes/chat/+page.svelte (chat UI)
- frontend/src/lib/api.js (API client)
- frontend/Dockerfile (multi-stage: builder → dev → prod)
- docker-compose.yml (updated for SvelteKit)

---

## 2025-11-13 21:40 - Iteration 1 Complete
✅ OpenRouter privacy settings configured ("Free model publication" enabled)
✅ Chat flow working with streaming responses
✅ Full stack verified (backend health, frontend UI, WebSocket streaming)
Next: Plan Iteration 2 - RAG with Qdrant vector database

---

## 2025-11-13 22:48 - Dynamic Model Selection Added
✅ Backend /models endpoint fetches from OpenRouter API (5min cache)
✅ Filters for free models (:free suffix) + GPT-5 + Claude 4.5
✅ WebSocket handlers accept optional model parameter (defaults to moonshotai/kimi-k2:free)
✅ Frontend dropdown with grouped options (Free/Paid)
✅ localStorage persistence for model selection
✅ Shows context length in dropdown labels
Next: User testing of model selection

Files:
- api/main.py (lines 96-196: /models endpoint, 217+301: WebSocket model parameter)
- frontend/src/lib/api.js (lines 28-38: fetchModels method)
- frontend/src/routes/chat/+page.svelte (lines 14-16: state, 122-151: onMount, 206-238: dropdown UI)

---

## 2025-11-13 23:15 - Model Filter Refinement
✅ Updated Anthropic filter to show only "4.5" models (claude-haiku-4.5, claude-sonnet-4.5)
✅ Excluded Claude Opus 4.1 and older versions
✅ GPT-5 filter excludes "image" and "5.1" variants
✅ Rebuilt backend Docker image with refined filters
Next: User testing of refined model list

Files:
- api/main.py (lines 147-151: Anthropic 4.5 filter)

---

## 2025-01-13 23:05 - Message Queue System
✅ Implemented message queue for questions submitted during streaming
✅ Removed disabled states from input/buttons during streaming
✅ Added processQueue() to automatically send queued messages after stream completes
✅ Messages queue visibly in chat UI while streaming
Next: User testing (submit multiple questions rapidly), then plan RAG iteration

Files:
- frontend/src/routes/chat/+page.svelte (lines 28: messageQueue, 245-259: send() queueing, 286-300: processQueue(), 202+207: processQueue() calls)

---

## 2025-11-14 03:45 - Inline Video Citations & Dynamic Questions
✅ Implemented inline video citation system (LLM embeds video titles in prose, frontend makes them clickable)
✅ Added /random-question endpoint - generates questions from Qdrant tags/titles
✅ Removed context length from model dropdown
✅ Fixed tooltip hover detection (mouseenter → mousemove)
✅ Storage versioning system (auto-clears old cached messages on format changes)
❌ LLM still putting quotes around video titles despite explicit prompt instructions
Next: Test updated prompt (removed all quote examples), decide on timestamp support

Files:
- api/main.py (lines 210-307: /random-question endpoint, 485-504: updated RAG prompt)
- frontend/src/lib/api.js (lines 40-50: getRandomQuestion method)
- frontend/src/routes/chat/+page.svelte (lines 63-91: renderWithInlineCitations, 329-347: async generateRandomQuestion, 573-580: dice button)

---

## 2025-01-14 04:30 - Timestamp Support Implementation
✅ Updated YouTubeTranscriptService with fetch_timed_transcript() method
✅ Added timed_transcript field to YouTubeArchive model (Optional[list[dict]])
✅ Updated LocalArchiveWriter to accept timed_transcript parameter
✅ Added chunk_timed_transcript() to indexing script for timestamp-aware chunking
✅ Modified indexing to store start_time in Qdrant payload when available
✅ Updated RAG endpoint to include start_time in sources
✅ Frontend now generates URLs with &t= parameter (10s before relevant part)
Next: Commit code, re-ingest all videos, final commit

Files:
- tools/services/youtube/transcript_service.py (lines 101-135: fetch_timed_transcript)
- tools/services/archive/models.py (line 89: timed_transcript field)
- tools/services/archive/local_writer.py (lines 67-107: timed_transcript parameter)
- projects/mentat/scripts/index_videos.py (lines 67-118: chunk_timed_transcript, 200-256: timed chunking)
- projects/mentat/api/main.py (lines 459-468: timestamp in sources)
- projects/mentat/frontend/src/routes/chat/+page.svelte (lines 80-87: URL with timestamp)

---

## 2025-01-14 05:00 - Archive Update (Partial)
✅ Updated 35/472 archives with timed transcripts
✅ Created update_archives_with_timestamps.py script
❌ Remaining 437 archives blocked by YouTube rate limiting
❌ Qdrant re-indexing failed with OpenAI 403 error
Next: Re-run indexing when API access restored
Blocker: OpenAI embeddings API returning 403 permission denied

Notes:
- System handles mixed archive formats gracefully
- 35 videos will have timestamped links, rest will link to video start
- Need to investigate OpenAI API permissions for embeddings

---

## 2025-01-14 14:03 - Rate Limit Investigation & Partial Re-index
✅ Verified indexing script uses python-dotenv with OPENAI_API_KEY from root .env
✅ Researched OpenAI Batch API (50% discount but 24hr delay - not worth complexity)
✅ Partial re-indexing: 45/472 videos indexed before OpenAI 403 error
✅ System works with mixed formats (35 timestamped, 437 plain text)
❌ Both YouTube and OpenAI APIs hit rate limits
Next: Test timestamp functionality, optionally retry when rate limits reset

Blockers:
- OpenAI Embeddings API: Rate limiting after ~45 requests (~$0.01 spent)
- YouTube Transcript API: IP ban after ~35 requests

Notes:
- All code is complete and deployed
- Timestamp feature is "syntactic sugar" - delay acceptable
- 2.5 cent savings from Batch API not worth implementation complexity
- System gracefully handles mixed archive formats
- Can test timestamp functionality with 35 available timestamped videos
