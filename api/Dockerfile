FROM python:3.14-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY .python-version .

# Install dependencies
# Note: This will create .venv in the image, but in dev we'll mount the host .venv
RUN uv sync --group api

# Copy application code
# Note: In development, this will be overridden by volume mount
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
