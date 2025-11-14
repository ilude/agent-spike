# Multi-stage build for Mentat backend
# Uses Alpine for minimal image size and security

# Stage 1: Builder - Install dependencies
FROM python:3.14-alpine AS builder

# Install system dependencies needed for Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    curl

# Install uv package manager
RUN pip install --no-cache-dir uv

WORKDIR /build

# Copy dependency files
COPY ../../pyproject.toml ../../uv.lock ./

# Install dependencies using uv (faster than pip)
# --no-dev excludes development dependencies for production
RUN uv sync --no-dev

# Stage 2: Development
FROM python:3.14-alpine AS development

# Install curl for health checks
RUN apk add --no-cache curl

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /workspace

# Copy virtual environment from builder
COPY --from=builder /build/.venv /workspace/.venv

# Copy application code (will be overridden by volume mount in dev)
COPY . /workspace/

# Set PATH to use virtual environment
ENV PATH="/workspace/.venv/bin:$PATH" \
    PYTHONPATH="/workspace:$PYTHONPATH" \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8001/health || exit 1

# Development command with hot reload
CMD python -m uvicorn projects.mentat.api.main:app --host 0.0.0.0 --port 8001 --reload

# Stage 3: Production
FROM python:3.14-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy only necessary application code
COPY projects/mentat/api /app/projects/mentat/api
COPY tools /app/tools

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8001/health || exit 1

# Production command (no reload)
CMD python -m uvicorn projects.mentat.api.main:app --host 0.0.0.0 --port 8001
