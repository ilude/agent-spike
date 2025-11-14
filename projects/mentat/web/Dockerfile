# Multi-stage build for Mentat frontend
# Uses Bun on Debian for better esbuild compatibility

# Stage 1: Builder - Install dependencies and build
FROM oven/bun:1-debian AS builder

WORKDIR /build

# Copy package files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source files
COPY . .

# Build the application
RUN bun run build

# Stage 2: Development
FROM oven/bun:1-debian AS development

# Install curl for health checks (optional for frontend)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy package files
COPY package.json bun.lockb* ./

# Install dependencies (including devDependencies for Vite)
RUN bun install

# Copy application code (will be overridden by volume mount in dev)
COPY . .

# Use the existing 'bun' user (UID 1000) from the base image
USER bun

EXPOSE 5173

# Development server (host configured in vite.config.js)
CMD ["bun", "run", "dev"]

# Stage 3: Production - Serve built files
FROM oven/bun:1-debian AS production

# Install curl for serving and health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built files from builder
COPY --from=builder /build/dist /app/dist

# Install a simple static file server
# Using Bun's built-in server capability
COPY --from=builder /build/package.json /app/

# Create a simple server script
RUN echo 'import { serve } from "bun"; \
serve({ \
  port: 5173, \
  fetch(req) { \
    const path = new URL(req.url).pathname; \
    const filePath = path === "/" ? "/app/dist/index.html" : `/app/dist${path}`; \
    return new Response(Bun.file(filePath)); \
  } \
});' > /app/server.js

# Use the existing 'bun' user (UID 1000) from the base image
USER bun

EXPOSE 5173

# Serve static files
CMD ["bun", "run", "/app/server.js"]
