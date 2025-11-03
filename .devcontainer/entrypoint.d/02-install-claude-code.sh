#!/bin/bash
set -euo pipefail

# Install Claude Code in devcontainer
# This script installs the Claude Code CLI tool via npm

echo "================================"
echo "Installing Claude Code CLI..."
echo "================================"

# Install globally via npm
if command -v npm &> /dev/null; then
    echo "Installing @anthropic-ai/claude-code via npm..."
    npm install -g @anthropic-ai/claude-code
    
    # Fix permissions if running as root (devcontainer entrypoint runs as root initially)
    if [ "$(id -u)" = "0" ]; then
        npm cache clean --force
        chown -R "${PUID:-1000}:${PGID:-1000}" /usr/local/lib/node_modules || true
        chown -R "${PUID:-1000}:${PGID:-1000}" "${HOME}/.npm" || true
    fi

    # Verify installation
    if command -v claude &> /dev/null; then
        echo "✓ Claude Code successfully installed"
        claude --version
    else
        echo "⚠ Claude Code installed but 'claude' command not found in PATH"
        echo "  Try running: npm list -g @anthropic-ai/claude-code"
    fi
else
    echo "⚠ npm not found, skipping Claude Code installation"
    echo "  Claude Code requires Node.js and npm"
fi

echo "================================"
echo "Claude Code installation complete"
echo "================================"
