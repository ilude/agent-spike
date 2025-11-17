# ==============================================================================
# Multi-stage Dockerfile for optimized caching and fast rebuilds
# ==============================================================================
#
# Stage 1: Base image with system dependencies
# Stage 2: Dependencies layer (heavy, cached unless pyproject.toml changes)
# Stage 3: Runtime layer (lightweight, rebuilds on code changes)
#
# Benefits:
# - Code changes only rebuild stage 3 (~seconds)
# - Dependency changes rebuild stages 2-3 (~minutes)
# - System dependency changes rebuild all stages (~rare)

# ==============================================================================
# Stage 1: Base - System dependencies
# ==============================================================================
FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv


# ==============================================================================
# Stage 2: Dependencies - Python packages (CACHED)
# ==============================================================================
FROM base AS dependencies

# Copy only dependency files (changes rarely)
COPY pyproject.toml .
COPY .python-version .

# Install lightweight API dependencies (no PyTorch/CUDA)
# This layer is cached and only rebuilds when pyproject.toml changes
RUN uv sync --group platform-api

# ==============================================================================
# Stage 3: Runtime - Application code (FAST REBUILD)
# ==============================================================================
FROM dependencies AS runtime

# Copy application code (changes frequently)
# Because dependencies are already installed in previous stage,
# this layer is tiny and rebuilds in seconds
#
# IMPORTANT: Copy to /app/src to avoid shadowing stdlib 'platform' module
COPY compose/ ./src/compose/
COPY tools/ ./src/tools/

# Set Python path to /app/src (avoids shadowing stdlib modules)
ENV PYTHONPATH=/app/src

# Change working directory for uv run
WORKDIR /app/src

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2.0)" || exit 1

# Run FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "compose.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
