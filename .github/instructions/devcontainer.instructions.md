---
description: "DevContainer configuration best practices for development environment"
applyTo: "**/.devcontainer/**"
---

# DevContainer Development Standards

Begin with a concise checklist (3-7 bullets) of what you will do; keep items conceptual, not implementation-level.

## Python Runtime and Environment
- Use Python 3.14 inside the devcontainer.
- Manage dependencies exclusively with `uv` (no virtualenv activation and no `.venv`).
- Prefer `uv run` for all Python execution.

## Container Configuration
- Use a multi-stage Dockerfile with a dedicated development target.
- Include Docker-in-Docker feature for container testing.
- Mount Docker socket for container integration testing.
- Use a non-root user (`anvil`) for improved security.

## Environment Management
- Load both the root `.env` and `.devcontainer/.env` files via `runArgs`.
- Initialize environment with `make initialize`, using the `initializeCommand` in `devcontainer.json`.
- The `.devcontainer/.env` file will be created by `make initialize`.

## Development Tools
- Configure `zsh` with autosuggestions for enhanced developer experience.
- Automatically install language development dependencies.
- Set up proper VS Code extensions and settings.

## Volumes
- Persist the home directory.
- Mount SSH keys.

## Post-create Steps
- Run `./.devcontainer/setup-dotfiles.sh`.
- Update language libraries.
- Prepare testing infrastructure.

After each configuration change or setup script, validate that the desired environment state is achieved, and document or self-correct any deviations.
