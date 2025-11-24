# ML Approaches Discussion Guide

**Purpose**: Educational document for understanding ML options for video recommendations
**Status**: Discussion topic for next session
**Last Updated**: 2025-11-24

## The Problem We're Solving

Given:
- A set of videos with metadata (title, channel, duration, tags, transcript)
- User signals (watched, thumbs up/down, not interested)

Predict:
- How likely is the user to enjoy a new video they haven't seen?

## Approach 1: RandomForest (The Original's Choice)

### What Is It?

RandomForest is a "ensemble" of decision trees. Think of it as asking 100 different experts to vote on whether you'll like a video.

```
Tree 1: "Duration > 10min AND channel = 'Nate Jones'? → Thumbs up"
Tree 2: "Has 'tutorial' in title AND views > 10K? → Thumbs up"
Tree 3: "Duration < 2min? → Thumbs down (you hate shorts)"
...
Final vote: 87 trees say thumbs up, 13 say thumbs down → 87% confidence
```

### How It Works

1. **Feature extraction**: Convert video into numbers
   - duration_minutes: 15.5
   - view_count_log: 4.7 (log10 of views)
   - has_tutorial_keyword: 1
   - channel_subscriber_tier: 2 (medium)
   - etc.

2. **Training**: Feed it videos you rated
   - "Video A with features [15.5, 4.7, 1, 2, ...] → thumbs_up"
   - "Video B with features [2.0, 3.1, 0, 1, ...] → thumbs_down"

3. **Prediction**: For new video, extract features → get probability

### Pros
- **Interpretable**: You can see which features matter ("duration is 40% of the decision")
- **Fast**: Training takes seconds, prediction is instant
- **Works with small data**: ~10-50 ratings is enough to start
- **Handles mixed data**: Numbers, categories, booleans all work

### Cons
- **Manual feature engineering**: You must decide what features to extract
- **Doesn't understand content**: Can't tell if two videos are about the same topic
- **Brittle to new patterns**: If you suddenly like a new topic, features might not capture it

### When To Use
- MVP with limited ratings
- When you want to understand why recommendations happen
- When features are well-defined (metadata-rich domain)

---

## Approach 2: Embedding Similarity

### What Is It?

Convert videos into points in high-dimensional space. Similar videos are nearby.

```
Video A (ESP32 tutorial) → [0.2, 0.8, 0.1, ..., 0.4]  (1024 numbers)
Video B (Arduino project) → [0.3, 0.7, 0.2, ..., 0.5]  (nearby!)
Video C (Cooking recipe)  → [0.9, 0.1, 0.8, ..., 0.2]  (far away)
```

### How It Works

1. **Embed videos**: Use a language model to convert transcript/title into a vector
   - We have this! Infinity service with bge-m3 produces 1024-dim vectors

2. **Embed user preferences**: Average the embeddings of liked videos
   - User profile = average([Video A embedding, Video D embedding, ...])

3. **Find similar**: Cosine similarity between user profile and candidate videos
   - "Video X is 0.89 similar to your profile → recommend"

### Pros
- **Understands content**: Knows "ESP32" and "Arduino" are related
- **No manual features**: Model figures out what matters
- **Handles new topics**: If you like one ESP32 video, finds others automatically

### Cons
- **Black box**: Hard to explain why a recommendation happened
- **Needs more data**: Works better with 50+ ratings
- **Compute cost**: Embedding generation isn't free (but we already have Infinity)

### When To Use
- Content-based discovery (find videos about similar topics)
- When transcript/content matters more than metadata
- When you have embedding infrastructure (we do!)

---

## Approach 3: Hybrid (RandomForest + Embeddings)

### What Is It?

Use embeddings as FEATURES for RandomForest. Best of both worlds.

```python
features = [
    duration_minutes,           # Traditional feature
    view_count_log,            # Traditional feature
    channel_affinity_score,    # Traditional feature
    *embedding[:50],           # First 50 dims of content embedding
    cosine_sim_to_profile,     # Similarity to user's liked videos
]
```

### How It Works

1. Extract traditional features (duration, views, etc.)
2. Generate content embedding
3. Compute similarity to user profile
4. Add embedding dimensions or similarity score as features
5. Train RandomForest on combined feature set

