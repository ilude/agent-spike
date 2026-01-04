"""Fixtures for integration tests.

Provides isolated SurrealDB and MinIO connections that use test-specific
namespaces/buckets, cleaned up after each test.
"""

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from surrealdb import AsyncSurreal

from compose.lib.env_loader import load_root_env
from compose.services.surrealdb.config import SurrealDBConfig

# Load environment variables from root .env
load_root_env()


# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(items):
    """Auto-mark all tests in integration/ as integration tests."""
    for item in items:
        if "/integration/" in str(item.fspath) or "\\integration\\" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest_asyncio.fixture
async def clean_tables() -> AsyncGenerator[AsyncSurreal, None]:
    """Provide a fresh SurrealDB connection with isolated test namespace.

    Each test gets its own namespace that is cleaned up after the test.
    """
    config = SurrealDBConfig()
    test_namespace = f"test_{uuid.uuid4().hex[:8]}"
    test_database = "integration"

    db = AsyncSurreal(config.url)

    try:
        # Use the test namespace/database first (creates if not exists)
        await db.use(test_namespace, test_database)

        # Then authenticate
        await db.signin({"username": config.user, "password": config.password})

        yield db

    finally:
        # Cleanup: remove the entire test namespace
        try:
            await db.query(f"REMOVE DATABASE {test_database};")
            await db.query(f"REMOVE NAMESPACE {test_namespace};")
        except Exception:
            pass  # Best effort cleanup


@pytest.fixture(scope="session")
def test_minio_bucket() -> str:
    """Generate a unique test bucket name for MinIO."""
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def minio_config(test_minio_bucket: str):
    """MinIO config pointing to test bucket."""
    from compose.services.minio.config import MinIOConfig

    config = MinIOConfig()
    config.bucket = test_minio_bucket
    return config


@pytest.fixture(scope="session")
def minio_client(minio_config) -> "MinIOClient":
    """Provide an isolated MinIO client for integration tests.

    Creates a test bucket, yields the client, then cleans up
    by removing all objects and the bucket itself.
    """
    from compose.services.minio.client import MinIOClient

    client = MinIOClient(minio_config)

    try:
        # Create test bucket
        client.ensure_bucket()
        print(f"\n[Integration] Using MinIO bucket={minio_config.bucket}")

        yield client

    finally:
        # Cleanup: remove all objects and the bucket
        try:
            # List and delete all objects
            objects = client.client.list_objects(minio_config.bucket, recursive=True)
            for obj in objects:
                client.client.remove_object(minio_config.bucket, obj.object_name)

            # Remove the bucket
            client.client.remove_bucket(minio_config.bucket)
            print(f"\n[Integration] Cleaned up bucket={minio_config.bucket}")
        except Exception as e:
            print(f"\n[Integration] MinIO cleanup warning: {e}")
