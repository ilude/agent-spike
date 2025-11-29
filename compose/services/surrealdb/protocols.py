"""Protocols for SurrealDB operations.

Defines abstract interfaces for database operations to enable
dependency injection and testability.
"""

from typing import Any, Protocol


class DatabaseExecutor(Protocol):
    """Protocol for database query execution.

    Implementations:
    - RealDatabaseExecutor: Uses actual SurrealDB connection
    - FakeDatabaseExecutor: In-memory implementation for testing
    """

    async def execute(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SurrealQL query and return results.

        Args:
            query: SurrealQL query string
            params: Query parameters

        Returns:
            List of result records as dictionaries
        """
        ...