### Pros
- **Interpretable + semantic**: See feature importance AND capture content similarity
- **Flexible**: Can weight metadata vs content
- **Robust**: Falls back to metadata if content is weird

### Cons
- **Complexity**: Two systems to maintain
- **Feature selection**: Which embedding dimensions matter?
- **Overfitting risk**: Many features, need enough data

### When To Use
- When you want to experiment with both approaches
- When you have both good metadata AND good content
- Later stage (not MVP)

---

## Approach 4: Multi-Persona Embeddings ⭐ CHOSEN FOR MVP

### What Is It?

Instead of a single user profile, maintain **multiple interest personas** as embedding clusters. User's taste isn't one point in embedding space - it's several distinct clusters that activate/deactivate over time.

```
User Personas (k-means clusters of liked videos):
├── Persona 0: AI/ML projects      (centroid embedding, activity: 0.8)
├── Persona 1: Mini painting       (centroid embedding, activity: 0.3)
├── Persona 2: Homelab/self-host   (centroid embedding, activity: 0.1)
├── Persona 3: Woodworking         (centroid embedding, activity: 0.0)
└── Persona 4: Music production    (centroid embedding, activity: 0.2)
```

### How It Works

1. **Build personas**: Cluster user's historical liked videos using k-means on embeddings
2. **Track activity**: Recent watches in a cluster boost that cluster's activity score
3. **Score candidates**: For each new video:
   ```python
   # Find best-matching persona
   persona_scores = [
       cosine_sim(video_embedding, persona.centroid) * persona.activity
       for persona in user_personas
   ]
   content_score = max(persona_scores)

   # Apply metadata multipliers
   final_score = content_score * channel_boost * view_health_score
   ```
4. **Recommend**: Rank by final_score, filter watched videos

### Why This Over RandomForest

The original project (Gaurz) used RandomForest because:
- She didn't have embedding infrastructure
- She was starting from scratch
- She wanted explainability

**Our situation is different**:
- We have Infinity for embeddings (already running)
- We have transcripts archived
- We care about **content similarity** more than metadata patterns
- We have **diverse, temporal interests** that don't fit a single profile

RandomForest optimizes for "what metadata features predict thumbs-up?" but we actually know what matters:
- Content similarity (embeddings)
- Channel affinity (simple lookup)
- View count health (simple curve)

No need to learn these relationships - we can encode them directly.

### Pros
- **Handles diverse interests**: Each persona captures a distinct interest area
- **Temporal adaptation**: Activity scores let current interests surface
- **Dormant interests preserved**: Old personas don't disappear, just go quiet
- **Content-aware**: Knows "ESP32" and "Arduino" are related without manual keywords
- **Leverages existing infrastructure**: Infinity embeddings, transcript archive

### Cons
- **Cold start harder than RandomForest**: Need ~30-50 rated videos for meaningful clusters
- **Cluster count (k) is a hyperparameter**: Too few = muddy, too many = fragmented
- **Black box for "why"**: Can't easily explain recommendations (v2 problem)
- **Naive averaging within clusters**: Outliers can skew centroids

### When To Use
- When user has diverse, distinct interest areas
- When content understanding matters more than metadata patterns
- When embedding infrastructure already exists
- When interests change over time (ebb and flow)

### Metadata as Multipliers

Metadata isn't ignored - it modifies the content score:

| Factor | Implementation | Effect |
|--------|----------------|--------|
| Channel affinity | Lookup: subscription, watch history, thumbs ratio | 0.5x to 2.0x boost |
| View count health | Sigmoid curve: penalize extremes (viral spam OR dead content) | 0.7x to 1.2x |
| Recency | Days since upload, decay curve | 0.8x to 1.1x |

```python
final_score = (
    content_score          # From persona matching
    * channel_boost        # 0.5 - 2.0
    * view_health          # 0.7 - 1.2
    * recency_factor       # 0.8 - 1.1
)
```

### Activity Score Decay

Personas have activity scores that:
- **Increase** when user watches/likes videos in that cluster
- **Decay** over time (exponential decay, half-life ~2 weeks?)
- **Never reach zero** (dormant interests can resurface)

```python
activity = base_activity * exp(-days_since_last_watch / half_life) + floor
```

This prevents the "one F1 video = forever F1 recommendations" problem.

---

## Comparison Table

