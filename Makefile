# =============================================================================
# Agent-Spike Platform Makefile
# =============================================================================
#
# Platform Architecture:
#   - Traefik: HTTPS reverse proxy (Let's Encrypt via Cloudflare)
#   - API: FastAPI backend container
#   - Worker: Background queue processor
#   - Frontend: SvelteKit (runs LOCALLY - see compose/frontend/)
#
# Quick Start:
#   make up                              # Start backend (traefik, api, worker)
#   cd compose/frontend && bun run dev   # Start frontend locally
#   make logs                            # View service logs
#   make down                            # Stop everything
#
# URLs (HTTPS via Traefik):
#   https://mentat.local.ilude.com     - Frontend (local dev server)
#   https://api.local.ilude.com        - API
#   https://traefik.local.ilude.com    - Traefik dashboard
#
# =============================================================================

# Docker configuration
export DOCKER_BUILDKIT := 1
export DOCKER_SCAN_SUGGEST := false
export COMPOSE_DOCKER_CLI_BUILD := 1

# Compose file location
COMPOSE_DIR := compose
COMPOSE_CMD := docker compose -f $(COMPOSE_DIR)/docker-compose.yml -f $(COMPOSE_DIR)/docker-compose.override.yml

# Include .env if it exists and is not encrypted by git-crypt
ifneq (,$(wildcard .env))
	ifeq (,$(shell file .env 2>/dev/null | grep -q "data" && echo binary))
		-include .env
		export
	endif
endif

# Cross-platform OS detection
ifeq ($(OS),Windows_NT)
	DETECTED_OS := windows
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		DETECTED_OS := linux
	endif
	ifeq ($(UNAME_S),Darwin)
		DETECTED_OS := macos
	endif
endif

# Semantic versioning
SEMANTIC_VERSION := $(shell git tag --list 'v*.*.*' --sort=-v:refname 2>/dev/null | head -n 1)
VERSION := $(shell if [ -z "$(SEMANTIC_VERSION)" ]; then echo "0.0.0"; else echo $(SEMANTIC_VERSION) | sed 's/^v//'; fi)

export DETECTED_OS SEMANTIC_VERSION

# =============================================================================
# PLATFORM TARGETS (Primary workflow)
# =============================================================================
.PHONY: up start down logs status restart rebuild

## Start platform services (traefik, api, worker)
up:
	@echo "Starting platform services at https://mentat.local.ilude.com/ ..."
	$(COMPOSE_CMD) up -d
	cd compose/frontend && bun run dev

## Start all services including frontend (background)
start:
	@echo "Starting platform services at https://mentat.local.ilude.com/ ..."
	
	$(COMPOSE_CMD) up -d
	@cd compose/frontend && nohup bun run dev > ../../logs/frontend.log 2>&1 & echo $$! > ../../logs/frontend.pid
	@echo ""
	@echo "Logs: tail -f logs/frontend.log"

## Stop all platform services (including frontend if running)
down:
	@if [ -f logs/frontend.pid ]; then echo "Stopping frontend..."; kill $$(cat logs/frontend.pid) 2>/dev/null || true; rm -f logs/frontend.pid; fi
	@echo "Stopping platform services..."
	$(COMPOSE_CMD) down

## View service logs (all services, follow mode)
logs:
	$(COMPOSE_CMD) logs -f

## View logs for specific service (usage: make logs-api, logs-worker, logs-traefik)
logs-%:
	$(COMPOSE_CMD) logs -f $*

## Show status of all services
status:
	@echo "=== Platform Status ==="
	@$(COMPOSE_CMD) ps
	@echo ""
	@echo "=== Service Health ==="
	@docker inspect --format='{{.Name}}: {{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' $$(docker ps -q --filter "name=agent-spike" --filter "name=traefik" --filter "name=queue-worker" 2>/dev/null) 2>/dev/null || echo "No services running"

## Restart all services (or specific: make restart-api)
restart:
	$(COMPOSE_CMD) restart

restart-%:
	$(COMPOSE_CMD) restart $*

## Rebuild and restart services
rebuild:
	@echo "Rebuilding services..."
	$(COMPOSE_CMD) build
	$(COMPOSE_CMD) up -d
	@echo "Rebuild complete"

## Rebuild specific service (usage: make rebuild-api, rebuild-worker)
rebuild-%:
	$(COMPOSE_CMD) build $*
	$(COMPOSE_CMD) up -d $*


# =============================================================================
# SETUP TARGETS
# =============================================================================
.PHONY: setup setup-gpg

setup:
ifeq ($(DETECTED_OS),windows)
	@pwsh -ExecutionPolicy Bypass -File scripts/setup-git-crypt.ps1
