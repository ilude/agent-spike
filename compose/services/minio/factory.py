"""Factory functions for creating MinIO service instances."""

from .client import MinIOClient
from .config import MinIOConfig


def create_minio_client() -> MinIOClient:
    """Create and initialize a MinIO client.

    Loads configuration from environment variables and ensures bucket exists.

    Returns:
        Initialized MinIOClient instance.
    """
    config = MinIOConfig()
    client = MinIOClient(config)
    client.ensure_bucket()
    return client