| Aspect | RandomForest | Single Embedding | Hybrid | Multi-Persona ⭐ |
|--------|--------------|------------------|--------|-----------------|
| Minimum ratings | ~10 | ~30-50 | ~20 | ~30-50 |
| Training time | Seconds | N/A | Seconds | Seconds (k-means) |
| Prediction time | Instant | Instant | Instant | Instant |
| Explainability | High | Low | Medium | Low (v2 problem) |
| Content understanding | None | High | Medium | High |
| New topic discovery | Poor | Good | Good | Good |
| Diverse interests | Poor | Poor | Medium | **Excellent** |
| Temporal adaptation | None | None | None | **Built-in** |
| Implementation complexity | Low | Medium | High | Medium |
| We have infrastructure? | Yes | Yes (Infinity) | Yes | Yes (Infinity) |

---

## Recommendation for MVP

**Start with Multi-Persona Embeddings** because:
1. Handles diverse, temporal interests (which we have)
2. Leverages existing Infinity infrastructure
3. Content understanding without manual feature engineering
4. Metadata can be added as multipliers without ML complexity

**Why not RandomForest (the original project's choice)?**
- The original (Gaurz) didn't have embedding infrastructure - we do
- She optimized for explainability - we're okay deferring that to v2
- Single-user profile doesn't capture our diverse interests

**Explainability is v2** when:
1. Persona clustering is validated
2. System is producing good recommendations
3. We want to surface "why this video?" in the UI

---

## Feature Ideas for RandomForest

Based on the original project + our infrastructure:

### Metadata Features
| Feature | Type | Source |
|---------|------|--------|
| duration_bucket | category | YouTube API |
| view_count_log | float | YouTube API |
| like_ratio | float | YouTube API |
| upload_recency_days | int | YouTube API |
| channel_subscriber_tier | category | YouTube API |
| has_transcript | bool | youtube-transcript-api |

### Channel Features
| Feature | Type | Source |
|---------|------|--------|
| channel_affinity | float | User signals |
| channel_videos_watched | int | User signals |
| channel_thumbs_up_ratio | float | User signals |

### Content Features (needs transcript)
| Feature | Type | Source |
|---------|------|--------|
| contains_keyword_X | bool | Transcript parsing |
| topic_category | category | LLM tagging |
| tutorial_score | float | Keyword density |

### User-relative Features
| Feature | Type | Source |
|---------|------|--------|
| category_match_score | float | Category keywords |
| similar_to_liked | float | Embedding similarity |

---

## Discussion Questions

1. **How many personas (k)?**
   - Too few (k=3): muddy clusters mixing interests
   - Too many (k=15): fragmented, sparse clusters
   - Start with k=5-8, tune based on silhouette score and manual inspection

2. **How much data do we have?**
   - Brave history: ~100s of watches
   - Takeout: ~1000s of watches
   - **Scoped to**: Last 3 months + 50 random historical videos

3. **What's the baseline?**
   - Random recommendations: ~10% thumbs up?
   - Recency-based: ~30%?
   - Target: >60%

4. **Cold start strategy?**
   - Import Brave + Takeout as "weak thumbs up" signals
   - 3 months of history should provide enough for initial clustering
   - 50 random historical videos add diversity for dormant interests

5. **Activity decay parameters?**
   - Half-life: ~2 weeks? (tune based on actual usage)
   - Floor: 0.1? (dormant but not dead)

6. **Cluster refresh frequency?**
   - On-demand via UI button?
   - After N new ratings?
   - Weekly batch?

---

## Next Steps

**Decided**: Multi-Persona Embeddings approach for MVP

Phase 0 spike:
1. Extract video IDs from Brave + Takeout (3 months + 50 random older)
2. Fetch transcripts for videos not in archive (respect rate limits)
3. Generate embeddings via Infinity
4. Cluster into personas (k-means, k=5-8)
5. Validate: do clusters represent coherent interests?
6. Test: does max-similarity-to-active-persona scoring work?

---

## Resources

- [scikit-learn RandomForest](https://scikit-learn.org/stable/modules/ensemble.html#forests-of-randomized-trees)
- [Original project's ML code](https://github.com/rosadiaznewyork/video-finder-algorithm/blob/main/src/ml/)
- Our embedding spec: `.claude/ideas/Recommendation Engine/embedding_pipeline_spec_for_coding_model.md`
