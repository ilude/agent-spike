#!/bin/bash
# Migrate named volumes to bind mount directories
# Run this on the GPU server BEFORE deploying the new docker-compose.yml

set -e

DATA_DIR="./data"
echo "Creating data directories in $DATA_DIR..."

mkdir -p "$DATA_DIR/ollama"
mkdir -p "$DATA_DIR/qdrant"
mkdir -p "$DATA_DIR/infinity"
mkdir -p "$DATA_DIR/n8n"
mkdir -p "$DATA_DIR/neo4j"
mkdir -p "$DATA_DIR/whisper"

echo "Stopping containers..."
docker compose down

echo "Copying data from named volumes to bind mount directories..."

# Function to copy volume data
copy_volume() {
    local volume_name=$1
    local target_dir=$2

    if docker volume inspect "$volume_name" &>/dev/null; then
        echo "  Copying $volume_name -> $target_dir"
        docker run --rm \
            -v "$volume_name":/source:ro \
            -v "$(pwd)/$target_dir":/target \
            alpine sh -c "cp -a /source/. /target/ 2>/dev/null || true"
        echo "    Done"
    else
        echo "  Volume $volume_name not found, skipping"
    fi
}

copy_volume "ai-services_ollama_data" "$DATA_DIR/ollama"
copy_volume "ai-services_qdrant_data" "$DATA_DIR/qdrant"
copy_volume "ai-services_infinity_models" "$DATA_DIR/infinity"
copy_volume "ai-services_n8n_data" "$DATA_DIR/n8n"
copy_volume "ai-services_neo4j_data" "$DATA_DIR/neo4j"
copy_volume "ai-services_whisper_models" "$DATA_DIR/whisper"

echo ""
echo "Migration complete! Data copied to $DATA_DIR/"
echo "Now deploy the updated docker-compose.yml with bind mounts."
echo ""
echo "After verifying everything works, you can remove old volumes with:"
echo "  docker volume prune"
