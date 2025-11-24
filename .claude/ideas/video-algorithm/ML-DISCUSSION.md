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

## Comparison Table

| Aspect | RandomForest | Embeddings | Hybrid |
|--------|--------------|------------|--------|
| Minimum ratings | ~10 | ~30-50 | ~20 |
| Training time | Seconds | N/A (no training) | Seconds |
| Prediction time | Instant | Instant | Instant |
| Explainability | High | Low | Medium |
| Content understanding | None | High | Medium |
| New topic discovery | Poor | Good | Good |
| Implementation complexity | Low | Medium | High |
| We have infrastructure? | Yes (scikit-learn) | Yes (Infinity) | Yes |

---

## Recommendation for MVP

**Start with RandomForest** because:
1. Works with fewer ratings (faster cold start)
2. Explainable (helps debug)
3. Proven in the inspiration project

**Add embeddings in v2** when:
1. You have 50+ ratings
2. You want content-based discovery
3. RandomForest accuracy plateaus

**Hybrid is v3** when:
1. Both approaches are working
2. You want to experiment with combining them

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

1. **Which features matter most?**
   - Duration? Channel? Content keywords?
   - The RandomForest will tell us after training

2. **How much data do we have?**
   - Brave history: ~100s of watches
   - Takeout: ~1000s of watches
   - Is this enough?

3. **What's the baseline?**
   - Random recommendations: ~10% thumbs up?
   - Recency-based: ~30%?
   - Target: >60%

4. **Cold start strategy?**
   - Show popular videos until 10 ratings
   - Use imported watch history as "weak thumbs up"

5. **Retraining frequency?**
   - After every N new ratings? (N=10?)
   - Daily batch?
   - On-demand button?

---

## Next Steps

After discussion:
1. Decide MVP approach (likely RandomForest)
2. Define initial feature set
3. Design schema to support chosen features
4. Implement Phase 0 spike to validate

---

## Resources

- [scikit-learn RandomForest](https://scikit-learn.org/stable/modules/ensemble.html#forests-of-randomized-trees)
- [Original project's ML code](https://github.com/rosadiaznewyork/video-finder-algorithm/blob/main/src/ml/)
- Our embedding spec: `.claude/ideas/Recommendation Engine/embedding_pipeline_spec_for_coding_model.md`
