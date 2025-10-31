---
mode: agent
model: gpt-5-mini
description: 'Run lint with uv; prefer /check for full triage.'
---

# /lint — Linting

## Steps
1) Run `uv run ruff check .`; fix issues; re-run until clean
2) Optionally run `uv run mypy src`
3) Prefer `/check` for tests-first triage
2) Optionally run `uv run mypy src`