else
	@echo "This setup script is designed for Windows. For Linux/macOS, install manually:"
	@echo "  Linux: sudo apt install gnupg git-crypt"
	@echo "  macOS: brew install gnupg git-crypt"
endif

setup-gpg:
ifeq ($(DETECTED_OS),windows)
	@pwsh -ExecutionPolicy Bypass -File scripts/setup-gpg-key.ps1
else
	@echo "Run: gpg --full-generate-key"
endif

# =============================================================================
# DEVELOPMENT & TESTING
# =============================================================================
.PHONY: sync-dev lint format test test-backend test-frontend test-coverage test-tools

## Sync development dependencies
sync-dev:
	@uv sync --group dev --group platform-api

## Lock and sync dependencies
uv.lock:
	uv lock
	uv sync --group dev --group platform-api

## Run linter
lint:
	@echo "Running ruff check..."
	uv run ruff check .

## Format code (black + isort)
format: uv.lock
	@echo "Formatting code..."
	uv run black src tests
	uv run isort src tests --profile black

## Run all tests
test: test-backend test-frontend
	@echo "All tests completed!"

## Run backend tests only
test-backend: sync-dev
	@echo "Running backend tests..."
	uv run python -m pytest compose/tests/ -v

## Run frontend tests only
test-frontend:
	@echo "Running frontend tests..."
	cd compose/frontend && bun test

## Run tests with coverage reports
test-coverage: sync-dev
	@echo "Running tests with coverage..."
	uv run python -m pytest compose/tests/ --cov=compose --cov-report=term-missing --cov-report=html:htmlcov-backend -v
	cd compose/frontend && bun run test:coverage
	@echo ""
	@echo "Coverage reports:"
	@echo "  Backend:  htmlcov-backend/index.html"
	@echo "  Frontend: compose/frontend/coverage/index.html"

## Run tools tests (legacy)
test-tools: sync-dev
	uv run python -m pytest tools/tests/ --cov=tools --cov-report=term-missing -v

# =============================================================================
# CLEANUP & MAINTENANCE
# =============================================================================
.PHONY: clean

## Clean Python cache and build artifacts
clean:
	@echo "Cleaning Python cache and build artifacts..."
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'dist' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'build' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '.coverage' -delete 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '*.pyo' -delete 2>/dev/null || true
	find . -type f -name '*.pyd' -delete 2>/dev/null || true
	find . -type f -name '.DS_Store' -delete 2>/dev/null || true
	uv cache clean 2>/dev/null || true
	@echo "Cleanup complete"

# =============================================================================
# VERSION MANAGEMENT
# =============================================================================
.PHONY: version bump-patch bump-minor bump-major

## Show version info
version:
	@echo "Version: $(VERSION) ($(SEMANTIC_VERSION))"
	@echo "OS: $(DETECTED_OS)"

define bump_version
	@echo "Latest version: $(SEMANTIC_VERSION)"
	@NEW_VERSION=$$(echo $(VERSION) | awk -F. -v type="$(1)" 'BEGIN {OFS="."} { \
		if (type == "patch") {$$3+=1} \
		else if (type == "minor") {$$2+=1; $$3=0} \
		else if (type == "major") {$$1+=1; $$2=0; $$3=0} \
		print $$1, $$2, $$3}') && \
	echo "New version: $$NEW_VERSION" && \
	git tag -a "v$$NEW_VERSION" -m "Release v$$NEW_VERSION" && \
	git push --tags && \
	echo "Tagged and pushed as v$$NEW_VERSION"
endef

bump-patch:
	$(call bump_version,patch)

bump-minor:
	$(call bump_version,minor)

bump-major:
	$(call bump_version,major)

# =============================================================================
# UTILITIES
# =============================================================================
.PHONY: brave-sync

## Sync Brave browser history to queue
brave-sync:
	@uv run python compose/cli/brave_history/copy_brave_history.py --incremental --dest compose/data/queues/brave_history

# =============================================================================
# GPU SERVER MANAGEMENT (Ansible)
# Remote server: 192.168.16.241
# =============================================================================
.PHONY: gpu-deploy gpu-update gpu-backup gpu-shell

## Deploy AI services to GPU server
gpu-deploy:
	@echo "Deploying AI services to GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/deploy.yml

## Update AI services on GPU server (pull + restart)
gpu-update:
	@echo "Updating AI services on GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/update.yml

## Backup current GPU server config
gpu-backup:
	@echo "Backing up GPU server config..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/backup.yml

## Deploy observability stack (Loki, Prometheus, Tempo, Grafana) to GPU server
gpu-deploy-observability:
	@echo "Deploying observability stack to GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/deploy-observability.yml

## Open Ansible shell for manual commands
gpu-shell:
	@cd infra/ansible && docker compose run --rm ansible bash
