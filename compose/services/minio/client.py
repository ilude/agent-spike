"""MinIO client wrapper for object storage operations."""

import json
from io import BytesIO

from minio import Minio

from .config import MinIOConfig


class MinIOClient:
    """Client for interacting with MinIO object storage."""

    def __init__(self, config: MinIOConfig):
        """Initialize MinIO client.

        Args:
            config: MinIOConfig instance with connection details.
        """
        endpoint = config.url.replace("http://", "").replace("https://", "")
        self.client = Minio(
            endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
        )
        self.bucket = config.bucket

    def ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_json(self, path: str, data: dict) -> str:
        """Store JSON data in MinIO.

        Args:
            path: Object path in bucket.
            data: Dictionary to store as JSON.

        Returns:
            The path where data was stored.
        """
        content = json.dumps(data, default=str).encode()
        self.client.put_object(
            self.bucket,
            path,
            BytesIO(content),
            len(content),
            content_type="application/json",
        )
        return path

    def get_json(self, path: str) -> dict:
        """Retrieve JSON data from MinIO.

        Args:
            path: Object path in bucket.

        Returns:
            Deserialized JSON data.
        """
        response = self.client.get_object(self.bucket, path)
        return json.loads(response.read().decode())

    def put_text(self, path: str, text: str) -> str:
        """Store text data in MinIO.

        Args:
            path: Object path in bucket.
            text: Text content to store.

        Returns:
            The path where data was stored.
        """
        content = text.encode()
        self.client.put_object(
            self.bucket,
            path,
            BytesIO(content),
            len(content),
            content_type="text/plain",
        )
        return path

    def get_text(self, path: str) -> str:
        """Retrieve text data from MinIO.

        Args:
            path: Object path in bucket.

        Returns:
            Text content.
        """
        response = self.client.get_object(self.bucket, path)
        return response.read().decode()

    def exists(self, path: str) -> bool:
        """Check if object exists in MinIO.

        Args:
            path: Object path in bucket.

        Returns:
            True if object exists, False otherwise.
        """
        try:
            self.client.stat_object(self.bucket, path)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> None:
        """Delete object from MinIO.

        Args:
            path: Object path in bucket.
        """
        self.client.remove_object(self.bucket, path)

    def list_objects(self, prefix: str = "") -> list:
        """List objects in MinIO bucket.

        Args:
            prefix: Optional prefix to filter objects.

        Returns:
            List of objects matching prefix.
        """
        return list(
            self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        )
