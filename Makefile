# Docker and build configuration
export DOCKER_BUILDKIT := 1
export DOCKER_SCAN_SUGGEST := false
export COMPOSE_DOCKER_CLI_BUILD := 1

# Include development targets if available
#-include .devcontainer/Makefile

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

# Version management
.PHONY: version bump-patch bump-minor bump-major publish

# Cleanup targets
.PHONY: clean

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
