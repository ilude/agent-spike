# SurrealDB Backup & Recovery Guide

## Quick Reference

**Backup SurrealDB**: `make surrealdb-backup`
**List backups**: `ls -lh infra/ansible/backups/surrealdb/`
**Restore backup**: See "Manual Restore" section below

## Backup System Overview

### What Gets Backed Up
- Namespace: `agent_spike`
- Database: `graph`
- All tables: `video`, `tag`, etc.
- All records with full data
- Schema definitions (DEFINE TABLE, DEFINE INDEX)

### Backup Location
- **Local**: `C:\Projects\working\agent-spike\infra\ansible\backups\surrealdb\`
- **Format**: `backup-YYYY-MM-DD_HH-MM-SS.sql`
- **Retention**: Last 7 days (auto-cleanup)

### Backup Schedule
- **Manual**: Run `make surrealdb-backup` anytime
- **Automated**: (Future) Daily at 2 AM via cron

### Backup Strategy
- **Method**: `surreal export` via Docker exec
- **Downtime**: Zero (live export while database is running)
- **Size**: Typically 1-10 MB (1,390 videos with embeddings)
- **Duration**: ~30 seconds for full export

## Manual Backup

```bash
# From project root
make surrealdb-backup

# Expected output:
# Backing up SurrealDB from GPU server...
# [Ansible playbook runs...]
# ✓ SurrealDB backup complete!
# Backup saved to: infra/ansible/backups/surrealdb/backup-2025-11-25_14-30-45.sql
# Size: 45.57 MB
```

## Manual Restore

**WARNING**: Restore is DESTRUCTIVE. Current data will be replaced.

### Quick Restore (Last Backup)

```bash
# 1. Find latest backup
ls -lt infra/ansible/backups/surrealdb/ | head -2

# 2. SSH to GPU server
ssh anvil@192.168.16.241

# 3. Copy backup to server
# (From local machine)
scp infra/ansible/backups/surrealdb/backup-2025-11-25_14-30-45.sql anvil@192.168.16.241:/tmp/

# 4. Import backup (on GPU server)
docker exec -i surrealdb surreal import \
  --conn http://localhost:8000 \
  --user root \
  --pass "$SURREALDB_PASSWORD" \
  --ns agent_spike \
  --db graph \
  /tmp/backup-2025-11-25_14-30-45.sql

# 5. Verify record count
docker exec surrealdb surreal sql \
  --conn http://localhost:8000 \
  --user root \
  --pass "$SURREALDB_PASSWORD" \
  --ns agent_spike \
  --db graph \
  --pretty \
  "SELECT count() FROM video GROUP BY true"
```

### Restore with Downtime (Safer)

If you want to avoid conflicts during restore:

```bash
# 1. Stop services that use SurrealDB
cd /apps/ai-services
docker compose stop api worker frontend

# 2. Import backup (as above)
docker exec -i surrealdb surreal import ...

# 3. Restart services
docker compose start api worker frontend

# 4. Verify via API
curl https://api.local.ilude.com/health
```

## Disaster Recovery Scenarios

### Scenario 1: Data Corruption (Records Lost)

**Symptoms**: Missing videos, incorrect counts, corrupted embeddings

**Recovery**:
1. Identify last known good backup: `ls -lt infra/ansible/backups/surrealdb/`
2. Check backup before corruption occurred
3. Restore that backup (see Manual Restore)
4. Verify record counts match expected values

**Prevention**: Regular backups, monitor record counts

---

### Scenario 2: Accidental Deletion

**Symptoms**: Specific records or table dropped accidentally

**Recovery**:
1. Don't panic - backups exist
2. Find backup from before deletion: `ls -lt infra/ansible/backups/surrealdb/`
3. Restore to temporary database first:
   ```bash
   docker exec -i surrealdb surreal import \
     --ns agent_spike \
     --db temp_restore \
     /tmp/backup-2025-11-25.sql
   ```
4. Query for deleted records from temp database
5. Manually re-import only those records to main database
6. Drop temp database

**Prevention**: Test queries in development first

---

### Scenario 3: GPU Server Complete Failure

**Symptoms**: Server won't boot, hardware failure, data loss

**Recovery**:
1. Provision new GPU server or VM
2. Deploy Docker Compose stack: `make gpu-deploy`
3. Copy latest backup to new server:
   ```bash
   scp backups/surrealdb/backup-latest.sql anvil@NEW_IP:/tmp/
   ```
4. Import backup to new SurrealDB instance
5. Update DNS/IP in project `.env` if needed
6. Verify connectivity: `curl https://api.local.ilude.com/health`

