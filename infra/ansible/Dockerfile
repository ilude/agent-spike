# Lightweight Ansible container for managing remote Docker Compose stacks
FROM python:3.12-slim

LABEL maintainer="agent-spike"
LABEL description="Ansible container for GPU server management"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    git \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Install Ansible
RUN pip install --no-cache-dir \
    ansible-core \
    && ansible-galaxy collection install community.docker community.general

# Create non-root user matching devcontainer pattern
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g ${PGID} ansible \
    && useradd -u ${PUID} -g ansible -m -s /bin/bash ansible

# Set up working directory
WORKDIR /ansible

# Copy ansible config (will be overridden by mount in most cases)
COPY ansible.cfg /etc/ansible/ansible.cfg

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint to fix SSH key permissions
ENTRYPOINT ["/entrypoint.sh"]

# Default command shows help
CMD ["ansible", "--version"]
