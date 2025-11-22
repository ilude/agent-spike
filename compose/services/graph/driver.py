"""Neo4j driver management with lazy initialization.

Provides a singleton driver instance that connects on first use.
Supports both sync and async operations.
"""

import os
from contextlib import contextmanager
from typing import Optional, Generator, Any

from neo4j import GraphDatabase, Driver, Session


# Configuration from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


# Singleton driver instance
_driver: Optional[Driver] = None


def get_driver() -> Driver:
    """Get or create the Neo4j driver singleton.

    Returns:
        Neo4j driver instance

    Raises:
        ValueError: If NEO4J_PASSWORD is not set
    """
    global _driver

    if _driver is None:
        if not NEO4J_PASSWORD:
            raise ValueError("NEO4J_PASSWORD environment variable is required")

        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,  # 1 hour
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )

    return _driver


def close_driver() -> None:
    """Close the driver connection. Call on application shutdown."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def reset_driver() -> None:
    """Reset driver for testing purposes."""
    global _driver
    _driver = None


@contextmanager
def get_session(database: str = "neo4j") -> Generator[Session, None, None]:
    """Context manager for Neo4j sessions.

    Usage:
        with get_session() as session:
            result = session.run("MATCH (n) RETURN n LIMIT 10")

    Args:
        database: Database name (default: neo4j)

    Yields:
        Neo4j session
    """
    driver = get_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        session.close()


def execute_query(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    database: str = "neo4j",
) -> list[dict[str, Any]]:
    """Execute a Cypher query and return results as dicts.

    Args:
        query: Cypher query string
        parameters: Query parameters
        database: Database name

    Returns:
        List of result records as dictionaries
    """
    with get_session(database) as session:
        result = session.run(query, parameters or {})
        return [dict(record) for record in result]


def execute_write(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    database: str = "neo4j",
) -> dict[str, Any]:
    """Execute a write query and return summary.

    Args:
        query: Cypher query string
        parameters: Query parameters
        database: Database name

    Returns:
        Query summary with counters
    """
    with get_session(database) as session:
        result = session.run(query, parameters or {})
        summary = result.consume()
        return {
            "nodes_created": summary.counters.nodes_created,
            "nodes_deleted": summary.counters.nodes_deleted,
            "relationships_created": summary.counters.relationships_created,
            "relationships_deleted": summary.counters.relationships_deleted,
            "properties_set": summary.counters.properties_set,
        }


def verify_connection() -> bool:
    """Verify Neo4j connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False
