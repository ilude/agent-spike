# Deferred Features (v2+ Backlog)

**Purpose**: Explicit documentation of what we're NOT building in MVP
**Last Updated**: 2025-11-24

## Why This Document Exists

Scope creep kills projects. By explicitly documenting what's deferred, we:
1. Acknowledge these are valid ideas
2. Commit to not building them now
3. Have a clear backlog for future work
4. Can revisit decisions with context

---

## Tier 1: High Value, Deferred for Simplicity

### Interest Graph Visualization

**What**: Visual map showing topic relationships and interest levels
```
         ┌─ ESP32 (80%)
         │
Home ────┼─ Arduino (70%)
Automation│
         └─ Raspberry Pi (60%)

         ┌─ Hand tools (50%)
Woodworking──┤
         └─ Joinery (40%)
```

**Why deferred**:
- Requires graph visualization library
- Text list of topics with percentages works for MVP
- Can add later without changing core architecture

**Trigger to build**: When you have 10+ categories and want to see relationships

### Smart Playlists

**What**: Auto-generated collections based on patterns
- "Your ESP32 rabbit hole" (sequential videos)
- "Weekend DIY projects" (short, practical)
- "Deep dives you'll actually finish" (high completion signals)

**Why deferred**:
- Requires playlist data model
- Needs viewing pattern analysis
- Topic filtering covers 80% of the need

**Trigger to build**: When simple topic filters feel limiting

### Rich "Not Interested" Feedback

**What**: Reasons for negative signals
```
Not interested because:
○ Already watched
○ Topic not interesting
○ Poor quality
○ Clickbait
○ Wrong difficulty level
○ Other: ________
```

**Why deferred**:
- Simple not-interested button works for MVP
- Adds UI complexity
- Need enough data to make reasons useful

**Trigger to build**: When model accuracy plateaus and you need more signal

---

## Tier 2: Architectural Enhancements

### Multi-User + BYOK (Bring Your Own Key)

**What**: Multiple users with separate preferences, each providing their own YouTube API key

**Current state**: Single user, API key in environment

**Why deferred**:
- Only you are using it now
- Adds auth complexity to every endpoint
- Quota management becomes per-user

**Trigger to build**: When someone else wants to use it

### Protocol Abstractions for Swappable Algorithms

**What**:
```python
class RecommendationAlgorithm(Protocol):
    def train(self, signals: list[Signal]) -> None: ...
    def predict(self, video: Video) -> float: ...

class RandomForestAlgorithm(RecommendationAlgorithm): ...
class EmbeddingSimilarity(RecommendationAlgorithm): ...
```

**Current state**: Direct RandomForest implementation

**Why deferred**:
- Premature abstraction
- Extract interface when second algorithm exists
- YAGNI until proven needed

**Trigger to build**: When adding embedding-based approach

### Background Agent Triggers

**What**: Agent runs automatically based on events
- After N new ratings
- Daily scheduled analysis
- When new topic cluster detected

**Current state**: On-demand "Suggest categories" button only

**Why deferred**:
- On-demand covers the need
- Background adds complexity
- Easier to debug when user-triggered

**Trigger to build**: When you forget to click the button and miss insights

### Event-Driven Agent Triggers

**What**: Agent reacts to real-time signals
- "You just thumbs-upped 3 ESP32 videos in a row"
- "New category detected: 3D printing"

**Current state**: No real-time analysis

**Why deferred**:
- Requires event streaming infrastructure
- On-demand + background covers most needs
- Higher complexity

**Trigger to build**: When you want proactive notifications

---

## Tier 3: Multi-Source Content

### Blog/Article Support

**What**: Ingest and recommend blog posts, not just videos

**Why deferred**:
- Different content type = different features
- YouTube is the immediate pain point
- Can add content_type field later

**Trigger to build**: After video recommendations are solid

### Podcast Support

**What**: Recommend podcasts with transcript analysis

**Why deferred**:
- Needs audio transcription (Whisper)
- Different discovery APIs
- Different consumption patterns

**Trigger to build**: If podcasts become part of learning workflow

### RSS Feed Monitoring

**What**: Monitor RSS feeds for new content automatically

**Why deferred**:
- Polling infrastructure
- Many YouTube channels have RSS feeds (future discovery method)
- Manual discovery works for MVP

**Trigger to build**: When you want automated content monitoring

---

## Tier 4: Advanced ML

### Embedding-Based Recommendations

**What**: Use content embeddings (bge-m3) for semantic similarity

**Current approach**: RandomForest with extracted features

**Why deferred**:
- RandomForest works with less data
- More explainable
- Embeddings are v2 enhancement

**Trigger to build**: When RandomForest accuracy plateaus

### Hybrid RandomForest + Embeddings

**What**: Combine metadata features with embedding similarity

**Why deferred**:
- Complexity of two systems
- Need to prove each works alone first

**Trigger to build**: After both approaches tested independently

### Collaborative Filtering

**What**: "Users like you also liked..."

**Why deferred**:
- Requires multi-user data
- You're the only user

**Trigger to build**: If/when multi-user is added

---

## Tier 5: UX Enhancements

### Mobile Responsive Design

**What**: Optimized layout for phone/tablet

**Current state**: Desktop-first

**Why deferred**:
- Primary use is desktop
- Can add responsive later

**Trigger to build**: When you want to browse on phone

### Video Preview on Hover

**What**: Play video preview on thumbnail hover (like YouTube)

**Why deferred**:
- Requires video preview infrastructure
- Nice-to-have, not essential

**Trigger to build**: When browsing feels slow

### Keyboard Navigation

**What**: j/k to navigate, u/d to rate, enter to open

**Why deferred**:
- Mouse works fine
- Adds accessibility

**Trigger to build**: Power user request

### Watch Later Queue

**What**: Save videos for later without rating

**Why deferred**:
- Topic filtering + hide watched covers most needs
- Adds state management

**Trigger to build**: When you want to queue without committing

---

## Review Criteria

When considering building a deferred feature, ask:

1. **Is the trigger condition met?**
2. **Does MVP feel limiting without it?**
3. **Is the effort worth the value?**
4. **Does it require architectural changes?**
5. **Can we add it incrementally?**

---

## Document History

| Date | Change |
|------|--------|
| 2025-11-24 | Initial creation from scope-boundary analysis |
