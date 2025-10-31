---
description: "Makefile standards"
applyTo: "**/Makefile"
---

# Makefile Standards

## Commands
- Avoid flags unless required; don’t add `-s`, `-j1` unprompted

## Targets
- Prefer real file targets over `.PHONY` when possible
- Group related targets; use `@` to reduce noise

## Background processes
- Send SIGTERM for graceful shutdown
- Use `--no-print-directory` for nested make calls

## Devcontainer integration
- Keep `.devcontainer/Makefile` for dev targets and include it

## Variables
- Export env vars for child processes; set defaults with `?=`
- Detect platform/runtime automatically; define variables at top
