# Architecture: Video Recommendation System

**Last Updated**: 2025-11-24

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (SvelteKit)                      │
│                         /videos route                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API (FastAPI)                            │
│                    /api/videos/* endpoints                       │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   SurrealDB   │     │  Queue Worker   │     │ Category Agent  │
│  (storage)    │     │ (batch jobs)    │     │ (Pydantic AI)   │
└───────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                      ┌─────────────────┐
                      │  YouTube API    │
                      │  + Transcripts  │
                      └─────────────────┘
```

## SurrealDB Schema

**Note**: Schema informed by Phase 0 persona clustering spike. Using multi-persona embeddings approach (see ML-DISCUSSION.md "Approach 4").

### Tables

#### `video_rec` (recommendation videos)
Separate from existing `video` cache to avoid conflicts.

```sql
DEFINE TABLE video_rec SCHEMAFULL;

-- Core identity
DEFINE FIELD video_id ON video_rec TYPE string;  -- YouTube video ID
DEFINE FIELD url ON video_rec TYPE string;
DEFINE FIELD title ON video_rec TYPE string;
DEFINE FIELD channel_id ON video_rec TYPE string;
DEFINE FIELD channel_name ON video_rec TYPE string;

-- Metadata (from YouTube API)
DEFINE FIELD thumbnail_url ON video_rec TYPE string;
DEFINE FIELD duration_seconds ON video_rec TYPE int;
DEFINE FIELD view_count ON video_rec TYPE int;
DEFINE FIELD like_count ON video_rec TYPE option<int>;
DEFINE FIELD upload_date ON video_rec TYPE datetime;
DEFINE FIELD description ON video_rec TYPE option<string>;

-- Content analysis
DEFINE FIELD transcript ON video_rec TYPE option<string>;
DEFINE FIELD tags ON video_rec TYPE array<string>;
DEFINE FIELD categories ON video_rec TYPE array<string>;  -- Derived from agent/ML

-- ML features (populated by feature extraction)
DEFINE FIELD features ON video_rec TYPE option<object>;  -- Flexible JSON for experimentation

-- Embeddings (optional, for semantic search)
DEFINE FIELD embedding ON video_rec TYPE option<array<float>>;

-- Timestamps
DEFINE FIELD created_at ON video_rec TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON video_rec TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_video_id ON video_rec FIELDS video_id UNIQUE;
DEFINE INDEX idx_channel ON video_rec FIELDS channel_id;
DEFINE INDEX idx_upload ON video_rec FIELDS upload_date;
```

#### `user_video_signal` (user interactions)
```sql
DEFINE TABLE user_video_signal SCHEMAFULL;

DEFINE FIELD user_id ON user_video_signal TYPE string;
DEFINE FIELD video_id ON user_video_signal TYPE string;
DEFINE FIELD signal_type ON user_video_signal TYPE string;  -- 'watched', 'thumbs_up', 'thumbs_down', 'not_interested', 'ingested'
DEFINE FIELD source ON user_video_signal TYPE string;  -- 'brave', 'takeout', 'api', 'mentat', 'ui'
DEFINE FIELD timestamp ON user_video_signal TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON user_video_signal TYPE option<object>;  -- Additional context

-- Indexes
DEFINE INDEX idx_user_video ON user_video_signal FIELDS user_id, video_id;
DEFINE INDEX idx_user_type ON user_video_signal FIELDS user_id, signal_type;
```

#### `user_channel_preference` (channel-level tracking)
```sql
DEFINE TABLE user_channel_preference SCHEMAFULL;

DEFINE FIELD user_id ON user_channel_preference TYPE string;
DEFINE FIELD channel_id ON user_channel_preference TYPE string;
DEFINE FIELD channel_name ON user_channel_preference TYPE string;

-- Aggregated signals
DEFINE FIELD videos_watched ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD thumbs_up ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD thumbs_down ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD affinity_score ON user_channel_preference TYPE float DEFAULT 0.5;  -- 0-1

DEFINE FIELD updated_at ON user_channel_preference TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_channel ON user_channel_preference FIELDS user_id, channel_id UNIQUE;
```

#### `user_category` (discovered categories)
```sql
DEFINE TABLE user_category SCHEMAFULL;

DEFINE FIELD user_id ON user_category TYPE string;
DEFINE FIELD category_name ON user_category TYPE string;
DEFINE FIELD description ON user_category TYPE option<string>;
DEFINE FIELD keywords ON user_category TYPE array<string>;
DEFINE FIELD source ON user_category TYPE string;  -- 'agent', 'manual', 'imported'
DEFINE FIELD interest_score ON user_category TYPE float DEFAULT 0.5;
DEFINE FIELD active ON user_category TYPE bool DEFAULT true;
DEFINE FIELD created_at ON user_category TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_category ON user_category FIELDS user_id, category_name UNIQUE;
```

#### `user_persona` (interest clusters)
```sql
DEFINE TABLE user_persona SCHEMAFULL;

DEFINE FIELD user_id ON user_persona TYPE string;
DEFINE FIELD persona_index ON user_persona TYPE int;  -- 0, 1, 2, ... (cluster number)
DEFINE FIELD label ON user_persona TYPE option<string>;  -- Human-assigned label ("AI/ML", "Homelab", etc.)
DEFINE FIELD centroid ON user_persona TYPE array<float>;  -- Embedding centroid (1024 dims for bge-m3)
DEFINE FIELD activity_score ON user_persona TYPE float DEFAULT 0.5;  -- 0.0 - 1.0
DEFINE FIELD last_activity ON user_persona TYPE datetime;  -- Last watch/like in this cluster
DEFINE FIELD video_count ON user_persona TYPE int DEFAULT 0;  -- Videos in this cluster
DEFINE FIELD sample_video_ids ON user_persona TYPE array<string>;  -- Example videos for inspection

DEFINE FIELD created_at ON user_persona TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON user_persona TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_persona ON user_persona FIELDS user_id, persona_index UNIQUE;
```

#### `persona_config` (clustering configuration)
```sql
DEFINE TABLE persona_config SCHEMAFULL;

DEFINE FIELD user_id ON persona_config TYPE string;
DEFINE FIELD k ON persona_config TYPE int;  -- Number of clusters
DEFINE FIELD last_clustered ON persona_config TYPE datetime;
DEFINE FIELD clustering_samples ON persona_config TYPE int;  -- Videos used in last clustering
DEFINE FIELD silhouette_score ON persona_config TYPE option<float>;  -- Quality metric

-- Decay parameters
DEFINE FIELD activity_half_life_days ON persona_config TYPE float DEFAULT 14.0;
DEFINE FIELD activity_floor ON persona_config TYPE float DEFAULT 0.1;

-- Metadata multiplier weights (tunable)
DEFINE FIELD channel_boost_weight ON persona_config TYPE float DEFAULT 1.0;
DEFINE FIELD view_health_weight ON persona_config TYPE float DEFAULT 1.0;
DEFINE FIELD recency_weight ON persona_config TYPE float DEFAULT 1.0;

DEFINE INDEX idx_user_config ON persona_config FIELDS user_id UNIQUE;
```

#### `ml_model` (trained models - kept for potential future use)
```sql
DEFINE TABLE ml_model SCHEMAFULL;

DEFINE FIELD user_id ON ml_model TYPE string;
DEFINE FIELD model_type ON ml_model TYPE string;  -- 'kmeans', 'random_forest' (future)
DEFINE FIELD version ON ml_model TYPE int;
DEFINE FIELD model_data ON ml_model TYPE bytes;  -- Serialized model (pickle/joblib)
DEFINE FIELD training_samples ON ml_model TYPE int;
DEFINE FIELD metrics ON ml_model TYPE object;  -- silhouette_score, etc.
DEFINE FIELD created_at ON ml_model TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_model ON ml_model FIELDS user_id, model_type;
```

## API Endpoints

### Videos

```
GET  /api/videos
     Query params: topic, sort_by, limit, offset, hide_watched
     Returns: List of recommended videos with confidence scores

GET  /api/videos/{video_id}
     Returns: Single video details

POST /api/videos/discover
     Body: { queries: string[], max_per_query: int }
     Triggers YouTube API search, queues for processing
     Returns: { job_id, estimated_videos }

POST /api/videos/{video_id}/rate
     Body: { rating: 'up' | 'down' | 'not_interested' }
     Returns: { success: true }

POST /api/videos/import
     Body: { source: 'brave' | 'takeout', data: ... }
     Returns: { imported: int, duplicates: int, errors: int }
```

### Categories

```
GET  /api/videos/categories
     Returns: List of user's categories with interest scores

POST /api/videos/categories/suggest
     Triggers category agent analysis
     Returns: { suggestions: [{ name, reasoning, keywords }] }

POST /api/videos/categories
     Body: { name, keywords, description }
     Create manual category

PUT  /api/videos/categories/{id}
     Update category

DELETE /api/videos/categories/{id}
     Deactivate category
```

### Personas

```
GET  /api/videos/personas
     Returns: List of user's personas with activity scores and sample videos
     Response: {
       personas: [{
         index: int,
         label: string | null,
         activity_score: float,
         video_count: int,
         sample_videos: [{ id, title, thumbnail }]
       }],
       config: { k, last_clustered, silhouette_score }
     }

POST /api/videos/personas/refresh
     Re-cluster based on current watch history
     Body: { k?: int }  // Optional override for cluster count
     Returns: { job_id, estimated_time }

PUT  /api/videos/personas/{index}/label
     Set human-readable label for persona
     Body: { label: string }
     Returns: { success: true }
```

### Model (legacy, kept for future use)

```
GET  /api/videos/model/status
     Returns: { trained: bool, samples: int, accuracy: float, last_trained: datetime }

POST /api/videos/model/train
     Force retrain (normally automatic after N new ratings)
     Returns: { job_id }
```

### Quota

```
GET  /api/videos/quota
     Returns: { used_today: int, limit: 10000, reset_at: datetime }
```

## Service Layer

### VideoRecommendationService

```python
class VideoRecommendationService:
    """Core recommendation logic."""

    async def get_recommendations(
        self,
        user_id: str,
        topic: Optional[str] = None,
        limit: int = 20,
        hide_watched: bool = True,
    ) -> list[VideoWithScore]:
        """Get ranked video recommendations."""
        pass

    async def record_signal(
        self,
        user_id: str,
        video_id: str,
        signal_type: SignalType,
        source: str,
    ) -> None:
        """Record user interaction signal."""
        pass

    async def should_retrain(self, user_id: str) -> bool:
        """Check if model needs retraining."""
        pass
```

### PersonaManager

```python
class PersonaManager:
    """Manage user interest personas (embedding clusters)."""

    async def get_personas(self, user_id: str) -> list[UserPersona]:
        """Load user's personas with current activity scores."""
        pass

    async def refresh_personas(
        self,
        user_id: str,
        video_embeddings: list[tuple[str, np.ndarray]],  # (video_id, embedding)
        k: int = 6,
    ) -> list[UserPersona]:
        """
        Re-cluster user's liked videos into personas.

        Uses k-means on embeddings, computes centroids,
        assigns activity scores based on recency.
        """
        pass

    async def update_activity(
        self,
        user_id: str,
        video_id: str,
        video_embedding: np.ndarray,
    ) -> None:
        """
        Update persona activity when user interacts with video.

        Finds closest persona, boosts its activity score.
        """
        pass

    async def decay_activities(self, user_id: str) -> None:
        """Apply time-based decay to all persona activities."""
        pass
```

### VideoScorer

```python
class VideoScorer:
    """Score videos using persona matching + metadata multipliers."""

    def score(
        self,
        video: VideoRec,
        personas: list[UserPersona],
        channel_prefs: dict[str, float],  # channel_id -> affinity
    ) -> VideoScore:
        """
        Score a video for recommendation.

        Returns:
            VideoScore with:
            - final_score: combined score
            - content_score: persona match (0-1)
            - matching_persona: best matching persona index
            - channel_boost: channel affinity multiplier
            - view_health: view count health multiplier
            - recency_factor: upload recency multiplier
        """
        pass

    def _persona_score(
        self,
        video_embedding: np.ndarray,
        personas: list[UserPersona],
    ) -> tuple[float, int]:
        """
        Compute content score from persona matching.

        Returns (score, best_persona_index).
        """
        scores = [
            cosine_sim(video_embedding, p.centroid) * p.activity_score
            for p in personas
        ]
        best_idx = np.argmax(scores)
        return scores[best_idx], best_idx

    def _channel_boost(
        self,
        channel_id: str,
        channel_prefs: dict[str, float],
    ) -> float:
        """Channel affinity multiplier (0.5 - 2.0)."""
        return channel_prefs.get(channel_id, 1.0)

    def _view_health(self, view_count: int) -> float:
        """
        View count health curve (0.7 - 1.2).

        Penalizes extremes: viral spam OR dead content.
        Sweet spot around 10k-500k views.
        """
        pass

    def _recency_factor(self, upload_date: datetime) -> float:
        """Upload recency multiplier (0.8 - 1.1)."""
        pass
```

### CategoryAgent

```python
class CategoryAgent:
    """Pydantic AI agent for category discovery."""

    async def suggest_categories(
        self,
        user_id: str,
        context: UserContext,
    ) -> list[CategorySuggestion]:
        """
        Analyze user behavior and content to suggest categories.

        Inputs:
        - Recent ratings (thumbs up/down)
        - Watch history patterns
        - Video tag clusters
        - Channel patterns

        Outputs:
        - Category name
        - Keywords to match
        - Reasoning ("You've watched 5 videos about...")
        """
        pass
```

## Duplicate Detection

Import pipeline must deduplicate across sources:

```python
async def import_with_dedup(
    user_id: str,
    video_ids: list[str],
    source: str,
) -> ImportResult:
    """
    Import videos, handling duplicates.

    Rules:
    1. If video not in video_rec: fetch metadata, add
    2. If video in video_rec: skip fetch, just add signal
    3. If signal already exists for user+video+type: skip
    4. Track import counts: new, existing, skipped
    """
    pass
```

## Queue Jobs

Background tasks via existing queue-worker:

```python
# Job types
class VideoDiscoveryJob(BaseJob):
    """Fetch new videos from YouTube API."""
    queries: list[str]
    max_per_query: int
    user_id: str

class TranscriptFetchJob(BaseJob):
    """Fetch transcript for a video."""
    video_id: str

class EmbeddingGenerationJob(BaseJob):
    """Generate embeddings for videos via Infinity."""
    video_ids: list[str]

class PersonaRefreshJob(BaseJob):
    """Re-cluster user's liked videos into personas."""
    user_id: str
    k: int = 6  # Number of clusters

class ActivityDecayJob(BaseJob):
    """Apply time-based decay to persona activities (scheduled daily)."""
    pass  # Runs for all users
```

## Integration Points

### Existing Infrastructure

| Component | Usage |
|-----------|-------|
| SurrealDB | All storage (new tables) |
| Queue Worker | Background jobs |
| Infinity | Embeddings (if using semantic similarity) |
| Auth | User identification (existing JWT) |

### New Components

| Component | Purpose |
|-----------|---------|
| YouTube API client | Video metadata + search |
| youtube-transcript-api | Transcript fetching |
| scikit-learn | k-means clustering for personas |
| PersonaManager | Manage user interest clusters |
| VideoScorer | Score videos with persona matching + metadata |
| CategoryAgent | Pydantic AI agent (Phase 6) |

## Error Handling

### API Errors
- YouTube quota exceeded: Return cached data, disable discovery
- Transcript unavailable: Store null, fall back to title/description embedding
- Personas not built: Return recency-sorted (fallback)
- Embedding service unavailable: Queue for retry, return cached scores

### UI Error States
- No videos: Empty state with "Import history" CTA
- All watched: "Discover more" CTA
- Personas building: "Learning your interests..." indicator
- No personas yet: "Rate more videos to build your profile" (need ~30)
- Quota exhausted: "Discovery paused until tomorrow"
