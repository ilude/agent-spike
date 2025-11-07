# Git Hooks

This directory contains git hooks that enhance the Brave history workflow.

## Available Hooks

### post-checkout
Prompts to update Brave history after checking out a branch.

### post-merge  
Prompts to update Brave history after pulling changes.

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
chmod +x .git/hooks/post-checkout .git/hooks/post-merge
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
cd projects/brave_history
python copy_brave_history.py
```
