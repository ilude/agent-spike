# GPG and Git-Crypt Setup Guide

This document explains how GPG keys and git-crypt are configured for cross-machine sync.

## Overview

This repository uses **git-crypt** to encrypt sensitive files (`.env`, credentials, etc.). The GPG keys are stored in `~/.ssh/` so they sync across your machines automatically.

## Architecture

```
~/.ssh/
├── gpg/                          # GPG keyring (synced)
│   └── ... (GPG database files)
└── git-crypt-keys/              # Key backups (synced)
    ├── git-crypt-private-key.asc
    ├── git-crypt-public-key.asc
    └── README.md

~/.gnupg → ~/.ssh/gpg            # Junction/symlink for GPG to find keyring

agent-spike/
├── .git-crypt/                  # Git-crypt metadata (in repo)
│   └── keys/default/0/
│       └── BEF464...632.gpg     # Encrypted key (safe to commit)
└── .gitattributes               # Encryption rules
```

## Key Details

- **Key ID**: `BEF464A08DC846D83764059CAFA2D36EE32CB632`
- **User**: Mike Glenn <mglenn@ilude.com>
- **Type**: RSA 4096-bit
- **Created**: November 7, 2025

## Setup Workflow

### Primary Machine (Initial Setup - Already Done)

1. Generated GPG key with `make setup-gpg`
   - Key stored in `~/.ssh/gpg` (synced location)
   - Junction created: `~/.gnupg` → `~/.ssh/gpg`

2. Initialized git-crypt:
   ```bash
   git-crypt init
   git-crypt add-gpg-user BEF464A08DC846D83764059CAFA2D36EE32CB632
   ```

3. Exported keys to `~/.ssh/git-crypt-keys/` for backup/sync:
   ```bash
   gpg --export-secret-keys --armor <KEY-ID> > ~/.ssh/git-crypt-keys/git-crypt-private-key.asc
   gpg --export --armor <KEY-ID> > ~/.ssh/git-crypt-keys/git-crypt-public-key.asc
   ```

### Secondary Machine (New Setup)

**Automatic (Recommended):**
```bash
# 1. Ensure ~/.ssh/ is synced (including git-crypt-keys/)
# 2. Clone the repository
git clone <repo-url>
cd agent-spike

# 3. Run setup - imports keys and unlocks automatically
make setup
```

**Manual (if needed):**
```bash
# Import the GPG key
gpg --import ~/.ssh/git-crypt-keys/git-crypt-private-key.asc

# Trust the key (required for git-crypt)
echo "BEF464A08DC846D83764059CAFA2D36EE32CB632:6:" | gpg --import-ownertrust

# Unlock the repository
git-crypt unlock
```

## What `make setup` Does

The `setup` target (defined in `Makefile`) runs `scripts/setup-git-crypt.ps1`, which:

1. ✅ Installs GPG and git-crypt (if not present)
2. ✅ Creates `~/.ssh/gpg` directory for keyring
3. ✅ Creates junction: `~/.gnupg` → `~/.ssh/gpg`
4. ✅ Imports GPG key from `~/.ssh/git-crypt-keys/` (if exists)
5. ✅ Trusts the imported key
6. ✅ Unlocks git-crypt repository automatically

## Encrypted Files

Files encrypted by git-crypt (defined in `.gitattributes`):

```
.env filter=git-crypt diff=git-crypt
**/.env filter=git-crypt diff=git-crypt
```

When locked:
- Files appear as binary gibberish in working directory
- Commits contain encrypted versions

When unlocked:
- Files appear as plain text
- You can read/edit them normally
- Git-crypt automatically encrypts on commit

## Verification

Check if repository is unlocked:
```bash
git-crypt status
```

Check if GPG key is imported:
```bash
gpg --list-keys BEF464A08DC846D83764059CAFA2D36EE32CB632
```

View encrypted files:
```bash
git-crypt status | grep encrypted
```

## Security Notes

⚠️ **Private Key Security**:
- The private key in `~/.ssh/git-crypt-keys/` can decrypt all encrypted files
- Ensure your sync solution is secure (encrypted, private)
- Never commit these keys to a git repository
- `~/.ssh/` should already have proper permissions (600/700)

✅ **Safe to Commit**:
- `.git-crypt/` directory (encrypted key material)
- `.gitattributes` (encryption rules)
- `scripts/setup-git-crypt.ps1` (setup automation)

❌ **Never Commit**:
- `~/.ssh/git-crypt-keys/` (private key backups)
- Decrypted `.env` files
- `~/.ssh/gpg/` keyring files

## Troubleshooting

### "Your credit balance is too low" on git-crypt

This means the repository is locked. Run:
```bash
git-crypt unlock
```

### "No secret key" error

Your GPG key is not imported or not trusted:
```bash
# Re-import
gpg --import ~/.ssh/git-crypt-keys/git-crypt-private-key.asc
echo "BEF464A08DC846D83764059CAFA2D36EE32CB632:6:" | gpg --import-ownertrust
```

### Files still appear encrypted

After unlocking, you may need to:
```bash
# Clear git's cached state
git checkout -- .

# Or reset working directory
git reset --hard HEAD
```

### New machine - no keys in ~/.ssh/git-crypt-keys/

Your sync hasn't completed yet, or you need to export from primary machine:
```bash
# On primary machine:
gpg --export-secret-keys --armor BEF464A08DC846D83764059CAFA2D36EE32CB632 > ~/.ssh/git-crypt-keys/git-crypt-private-key.asc
```

## Adding New Encrypted Files

Edit `.gitattributes`:
```bash
echo 'secrets/*.key filter=git-crypt diff=git-crypt' >> .gitattributes
git add .gitattributes
git commit -m "docs: add secrets/*.key to git-crypt"
```

## See Also

- `.gitattributes` - Encryption rules
- `scripts/setup-git-crypt.ps1` - Automated setup script
- `scripts/setup-gpg-key.ps1` - GPG key generation script
- `~/.ssh/git-crypt-keys/README.md` - Key backup documentation
