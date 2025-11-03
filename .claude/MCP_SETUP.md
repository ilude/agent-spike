# MCP Setup for Devcontainer

This document explains how to access MCP tools while working inside the devcontainer.

## Overview

The devcontainer has access to MCP servers through a mounted Docker socket and network connectivity to the host. This allows you to use MCP tools directly within Claude Code while developing in the containerized environment.

## Available MCP Servers

### 1. Docker MCP Server
- **Description**: Control and inspect Docker containers, images, and operations
- **How it works**: Uses the mounted Docker socket (`/var/run/docker.sock`)
- **Available in devcontainer**: ✅ Yes (socket is mounted)

### 2. YouTube MCP Server
- **Description**: Retrieve and analyze YouTube video transcripts
- **Available in devcontainer**: ✅ Yes (network access)

### 3. Obsidian MCP Server
- **Description**: Integrate with Obsidian vault for note management
- **Available in devcontainer**: ✅ Yes (if vault is accessible)
- **Path**: Points to workspace root by default

### 4. IDE MCP Server
- **Description**: VS Code diagnostics and Jupyter notebook support
- **Available in devcontainer**: ✅ Yes (works with VS Code remote)

## Using MCP Tools in Devcontainer

### When opening the workspace in VS Code devcontainer:

1. **Open workspace folder** in VS Code devcontainer (not on host)
2. **Claude Code runs inside the container** and has access to all MCP tools
3. The Docker socket mount allows Docker operations directly
4. Other MCP servers work through normal network/file access

### Configuration Files

- **`mcp.json`**: Overview of available MCP servers (reference)
- **`claude_config.devcontainer.json`**: MCP server configuration for devcontainer environment

## Network Connectivity

The devcontainer can reach the host via:
- **Docker socket**: Mounted at `/var/run/docker.sock` for direct Docker access
- **Network**: Standard networking to reach external services (YouTube, etc.)
- **Workspace**: Full access to workspace files

## Limitations

- MCP servers must be available (either running in devcontainer or accessible via network)
- Docker operations use the mounted socket (direct access to host Docker daemon)
- Obsidian vault must be accessible from the devcontainer

## Troubleshooting

If MCP tools aren't working in the devcontainer:

1. Ensure Claude Code is running with the workspace open in VS Code devcontainer
2. Check that Docker socket is properly mounted: `ls -la /var/run/docker.sock`
3. Verify MCP server packages are installed: `npm list @modelcontextprotocol/*`
4. Check Claude Code logs for MCP server connection errors

## Related Files

- `.devcontainer/devcontainer.json`: Container configuration with Docker socket mount
- `Dockerfile`: Contains devcontainer stage with required tools
