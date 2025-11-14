# Mentat - Docker Compose Development Commands
#
# Quick start:
#   make build    - Build Docker images
#   make up       - Start everything with Docker Compose
#   make down     - Stop everything
#   make logs     - View container logs

.PHONY: help build up down restart logs ps clean install browser

# Configuration
BACKEND_PORT = 8001
FRONTEND_PORT = 5173

# Default target - show help
help:
	@echo "Mentat - Docker Compose Commands"
	@echo ""
	@echo "Docker Compose (Recommended):"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services (detached)"
	@echo "  make down     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - Follow container logs"
	@echo "  make ps       - Show container status"
	@echo "  make browser  - Open browser to frontend"
	@echo ""
	@echo "Local Development (Alternative):"
	@echo "  make local-install  - Install dependencies locally"
	@echo "  make local-backend  - Run backend locally (no Docker)"
	@echo "  make local-frontend - Run frontend locally (no Docker)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean    - Remove containers, volumes, and images"

# Build Docker images
build:
	@echo "Building Docker images..."
	@docker compose build

# Start services with Docker Compose
up: build
	@echo "Starting Mentat with Docker Compose..."
	@docker compose up -d
	@echo ""
	@echo "========================================"
	@echo "Mentat is running!"
	@echo "========================================"
	@echo "  Backend:  http://localhost:$(BACKEND_PORT)"
	@echo "  Frontend: http://localhost:$(FRONTEND_PORT)"
	@echo "  API Docs: http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "Commands:"
	@echo "  make logs    - Follow container logs"
	@echo "  make ps      - Show container status"
	@echo "  make down    - Stop all services"
	@echo "========================================"

# Stop Docker containers
down:
	@echo "Stopping Docker containers..."
	@docker compose down

# Restart Docker containers
restart:
	@echo "Restarting Docker containers..."
	@docker compose restart

# Follow Docker container logs
logs:
	@echo "Following Docker logs (Ctrl+C to exit)..."
	@docker compose logs -f

# Show container status
ps:
	@docker compose ps

# Open browser
browser:
	@echo "Opening browser..."
	@powershell -Command "Start-Sleep -Seconds 2"
	@powershell -Command "Start-Process 'http://localhost:$(FRONTEND_PORT)'"

# Clean Docker resources
clean:
	@echo "Cleaning Docker resources..."
	@docker compose down -v --rmi local
	@echo "Docker resources cleaned!"

# ========================================
# Local Development (Without Docker)
# ========================================

# Install dependencies locally
local-install:
	@echo "Installing dependencies locally..."
	@powershell -Command "if (-not (Test-Path 'logs')) { New-Item -ItemType Directory -Path 'logs' | Out-Null }"
	@echo "[1/2] Installing Python packages..."
	@cd ../.. && uv sync
	@echo "[2/2] Installing frontend packages..."
	@cd web && bun install
	@echo ""
	@echo "Done! Run 'make local-backend' and 'make local-frontend' to start locally."

# Run backend locally (without Docker)
local-backend:
	@echo "Starting backend locally on port $(BACKEND_PORT)..."
	@cd ../.. && uv run uvicorn projects.mentat.api.main:app --reload --port $(BACKEND_PORT)

# Run frontend locally (without Docker)
local-frontend:
	@echo "Starting frontend locally on port $(FRONTEND_PORT)..."
	@cd web && bun run dev
