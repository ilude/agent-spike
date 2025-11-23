# Suggested Next Steps

**Created**: 2025-11-18
**Context**: After completing containerized microservices migration
**Goal**: Move toward Personal AI Research Assistant vision

---

## Priority Ranking

Each suggestion is rated on:
- **Vision Alignment**: How directly it advances toward the recommendation engine goal
- **Worktree Suitability**: How well it fits parallel development in git worktrees
- **Dependencies**: What must be done first
- **Value**: Immediate vs long-term benefit

---

## 1. ✅ COMPLETE - Implement Dual-Collection Embedding Architecture

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Core infrastructure for recommendations)
**Worktree Suitability**: ⭐⭐⭐⭐ (Clean separation, minimal conflicts)
**Complexity**: Medium (2-3 days)
**Status**: COMPLETE (2025-11-23) - Implemented using SurrealDB native vector search

### What Was Implemented
- **SurrealDB with HNSW indexes**: Native vector search (replaced Qdrant)
- **`video` table**: Global embedding per video (1024-dim, gte-large-en-v1.5)
- **`video_chunk` table**: Chunk embeddings for timestamp search (bge-m3)
- **Embedding service**: `compose/services/embeddings/` - Infinity HTTP API wrapper
- **Chunking service**: `compose/services/chunking/` - Time+token hybrid chunking

### Files Changed/Created
- `compose/services/surrealdb/repository.py` - Added HNSW indexes and chunk CRUD
- `compose/services/surrealdb/models.py` - VideoChunkRecord, ChunkSearchResult models
- `compose/services/embeddings/__init__.py` - EmbeddingService class
- `compose/services/chunking/{models.py, youtube_chunker.py}` - Chunking algorithm
- `compose/cli/ingest_video.py` - Updated with `--chunks` flag

### Success Criteria ✅
- [x] HNSW indexes on video.embedding and video_chunk.embedding
- [x] Ingestion generates both embedding types (`--chunks` flag)
- [x] Can search by chunks (precise) or by global vector (thematic)
- [x] Chunk search returns timestamp ranges for navigation

---

## 2. Build Preference Learning & Feedback System

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Essential for personalized recommendations)
**Worktree Suitability**: ⭐⭐⭐⭐⭐ (Completely new feature, zero conflicts)
**Complexity**: Medium (3-4 days)

### What
Implement the preference tracking system described in VISION.md:
- User ratings for content (1-5 stars)
- Topic interest tracking (learned from ratings)
- Source trust levels
- Feedback loops to improve recommendations

### Why
Without preference learning, the system is just search. This makes it a true recommendation engine that learns what you care about.

### Worktree Approach
```bash
git worktree add ../agent-spike-preferences -b feature/preference-learning

# In worktree: Build preference infrastructure
# - Create preferences storage (Mem0 or separate Qdrant collection)
# - Build CLI for rating content
# - Implement preference extraction from ratings
# - Create recommendation scoring algorithm
```

### Files to Create
- `compose/services/preferences/` - New service
  - `preference_manager.py` - Interface for tracking preferences
  - `preference_storage.py` - Mem0 or Qdrant backend
  - `recommendation_scorer.py` - Score content by preferences
- `compose/cli/rate_content.py` - CLI to rate items
- `compose/cli/show_recommendations.py` - Get personalized recommendations
- Tests for preference learning

### Success Criteria
- Can rate any cached content (1-5 stars)
- System tracks topic preferences based on ratings
- Recommendations ranked by: semantic match + preference score
- Higher-rated topics get boosted in recommendations

---

## 3. Add YouTube Channel Monitor & Auto-Ingestion

**Vision Alignment**: ⭐⭐⭐⭐ (Content acquisition automation)
**Worktree Suitability**: ⭐⭐⭐ (Some overlap with ingestion scripts)
**Complexity**: Low-Medium (2-3 days)

### What
Automated monitoring for new content from trusted sources:
- Subscribe to YouTube channels (Nate Jones, Anthropic, etc.)
- Periodic checks for new videos (daily/weekly)
- Auto-ingest new content to queue
- Optional: Auto-tag and analyze new videos

