---
description: "Dockerfile best practices"
applyTo: "**/Dockerfile*"
---

# Dockerfile Standards

### Base Images
- Use Alpine Linux containers for minimal attack surface, unless there are issues installing a needed package, then use Debian Slim based containers.
- Specify version tags for reproducible builds

### Multi-stage Builds
- Separate base/development/production stages
- Copy only necessary artifacts to final stage

### Security
- Create a non-root user
- Set USER before EXPOSE and CMD
- Never include secrets

### Layer Optimization
- Group RUN commands to reduce layers
- Use `--no-cache` and clean package caches
- Copy requirements files separately for better caching
- Order commands from least to most frequently changing

### Package Organization
- Keep apk/apt packages alphabetical

### Environment Variables
- Use ARG for build-time variables (PUID, PGID, USER, WORKDIR)
- Use ENV for runtime variables
- Provide sensible defaults

### Health Checks
- Include health checks for orchestration
- Use lightweight commands (curl/wget)
- Set appropriate intervals and timeouts

### BuildKit Features
- Use cache mounts for RUN commands

### Build Performance
- Order COPY operations from least to most frequently changing
- Copy dependency files (requirements.txt, pyproject.toml, package.json) before source code
- Use cache mounts for package managers: `--mount=type=cache,target=/root/.cache/pip`
- Implement multi-stage builds with dedicated dependency stages
- Pin base image versions to exact patches for consistent caching
- Use BuildKit cache exports for CI/CD: `--cache-to=type=registry` and `--cache-from=type=registry`
- Keep .dockerignore comprehensive to minimize build context

### Build Context
- Maintain comprehensive .dockerignore files
- Exclude: tests/, .git/, __pycache__/, *.pyc, .coverage/, notebooks/, .spec/
- Include only necessary files in build context
- Regularly audit .dockerignore for new directories

## Entrypoints
- Use `exec` form to forward signals
- Drop root privileges in entrypoint when applicable
