# Docker and build configuration
export DOCKER_BUILDKIT := 1
export DOCKER_SCAN_SUGGEST := false
export COMPOSE_DOCKER_CLI_BUILD := 1

# Include development targets
-include .devcontainer/Makefile

# Include .env if it exists and is not encrypted by git-crypt
# Skip if file is binary data (encrypted)
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

# Host IP detection
ifndef HOSTIP
	ifeq ($(DETECTED_OS),linux)
		HOSTIP := $(shell ip route get 1 2>/dev/null | head -1 | awk '{print $$7}' || echo "127.0.0.1")
	else ifeq ($(DETECTED_OS),macos)
		HOSTIP := $(shell ifconfig 2>/dev/null | grep "inet " | grep -Fv 127.0.0.1 | head -1 | awk '{print $$2}' || echo "127.0.0.1")
	else
		HOSTIP := 127.0.0.1
	endif
endif

# Container runtime detection
ifndef CONTAINER_RUNTIME
	ifneq (, $(shell which podman 2>/dev/null))
		CONTAINER_RUNTIME := podman
	else
		CONTAINER_RUNTIME := docker
	endif
endif

# Semantic versioning
SEMANTIC_VERSION := $(shell git tag --list 'v*.*.*' --sort=-v:refname 2>/dev/null | head -n 1)
VERSION := $(shell if [ -z "$(SEMANTIC_VERSION)" ]; then echo "0.0.0"; else echo $(SEMANTIC_VERSION) | sed 's/^v//'; fi)

# Export variables
export HOSTIP DETECTED_OS CONTAINER_RUNTIME SEMANTIC_VERSION

.PHONY: .env
.env:
	touch .env

# Setup targets
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

# Build targets
.PHONY: build build-dev start up down logs restart

build: .env
	$(CONTAINER_RUNTIME) build -t app:prod --target production .

build-dev: .env
	$(CONTAINER_RUNTIME) build --target devcontainer -t app .



# Container run targets
.PHONY: 

start: build
	$(CONTAINER_RUNTIME) run --rm -d --name app_prod -p 8000:8000 app:prod

up: build
	$(CONTAINER_RUNTIME) run --rm --name app_prod -p 8000:8000 app:prod

down:
	$(CONTAINER_RUNTIME) stop app_prod 2>/dev/null || true

logs:
	$(CONTAINER_RUNTIME) logs app_prod -f

restart: build down start

# Lesson 007: Video Ingestion Tools
.PHONY: ingest ingest-old

ingest:
	@echo "Starting YouTube Video Queue Ingestion REPL..."
	@echo "Features:"
	@echo "  - Queue-based processing (all CSVs in pending/ directory)"
	@echo "  - Workflow: pending/ -> processing/ -> completed/"
	@echo "  - Manual ingestion (instant, no rate limit)"
	@echo "  - Webshare proxy enabled (no rate limiting)"
	@echo "  - Archive-first pipeline (all expensive data saved)"
	@echo ""
	@echo "Queue: projects/data/queues/pending/"
	@echo "Press Ctrl+C to stop (progress is saved)"
	@echo ""
	@uv run python tools/scripts/ingest_youtube.py

ingest-old:
	@echo "Starting OLD Hybrid REPL (rate limited)..."
	@echo "Note: Use 'make ingest' for the new fast version"
	@echo ""
	@uv run python lessons/lesson-007/hybrid_ingest_repl.py

# API Credits Management
.PHONY: credit

credit:
	@echo "Opening API billing dashboards..."
	@echo ""
	@echo "Anthropic (Claude) Usage & Cost:"
	@echo "  https://console.anthropic.com/workspaces/default/cost"
	@echo "Anthropic Billing:"
	@echo "  https://console.anthropic.com/settings/billing"
	@echo ""
	@echo "OpenAI Billing:"
	@echo "  https://platform.openai.com/settings/organization/billing"
	@echo ""
