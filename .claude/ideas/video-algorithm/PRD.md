# Product Requirements Document: Video Recommendation System

**Version**: 1.0 (MVP)
**Last Updated**: 2025-11-24

## Problem Statement

YouTube's recommendation algorithm optimizes for engagement, not user value. It:
- Pushes content from subscriptions you rarely watch
- Creates filter bubbles limiting discovery
- Shows videos you've already seen
- Doesn't understand your actual interests beyond watch history

**Result**: Hours wasted scrolling, missing content you'd actually enjoy.

## Solution

A personal video recommendation engine that:
1. Learns your preferences from multiple signals (not just watch history)
2. Discovers content beyond your subscriptions
3. Filters out watched videos
4. Uses agents to suggest and refine content categories
5. Gives you control via explicit feedback

## User Stories

### Core Experience

**US-1: Home Page**
> As a user, I want to see a page of unwatched videos matching my interests, so I can quickly find something worth watching.

Acceptance criteria:
- Videos I've watched are never shown
- Videos are ranked by predicted interest
- Topics I enjoy are represented
- New creators appear (not just subscriptions)

**US-2: Thumbs Rating**
> As a user, I want to thumbs up/down videos, so the system learns my preferences.

Acceptance criteria:
- Single click thumbs up/down
- Rating persists and influences future recommendations
- Can undo a rating

**US-3: Topic Filtering**
> As a user, I want to filter by topic, so I can focus on one interest area.

Acceptance criteria:
- Topics derived from my preference profile
- Selecting a topic shows only matching videos
- Can clear filter to see all

**US-4: Category Suggestions**
> As a user, I want the system to suggest new categories based on my behavior, so I discover interests I didn't know I had.

Acceptance criteria:
- "Suggest categories" button triggers agent analysis
- Agent examines my ratings, watches, and video content
- Suggestions include reasoning ("You've watched 5 videos about ESP32...")
- I can accept or dismiss suggestions

### Data Import

**US-5: Brave History Import**
> As a user, I want to import my browser history, so the system has initial data about what I watch.

**US-6: Google Takeout Import**
> As a user, I want to import my YouTube history export, so the system has comprehensive watch data.

**US-7: Mentat Ingest Signal**
> As a user, when I paste a YouTube URL into Mentat for transcription, that should count as interest in that content.

### Edge Cases

**US-8: Empty State**
> As a new user with no history, I want to see popular videos across categories, so I can start rating and training the system.

Acceptance criteria:
- Show diverse sample of recent popular videos
- Prompt user to rate a few to get started
- Display "Rate 10 videos to unlock personalized recommendations"

**US-9: All Watched State**
> As a user who has watched all recommended videos, I want to see a clear message and options, not an empty page.

Acceptance criteria:
- "You've seen everything! Time to discover more."
- Button to fetch new videos from YouTube API
- Option to expand topic scope

**US-10: Not Interested**
> As a user, I want to mark a video as "not interested" with a reason, so I can train the system on negative preferences.

MVP: Simple "not interested" button (hides video, negative signal)
v2: Rich reasons (already watched, topic not interesting, poor quality, clickbait)

## Functional Requirements

### FR-1: Video Display
- Show video thumbnail, title, channel, duration, upload date
- Show predicted confidence score (0-100%)
- Watched indicator (if in history but somehow shown)
- Thumbs up/down buttons
- "Not interested" button

### FR-2: Filtering & Sorting
- Filter by topic/category
- Sort by: confidence, recency, duration
- Hide watched videos (default on)

### FR-3: YouTube API Integration
- Fetch videos via YouTube Data API v3
- Respect quota limits (~2-3K units/day for scheduled batches)
- Fetch transcripts via youtube-transcript-api
- Queue background jobs for batch discovery

### FR-4: Preference Learning
- Multi-persona embedding model using k-means clustering
- User interests clustered into distinct personas (AI, homelab, etc.)
- Scoring: persona similarity × activity weight × metadata multipliers
- Personas refresh when sufficient new ratings collected
- Minimum threshold before predictions (~30 rated videos)

### FR-5: Category Agent
- On-demand invocation via UI button
- Analyzes: rating patterns, watch history, video content clusters
- Outputs: suggested categories with reasoning
- User can accept/dismiss suggestions

## Non-Functional Requirements

### NFR-1: Performance
- Home page loads in <2 seconds
- Rating response is instant (optimistic UI)
- Background jobs don't block UI

### NFR-2: Data Privacy
- All data stored locally (SurrealDB on your server)
- YouTube API key is user-provided (BYOK for multi-user)
- No data sent to third parties except YouTube API

### NFR-3: Quota Efficiency
- Batch API calls to minimize quota usage
- Cache video metadata
- Show quota usage in UI

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to find interesting video | <30 seconds |
| Recommendation accuracy (thumbs up rate) | >60% |
| Daily active usage | User returns daily |
| Category agent usefulness | Accepted suggestions >40% |

## Out of Scope (v1)

See [DEFERRED.md](DEFERRED.md) for full backlog:
- Interest graph visualization
- Smart playlists
- Multi-user support
- Rich "not interested" feedback
- Background/event-driven agent triggers
- Multi-source content (blogs, podcasts)
