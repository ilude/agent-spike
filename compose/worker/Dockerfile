# Queue processor worker container
# Polls pending/ directory for CSV files and processes them

FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for package management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY .python-version .

# Install dependencies (same as API - shares the platform-api group)
RUN uv sync --group platform-api

# Copy application code
COPY compose/ ./src/compose/
COPY tools/ ./src/tools/

WORKDIR /app/src

# Run the queue processor
CMD ["uv", "run", "python", "-m", "compose.worker.queue_processor"]
