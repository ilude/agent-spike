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

