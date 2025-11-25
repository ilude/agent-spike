# Phase 4-8 Implementation Context

**Created**: 2025-11-22
**Purpose**: Full context for ChatGPT replacement feature implementation. Use this document to resume work if interrupted.

---

## Background

This document captures the research, decisions, and implementation plan for extending Mentat chat with features that replace ChatGPT/Claude web interfaces.

**Phases 1-3** (handled by another instance):
- Phase 1: Conversation history persistence
- Phase 2: Projects (grouping, custom instructions, file uploads)
- Phase 3: Canvas (document/code editing sidebar)

**Phases 4-8** (this plan):
- Phase 4: Writing Styles
- Phase 5: Global Memory
- Phase 6: Web Search + Freedium
- Phase 7: Code Execution Sandbox
- Phase 8: Image Generation

---

## Research Summary

### ChatGPT Features (2024-2025)

**Already in Phase 1-3 plan:**
| Feature | Phase |
|---------|-------|
| Conversation History | 1 |
| Auto-naming | 1 |
| Search conversations | 1 |
| Projects | 2 |
| File uploads | 2 |
| Per-project memory | 2 |
| Canvas | 3 |

**Missing from original plan (now Phase 4-8):**
| Feature | Description | Priority |
|---------|-------------|----------|
| Global Memory | Remembers preferences across ALL conversations | HIGH |
| Web Search | Real-time browsing with citations | HIGH |
| Writing Styles | Presets (Concise, Detailed, Formal, etc.) | MEDIUM |
| Code Execution | Python sandbox for data analysis | MEDIUM |
| Image Generation | Native GPT-4o images | LOWER |
| Deep Research | Autonomous research agent (5-30 min) | SKIP |
| Voice Mode | Advanced conversational voice | SKIP |
| Tasks/Reminders | Scheduled recurring tasks | SKIP |
| Custom GPTs | User-created specialized chatbots | SKIP |
| ChatGPT Agent | Browser automation | SKIP |

### Claude Features (claude.ai)

| Feature | Notes |
|---------|-------|
| Artifacts | More powerful than Canvas for code (live preview) |
| Writing Styles | Built-in presets + custom styles from samples |
| 200K Context | Larger than ChatGPT |
| Privacy-First Memory | User-controlled, not automatic |

### Key Differentiators

- **ChatGPT strength**: Always-on memory, image generation, voice
- **Claude strength**: Artifacts with live code, larger context, privacy-focused memory

---

## Decisions Made

### Feature Selection

