# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI agent spike project for exploration and development. Python-based CLI application using Typer, with a containerized development workflow using Docker/Podman.

## Development Environment

This project uses **devcontainer** for development. The recommended workflow is:

```bash
# Build and enter the devcontainer
make build-dev
```

The devcontainer is based on Python 3.14 and includes all development tools pre-installed (ruff, black, isort, mypy, pytest).

## Key Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run tests quietly (less verbose)
make test
```

### Code Quality
```bash
# Format code with black and isort
make format

# Lint code with ruff
make lint
```

### Dependencies
```bash
# Lock and sync dependencies (including dev)
uv lock
uv sync --dev
```

### Building and Running

```bash
# Build production image
make build

# Build with optimized caching (BuildX)
make buildx

# Run production container
make start    # Background
make up       # Foreground
make down     # Stop container
```

## Architecture

### Package Management
- Uses **uv** (modern Python package manager) instead of pip
- Dependencies defined in `pyproject.toml`
- Lock file: `uv.lock`

### Project Structure
```
src/
  app/
    cli.py          # Typer CLI entrypoint
```

The CLI is registered as `agent-spike` command via `project.scripts` in pyproject.toml.

### Container Architecture
Multi-stage Dockerfile with four stages:
1. **base**: Python 3.14 slim with uv installed, user setup, entrypoint script
2. **build-base**: Adds build tools (gcc, cmake, git, etc.)
3. **production**: Minimal runtime with only necessary dependencies
4. **devcontainer**: Full development environment with tools (zsh, ripgrep, gh, docker, etc.)

### Makefile System
Two-level Makefile structure:
- Root `Makefile`: Container builds, version management, deployment
- `.devcontainer/Makefile`: Development tasks (lint, test, format, clean)

The root Makefile includes `.devcontainer/Makefile`, so all dev commands are available from the root.

### Environment Variables
- Cross-platform OS detection (linux/macos/windows)
- Container runtime auto-detection (docker/podman)
- Host IP detection for networking
- Semantic versioning from git tags

## CLI Entry Point

The main CLI app is in `src/app/cli.py` using Typer. Currently has a single `hello` command. Add new commands by creating functions decorated with `@app.command()`.

## Python Configuration

- **Line length**: 88 (black standard)
- **Target version**: Python 3.14
- **Type checking**: mypy with strict mode enabled
- **Linting**: ruff with E, F, W, I, UP rules
- **Import sorting**: isort with black profile
