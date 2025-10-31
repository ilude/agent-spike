---
description: "Ignore files management"
applyTo: "**/.{gitignore,dockerignore}"
---

# Ignore Files Standards

## Organization
- Keep entries alphabetical within sections (case-sensitive; ASCII for specials)

## Synchronization
- Both files include: `*.pyc`, `__pycache__/`, build artifacts, test outputs, `.env.*`, `.specstory/`
- Only `.gitignore`: editor dirs (`.vscode/`, `.idea/`), local dev files
- Only `.dockerignore`: docs (`README.md`, `docs/`), CI/CD (`.github/`), Git metadata (`.git/`, `.gitignore`)
