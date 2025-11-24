# Implementation Phases: Video Recommendation System

**Last Updated**: 2025-11-24

## Overview

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
  Spike     Schema      UI         Discovery   ML         Feedback    Agent
```

Each phase delivers working functionality. No phase depends on future phases.

---

## Phase 0: RandomForest Spike

**Goal**: Learn what features RandomForest needs before designing schema.

**Why first**: Schema design depends on knowing what data to store. We don't want to redesign tables mid-project.

### Deliverables
- [ ] Minimal Python script that trains RandomForest on sample data
- [ ] List of features that work well
- [ ] Understanding of data types needed

### Tasks
1. Create sample dataset (50 videos with fake ratings)
2. Implement basic feature extraction
3. Train RandomForest, check accuracy
4. Identify which features have highest importance
5. Document findings → inform schema design

### Success Criteria
- Can train model on sample data
- Accuracy > random (>50% on binary classification)
- Clear list of features to store in database

### Estimated Effort
- 2-4 hours of focused work
- Can be done in isolation (no infrastructure changes)

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

## Phase 4: Feature Extraction + RandomForest

**Goal**: ML model that predicts video interest.

### Deliverables
- [ ] Feature extraction pipeline
- [ ] RandomForest training service
- [ ] Prediction endpoint
- [ ] Confidence scores in UI

### Tasks
1. Implement FeatureExtractor class
   - Extract features defined in Phase 0 spike
   - Handle missing data gracefully
2. Build ModelTrainer service
   - Load user signals as training data
   - Train RandomForest
   - Save model to database
   - Track model metrics
3. Implement prediction service
   - Load trained model
   - Score new videos
   - Cache predictions
4. Add confidence scores to video API
5. Update UI to show confidence
6. Implement retrain trigger (after N ratings)

### API Endpoints
```
GET  /api/videos/model/status
POST /api/videos/model/train
GET  /api/videos (now includes confidence_score)
```

### Background Jobs
```
FeatureExtractionJob - Extract features for batch of videos
ModelTrainJob - Train RandomForest model
```

### Success Criteria
- Model trains on user's rating history
- Predictions have confidence scores
- UI shows confidence per video
- Accuracy is trackable

### Dependencies
- Phase 3 complete (videos have transcripts for features)
- Minimum 10 ratings from imported data

### Estimated Effort
- Feature extraction: 3-4 hours
- Model training: 2-3 hours
- Prediction service: 2-3 hours
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
| 0 | Spike | Feature requirements for schema |
| 1 | Data | Import pipeline working |
| 2 | UI | Basic /videos page |
| 3 | Discovery | New videos from YouTube |
| 4 | ML | Predictions with confidence |
| 5 | Feedback | Ratings improve model |
| 6 | Agent | Category suggestions |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Schema redesign needed | Phase 0 spike validates features first |
| Not enough rating data | Import Brave + Takeout provides cold start |
| YouTube API quota | Quota tracking + conservative defaults |
| Model accuracy poor | Fallback to recency sort |
| Agent suggestions irrelevant | Human review + accept/dismiss UX |

## Decision Points

After each phase, evaluate:
1. Is this useful as-is? (Could stop here)
2. What's blocking the next phase?
3. Should we change direction?

**No phase requires all phases to be complete to provide value.**
