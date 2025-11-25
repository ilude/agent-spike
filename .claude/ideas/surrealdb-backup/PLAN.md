# SurrealDB Backup to Local Machine - Implementation Plan

**Created**: 2025-11-24
**Status**: ✅ COMPLETE (2025-11-25)

**Implementation Summary**:
- Ansible playbook: `infra/ansible/playbooks/backup-surrealdb.yml` (99 lines)
- Makefile target: `make surrealdb-backup`
- Documentation: `docs/SURREALDB-BACKUP.md` (280+ lines)
- Backup location: `infra/ansible/backups/surrealdb/`
- Backup size: 45.57 MB (full schema + data)
- Features: Zero-downtime, 7-day retention, validated exports
- Time: ~2.5 hours (including debugging)

## Goal

Pull SurrealDB SQL dumps from GPU server (192.168.16.241) to local Windows machine for disaster recovery.

## Requirements (User Confirmed)

- **Frequency**: Manual + Daily cron (2 AM on GPU server)
- **Storage**: `backups/surrealdb/` (project root, gitignored)
- **Retention**: Keep last 7 backups, auto-delete older
- **Method**: SurrealDB EXPORT (SQL dump) - portable, version-independent

## Current State

**Existing backup infrastructure:**
- `make gpu-backup` - Only backs up Docker Compose config files
- `infra/ansible/playbooks/backup.yml` - Fetches compose files to local

**What's missing:**
- NO database backups
- NO disaster recovery plan
- NO automated backups
- BackupRecord model exists in code but not implemented

## Components to Implement

### 1. Ansible Playbook: `infra/ansible/playbooks/backup-surrealdb.yml`

**Purpose**: Export SurrealDB and fetch to local machine

**Tasks**:
- Generate timestamp (YYYY-MM-DD_HH-MM-SS)
- Run `surreal export` on GPU server container
  - Export to: `/tmp/surrealdb-backup-{timestamp}.sql`
  - Use credentials from environment
  - Target: namespace=agent_spike, database=graph
- Fetch SQL dump to local `backups/surrealdb/`
- Cleanup remote temp file
- Local cleanup: keep only last 7 backups (delete older)

**Command example**:
```bash
docker exec surrealdb surreal export \
  --conn http://localhost:8000 \
  --user root \
  --pass $SURREALDB_PASSWORD \
  --ns agent_spike \
  --db graph \
  /tmp/surrealdb-backup-$(date +%Y-%m-%d_%H-%M-%S).sql
```

### 2. Makefile Target: `surrealdb-backup`

**Location**: Root `Makefile` (GPU Server Management section)

**Implementation**:
```makefile
## Backup SurrealDB database to local machine
surrealdb-backup:
	@echo "Backing up SurrealDB from GPU server..."
	@cd infra/ansible && docker compose run --rm ansible ansible-playbook playbooks/backup-surrealdb.yml
	@echo "Backup complete: backups/surrealdb/"
```

### 3. Daily Cron Job on GPU Server

**Options**:
- Add cron task to existing `infra/ansible/playbooks/deploy.yml`
- OR create new `infra/ansible/playbooks/setup-backup-cron.yml`

**Cron schedule**: `0 2 * * *` (2 AM daily)

**Implementation**:
```yaml
- name: Setup daily SurrealDB backup cron
  ansible.builtin.cron:
    name: "SurrealDB backup to local"
    minute: "0"
    hour: "2"
    job: "cd /home/user/ansible && docker compose run --rm ansible ansible-playbook playbooks/backup-surrealdb.yml"
    user: "{{ ansible_user }}"
```

**Note**: May need to adjust path/user based on GPU server setup

### 4. Gitignore Update

**File**: `.gitignore`

**Add**:
```
# SurrealDB backups (local disaster recovery)
backups/
```

### 5. Documentation: `docs/SURREALDB-BACKUP.md`

**Contents**:
- Manual backup: `make surrealdb-backup`
- Automated daily backups (2 AM)
- Restore procedure:
  ```bash
  # 1. Stop SurrealDB on GPU server
  # 2. Import backup
  docker exec surrealdb surreal import \
    --conn http://localhost:8000 \
    --user root --pass $PASS \
    --ns agent_spike --db graph \
    /path/to/backup.sql
  # 3. Restart SurrealDB
  ```
- Verify backup integrity (check file size, test import)
- Retention policy (7 backups)
- Recovery scenarios (data corruption, server failure, accidental deletion)

## Files to Create/Modify

**Create**:
- `infra/ansible/playbooks/backup-surrealdb.yml` - Main backup playbook
- `docs/SURREALDB-BACKUP.md` - Backup/restore documentation
- `backups/.keep` - Ensure directory exists in git

**Modify**:
- `Makefile` - Add `surrealdb-backup` target (around line 300)
- `.gitignore` - Add `backups/` exclusion
- `infra/ansible/playbooks/deploy.yml` - Add cron job task (optional)

## Dependencies

**Already in place**:
- ✅ SurrealDB CLI available in container on GPU server
- ✅ Ansible SSH access to GPU server (192.168.16.241)
- ✅ SURREALDB_PASSWORD in root `.env` (git-crypt encrypted)
- ✅ Ansible Docker Compose setup in `infra/ansible/`

**No additional dependencies required**

## Testing Plan

1. **Manual backup test**: `make surrealdb-backup`
   - Verify SQL dump created in `backups/surrealdb/`
   - Check file size (should be >0 bytes)
   - Verify timestamp format

2. **Retention test**: Run backup 8 times
   - Verify only 7 newest backups remain
   - Verify oldest deleted automatically

3. **Restore test**:
   - Create test database
   - Import backup
   - Verify data integrity

4. **Cron test** (optional):
   - Wait for 2 AM or manually trigger cron
   - Verify backup appears in `backups/surrealdb/`

## Implementation Order

1. ✅ Create plan document (this file)
2. Update `.gitignore` (add `backups/`)
3. Create Ansible playbook (`backup-surrealdb.yml`)
4. Add Makefile target (`surrealdb-backup`)
5. Test manual backup (`make surrealdb-backup`)
6. Create documentation (`docs/SURREALDB-BACKUP.md`)
7. Add cron job to `deploy.yml` (if desired)
8. Test automated backup

## Future Enhancements

- Upload backups to offsite storage (cloud storage, NAS)
- Monitor backup health (file size, age)
- Backup verification (test restore in separate container)
- Incremental backups (though SurrealDB EXPORT is always full)
- Backup encryption (gpg)
- Backup compression (gzip)

## Notes

- **Why SQL dump over file copy?**
  - SQL dump doesn't require stopping SurrealDB
  - Version-independent (can restore to different SurrealDB versions)
  - Portable and human-readable
  - Can selective restore (tables, records)

- **Why local backups?**
  - MinIO is on same server/drive as SurrealDB
  - Single point of failure - server failure takes out both
  - Local backups survive GPU server complete failure

- **Backup size estimate**:
  - Current database: Unknown (need to measure)
  - SQL dumps are typically larger than binary (text format)
  - Expect ~1-10MB per backup initially
  - 7 backups × 10MB = ~70MB max storage

## Related Files

- Current backup playbook: `infra/ansible/playbooks/backup.yml` (config only)
- SurrealDB config: `compose/services/surrealdb/config.py`
- SurrealDB repository: `compose/services/surrealdb/repository.py`
- Docker Compose: `infra/ansible/files/ai-services/docker-compose.yml`
