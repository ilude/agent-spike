#!/bin/bash
# Daily backup script for SurrealDB and MinIO
# Run via cron: 0 3 * * * cd /apps/ai-services && ./backup.sh

set -e
BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "$(date): Starting backup to $BACKUP_DIR"

# Stop services for consistent backup
docker compose stop surrealdb minio

# Backup SurrealDB
tar -czf "$BACKUP_DIR/surrealdb.tar.gz" ./data/surrealdb/

# Backup MinIO
tar -czf "$BACKUP_DIR/minio.tar.gz" ./data/minio/

# Restart services
docker compose start surrealdb minio

# Keep only last 7 days of backups
find ./backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

echo "$(date): Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