### Why
Manual ingestion doesn't scale. The vision requires monitoring multiple sources and automatically processing new content.

### Worktree Approach
```bash
git worktree add ../agent-spike-monitor -b feature/channel-monitor

# In worktree: Build monitoring service
# - Channel subscription registry
# - Periodic check scheduler (cron or n8n workflow)
# - Auto-queue new videos for ingestion
# - Notification system for new content
```

### Files to Create
- `compose/services/monitor/` - New service
  - `channel_monitor.py` - Check channels for new videos
  - `subscription_registry.py` - Manage watched channels
  - `scheduler.py` - Periodic check logic
- `compose/data/subscriptions.json` - Channel list (git-crypt encrypted)
- `compose/cli/subscribe_channel.py` - Add channels to monitor
- Integration with existing ingestion pipeline

### Success Criteria
- Can subscribe to YouTube channels
- Daily check finds new videos
- New videos auto-added to ingestion queue
- Optional: Auto-ingest and tag without manual intervention

---

## 4. ✅ COMPLETE - Implement Chunking Strategy for Long Videos

**Vision Alignment**: ⭐⭐⭐⭐ (Improves search precision)
**Worktree Suitability**: ⭐⭐⭐⭐ (Clean feature addition)
**Complexity**: Medium (2-3 days)
**Status**: COMPLETE (2025-11-23) - Implemented as part of dual-collection work

### What Was Implemented
- **Time+token hybrid chunking**: `compose/services/chunking/youtube_chunker.py`
- **Chunk models**: TranscriptChunk, ChunkingConfig, ChunkingResult
- **SurrealDB storage**: `video_chunk` table with HNSW index
- **Chunk search**: `semantic_search_chunks()` returns timestamp ranges

### Chunking Algorithm
- Target: 2500 tokens per chunk (configurable)
- Splits at natural pause boundaries (8+ second gaps in transcript)
- Falls back to token-count splits when no pauses found
- Preserves start/end timestamps for each chunk

### Files Created
- `compose/services/chunking/__init__.py` - Public API
- `compose/services/chunking/models.py` - TranscriptChunk, ChunkingConfig
- `compose/services/chunking/youtube_chunker.py` - Chunking algorithm
- `compose/services/surrealdb/models.py` - VideoChunkRecord, ChunkSearchResult

### Success Criteria ✅
- [x] Long videos split into ~2.5K token chunks
- [x] Each chunk has start/end timestamp metadata
- [x] `semantic_search_chunks()` returns matching chunks with timestamps
- [x] Chunk results include parent video info (title, URL)

---

## 5. Build Application Suggester (Connect Learnings to Projects)

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Ultimate goal - apply learning to real work)
**Worktree Suitability**: ⭐⭐⭐⭐⭐ (Completely new feature)
**Complexity**: High (4-5 days)

### What
The "killer feature" from VISION.md - suggest how learned concepts apply to your active projects:
- Track active project goals and challenges
- Match learned techniques to project needs
- Suggest: "You learned X from video Y, apply to project Z"
- Cross-reference with what's already been applied

### Why
This closes the learning loop. Instead of passively consuming content, the system actively helps you apply it.

### Worktree Approach
```bash
git worktree add ../agent-spike-suggester -b feature/application-suggester

# In worktree: Build application suggester
# - Project registry (goals, challenges, tech stack)
# - Technique extraction from content
# - Matching algorithm (techniques → project needs)
# - Application tracking (what's been used)
```

### Files to Create
- `compose/services/suggester/` - New service
  - `project_registry.py` - Track projects and goals
  - `technique_extractor.py` - Extract techniques from content
  - `application_matcher.py` - Match techniques to projects
  - `application_tracker.py` - Track what's been applied
- `compose/cli/add_project.py` - Register a project
- `compose/cli/get_suggestions.py` - "How can I improve project X?"
- `compose/data/projects.json` - Project metadata (git-crypt)

