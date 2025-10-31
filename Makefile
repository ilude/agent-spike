# Docker and build configuration
export DOCKER_BUILDKIT := 1
export DOCKER_SCAN_SUGGEST := false
export COMPOSE_DOCKER_CLI_BUILD := 1

# Include development targets if available
-include .devcontainer/Makefile

ifneq (,$(wildcard .env))
	include .env
	export
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

# Build targets
.PHONY: build build-dev buildx buildx-dev

build: .env
	$(CONTAINER_RUNTIME) build -t app:prod --target production .

build-dev: .env
	$(CONTAINER_RUNTIME) build --target devcontainer -t app .

# BuildX setup and targets (for cross-platform/optimized builds)
.PHONY: buildx-setup

buildx-setup:
	@if [ "$(CONTAINER_RUNTIME)" != "docker" ]; then \
		echo "[buildx] Skipping: buildx requires docker runtime"; \
		exit 0; \
	fi
	@if docker buildx version >/dev/null 2>&1; then \
		docker buildx ls | grep -q "app-builder" || docker buildx create --name app-builder --use >/dev/null; \
	else \
		echo "[buildx] Plugin not available"; \
	fi
	@mkdir -p .buildcache

buildx: .env buildx-setup
	@if [ "$(CONTAINER_RUNTIME)" != "docker" ] || ! docker buildx version >/dev/null 2>&1; then \
		echo "[buildx] Using standard build"; \
		$(CONTAINER_RUNTIME) build -t app:prod --target production .; \
	else \
		echo "[buildx] Building production with cache"; \
		docker buildx build \
			--target production \
			-t app:prod \
			--cache-from=type=local,src=.buildcache \
			--cache-to=type=local,dest=.buildcache,mode=max \
			--load \
			.; \
	fi

buildx-dev: .env buildx-setup
	@if [ "$(CONTAINER_RUNTIME)" != "docker" ] || ! docker buildx version >/dev/null 2>&1; then \
		echo "[buildx] Using standard build"; \
		$(CONTAINER_RUNTIME) build --target devcontainer -t app .; \
	else \
		echo "[buildx] Building devcontainer with cache"; \
		docker buildx build \
			--target devcontainer \
			-t app \
			--cache-from=type=local,src=.buildcache \
			--cache-to=type=local,dest=.buildcache,mode=max \
			--load \
			.; \
	fi

# Container run targets
.PHONY: start up down logs restart

start: buildx
	$(CONTAINER_RUNTIME) run --rm -d --name app_prod -p 8000:8000 app:prod

up: buildx
	$(CONTAINER_RUNTIME) run --rm --name app_prod -p 8000:8000 app:prod

down:
	$(CONTAINER_RUNTIME) stop app_prod 2>/dev/null || true

logs:
	$(CONTAINER_RUNTIME) logs app_prod -f

restart: buildx down start

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

# Testing targets
.PHONY: test-if-py-changed

test-if-py-changed:
	@echo "[tests] Checking for Python changes..."
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		changed=$$( (git diff --name-only HEAD; git ls-files --others --exclude-standard) | grep -E '\\.py$$' | sort -u ); \
		if [ -n "$$changed" ]; then \
			echo "[tests] Python changes detected, running pytest"; \
			uv run pytest; \
		else \
			echo "[tests] No Python changes detected"; \
		fi; \
	else \
		echo "[tests] Not a git repo"; \
		uv run pytest; \
	fi