| Feature | Decision | Rationale |
|---------|----------|-----------|
| Global Memory | ✅ Include | ChatGPT's killer feature, users expect it |
| Web Search | ✅ Include | Essential for current information |
| Writing Styles | ✅ Include | Easy win, just system prompts |
| Code Execution | ✅ Include | High utility for data analysis |
| Image Generation | ✅ Later phase | Worth the API cost, but not priority |
| Deep Research | ❌ Skip | Complex orchestration, 5-30 min compute |
| Voice Mode | ❌ Skip | Complex audio processing, mobile-focused |
| Tasks/Reminders | ❌ Skip | Requires scheduler, background jobs |
| Custom GPTs | ❌ Skip | Massive undertaking for personal use |

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Server IP 192.168.16.241 | Keep (intentional) | Home GPU server for Ollama/SurrealDB/etc. |
| Web search backend | flaresolverr MCP | Already built, reuse existing work |
| Code sandbox | Docker container | Server-side, more powerful than browser |
| Memory style | Auto-extract | ChatGPT approach (vs Claude's explicit save) |
| Freedium hosting | Standalone Docker | Add to compose.yaml, chain with flaresolverr |
| Plan structure | New phases 4+ | Keep Phase 1-3 as-is (another instance working) |
| Testing strategy | Phase 0 first | Set up infra before features, test alongside |
| Existing code tests | api.js + chat.py | Test foundation before building on it |

---

## Adversarial Review Findings

### Blockers Identified

| Issue | Severity | Status |
|-------|----------|--------|
| Hardcoded IP 192.168.16.241 | HIGH | Intentional - home GPU server |
| Docling commented out | HIGH | Needs uncommenting or graceful degradation |
| Project-chat integration incomplete | MODERATE | Another instance handling (Phase 1-3) |
| Env var inconsistency | MODERATE | Fix as pre-work |
| Unstaged changes in chat.py | LOW | Another instance WIP |

### What's Working
- Conversation CRUD ✅
- WebSocket streaming ✅
- Models API ✅
- Project CRUD ✅
- File storage ✅

### What's Broken/Incomplete
- Docling integration (commented out)
- File processing (needs Docling)
- Project-aware chat (RAG ignores project context)

---

## Testing Strategy

### Phase 0: Test Infrastructure First

**Frontend (Vitest):**
- Install vitest, @testing-library/svelte, jsdom
- Test api.js (24 methods, pure JS, highest ROI)
- Test edge cases and error handling

**Backend (pytest-cov):**
- Configure coverage in pyproject.toml
- Create conftest.py with fixtures
- Test chat.py WebSocket handlers
- Test RAG integration
- Test error handling

**Make Targets:**
- `make test` - run all tests
- `make test-frontend` - vitest
- `make test-backend` - pytest
- `make test-coverage` - full coverage report

### Coverage Targets
- Backend: >80% on new code
- Frontend: >70% on api.js, >50% on components

---

## Implementation Plan

### Step 0: Document Context (this file)
```
git commit -m "docs: add Phase 4-8 implementation context and decisions"
git push
```

### Phase 0: Test Infrastructure (~1 week)

| Step | Task | Commit |
|------|------|--------|
| 0.1.1 | Install Vitest + deps | `build(frontend): add vitest test framework with coverage` |
| 0.1.2 | Create test structure | `build(frontend): add test directory structure and npm scripts` |
| 0.1.3 | api.js unit tests | `test(frontend): add unit tests for api.js (24 methods)` |
| 0.1.4 | api.js edge cases | `test(frontend): add api.js edge case and error tests` |
| 0.2.1 | Configure pytest-cov | `build(backend): add pytest-cov configuration` |
| 0.2.2 | Create conftest.py | `test(backend): add pytest fixtures and test infrastructure` |
| 0.3.1 | WebSocket tests | `test(chat): add WebSocket connection and routing tests` |
| 0.3.2 | RAG tests | `test(chat): add RAG integration tests` |
| 0.3.3 | Error tests | `test(chat): add error handling and edge case tests` |
| 0.4 | Make targets | `build: add test and coverage make targets` |

### Phase 4: Writing Styles (2-3 days)

| Step | Task | Commit |
|------|------|--------|
| 4.1 | Backend service | `feat(styles): add styles service with preset definitions` |
| 4.2 | Unit tests | `test(styles): add unit tests for styles service` |
| 4.3 | API router | `feat(styles): add styles REST API router` |
| 4.4 | Chat integration | `feat(styles): integrate style injection into chat WebSocket` |
| 4.5 | Chat tests | `test(chat): add style injection tests` |
| 4.6 | Frontend dropdown | `feat(frontend): add style selector dropdown to chat` |
| 4.7 | Frontend tests | `test(frontend): add style selector component tests` |

### Phase 5: Global Memory (1-1.5 weeks)

| Step | Task | Commit |
|------|------|--------|
| 5.1 | Memory service | `feat(memory): add memory service with auto-extraction` |
| 5.2 | Service tests | `test(memory): add unit tests for memory CRUD` |
| 5.3 | Auto-extraction | `feat(memory): add post-response auto-extraction logic` |
| 5.4 | Extraction tests | `test(memory): add auto-extraction and relevance tests` |
| 5.5 | Memory API | `feat(memory): add memory REST API endpoints` |
| 5.6 | API tests | `test(memory): add API endpoint tests` |
| 5.7 | Chat integration | `feat(memory): integrate memory injection into chat` |
| 5.8 | Chat tests | `test(chat): add memory injection tests` |
| 5.9 | Settings page | `feat(frontend): add memory management settings page` |
| 5.10 | Memory toggle | `feat(frontend): add per-conversation memory toggle` |
| 5.11 | Frontend tests | `test(frontend): add memory UI component tests` |

### Phase 6: Web Search + Freedium (1.5-2 weeks)

| Step | Task | Commit |
|------|------|--------|
| 6.1 | Search service | `feat(search): add web search service with flaresolverr` |
| 6.2 | Search tests | `test(search): add web search unit tests with mocks` |
| 6.3 | Freedium container | `feat(freedium): add freedium container to compose stack` |
| 6.4 | Freedium client | `feat(freedium): add freedium API client with Medium detection` |
| 6.5 | Freedium tests | `test(freedium): add freedium client tests` |
| 6.6 | Chain integration | `feat(search): chain flaresolverr and freedium for paywalled content` |
| 6.7 | Chain tests | `test(search): add chain integration tests` |
| 6.8 | Search API | `feat(search): add web search API endpoint` |
| 6.9 | Chat tools | `feat(chat): add search_web and read_article tools` |
| 6.10 | Tool tests | `test(chat): add search tool integration tests` |
| 6.11 | Citations | `feat(search): add citation formatting for search results` |
| 6.12 | Frontend citations | `feat(frontend): add citation rendering in chat messages` |
| 6.13 | Frontend tests | `test(frontend): add citation component tests` |

### Phase 7: Code Execution Sandbox (2-3 weeks)

| Step | Task | Commit |
|------|------|--------|
| 7.1 | Sandbox container | `feat(sandbox): add code execution container with security limits` |
| 7.2 | Sandbox service | `feat(sandbox): add code execution orchestrator service` |
| 7.3 | Basic tests | `test(sandbox): add basic execution tests` |
| 7.4 | Security hardening | `feat(sandbox): add security hardening and code validation` |
| 7.5 | Security tests | `test(sandbox): add security tests (network, filesystem, timeout)` |
| 7.6 | Output capture | `feat(sandbox): add output capture for plots and files` |
| 7.7 | Output tests | `test(sandbox): add plot and file capture tests` |
| 7.8 | Execution API | `feat(sandbox): add code execution API endpoint` |
| 7.9 | Chat tool | `feat(chat): add execute_code tool for LLM` |
| 7.10 | Tool tests | `test(chat): add code execution tool tests` |
| 7.11 | Results panel | `feat(frontend): add code results artifact panel` |
| 7.12 | Plot display | `feat(frontend): add plot rendering and file downloads` |
| 7.13 | Frontend tests | `test(frontend): add artifact panel component tests` |

### Phase 8: Image Generation (1-1.5 weeks)

| Step | Task | Commit |
|------|------|--------|
| 8.1 | Image service | `feat(images): add image generation service with provider abstraction` |
| 8.2 | Service tests | `test(images): add image generation unit tests` |
| 8.3 | Cost tracking | `feat(images): add cost tracking per generation` |
| 8.4 | Cost tests | `test(images): add cost tracking tests` |
| 8.5 | Image storage | `feat(images): add image storage and retrieval` |
| 8.6 | Images API | `feat(images): add images REST API endpoints` |
| 8.7 | API tests | `test(images): add API endpoint tests` |
| 8.8 | Chat tool | `feat(chat): add generate_image tool for LLM` |
| 8.9 | Tool tests | `test(chat): add image generation tool tests` |
| 8.10 | Image display | `feat(frontend): add image display in chat and artifact panel` |
| 8.11 | Image library | `feat(frontend): add image library with gallery view` |
| 8.12 | Frontend tests | `test(frontend): add image library component tests` |

---

## Files to Create

```
# Documentation
.claude/ideas/chatgpt-replacement/phase4-8-implementation-context.md (this file)

# Phase 0 - Test Infrastructure
compose/frontend/vitest.config.js
compose/frontend/src/lib/__tests__/api.test.js
compose/tests/conftest.py
compose/tests/test_chat_websocket.py

# Phase 4 - Styles
compose/services/styles.py
compose/api/routers/styles.py
compose/tests/test_styles.py

# Phase 5 - Memory
compose/services/memory.py
compose/api/routers/memory.py
compose/data/memory/.gitkeep
compose/tests/test_memory.py
compose/tests/test_memory_api.py

# Phase 6 - Search/Freedium
compose/services/web_search.py
compose/services/freedium_client.py
compose/tests/test_web_search.py
compose/tests/test_freedium.py

# Phase 7 - Code Sandbox
compose/services/code_sandbox.py
compose/tests/test_code_sandbox.py

# Phase 8 - Images
compose/services/image_gen.py
compose/api/routers/images.py
compose/data/images/.gitkeep
compose/tests/test_image_gen.py
compose/tests/test_images_api.py
```

## Files to Modify

```
# Test Infrastructure
compose/frontend/package.json (add vitest deps)
pyproject.toml (add pytest-cov config)
Makefile (add test targets)

# Feature Integration
compose/api/main.py (register routers: styles, memory, images)
compose/api/routers/chat.py (style injection, memory injection, tools)
compose.yaml (add freedium, code-sandbox services)
compose/frontend/src/routes/chat/+page.svelte (UI changes)
compose/frontend/src/lib/api.js (new API methods)
```

---

## Verification Commands

### Phase 0
```bash
cd compose/frontend && npm test
uv run pytest compose/tests/ -v --cov
make test-coverage
```

### Phase 4-8 (per phase)
```bash
# Backend tests
uv run pytest compose/tests/test_<feature>.py -v --cov

# Frontend tests
cd compose/frontend && npm test

# Service verification
docker compose up -d
docker compose logs -f api | grep -i "<feature>"
curl http://localhost:8000/<endpoint>
```

---

## Recovery Instructions

If work is interrupted:

1. Read this document to understand full context
2. Check git log for last completed commit
3. Check `.claude/STATUS.md` for overall project state
4. Resume from next uncommitted step in the plan above
5. Use todo list pattern to track remaining work

---

## Research Sources

**ChatGPT Features:**
- ChatGPT Release Notes (help.openai.com)
- ChatGPT Evolution 2024-2025 (opentools.ai)
- Projects, Canvas, Deep Research, Agent docs (openai.com)

**Claude Features:**
- Claude Artifacts (claude.com/blog)
- Claude Styles (anthropic.com/news)
- Claude vs ChatGPT comparisons (zapier.com, docsbot.ai)

**Freedium:**
- https://techpp.com/2025/11/03/best-freedium-alternatives-to-read-medium-articles-for-free/
- https://freedium-mirror.cfd/
