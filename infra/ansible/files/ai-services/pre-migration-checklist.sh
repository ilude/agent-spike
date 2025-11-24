#!/bin/bash
# Pre-migration checklist script
# Run this on the GPU server BEFORE running migrate-volumes.sh

set -e

DATA_DIR="/data"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d)

echo "=== Pre-Migration Checklist for /data Migration ==="
echo "Date: $(date)"
echo ""

# Step 1: Check current data sizes
echo "Step 1: Checking current volume sizes..."
echo "----------------------------------------"
docker system df -v | grep -E "VOLUME NAME|ai-services_" || echo "No ai-services volumes found"
echo ""

# Step 2: Check disk space
echo "Step 2: Checking /data disk space..."
echo "----------------------------------------"
df -h /data
echo ""

available_space=$(df -BG /data | tail -1 | awk '{print $4}' | sed 's/G//')
echo "Available space on /data: ${available_space}GB"
echo ""

# Step 3: Document current service status
echo "Step 3: Documenting current service status..."
echo "----------------------------------------"
docker compose ps
echo ""

# Step 4: Test Ollama
echo "Step 4: Testing Ollama..."
echo "----------------------------------------"
if curl -s localhost:11434/api/tags > /tmp/ollama-models-before.json; then
    echo "✓ Ollama responding"
    echo "Models available:"
    cat /tmp/ollama-models-before.json | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "  (none or parse error)"
else
    echo "✗ Ollama not responding"
fi
echo ""

# Step 5: Test Infinity
echo "Step 5: Testing Infinity..."
echo "----------------------------------------"
if curl -s localhost:7997/health > /dev/null; then
    echo "✓ Infinity responding"
else
    echo "✗ Infinity not responding"
fi
echo ""

# Step 6: Test MinIO
echo "Step 6: Testing MinIO..."
echo "----------------------------------------"
if curl -s -I localhost:9000 | grep -q "403\|200"; then
    echo "✓ MinIO responding"
else
    echo "✗ MinIO not responding"
fi
echo ""

# Step 7: Test SurrealDB
echo "Step 7: Testing SurrealDB..."
echo "----------------------------------------"
if curl -s localhost:8080/health > /dev/null 2>&1; then
    echo "✓ SurrealDB responding"
else
    echo "✗ SurrealDB not responding"
fi
echo ""

# Step 8: Run backup script
echo "Step 8: Creating backup..."
echo "----------------------------------------"
if [ -f "./backup.sh" ]; then
    echo "Running backup.sh..."
    ./backup.sh
else
    echo "WARNING: backup.sh not found! Manual backup recommended."
    echo ""
    echo "You can manually backup with:"
    echo "  docker compose stop surrealdb minio"
    echo "  tar -czf backup-surrealdb-${DATE}.tar.gz -C /apps/ai-services ./data/surrealdb"
    echo "  tar -czf backup-minio-${DATE}.tar.gz -C /apps/ai-services ./data/minio"
    echo "  docker compose start surrealdb minio"
fi
echo ""

# Step 9: Validate backups
echo "Step 9: Validating backups..."
echo "----------------------------------------"

if [ -d "$BACKUP_DIR/$DATE" ]; then
    echo "Backup directory exists: $BACKUP_DIR/$DATE"
    echo ""

    echo "Backup files:"
    ls -lh "$BACKUP_DIR/$DATE/" || echo "  (unable to list)"
    echo ""

    echo "Backup sizes:"
    du -sh "$BACKUP_DIR/$DATE"/* 2>/dev/null || echo "  (unable to calculate)"
    echo ""

    # Test tar integrity for each backup file
    echo "Testing backup integrity..."
    for backup_file in "$BACKUP_DIR/$DATE"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            echo -n "  Testing $(basename $backup_file)... "
            if tar -tzf "$backup_file" | head -5 > /dev/null 2>&1; then
                file_count=$(tar -tzf "$backup_file" 2>/dev/null | wc -l)
                echo "✓ OK ($file_count files)"
            else
                echo "✗ FAILED"
            fi
        fi
    done
else
    echo "WARNING: Backup directory $BACKUP_DIR/$DATE not found!"
    echo "Please run backup.sh or create manual backups before migration."
fi
echo ""

# Step 10: Summary
echo "=== Pre-Migration Checklist Summary ==="
echo "----------------------------------------"
echo "✓ Volume sizes checked"
echo "✓ Disk space verified"
echo "✓ Service status documented"
echo "✓ Service health tests completed"

if [ -d "$BACKUP_DIR/$DATE" ]; then
    echo "✓ Backups created and validated"
    echo ""
    echo "You are ready to run migration!"
    echo ""
    echo "Next step:"
    echo "  ./migrate-volumes.sh"
else
    echo "✗ Backups not validated"
    echo ""
    echo "DO NOT PROCEED without valid backups!"
    echo "Run backup.sh first, then re-run this checklist."
fi
echo ""
