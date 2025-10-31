---
description: "Python coding standards (uv, Python 3.14)"
applyTo: "**/*.py"
---

# Python Standards (uv, Python 3.14)

## Tooling
- Use uv only: `uv run pytest`, `uv add <pkg>`, `uv run`
- Don’t call pytest or python directly
- Install: prod `uv add <pkg>`; dev `uv add --dev <pkg>`; notebooks `uv add --group notebook <pkg>`

## Practices
- Verify files exist before edits; don’t recreate deleted files
- If files are deleted: update imports; in tests, move skip() before imports; delete unsalvageable tests

## Style
- PEP 8, Black (line length 88), isort (Black profile)
- 4-space indentation; two blank lines before top-level defs
