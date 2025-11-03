# Claude Code in Devcontainer

This guide explains how Claude Code is set up in the devcontainer environment.

## Installation

Claude Code is automatically installed when the devcontainer is built and launched.

### Installation Methods

The devcontainer uses two complementary installation methods:

1. **Dockerfile Stage (Primary)**
   - Claude Code is installed during the devcontainer image build via npm
   - Location: `Dockerfile` lines 217-219
   - Ensures Claude Code is available immediately when the container launches
   - More reliable and reproducible

2. **Entrypoint Script (Backup)**
   - Location: `.devcontainer/entrypoint.d/02-install-claude-code.sh`
   - Runs during container initialization if needed
   - Provides flexibility for updates or troubleshooting

## Using Claude Code in Devcontainer

### Starting Claude Code

Once the devcontainer is running, Claude Code is available in the terminal:

```bash
# Check Claude Code version
claude --version

# Open Claude Code
claude

# Run specific commands
claude write src/app/cli.py
claude bash "make test"
```

### Workflow

1. **Open workspace in VS Code devcontainer**
   ```bash
   # In VS Code: Remote Explorer → Open Folder in Container
   # OR from terminal in workspace:
   make build-dev
   ```

2. **Launch Claude Code inside the container**
   ```bash
   claude
   ```

3. **Use MCP tools**
   - All MCP tools (Docker, YouTube, Obsidian, IDE) are available
   - Docker socket is mounted for direct container operations
   - Full workspace access

### Configuration

Claude Code configuration in the devcontainer inherits from:
- `.claude/CLAUDE.md` - Project guidance
- `.claude/claude_config.devcontainer.json` - MCP server config
- Standard Claude Code configuration

## Architecture

```
Host Machine
├─ Claude Code instance
└─ Devcontainer (running in Docker)
   ├─ Claude Code CLI (installed)
   ├─ MCP Tools accessible
   ├─ Docker socket mounted
   └─ Full workspace access
```

## Benefits

- **No external tools needed**: Claude Code runs inside the container
- **Consistent environment**: Same tools and dependencies in devcontainer
- **MCP integration**: Access to all MCP servers from inside the container
- **Faster iteration**: No context switching between host and container

## Troubleshooting

### Claude Code command not found

```bash
# Check if installation succeeded
npm list -g @anthropic-ai/claude-code

# Manually reinstall if needed
npm install -g @anthropic-ai/claude-code

# Verify installation
which claude
claude --version
```

### NPM issues

If npm has issues during build:

```bash
# Clear npm cache and rebuild
npm cache clean --force
make build-dev
```

### Path issues

If `claude` command is not in PATH:

```bash
# Find where claude is installed
find /usr -name claude -type f 2>/dev/null

# Add to PATH if needed
export PATH="/usr/local/bin:$PATH"
```

## Related Files

- `Dockerfile` - Installation in devcontainer stage
- `.devcontainer/entrypoint.d/02-install-claude-code.sh` - Entrypoint script
- `.claude/claude_config.devcontainer.json` - MCP configuration
- `.devcontainer/devcontainer.json` - Container configuration