**Prevention**: Keep local backups (already happening), consider cloud backup

---

### Scenario 4: Backup File Corrupted

**Symptoms**: Import fails with syntax errors

**Recovery**:
1. Try next-oldest backup: `ls -lt infra/ansible/backups/surrealdb/ | head -10`
2. Validate backup syntax before import:
   ```bash
   head -50 infra/ansible/backups/surrealdb/backup-2025-11-25.sql
   # Should see: DEFINE TABLE, CREATE, INSERT statements
   ```
3. If all backups corrupted: Fall back to archive strategy
4. Repopulate from MinIO archives: `make populate-surrealdb`

**Prevention**: Validation already built into backup playbook (file size check)

## Troubleshooting

### Backup Fails: "Container not running"

**Cause**: SurrealDB container stopped or crashed

**Fix**:
```bash
ssh anvil@192.168.16.241
docker ps | grep surrealdb
docker compose up -d surrealdb
# Wait 10 seconds, then retry backup
```

---

### Backup Fails: "Authentication failed"

**Cause**: `SURREALDB_PASSWORD` incorrect or missing

**Fix**:
1. Check `.env` file has `SURREALDB_PASSWORD`
2. Unlock git-crypt: `git-crypt unlock`
3. Verify password matches: `ssh anvil@192.168.16.241 cat /apps/ai-services/.env | grep SURREALDB_PASSWORD`

---

### Backup File Size 0 Bytes

**Cause**: Export failed silently, or namespace/database wrong

**Fix**:
1. Check namespace and database names in playbook
2. Verify data exists: `docker exec surrealdb surreal sql --conn http://localhost:8000 ... "INFO FOR DB"`
3. Manually test export: `docker exec surrealdb surreal export ...`

---

### Cannot Find Backups Directory

**Cause**: `.gitignore` hides directory, or not created yet

**Fix**:
```bash
mkdir -p infra/ansible/backups/surrealdb
# Run backup again
make surrealdb-backup
```

---

### Import Hangs or Times Out

**Cause**: Large backup file, slow network, or database locked

**Fix**:
1. Stop services using database (api, worker) for clean import
2. Increase timeout if needed
3. Check disk space on server: `df -h`

## Testing Your Backup

**Before relying on backups, test the restore process**:

```bash
# 1. Create a test backup
make surrealdb-backup

# 2. Record current video count
curl https://api.local.ilude.com/cache/stats

# 3. Restore backup to temp database (non-destructive)
ssh anvil@192.168.16.241
docker exec -i surrealdb surreal import \
  --ns agent_spike \
  --db test_restore \
  /tmp/backup-latest.sql

# 4. Verify record count matches
docker exec surrealdb surreal sql \
  --ns agent_spike \
  --db test_restore \
  "SELECT count() FROM video GROUP BY true"

# 5. Drop test database
docker exec surrealdb surreal sql \
  --ns agent_spike \
  "REMOVE DATABASE test_restore"
```

If this works, your backups are valid and restorable!

## Next Steps

1. **Automate backups**: Add cron job to run daily at 2 AM
2. **Cloud backup**: Upload to S3 or Azure Blob for offsite storage
3. **Monitoring**: Set up alerts if backup fails or is >24 hours old
4. **Compression**: Add gzip to reduce backup file sizes (optional)

## Questions?

See `.claude/ideas/surrealdb-backup/PLAN.md` for original design decisions.
