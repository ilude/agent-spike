# syntax=docker/dockerfile:1.7-labs
ARG PYTHON_VERSION=3.14-slim-bookworm

FROM python:${PYTHON_VERSION} as base

ARG TZ=America/New_York
ENV TZ=${TZ}

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    gosu \
    locales \
    tzdata && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# User setup
ARG PUID=${PUID:-1000}
ARG PGID=${PGID:-1000}
ARG USER=anvil
ENV USER=${USER}
ENV HOME=/home/${USER}

ARG PROJECT_PATH=/srv
ENV PROJECT_PATH=${PROJECT_PATH}

WORKDIR $PROJECT_PATH

RUN sed -i 's/UID_MAX .*/UID_MAX    100000/' /etc/login.defs && \
    groupadd --gid ${PGID} ${USER} && \
    useradd --uid ${PUID} --gid ${PGID} -s /bin/sh -m ${USER} && \
    mkdir -p ${PROJECT_PATH} && \
    chown -R ${USER}:${USER} ${PROJECT_PATH} && \
    chown -R ${USER}:${USER} ${HOME}

# Entrypoint script
COPY --chmod=755 <<-"EOF" /usr/local/bin/docker-entrypoint.sh
#!/bin/bash
set -euo pipefail
if [ "${DOCKER_ENTRYPOINT_DEBUG:-}" = "1" ]; then
    set -x
fi

# If running as root, adjust the ${USER} user's UID/GID and drop to that user
if [ "$(id -u)" = "0" ]; then
    groupmod -o -g ${PGID:-1000} ${USER} 2>&1 >/dev/null || true
    usermod -o -u ${PUID:-1000} ${USER} 2>&1 >/dev/null || true

    # Run devcontainer entrypoint hooks if present
    if [ -d "${PROJECT_PATH}/.devcontainer/entrypoint.d" ]; then
        for hook in "${PROJECT_PATH}"/.devcontainer/entrypoint.d/*.sh; do
            if [ -f "$hook" ]; then
                echo "devcontainer hook START: $hook at $(date) PID=$$"
                set +e
                bash "$hook"
                rc=$?
                set -e
                echo "devcontainer hook FINISH: $hook at $(date) rc=${rc}"
            fi
        done
    fi

    # Ensure project path ownership for the runtime user
    ( [ -S /var/run/docker.sock ] || [ -e /var/run/docker.sock ] ) && chown ${USER}:${USER} /var/run/docker.sock || true
    chown -R ${USER}:${USER} ${PROJECT_PATH} || true

    echo "Running as user ${USER}: $@"
    exec gosu ${USER} "$@"
fi

echo "Running: $@"
exec "$@"
EOF

ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh" ]

# uv environment configuration
ENV PYTHONUNBUFFERED=TRUE
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1
ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_BREAK_SYSTEM_PACKAGES=1
ENV XDG_CACHE_HOME=${HOME}/.cache
ENV UV_CACHE_DIR=${HOME}/.cache/uv

# Build-base stage
FROM base as build-base

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y --no-install-recommends \
    bash \
    binutils \
    build-essential \
    pkg-config \
    cmake \
    git \
    openssl \
    openssh-client \
    sqlite3 \
    libsqlite3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/*

# Build stage
FROM build-base as build

COPY uv.lock* pyproject.toml ${PROJECT_PATH}/

RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=cache,id=pip-cache,target=/root/.cache/pip,sharing=locked \
    cd ${PROJECT_PATH} && \
    ([ -f uv.lock ] || uv lock) && \
    uv sync --no-editable --no-dev

COPY src ${PROJECT_PATH}/src

# Production stage
FROM base as production

COPY --chown=${USER}:${USER} src ${PROJECT_PATH}/src
COPY --from=build --chown=${USER}:${USER} /usr/local/lib/python3*/site-packages /usr/local/lib/python3*/site-packages
COPY --from=build --chown=${USER}:${USER} /usr/local/bin /usr/local/bin

USER ${USER}
CMD [ "uv", "run", "--no-sync", "python", "-m", "src.app.cli" ]

# Development OS packages stage
FROM build-base as development-base

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    coreutils \
    docker.io \
    dnsutils \
    exa \
    gh \
    gnuplot \
    gnuplot-x11 \
    graphviz \
    imagemagick \
    iproute2 \
    iputils-ping \
    jq \
    less \
    libpq-dev \
    libzmq3-dev \
    make \
    nodejs \
    npm \
    passwd \
    python3-pip \
    python3-setuptools \
    ripgrep \
    rsync \
    sshpass \
    sudo \
    tar \
    tree \
    unison \
    util-linux \
    yarnpkg \
    yq \
    zsh \
    zsh-autosuggestions \
    zsh-syntax-highlighting && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/* && \
    echo ${USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER} && \
    # set the shell for $USER and root
    chsh -s "$(which zsh)" ${USER}  && \
    chsh -s "$(which zsh)" root

# Devcontainer stage
FROM development-base as devcontainer

# Copy lockfile and root pyproject for reproducible resolution
COPY uv.lock* pyproject.toml ${PROJECT_PATH}/

# Install Python dependencies into the system environment (run as root)
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=cache,id=pip-cache,target=/root/.cache/pip,sharing=locked \
    cd ${PROJECT_PATH} && \
    ([ -f uv.lock ] || uv lock) && \
    uv sync --dev && \
    chown -R $USER:$USER /usr/local/lib/python*/site-packages/ && \
    chown -R $USER:$USER /usr/local/bin


# Switch to non-root user for development
USER ${USER}

# Note: For production images, don't set DOCKER_BUILDKIT/COMPOSE_DOCKER_CLI_BUILD.
# We set DOCKER_BUILDKIT=1 only in the devcontainer stage to affect the docker CLI inside the container.

# Enable BuildKit for docker CLI inside the devcontainer
ENV DOCKER_BUILDKIT=1

# https://code.visualstudio.com/remote/advancedcontainers/start-processes#_adding-startup-commands-to-the-docker-image-instead
CMD [ "sleep", "infinity" ]
