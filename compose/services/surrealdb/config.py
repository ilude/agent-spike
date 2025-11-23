"""SurrealDB configuration from environment variables."""

import os
from dataclasses import dataclass, field


def _get_env(key: str, default: str) -> str:
    """Get environment variable at call time, not import time."""
    return os.getenv(key, default)


@dataclass
class SurrealDBConfig:
    """Configuration for SurrealDB connection.

    All settings come from environment variables with sensible defaults
    for local development.

    Note: Uses field(default_factory=...) to read env vars at instance
    creation time, not at class definition time.
    """

    url: str = field(default_factory=lambda: _get_env("SURREALDB_URL", "ws://localhost:8000"))
    user: str = field(default_factory=lambda: _get_env("SURREALDB_USER", "root"))
    password: str = field(default_factory=lambda: _get_env("SURREALDB_PASSWORD", "root"))
    namespace: str = field(default_factory=lambda: _get_env("SURREALDB_NAMESPACE", "agent_spike"))
    database: str = field(default_factory=lambda: _get_env("SURREALDB_DATABASE", "graph"))

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.url:
            raise ValueError("SURREALDB_URL is required")
        if not self.user:
            raise ValueError("SURREALDB_USER is required")
        if not self.password:
            raise ValueError("SURREALDB_PASSWORD is required")
        if not self.namespace:
            raise ValueError("SURREALDB_NAMESPACE is required")
        if not self.database:
            raise ValueError("SURREALDB_DATABASE is required")
