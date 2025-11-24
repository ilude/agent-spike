# Implementation Phases: Video Recommendation System

**Last Updated**: 2025-11-24

## Overview

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
  Spike     Schema      UI         Discovery   ML         Feedback    Agent
```

Each phase delivers working functionality. No phase depends on future phases.

---

## Phase 0: Persona Clustering Spike

**Goal**: Validate that user watch history clusters into coherent interest personas.

**Why first**: The multi-persona approach assumes interests are clusterable. If clustering produces muddy results, we need to know before building the full system.

**Approach change**: Originally planned RandomForest on hand-crafted features. After discussion, pivoted to multi-persona embeddings because:
- We have diverse, temporal interests that don't fit a single profile
- We have embedding infrastructure (Infinity) already running
- Content understanding matters more than metadata patterns
- See ML-DISCUSSION.md "Approach 4" for full reasoning

### Data Scope

**Primary (last 3 months)**:
- Brave browser history (YouTube URLs)
- Google Takeout watch history (`compose/data/google-takeout-20250723T204430Z-1-001.zip`)
- Already-ingested videos in archive

**Historical sample (older than 3 months)**:
- ~50 random videos from older history
- Prevents recency bias, catches dormant interests

### Deliverables
- [ ] Script to extract video IDs from Brave + Takeout (with date filtering)
- [ ] Transcripts fetched for videos not in archive
- [ ] Embeddings generated via Infinity
- [ ] k-means clustering into personas (k=5-8)
- [ ] Visualization/report of cluster contents
- [ ] Manual validation: do clusters represent coherent interests?

### Tasks
1. Parse Brave history, extract YouTube video IDs (last 3 months)
2. Parse Google Takeout watch-history.json (last 3 months + 50 random older)
3. Deduplicate video IDs across sources
4. For videos not in archive: fetch transcripts (respect rate limits, archive immediately)
5. Generate embeddings via Infinity service
6. Run k-means with varying k (5, 6, 7, 8), evaluate silhouette scores
7. For best k: inspect clusters, label them manually ("AI cluster", "homelab cluster", etc.)
8. Test scoring: pick 5 new videos, check if max-similarity-to-persona feels right

### Success Criteria
- Clusters are interpretable (can assign human-readable labels)
- At least 3-4 distinct interest areas emerge
- New video scoring produces sensible results
- Clear path forward for building the full system

### Failure Modes
- **Clusters are muddy**: One cluster contains unrelated topics → may need different k or hierarchical clustering
- **Not enough data**: 3 months doesn't produce enough videos → extend time range or rely more on historical sample
- **Transcripts unavailable**: Many videos lack transcripts → fall back to title/description embeddings

### Estimated Effort
- Data extraction: 2-3 hours
- Transcript fetching: depends on rate limits (may need to batch over days)
- Embedding + clustering: 2-3 hours
- Validation: 1-2 hours

---

## Phase 1: Schema + Data Import

**Goal**: Database tables and ability to import historical data.

### Deliverables
- [ ] SurrealDB tables created (video_rec, user_video_signal, user_channel_preference, user_category)
- [ ] Brave history import working
- [ ] Google Takeout import working
- [ ] Deduplication logic tested

### Tasks
1. Create SurrealDB migration script for new tables
2. Implement Brave history parser
   - Extend existing `compose/cli/brave_history/` pipeline
   - Filter YouTube URLs
   - Extract video IDs
3. Implement Google Takeout parser
   - Parse watch-history.json
   - Parse liked-videos.json (thumbs_up signals)
   - Parse subscriptions.json (channel preferences)
4. Build import pipeline with deduplication
5. Create import CLI command

### API Endpoints
```
POST /api/videos/import/brave
POST /api/videos/import/takeout
GET  /api/videos/import/status
```

### Success Criteria
- Can import Brave history from file
- Can import Google Takeout from directory
- Duplicates are correctly detected
- Data appears in SurrealDB tables

### Dependencies
- Phase 0 complete (schema informed by feature needs)

### Estimated Effort
- Schema: 1-2 hours
- Brave import: 2-3 hours
- Takeout import: 2-3 hours
- Testing: 2 hours

---

## Phase 2: Basic UI + Manual Video Add

**Goal**: Visible /videos page with imported data.

### Deliverables
- [ ] SvelteKit /videos route
- [ ] Video grid display (thumbnail, title, channel, duration)
- [ ] Basic filtering (hide watched, sort by date)
- [ ] Manual video add form

### Tasks
1. Create SvelteKit route at `/videos`
2. Build video card component
3. Implement video grid with pagination
4. Add filter controls (watched toggle, sort dropdown)
5. Build "Add video" modal (paste YouTube URL)
6. Connect to existing auth

### UI Components
```
/videos
├── Header (title, filter controls, add button)
├── VideoGrid
│   └── VideoCard (thumbnail, title, channel, duration, watched badge)
├── Pagination
└── AddVideoModal
```

### API Endpoints
```
GET  /api/videos?hide_watched=true&sort=date&limit=20&offset=0
POST /api/videos (manual add)
```

### Success Criteria
- Can see imported videos in grid
- Can hide/show watched videos
- Can manually add a video by URL
- Responsive on desktop

### Dependencies
- Phase 1 complete (data in database)

### Estimated Effort
- Route + layout: 1-2 hours
- Video card: 1-2 hours
- Filtering: 1-2 hours
- Manual add: 1-2 hours
- Polish: 2 hours

---

## Phase 3: YouTube API Discovery + Transcripts

**Goal**: Fetch new videos from YouTube, get transcripts for analysis.

### Deliverables
- [ ] YouTube API client wrapper
- [ ] Video discovery by search query
- [ ] Transcript fetching via youtube-transcript-api
- [ ] Quota tracking
- [ ] Scheduled discovery job

### Tasks
1. Create YouTube API client service
   - Search endpoint wrapper
   - Video metadata endpoint
   - Channel info endpoint
2. Implement quota tracker (10K daily limit)
3. Build discovery job
   - Take queries from user categories
   - Fetch videos
   - Filter out known videos
   - Store metadata
4. Integrate youtube-transcript-api for transcripts
5. Create queue jobs for batch processing
6. Add quota display in UI

### API Endpoints
```
POST /api/videos/discover { queries: [...], max_per_query: 10 }
GET  /api/videos/quota
```

### Background Jobs
```
VideoDiscoveryJob - Fetch videos from YouTube
TranscriptFetchJob - Get transcript for single video
```

### Success Criteria
- Can discover new videos by topic
- Transcripts are fetched and stored
- Quota is tracked and respected
- Discovery can run on schedule

### Dependencies
- Phase 2 complete (UI to see results)
- YouTube API key configured

### Estimated Effort
- API client: 2-3 hours
- Discovery job: 2-3 hours
- Transcript fetching: 1-2 hours
- Quota tracking: 1-2 hours
- Scheduling: 1-2 hours

---

## Phase 4: Persona Scoring + Recommendations

**Goal**: Score videos using multi-persona embeddings with metadata multipliers.

**Approach change**: Originally planned RandomForest classifier. Now using persona-based scoring:
1. Match video embedding to user's persona clusters
2. Weight by persona activity
3. Apply metadata multipliers (channel affinity, view health, recency)

### Deliverables
- [ ] PersonaManager service (create, update, query personas)
- [ ] VideoScorer service (score videos against personas)
- [ ] Metadata multiplier functions
- [ ] Recommendation endpoint with confidence scores
- [ ] Confidence scores in UI

### Tasks
1. Implement PersonaManager
   - Load/save personas from database
   - Compute cluster centroids
   - Track activity scores with decay
2. Implement VideoScorer
   - Compute cosine similarity to each persona
   - Apply activity weighting
   - Apply metadata multipliers
3. Implement metadata multipliers
   - Channel affinity (subscribed, watch history, thumbs ratio)
   - View count health (sigmoid curve)
   - Recency factor (upload date decay)
4. Add scoring to video API
5. Update UI to show match score per video
6. Implement persona refresh trigger (after N ratings)

### Scoring Formula
```python
# Persona matching
persona_scores = [
    cosine_sim(video_emb, persona.centroid) * persona.activity
    for persona in user_personas
]
content_score = max(persona_scores)

