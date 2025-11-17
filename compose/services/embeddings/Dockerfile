# ==============================================================================
# Embedding Service - Heavy ML container with PyTorch/CUDA
# ==============================================================================
#
# This service handles:
# - Generating embeddings via sentence-transformers
# - PyTorch model inference
# - CUDA acceleration (if available)
#
# Size: ~14GB (includes PyTorch + CUDA libraries)
# Rebuild time: ~10min first build, ~seconds on code changes

# ==============================================================================
# Stage 1: Base - System dependencies
# ==============================================================================
FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies needed for ML packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv


# ==============================================================================
# Stage 2: ML Dependencies - PyTorch + CUDA (HEAVY, CACHED)
# ==============================================================================
FROM base AS dependencies

# Copy dependency files
COPY pyproject.toml .
COPY .python-version .

# Install heavy ML dependencies (PyTorch, sentence-transformers, CUDA)
# This layer is ~14GB and takes ~10min to build
# But it's cached and only rebuilds when dependencies change
RUN uv sync --group platform-embeddings


# ==============================================================================
# Stage 3: Runtime - Application code (FAST REBUILD)
# ==============================================================================
FROM dependencies AS runtime

# Copy application code
COPY platform/ ./platform/
COPY tools/ ./tools/

# Set Python path
ENV PYTHONPATH=/app

# Expose service port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health', timeout=2.0)" || exit 1

# Run embedding service
CMD ["uv", "run", "uvicorn", "platform.services.embeddings.api:app", "--host", "0.0.0.0", "--port", "8001"]
