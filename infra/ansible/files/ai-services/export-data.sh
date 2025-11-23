#!/bin/bash
# Manual export script - run before major changes
# Usage: ./export-data.sh

set -e
EXPORT_DIR="./exports/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

echo "Exporting data to $EXPORT_DIR..."

# Export SurrealDB database
docker exec surrealdb /surreal export \
  --conn http://localhost:8000 \
  --user root --pass "${SURREALDB_PASSWORD}" \
  --ns data --db graph_db \
  > "$EXPORT_DIR/surrealdb_export.surql" 2>/dev/null || echo "SurrealDB export failed or empty"

# List MinIO objects
docker exec minio mc alias set local http://localhost:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" 2>/dev/null
docker exec minio mc ls --recursive local/ > "$EXPORT_DIR/minio_objects.txt" 2>/dev/null || echo "MinIO listing failed or empty"

# Create final archive
tar -czf "${EXPORT_DIR}.tar.gz" -C "$(dirname $EXPORT_DIR)" "$(basename $EXPORT_DIR)"
rm -rf "$EXPORT_DIR"

echo "Export saved to: ${EXPORT_DIR}.tar.gz"
