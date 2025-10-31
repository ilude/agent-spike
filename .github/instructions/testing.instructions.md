---
description: "Testing standards (uv, Python 3.14)"
applyTo: "**/tests/**/*.py"
---

# Testing Standards (uv, Python 3.14)

## Execution
- Use `uv run pytest` only (never call pytest directly)
- If available, `make test` may be used for consistent execution

## Strategy
- Test public APIs only
- Install missing dev deps with `uv add --dev` (avoid skips)
- If files are deleted: move skip() before imports; delete unsalvageable tests