ifeq ($(DETECTED_OS),windows)
	@cmd.exe /c start https://console.anthropic.com/workspaces/default/cost
	@cmd.exe /c start https://console.anthropic.com/settings/billing
	@cmd.exe /c start https://platform.openai.com/settings/organization/billing
else ifeq ($(DETECTED_OS),macos)
	@open https://console.anthropic.com/workspaces/default/cost
	@open https://console.anthropic.com/settings/billing
	@open https://platform.openai.com/settings/organization/billing
else
	@xdg-open https://console.anthropic.com/workspaces/default/cost 2>/dev/null || echo "Please open manually"
	@xdg-open https://console.anthropic.com/settings/billing 2>/dev/null || echo "Please open manually"
	@xdg-open https://platform.openai.com/settings/organization/billing 2>/dev/null || echo "Please open manually"
endif

# Install development dependencies
uv.lock:
	uv lock
	uv sync --group dev --group platform-api

# Run linting
lint:
	@echo "Running ruff check..."
	uv run ruff check .
	@echo "Linting completed!"

# Run tests
.PHONY: test test-backend test-frontend test-coverage test-tools sync-dev

sync-dev:
	@uv sync --group dev --group platform-api

test: test-backend test-frontend
	@echo "All tests completed!"

test-backend: sync-dev
	@echo "Running backend tests..."
	uv run python -m pytest compose/tests/ -v

test-frontend:
	@echo "Running frontend tests..."
	cd compose/frontend && npm test

test-coverage: sync-dev
	@echo "Running tests with coverage..."
	@echo ""
	@echo "=== Backend Coverage ==="
	uv run python -m pytest compose/tests/ --cov=compose --cov-report=term-missing --cov-report=html:htmlcov-backend -v
	@echo ""
	@echo "=== Frontend Coverage ==="
	cd compose/frontend && npm run test:coverage
	@echo ""
	@echo "Coverage reports:"
	@echo "  Backend:  htmlcov-backend/index.html"
	@echo "  Frontend: compose/frontend/coverage/index.html"

# Legacy test target for tools/
test-tools: sync-dev
	@echo "Running tools tests with coverage..."
	uv run python -m pytest tools/tests/ --cov=tools --cov-report=term-missing --cov-report=html -v

# Format code with black and isort
format: uv.lock
	@echo "Formatting code with black..."
	uv run black src tests
	@echo "Organizing imports with isort..."
	uv run isort src tests --profile black
	@echo "Code formatting completed!"

# Clean Python cache files and build artifacts
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
	@echo "✓ Cleanup complete"

# Version management
.PHONY: version bump-patch bump-minor bump-major publish

version:
	@echo "=============================================="
	@echo "Semantic Version: $(SEMANTIC_VERSION)"
	@echo "Version (without v prefix): $(VERSION)"
	@echo "Host IP: $(HOSTIP)"
	@echo "Detected OS: $(DETECTED_OS)"
	@echo "Container Runtime: $(CONTAINER_RUNTIME)"
	@echo ""

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

publish: bump-patch
	@git push --all

# Brave History Sync
.PHONY: brave-sync brave-full-sync

brave-sync:
	@uv run python compose/cli/brave_history/copy_brave_history.py --incremental --dest compose/data/queues/brave_history

# GPU Server Management (Ansible)
.PHONY: gpu-deploy gpu-update gpu-backup gpu-shell gpu-deploy-observability

gpu-deploy:
	@echo "Deploying AI services to GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/deploy.yml

gpu-update:
	@echo "Updating AI services on GPU server (pull + restart)..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/update.yml

gpu-backup:
	@echo "Backing up current GPU server config..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/backup.yml

gpu-shell:
	@echo "Opening Ansible shell for manual commands..."
	@cd infra/ansible && docker compose run --rm ansible bash

gpu-deploy-observability:
	@echo "Deploying observability stack (LGTM) to GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/deploy-observability.yml
