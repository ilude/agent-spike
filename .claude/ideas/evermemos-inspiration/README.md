# EverMemOS Inspiration

**Created**: 2025-11-22
**Source**: https://github.com/EverMind-AI/EverMemOS
**Status**: Research complete, integration opportunities identified

**IMPORTANT**: This directory contains research and comparison notes. References to Qdrant have been updated to SurrealDB (current architecture). Historical context preserved for reference.

---

## What Is EverMemOS?

An open-source **enterprise-grade AI memory system** that provides conversational AI with persistent, contextual memory capabilities. Their tagline: "AI memory that never forgets, making every conversation built on previous understanding."

### Key Stats
- 578+ GitHub stars
- 92.3% reasoning accuracy on LoCoMo benchmark
- Apache 2.0 licensed

---

## Why It's Relevant to Agent-Spike

EverMemOS solves similar problems to our VISION.md goals:

| Their Problem | Our Problem |
|---------------|-------------|
| Conversations lack persistent memory | Content insights get lost |
| Isolated fragments, no narrative | No connection between learnings and projects |
| No proactive recall | Manual effort to apply learned concepts |
| Static user profiles | Preferences don't evolve |

Their **Memory Construction + Memory Perception** architecture maps well to our **Content Ingestion + Recommendation Engine** goals.

---

## Quick Links

- **Full Comparison**: [COMPARISON.md](COMPARISON.md)
- **What to Borrow**: [BORROWING-OPPORTUNITIES.md](BORROWING-OPPORTUNITIES.md)
- **Implementation Plan**: [INTEGRATION-ROADMAP.md](INTEGRATION-ROADMAP.md)
- **Technical Notes**: [EVERMEMOS-NOTES.md](EVERMEMOS-NOTES.md)

---

## TL;DR - Top 3 Borrowing Opportunities

1. **MemCell Extraction**: Extract atomic "insights" from content (not just tags)
2. **7 Memory Types**: Richer taxonomy than content/preferences split
3. **Living Profiles**: Evolve persona vectors with each interaction

See [BORROWING-OPPORTUNITIES.md](BORROWING-OPPORTUNITIES.md) for details.