# Metadata multipliers
channel_boost = get_channel_affinity(user, video.channel_id)  # 0.5 - 2.0
view_health = view_health_curve(video.view_count)             # 0.7 - 1.2
recency = recency_curve(video.upload_date)                    # 0.8 - 1.1

# Final score
final_score = content_score * channel_boost * view_health * recency
```

### API Endpoints
```
GET  /api/videos/personas
POST /api/videos/personas/refresh
GET  /api/videos (now includes match_score, matching_persona)
```

### Background Jobs
```
PersonaRefreshJob - Re-cluster based on new ratings
EmbeddingGenerationJob - Embed new videos via Infinity
```

### Success Criteria
- Videos ranked by persona match + metadata
- Scores feel reasonable (highly-matched videos at top)
- Persona activity updates on user interactions
- Can refresh personas on demand

### Dependencies
- Phase 3 complete (videos have embeddings)
- Phase 0 persona clustering validated

### Estimated Effort
- PersonaManager: 2-3 hours
- VideoScorer: 2-3 hours
- Metadata multipliers: 2 hours
- API integration: 1-2 hours
- UI integration: 1-2 hours
- Testing: 2 hours

---

## Phase 5: Rating Feedback Loop

**Goal**: UI ratings that improve recommendations.

### Deliverables
- [ ] Thumbs up/down buttons in UI
- [ ] Not interested button
- [ ] Rating persistence
- [ ] Channel affinity updates
- [ ] Automatic retrain trigger

### Tasks
1. Add rating buttons to VideoCard
2. Implement optimistic UI updates
3. Create rating API endpoint
4. Update channel affinity on rating
5. Trigger retrain after threshold
6. Add rating history view

### UI Components
```
VideoCard
├── ThumbsUp button
├── ThumbsDown button
└── NotInterested button (dropdown?)

