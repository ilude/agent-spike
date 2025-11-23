"""MinIO configuration from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class MinIOConfig:
    """MinIO configuration loaded from environment variables."""

    url: str = os.getenv("MINIO_URL", "http://localhost:9000")
    access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket: str = os.getenv("MINIO_BUCKET", "vectors")
    secure: bool = False
