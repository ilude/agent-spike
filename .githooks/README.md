# Git Hooks

This directory contains git hooks for security and workflow automation.

## Available Hooks

### pre-commit (ACTIVE)
Verifies git-crypt encryption for sensitive files being committed.

**Performance**: Only checks **staged files** (fast, ~1-2 seconds)
- Ensures .env, secrets/, browser_history/, and brave_history/ are encrypted
- Prevents accidentally committing unencrypted sensitive data
- **Previously**: Scanned all 1,633 encrypted files (~1 minute 15 seconds)
- **Now**: Only scans files you're committing (typically 1-5 files)

## Manual Operations

### Sync Brave History
```bash
make brave-sync
```

Manually runs Brave history sync. No longer runs automatically on checkout/merge to avoid slowing down git operations.

### Check Encryption Status
```bash
git crypt status -e           # Show all encrypted files (slow, 1min+)
git crypt status -f <file>    # Check specific file (fast)
```

## Installation

Hooks are automatically used via:
```bash
git config core.hooksPath .githooks
```

This is already configured in the repository.

## Removed Hooks

The following hooks were removed for performance:

- **post-checkout** - Previously auto-synced Brave history after branch checkout (~30 seconds)
- **post-merge** - Previously auto-synced Brave history after git pull (~30 seconds)

Use `make brave-sync` to manually sync when needed.