RatingHistory (optional)
└── List of recent ratings
```

### API Endpoints
```
POST /api/videos/{video_id}/rate { rating: 'up'|'down'|'not_interested' }
GET  /api/videos/ratings/history
```

### Success Criteria
- Can rate videos with single click
- Ratings persist and appear in history
- Channel affinity updates automatically
- Model retrains after enough new ratings

### Dependencies
- Phase 4 complete (model exists to retrain)

### Estimated Effort
- UI buttons: 1-2 hours
- API endpoint: 1-2 hours
- Affinity updates: 1-2 hours
- Retrain trigger: 1 hour
- Testing: 1-2 hours

---

## Phase 6: Category Suggestion Agent

**Goal**: On-demand agent that suggests new interest categories.

### Deliverables
- [ ] CategoryAgent (Pydantic AI)
- [ ] "Suggest categories" button in UI
- [ ] Category management UI
- [ ] Integration with discovery

### Tasks
1. Design CategoryAgent prompt
   - Input: user ratings, watch patterns, video content
   - Output: category suggestions with reasoning
2. Implement agent with Pydantic AI
3. Build category suggestion endpoint
4. Create category management UI
   - View active categories
   - Accept/dismiss suggestions
   - Manual category creation
5. Connect categories to discovery queries

### Agent Design
```python
class CategoryAgent:
    system_prompt = """
    You analyze user video preferences to suggest interest categories.

    Given:
    - Recent thumbs up videos (titles, channels, tags)
    - Recent thumbs down videos
    - Watch patterns (channels, topics)

    Suggest categories the user might enjoy exploring.
    For each suggestion, explain your reasoning.
    """

    async def suggest(self, context: UserContext) -> list[Suggestion]:
        ...
```

### UI Components
```
/videos
├── "Suggest Categories" button
└── CategorySuggestionModal
    └── SuggestionCard (name, reasoning, accept/dismiss)

/videos/categories (optional separate page)
├── ActiveCategories list
├── AddCategory form
└── CategoryStats
```

### API Endpoints
```
GET  /api/videos/categories
POST /api/videos/categories/suggest
POST /api/videos/categories { name, keywords, description }
PUT  /api/videos/categories/{id}
DELETE /api/videos/categories/{id}
```

### Success Criteria
- Agent suggests relevant categories
- Suggestions include clear reasoning
- Can accept suggestions → appear in filters
- Categories influence discovery queries

### Dependencies
- Phase 5 complete (enough ratings for analysis)
- Pydantic AI setup

### Estimated Effort
- Agent design: 2-3 hours
- Agent implementation: 2-3 hours
- Category API: 2-3 hours
- UI: 3-4 hours
- Integration: 1-2 hours

---

## Summary Timeline

| Phase | Focus | Key Deliverable |
|-------|-------|-----------------|
| 0 | Spike | Persona clustering validated |
| 1 | Data | Import pipeline working |
| 2 | UI | Basic /videos page |
| 3 | Discovery | New videos from YouTube + embeddings |
| 4 | ML | Persona scoring with metadata multipliers |
| 5 | Feedback | Ratings update personas |
| 6 | Agent | Category suggestions |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Clusters are muddy | Try different k values, hierarchical clustering, or fall back to simpler approach |
| Not enough data | 3 months + 50 historical should be sufficient; extend range if needed |
| Transcripts unavailable | Fall back to title/description embeddings |
| YouTube API quota | Quota tracking + conservative defaults |
| Scoring feels wrong | Tune metadata multiplier weights; add manual override |
| Agent suggestions irrelevant | Human review + accept/dismiss UX |

## Decision Points

After each phase, evaluate:
1. Is this useful as-is? (Could stop here)
2. What's blocking the next phase?
3. Should we change direction?

**No phase requires all phases to be complete to provide value.**
