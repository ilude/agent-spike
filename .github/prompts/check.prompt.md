---
mode: 'agent'
model: gpt-5-mini
description: 'Unified quality gate: run uv run pytest; triage and fix failures; optionally run lint (isort/black/flake8). Keep changes minimal and avoid unnecessary flags.'
---

# Quality Check and Fix

## Objective
Run `uv run pytest -q` and systematically address any test collection/execution failures until the suite passes cleanly. Optionally, run lint (isort/black/flake8) and fix high-signal issues.

## Context
- Project uses uv; tests are executed with `uv run pytest` (no Make targets required)
- Primary quality gate: tests green. Lint checks are optional if configured
- Constraints from repository instructions:
  - Use `uv run pytest` (do not add `-m`)
  - Do not prefix commands with `cd`
  - Prefer small, surgical fixes that preserve behavior
 - If a Makefile provides a `check` target, you may run it as a final comprehensive gate after tests are green
