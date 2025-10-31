---
applyTo:
  - ".github/prompts/*.prompt.md"
---

# Copilot Prompt Files — Guidelines

## Purpose
- Create focused prompts for repeatable tasks and workflows

## Structure
- File name: `<task>.prompt.md`
- Frontmatter: `description`
- Content: objective, minimal context, clear step-by-step instructions

## Tools (uv-first)
- `uv run pytest` — tests
- `uv run ruff check .` — lint
- `uv run mypy src` — type check
- Optional: `make check` as a final gate if present

## Content checklist
- Objective
- Minimal context
- Clear steps
