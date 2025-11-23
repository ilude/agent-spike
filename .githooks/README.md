# Git Hooks

This directory contains git hooks that enhance the Brave history workflow.

## Available Hooks

### post-checkout
Prompts to update Brave history after checking out a branch.

### post-merge
Prompts to update Brave history after pulling changes.

### pre-commit
Verifies git-crypt encryption for sensitive brave_history files.

## Installation

### Automatic (Recommended)
```bash
git config core.hooksPath .githooks
```

This tells git to use the `.githooks` directory instead of `.git/hooks`.

### Manual
Copy the hooks to your `.git/hooks` directory:

**Unix/Linux/macOS:**
```bash
cp .githooks/* .git/hooks/
chmod +x .git/hooks/post-checkout .git/hooks/post-merge .git/hooks/pre-commit
```

**Windows (Git Bash):**
```bash
cp .githooks/* .git/hooks/
```

**Windows (PowerShell):**
```powershell
Copy-Item .githooks\* .git\hooks\ -Force
```

## Usage

Once installed, the hooks will automatically prompt you to update the Brave history database when:
- Checking out a branch
- Pulling changes from remote

You can choose to update (y) or skip (n) the prompt.

## Manual Execution

You can always run the update manually:
```bash
uv run python compose/cli/brave_history/copy_brave_history.py --incremental --dest compose/data/queues/brave_history
```

Or use the Makefile target:
```bash
make brave-sync
```