### Success Criteria
- Can register project with goals/challenges
- System extracts techniques from rated content
- Suggests: "Technique X from video Y could solve problem Z"
- Tracks when suggestions are applied
- Learns which suggestions are most useful

---

## Recommended Sequence

### Phase 1: Infrastructure (Weeks 1-2)
1. **Dual-Collection Embeddings** (Task #1)
2. **Transcript Chunking** (Task #4)

These two tasks build the search foundation. Do them first in parallel worktrees.

### Phase 2: Intelligence (Weeks 3-4)
3. **Preference Learning** (Task #2)
4. **Channel Monitor** (Task #3)

Add intelligence and automation. Preferences make it personal, monitoring makes it automatic.

### Phase 3: Application (Week 5+)
5. **Application Suggester** (Task #5)

The capstone feature that ties everything together.

---

## Git Worktree Strategy

### Why Use Worktrees?

1. **Parallel Development**: Work on multiple features simultaneously
2. **Clean Context**: Each feature gets its own working directory
3. **Easy Comparison**: Switch between implementations without losing state
4. **Risk Isolation**: Experimental features don't touch main branch

### Recommended Workflow

```bash
# Set up worktrees
git worktree add ../agent-spike-dual-embeddings -b feature/dual-embeddings
git worktree add ../agent-spike-chunking -b feature/transcript-chunking

# Work in parallel
# Terminal 1: cd ../agent-spike-dual-embeddings
# Terminal 2: cd ../agent-spike-chunking
# Terminal 3: cd agent-spike (main - continue ingestion)

# When ready, merge one feature at a time
cd agent-spike
git merge feature/dual-embeddings
git push
git merge feature/transcript-chunking
git push

# Clean up worktrees
git worktree remove ../agent-spike-dual-embeddings
git worktree remove ../agent-spike-chunking
```

### Tips for Success

1. **Start each worktree from main**: `git worktree add <path> -b <branch>`
2. **Sync main regularly**: `cd agent-spike && git pull && cd ../worktree && git rebase main`
3. **Keep features independent**: Minimal file overlap between worktrees
4. **Test before merge**: Run full test suite in each worktree
5. **Merge sequentially**: Don't merge multiple worktrees at once

---

## Dependencies & Blockers

### Task Dependencies
- **Task #4 (Chunking)** → Should happen before/with **Task #1 (Dual-Embeddings)**
- **Task #2 (Preferences)** → Requires **Task #1** (need global embeddings for recommendations)
- **Task #5 (Suggester)** → Requires **Task #2** (needs preference data)

### Current Blockers
- None! Infrastructure is ready after containerization migration

### Nice-to-Haves (Not Blockers)
- More cached content for testing recommendations
- User feedback on what project challenges matter most

---

## Quick Wins (If Short on Time)

If you only have a few hours, start with these smaller tasks:

1. **Add ratings CLI** (2-3 hours)
   - Simple CLI to rate cached videos 1-5 stars
   - Store in JSON file for now
   - Later migrate to proper preference system

2. **Implement basic chunking** (3-4 hours)
   - Just split on token count for now
   - Don't worry about timestamps yet
   - Gets you 80% of the value

3. **Channel subscription list** (1-2 hours)
   - JSON file with YouTube channel IDs
   - Manual check script (run it yourself daily)
   - Later automate with scheduler

---

**Next Session**: Pick one task, create a worktree, start building!

---

## Addendum: Test Coverage Analysis (2025-11-22)

During comprehensive test coverage work, additional improvements were identified:

### Test Coverage Status

**Services with tests (complete)**:
- archive, cache, display, metadata, tagger, youtube, pipeline
- webpage (new), conversations (new), file_processor (new), projects (new)

**Routers with tests (complete)**:
- ingest, youtube_rag, chat
- cache (new), youtube (new), conversations (new), projects (new), stats (new), health (new)

**Still needed**:
- Integration tests for end-to-end ingest pipeline
- analytics, graph services (if substantive)

### Schema Alignment Quick Wins

Add these fields to cache schema to match VISION.md:

```python
# User-specific metadata
"my_rating": int,           # 1-5 user rating
"watched_date": str,        # When user consumed content
"notes": str,               # Personal notes
"importance": str,          # "high" | "medium" | "low"

# Relationship fields
"inspired_projects": list[str],
"related_content": list[str],
"applied_techniques": list[str],
"solved_problems": list[str]
```

**Files**: `compose/services/cache/models.py`, `compose/services/archive/models.py`

### LLM Cost Auto-Tracking

Current state: `cost_usd` placeholder exists but needs manual population.

Quick fix - add cost calculator:
```python
def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = {
        "claude-3-5-haiku-20241022": {"input": 0.25e-6, "output": 1.25e-6},
        "claude-3-5-sonnet-20241022": {"input": 3.0e-6, "output": 15.0e-6},
    }
    r = rates.get(model, {"input": 0, "output": 0})
    return prompt_tokens * r["input"] + completion_tokens * r["output"]
```

**File**: `compose/services/archive/models.py`

### CLI Consolidation (Lower Priority)

Merge these scripts:
- `ingest_youtube.py`, `batch_ingest_youtube.py`, `ingest_video.py`, `simple_batch_ingest.py`

Into single Typer CLI:
```bash
uv run python -m compose.cli.ingest video <url>
uv run python -m compose.cli.ingest batch <csv> --workers 4
uv run python -m compose.cli.ingest repl
```

---

**Last Updated**: 2025-11-23 - Backup service working, SurrealDB syntax documented

---

## 6. ✅ COMPLETE - Migrate Conversations & Projects to SurrealDB/MinIO

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Unified data layer, essential for production)
**Worktree Suitability**: ⭐⭐⭐⭐ (Self-contained migration)
**Complexity**: Medium (2-3 days)
**Status**: COMPLETE (2025-11-23)

### Current State

- **Conversations**: JSON files in `compose/data/conversations/` (index.json + {id}.json per conversation)
- **Projects**: JSON files in `compose/data/projects/` + binary files in `{project_id}/files/`
- Both services use file-based singletons with manual index management

### Target State

- **Conversations & Projects metadata**: SurrealDB tables (matches video/channel/topic pattern)
- **Project files (PDFs, docs, etc.)**: MinIO blob storage
- **Services**: Same public API, different backend

### SurrealDB Schema

Add to `compose/services/surrealdb/repository.py`:

```surql
-- Conversation table
DEFINE TABLE conversation SCHEMAFULL;
DEFINE FIELD title ON TABLE conversation TYPE string;
DEFINE FIELD model ON TABLE conversation TYPE option<string>;
DEFINE FIELD created_at ON TABLE conversation TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE conversation TYPE datetime VALUE time::now();
DEFINE INDEX idx_conversation_updated ON TABLE conversation COLUMNS updated_at;

-- Message table (separate for efficient queries)
DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD conversation_id ON TABLE message TYPE string;
DEFINE FIELD role ON TABLE message TYPE string;  -- "user" | "assistant"
DEFINE FIELD content ON TABLE message TYPE string;
DEFINE FIELD sources ON TABLE message TYPE option<array>;
DEFINE FIELD timestamp ON TABLE message TYPE datetime VALUE time::now();
DEFINE INDEX idx_message_conversation ON TABLE message COLUMNS conversation_id;

-- Project table
DEFINE TABLE project SCHEMAFULL;
DEFINE FIELD name ON TABLE project TYPE string;
DEFINE FIELD description ON TABLE project TYPE option<string>;
DEFINE FIELD custom_instructions ON TABLE project TYPE option<string>;
DEFINE FIELD created_at ON TABLE project TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE project TYPE datetime VALUE time::now();
DEFINE INDEX idx_project_updated ON TABLE project COLUMNS updated_at;

-- Project file metadata (actual files in MinIO)
DEFINE TABLE project_file SCHEMAFULL;
DEFINE FIELD project_id ON TABLE project_file TYPE string;
DEFINE FIELD filename ON TABLE project_file TYPE string;
DEFINE FIELD original_filename ON TABLE project_file TYPE string;
DEFINE FIELD content_type ON TABLE project_file TYPE string;
DEFINE FIELD size_bytes ON TABLE project_file TYPE int;
DEFINE FIELD minio_key ON TABLE project_file TYPE string;  -- e.g., "projects/{project_id}/{file_id}"
DEFINE FIELD processed ON TABLE project_file TYPE bool DEFAULT false;
DEFINE FIELD indexed ON TABLE project_file TYPE bool DEFAULT false;
DEFINE FIELD processing_error ON TABLE project_file TYPE option<string>;
DEFINE FIELD uploaded_at ON TABLE project_file TYPE datetime VALUE time::now();
DEFINE INDEX idx_file_project ON TABLE project_file COLUMNS project_id;

-- Project-conversation relationship
DEFINE TABLE project_conversation SCHEMAFULL;
DEFINE FIELD project_id ON TABLE project_conversation TYPE string;
DEFINE FIELD conversation_id ON TABLE project_conversation TYPE string;
DEFINE FIELD created_at ON TABLE project_conversation TYPE datetime VALUE time::now();
```

### MinIO Integration

**New file**: `compose/services/surrealdb/minio_client.py`

```python
from minio import Minio
import os

BUCKET_NAME = "project-files"

def get_minio_client() -> Minio:
    return Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )

async def upload_file(project_id: str, file_id: str, filename: str, data: bytes, content_type: str) -> str:
    """Upload file to MinIO, return object key."""
    client = get_minio_client()
    key = f"projects/{project_id}/{file_id}_{filename}"
    client.put_object(BUCKET_NAME, key, io.BytesIO(data), len(data), content_type)
    return key

async def download_file(minio_key: str) -> bytes:
    """Download file from MinIO."""
    client = get_minio_client()
    response = client.get_object(BUCKET_NAME, minio_key)
    return response.read()

async def delete_file(minio_key: str) -> None:
    """Delete file from MinIO."""
    client = get_minio_client()
    client.remove_object(BUCKET_NAME, minio_key)
```

### Files to Modify

1. **`compose/services/surrealdb/repository.py`** - Add conversation/project CRUD functions
2. **`compose/services/surrealdb/models.py`** - Add Pydantic models for new tables
3. **`compose/services/conversations.py`** - Replace JSON backend with SurrealDB
4. **`compose/services/projects.py`** - Replace JSON + filesystem with SurrealDB + MinIO
5. **New: `compose/services/surrealdb/minio_client.py`** - MinIO operations

### Migration Script

Create `compose/cli/migrate_to_surrealdb.py`:

1. Read all conversations from `compose/data/conversations/`
2. Insert into SurrealDB `conversation` and `message` tables
3. Read all projects from `compose/data/projects/`
4. Insert into SurrealDB `project`, `project_file`, `project_conversation` tables
5. Upload project files to MinIO
6. Verify counts match
7. (Optional) Archive old JSON files

### Implementation Order

1. Add SurrealDB schema (no breaking changes to existing code)
2. Add Pydantic models
3. Add MinIO client
4. Update `ConversationService` to use SurrealDB (same public API)
5. Update `ProjectService` to use SurrealDB + MinIO (same public API)
6. Write migration script
7. Test with existing data
8. Run migration
9. Remove old JSON storage code

### Success Criteria

- [x] Backup service working with SurrealDB + MinIO (2025-11-23)
- [x] All CRUD operations work via SurrealDB (2025-11-23)
- [x] Project files stored in MinIO, retrievable via API (2025-11-23)
- [x] Existing conversations/projects migrated without data loss (2025-11-23)
- [x] API routers unchanged (services maintain same interface) (2025-11-23)
- [x] Tests pass with new backend (2025-11-23)

### SurrealDB Syntax Lessons Learned (2025-11-23)

**Record ID syntax for UUIDs with dashes**: Use backticks around the ID value.

```surql
-- CORRECT: Creates record with specific ID
CREATE backup:`3810d02f-552b-453e-86ed-b0f5677181c2` SET status = 'pending';

-- WRONG: Creates a field called 'id', not a record ID
CREATE backup SET id = '3810d02f-552b-453e-86ed-b0f5677181c2', status = 'pending';
```

**Python f-string pattern**:
```python
backup_id = str(uuid4())  # e.g., "3810d02f-552b-453e-86ed-b0f5677181c2"

# CREATE with specific record ID
await execute_query(f"CREATE backup:`{backup_id}` SET status = $status", {"status": "pending"})

# SELECT by record ID
await execute_query(f"SELECT * FROM backup:`{backup_id}`")

# UPDATE by record ID
await execute_query(f"UPDATE backup:`{backup_id}` SET status = $status", {"status": "completed"})

# DELETE by record ID
await execute_query(f"DELETE backup:`{backup_id}`")
```

**RecordID object handling**: SurrealDB returns `RecordID` objects, not strings. Convert with `str()`:
```python
record_id = str(record.get("id", ""))  # e.g., "backup:3810d02f-..."
if ":" in record_id:
    record_id = record_id.split(":")[1]  # Extract just the UUID part
```

### Benefits

- **Unified data layer**: Everything in SurrealDB (videos, conversations, projects)
- **Scalable file storage**: MinIO handles large files properly
- **Query capabilities**: Can search conversations, join with projects, etc.
- **Backup simplicity**: SurrealDB export + MinIO bucket = complete backup
- **Future features**: Conversation embeddings, semantic search over chat history

---

## 7. Implement Memory Service with SurrealDB

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Essential for personalized AI assistant)
**Worktree Suitability**: ⭐⭐⭐⭐⭐ (Self-contained, no conflicts)
**Complexity**: Medium (2-3 days)
**Status**: TODO

### Background

The old `compose/services/memory.py` used JSON file storage (`compose/data/memory/`) for ChatGPT-style auto-extraction of user preferences. This was deleted during cleanup (2025-11-23) since all persistent data should use SurrealDB.

### What

Implement a memory service that:
- Auto-extracts user preferences/facts from conversations (using Claude Haiku)
- Stores memories in SurrealDB with vector embeddings for semantic retrieval
- Retrieves relevant memories based on conversation context
- Supports memory categories: preferences, facts, context, instructions

### SurrealDB Schema

```surql
DEFINE TABLE memory SCHEMAFULL;
DEFINE FIELD content ON TABLE memory TYPE string;           -- "User prefers concise code examples"
DEFINE FIELD category ON TABLE memory TYPE string;          -- "preference" | "fact" | "context" | "instruction"
DEFINE FIELD embedding ON TABLE memory TYPE array<float>;   -- For semantic retrieval
DEFINE FIELD source_conversation_id ON TABLE memory TYPE option<string>;
DEFINE FIELD relevance_score ON TABLE memory TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON TABLE memory TYPE datetime VALUE time::now();
DEFINE FIELD updated_at ON TABLE memory TYPE datetime VALUE time::now();

-- HNSW index for semantic search
DEFINE INDEX idx_memory_embedding ON TABLE memory FIELDS embedding HNSW DIMENSION 1024;
DEFINE INDEX idx_memory_category ON TABLE memory COLUMNS category;
```

### Files to Create

- `compose/services/memory/` - New service package
  - `__init__.py` - Public API
  - `models.py` - MemoryItem, MemorySearchResult models
  - `repository.py` - SurrealDB CRUD operations
  - `extractor.py` - LLM-based memory extraction from conversations
  - `retriever.py` - Semantic search for relevant memories

### API Integration

Add to chat router:
1. Before generating response: retrieve relevant memories
2. Include memories in system prompt context
3. After conversation: extract new memories from exchange

### Success Criteria

- [ ] Memories stored in SurrealDB with embeddings
- [ ] Can retrieve memories semantically (not just keyword match)
- [ ] Auto-extraction from conversations works
- [ ] Memory deduplication (don't store same fact twice)
- [ ] Memory relevance decay over time (optional)
- [ ] Tests for extraction and retrieval
