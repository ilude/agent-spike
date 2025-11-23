# Multi-stage Dockerfile for SvelteKit with Bun and adapter-node
# Stages: builder -> development -> production

# ============================================================
# Builder Stage: Install dependencies
# ============================================================
FROM oven/bun:1-debian AS builder

WORKDIR /workspace

# Copy package files
COPY package.json bun.lock* package-lock.json* ./

# Install all dependencies (including devDependencies for build)
RUN bun install

# ============================================================
# Development Stage: Hot reload with Vite
# ============================================================
FROM oven/bun:1-debian AS development

WORKDIR /workspace

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /workspace/node_modules ./node_modules

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run dev server with hot reload
CMD ["bun", "run", "dev"]

# ============================================================
# Production Stage: Built Node.js server with adapter-node
# ============================================================
FROM oven/bun:1-debian AS production

WORKDIR /workspace

# Install Node.js (required for adapter-node production server)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /workspace/node_modules ./node_modules

# Copy application code
COPY . .

# Build the SvelteKit app (creates build/ directory)
RUN bun run build

# Remove devDependencies to reduce image size
RUN bun install --production

# Expose production server port
EXPOSE 5173

# Set production environment
ENV NODE_ENV=production

# Run the built Node.js server
CMD ["node", "build/index.js"]
