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

## 1. Implement Dual-Collection Embedding Architecture

**Vision Alignment**: ⭐⭐⭐⭐⭐ (Core infrastructure for recommendations)
**Worktree Suitability**: ⭐⭐⭐⭐ (Clean separation, minimal conflicts)
**Complexity**: Medium (2-3 days)

### What
Implement the dual-collection strategy from the embedding pipeline spec:
- **Collection 1**: `content` - One global embedding per item (recommendations, preferences)
- **Collection 2**: `content_chunks` - Multiple chunk embeddings per item (search, Q&A)

### Why
Currently we only have chunk-level embeddings. For preference-based recommendations, we need whole-document embeddings to understand overall content relevance.

### Worktree Approach
```bash
# Main branch: Continue ingestion with current setup
git worktree add ../agent-spike-dual-embeddings -b feature/dual-embeddings

# In worktree: Implement dual-collection architecture
# - Add `content` collection with gte-large-en-v1.5 embeddings
# - Migrate existing data to dual-collection structure
# - Update ingestion scripts to populate both collections
# - Add tests for dual retrieval modes
```

### Files to Change
- `compose/services/cache/qdrant_cache.py` - Add dual-collection support
- `compose/services/cache/config.py` - Configure both embedding models
- `compose/cli/ingest_*.py` - Generate both embeddings during ingestion
- `compose/docker-compose.yml` - Add gte-large-en-v1.5 to Infinity service
- New: `compose/services/cache/retrieval_modes.py` - Search vs Recommendation modes

### Success Criteria
- Two Qdrant collections: `content` (global) and `content_chunks` (local)
- Ingestion generates both embedding types
- Can search by chunks (precise) or by global vector (thematic)
- Tests verify both retrieval modes work

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

## 4. Implement Chunking Strategy for Long Videos

**Vision Alignment**: ⭐⭐⭐⭐ (Improves search precision)
**Worktree Suitability**: ⭐⭐⭐⭐ (Clean feature addition)
**Complexity**: Medium (2-3 days)

### What
Implement time-based + token hybrid chunking for YouTube transcripts:
- Split transcripts into 2-3K token chunks
- Respect natural pause boundaries (sentence breaks)
- Store chunk metadata (timestamp ranges)
- Enable timestamp-level search ("find where they discussed X")

### Why
Current approach embeds entire transcripts. For 2-hour videos, this loses precision. Chunking enables "find the 5-minute segment about topic X" searches.

### Worktree Approach
```bash
git worktree add ../agent-spike-chunking -b feature/transcript-chunking

# In worktree: Implement chunking system
# - Chunking algorithm (time + token hybrid)
# - Metadata storage (start/end timestamps)
# - Update ingestion to chunk long transcripts
# - Search returns timestamp ranges
```

### Files to Change/Create
- New: `compose/services/chunking/`
  - `youtube_chunker.py` - Time-aware chunking
  - `chunk_metadata.py` - Timestamp tracking
- Update: `compose/cli/ingest_youtube.py` - Chunk before embedding
- Update: `compose/services/cache/qdrant_cache.py` - Store chunk metadata
- New: `compose/cli/search_with_timestamps.py` - Return timestamp ranges

### Success Criteria
- Long videos (>1 hour) split into 2-3K token chunks
- Each chunk has start/end timestamp metadata
- Search returns: "Found in video X at 15:30-18:45"
- Can navigate directly to relevant segment

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

**Last Updated**: 2025-11-22 - Added test coverage analysis
