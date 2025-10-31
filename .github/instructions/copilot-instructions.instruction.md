---
applyTo:
  - ".github/instructions/*.instruction.md"
---

# Copilot Instruction Files — Guidelines

## Purpose
- Create targeted instruction files for specific file types, tools, or workflows

## Structure
- File name: `<topic>.instruction.md`
- Frontmatter with `applyTo` patterns
- Content: purpose, rules/standards, tool usage, validation

## Patterns (examples)
- `**/*.py` — Python files
- `tests/**/*.py` — Test files
- `src/app/**/*.py` — App module files
- `Makefile` — Makefile
- `pyproject.toml` — Python config

## Principles
- One instruction per domain
- Specific `applyTo` globs
- Reference project tools and avoid duplication
