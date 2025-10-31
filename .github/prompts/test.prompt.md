---
mode: agent
model: gpt-5-mini
description: 'Run uv run pytest; report and fix failures. Prefer /check for full triage.'
---

# /test — Run Tests

## Steps
1) Run `uv run pytest -q`
2) Fix collection/execution failures; re-run until green
3) Prefer `/check` for full triage
