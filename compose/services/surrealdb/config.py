"""SurrealDB configuration from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class SurrealDBConfig:
    """Configuration for SurrealDB connection.

    All settings come from environment variables with sensible defaults
    for local development.
    """

    url: str = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    user: str = os.getenv("SURREALDB_USER", "root")
    password: str = os.getenv("SURREALDB_PASSWORD", "root")
    namespace: str = os.getenv("SURREALDB_NAMESPACE", "agent_spike")
    database: str = os.getenv("SURREALDB_DATABASE", "graph")

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
