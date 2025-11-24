# Video Recommendation System

**Status**: Planning
**Created**: 2025-11-24
**Inspiration**: [video-finder-algorithm](https://github.com/rosadiaznewyork/video-finder-algorithm) + [ChrisJol/MyTube](https://github.com/ChrisJol/MyTube)

## Vision

Personal YouTube home page that shows **unwatched videos from topics you enjoy** - not just subscriptions. Discovery beyond your bubble, filtered by your actual interests.

## Documents

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Product requirements, MVP scope, user stories |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical design, schema, APIs |
| [DATA-SOURCES.md](DATA-SOURCES.md) | Import strategies, signal collection |
| [ML-DISCUSSION.md](ML-DISCUSSION.md) | ML approaches education (discussion guide) |
| [IMPLEMENTATION-PHASES.md](IMPLEMENTATION-PHASES.md) | Phased rollout plan |
| [DEFERRED.md](DEFERRED.md) | Explicit v2 backlog |

## Quick Summary

### What We're Building

- `/videos` route in existing SvelteKit frontend
- YouTube video recommendations based on learned preferences
- Agent-driven category discovery (not manual config)
- Thumbs up/down + implicit watch signals

### Key Differentiators from Original

| Original | Ours |
|----------|------|
| Manual category config (config.ini) | Agent suggests categories |
| SQLite standalone | SurrealDB integrated |
| CLI + web | Web only |
| Single content type | Designed for multi-source (YouTube MVP) |

### MVP Scope

**In scope:**
- Unwatched video display with topic filtering
- Brave history + Google Takeout import
- YouTube API discovery
- RandomForest preference learning
- Thumbs rating
- On-demand category suggestions

**Deferred to v2:**
- Interest graph visualization
- Smart playlists
- Multi-user + BYOK
- Rich "not interested" feedback
- Background agent triggers

## Related Context

- [VISION.md](../../VISION.md) - Long-term project vision
- [Recommendation Engine ideas](../Recommendation%20Engine/) - Embedding strategies
- [orchestrator/](../orchestrator/) - Agent patterns
