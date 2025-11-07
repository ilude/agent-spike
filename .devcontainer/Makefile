# Development-specific Makefile targets for devcontainer
.PHONY: initialize setup-container uv.lock lint test format clean

# Read and include .devcontainer/.env
ifneq (,$(wildcard .devcontainer/.env))
	include .devcontainer/.env
	export
endif

# Initialize development environment
initialize:
	@echo "Initializing development environment..."
	@echo "HOSTIP=$$(hostname -I | awk '{print $$1}')" > .devcontainer/.env

# One-step container setup invoked by devcontainer postCreateCommand
setup-container:
	@echo "Running entrypoint scripts..."
	@for script in .devcontainer/entrypoint.d/*.sh; do \
		if [ -f "$$script" ]; then \
			echo "Running $$script"; \
			bash "$$script" || echo "entrypoint script failed: $$script"; \
		fi \
	done
	@echo "Entrypoint scripts completed."

# Install development dependencies
uv.lock:
	uv lock
	uv sync --dev

# Run linting
lint:
	@echo "Running ruff check..."
	uv run ruff check .
	@echo "Linting completed!"

# Run tests
test: uv.lock
	@echo "Running tests..."
	uv run pytest -q

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
