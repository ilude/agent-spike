#!/bin/bash
# Migrate named volumes to bind mount directories
# Run this on the GPU server BEFORE deploying the new docker-compose.yml

set -e

DATA_DIR="/data"
COMPOSE_DIR="/apps/ai-services"

echo "=== Docker Volume to /data Migration Script ==="
echo ""

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found. Please run from $COMPOSE_DIR"
    exit 1
fi

# Check disk space before starting
echo "Checking disk space on /data..."
available_space=$(df -BG /data | tail -1 | awk '{print $4}' | sed 's/G//')
echo "  Available space on /data: ${available_space}GB"

# Get total volume size
total_volume_size=$(docker system df -v 2>/dev/null | grep -E "ai-services_(ollama|infinity|n8n|surrealdb|minio)" | awk '{sum+=$3} END {print sum}')
echo "  Estimated volume data: ~${total_volume_size:-unknown}"

if [ -n "$total_volume_size" ] && [ "$available_space" -lt "$((total_volume_size * 2))" ]; then
    echo "WARNING: Low disk space. Recommend at least 2x volume size available."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Creating data directories in $DATA_DIR..."
mkdir -p "$DATA_DIR/ollama"
mkdir -p "$DATA_DIR/infinity"
mkdir -p "$DATA_DIR/n8n"
mkdir -p "$DATA_DIR/surrealdb"
mkdir -p "$DATA_DIR/minio"

echo ""
echo "Stopping containers..."
docker compose down

echo ""
echo "Copying data from named volumes to bind mount directories..."
echo ""

# Function to copy volume data with verification
copy_volume() {
    local volume_name=$1
    local target_dir=$2

    if docker volume inspect "$volume_name" &>/dev/null; then
        echo "  Copying $volume_name -> $target_dir"

        # Get source file count (if possible)
        source_files=$(docker run --rm -v "$volume_name":/source:ro alpine sh -c "find /source -type f 2>/dev/null | wc -l" || echo "unknown")
        echo "    Source files: $source_files"

        # Copy data
        docker run --rm \
            -v "$volume_name":/source:ro \
            -v "$target_dir":/target \
            alpine sh -c "cp -a /source/. /target/ 2>/dev/null || true"

        # Get destination file count
        dest_files=$(find "$target_dir" -type f 2>/dev/null | wc -l || echo "0")
        echo "    Destination files: $dest_files"

        # Get sizes
        dest_size=$(du -sh "$target_dir" 2>/dev/null | cut -f1 || echo "unknown")
        echo "    Destination size: $dest_size"

        if [ "$source_files" != "unknown" ] && [ "$source_files" != "$dest_files" ]; then
            echo "    WARNING: File count mismatch! Source: $source_files, Dest: $dest_files"
        else
            echo "    ✓ Done"
        fi
    else
        echo "  Volume $volume_name not found, skipping"
    fi
    echo ""
}

copy_volume "ai-services_ollama_data" "$DATA_DIR/ollama"
copy_volume "ai-services_infinity_models" "$DATA_DIR/infinity"
copy_volume "ai-services_n8n_data" "$DATA_DIR/n8n"
copy_volume "ai-services_surrealdb_data" "$DATA_DIR/surrealdb"
copy_volume "ai-services_minio_data" "$DATA_DIR/minio"

echo "=== Migration Summary ==="
echo ""
echo "Data copied to $DATA_DIR/:"
du -sh "$DATA_DIR"/* 2>/dev/null || echo "  (unable to calculate sizes)"
echo ""
echo "Total space used:"
du -sh "$DATA_DIR" 2>/dev/null || echo "  (unable to calculate total)"
echo ""
echo "=== Next Steps ==="
echo "1. Deploy the updated docker-compose.yml with bind mounts:"
echo "   (From local machine: make gpu-deploy)"
echo ""
echo "2. Verify all services start correctly:"
echo "   docker compose ps"
echo "   docker compose logs --tail=50"
echo ""
echo "3. Test services:"
echo "   curl localhost:11434/api/tags              # Ollama models"
echo "   curl localhost:7997/health                  # Infinity health"
echo "   curl localhost:9000                         # MinIO (expect 403)"
echo "   # Check SurrealDB data"
echo "   # Check N8N workflows at http://IP:5678"
echo ""
echo "4. After verifying everything works, remove old volumes:"
echo "   docker volume ls | grep ai-services"
echo "   docker volume prune -f"
echo ""
