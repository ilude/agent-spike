# GPU Server Management with Ansible

Ansible container setup for managing Docker Compose stacks on the GPU server.

## Quick Start

```bash
# First time: Backup existing configuration from GPU server
make gpu-backup

# Deploy changes (syncs files + pulls images + starts services)
make gpu-deploy

# Quick update (just pulls latest images and restarts)
make gpu-update

# Manual commands via Ansible shell
make gpu-shell
```

## Structure

```
infra/ansible/
├── Dockerfile              # Ansible container image
├── docker-compose.yml      # Container configuration
├── ansible.cfg             # Ansible settings
├── inventory/
│   └── hosts.yml           # GPU server connection details
├── playbooks/
│   ├── backup.yml          # Fetch current config from server
│   ├── deploy.yml          # Full deploy with file sync
│   └── update.yml          # Quick pull + restart
└── files/
    └── ai-services/        # Compose stack to deploy
        └── docker-compose.yml
```

## Configuration

Edit `inventory/hosts.yml` to update:
- `ansible_host`: GPU server IP address
- `ansible_user`: SSH user (default: root)
- `compose_dir`: Remote path for compose files (default: /apps/ai-services)

## Workflow

1. **Initial setup**: Run `make gpu-backup` to fetch current server config
2. **Edit locally**: Modify files in `files/ai-services/`
3. **Deploy**: Run `make gpu-deploy` to push changes and restart services
4. **Updates**: Run `make gpu-update` to pull latest images without file changes

## Requirements

- Docker (for running the Ansible container)
- SSH key access to GPU server (keys mounted from `~/.ssh/`)
