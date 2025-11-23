"""SurrealDB driver management with async support and retry logic.

Provides a singleton async connection that connects on first use.
Supports context manager for query operations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from surrealdb import AsyncSurreal

from .config import SurrealDBConfig

logger = logging.getLogger(__name__)

# Singleton connection instance
_db: Optional[AsyncSurreal] = None
_lock = asyncio.Lock()


async def get_db() -> AsyncSurreal:
    """Get or create the SurrealDB connection singleton.

    Uses lazy initialization with async locking to ensure thread-safe
    connection creation.

    Returns:
        SurrealDB connection instance

    Raises:
        ValueError: If configuration validation fails
        Exception: If connection fails after retries
    """
    global _db

    if _db is not None:
        return _db

    async with _lock:
        # Double-check pattern for thread safety
        if _db is not None:
            return _db

        config = SurrealDBConfig()
        config.validate()

        # Create connection - no explicit connect() needed with AsyncSurreal
        db = AsyncSurreal(config.url)

        # Use namespace and database first
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await db.use(config.namespace, config.database)
                logger.info(f"Connected to SurrealDB at {config.url}")
                logger.info(
                    f"Using namespace={config.namespace}, database={config.database}"
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to connect to SurrealDB: {e}")
                    raise
                logger.warning(
                    f"Connection attempt {attempt + 1} failed, retrying: {e}"
                )
                await asyncio.sleep(1)

        # Sign in
        try:
            await db.signin({
                "username": config.user,
                "password": config.password,
            })
            logger.info("Signed in to SurrealDB")
        except Exception as e:
            logger.error(f"Failed to sign in: {e}")
            raise

        _db = db
        return _db


async def close_db() -> None:
    """Close the database connection. Call on application shutdown."""
    global _db
    if _db is not None:
        try:
            # AsyncSurreal may not have close() - just reset the reference
            _db = None
            logger.info("Closed SurrealDB connection")
        except Exception as e:
            logger.error(f"Error closing SurrealDB connection: {e}")
            _db = None


def reset_db() -> None:
    """Reset database connection for testing purposes."""
    global _db
    _db = None


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[AsyncSurreal, None]:
    """Context manager for SurrealDB operations.

    Usage:
        async with get_transaction() as db:
            result = await db.select("video")

    Yields:
        SurrealDB connection instance
    """
    db = await get_db()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error in transaction: {e}")
        raise


async def execute_query(
    query: str,
    params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Execute a SurrealQL query and return results.

    Args:
        query: SurrealQL query string
        params: Query parameters

    Returns:
        List of result records as dictionaries
    """
    db = await get_db()
    try:
        result = await db.query(query, params or {})
        # SurrealDB Python client returns results directly as a list
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise


async def verify_connection() -> bool:
    """Verify SurrealDB connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        db = await get_db()
        # SurrealDB requires a valid query - use time::now() as a simple ping
        await db.query("RETURN time::now()")
        return True
    except Exception as e:
        logger.error(f"Connection verification failed: {e}")
        return False
