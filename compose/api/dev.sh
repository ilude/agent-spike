#!/bin/bash
# Hot-reload development server for FastAPI

set -e

cd "$(dirname "$0")/.."

echo "Starting FastAPI development server with hot reload..."
echo "API will be available at: http://localhost:8000"
echo "Swagger docs at: http://localhost:8000/docs"
echo ""

uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
