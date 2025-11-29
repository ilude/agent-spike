"""Project storage service for organizing conversations and files.

Projects group conversations together with shared:
- Custom instructions (system prompt)
- Uploaded files (RAG-indexed)
- Memory (conversation context within project)

Storage:
- SurrealDB for metadata (projects, files, conversations)
- MinIO for file content
"""

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from .minio.factory import create_minio_client
from .surrealdb.driver import RealDatabaseExecutor

if TYPE_CHECKING:
    from .minio.client import MinIOClient
    from .surrealdb.protocols import DatabaseExecutor

def _extract_id(record_id) -> str:
    """Extract clean ID from SurrealDB RecordID.

    SurrealDB returns RecordID objects instead of plain strings.
    These convert to 'table:id' format when stringified.
    This helper converts to string and strips the table prefix.
    """
    id_str = str(record_id)
    if ":" in id_str:
        return id_str.split(":", 1)[1]
    return id_str


class ProjectMeta(BaseModel):
    """Project metadata for index listing."""

    id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    conversation_count: int = 0
    file_count: int = 0


class ProjectFile(BaseModel):
    """A file uploaded to a project."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Processing status
    processed: bool = False
    vector_indexed: bool = False
    processing_error: Optional[str] = None


class Project(BaseModel):
    """Full project with settings and file list."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Project"
    description: str = ""
    custom_instructions: str = ""  # System prompt for all project conversations
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    conversation_ids: list[str] = Field(default_factory=list)
    files: list[ProjectFile] = Field(default_factory=list)

    def to_meta(self) -> ProjectMeta:
        """Convert to metadata for index."""
        return ProjectMeta(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
            conversation_count=len(self.conversation_ids),
            file_count=len(self.files),
        )


class ProjectIndex(BaseModel):
    """Index of all projects."""

    projects: list[ProjectMeta] = Field(default_factory=list)


class ProjectService:
    """Service for managing project storage using SurrealDB + MinIO.

    - SurrealDB stores project metadata, file records, and conversation links
    - MinIO stores actual file content at projects/{project_id}/{file_id}_{filename}

    Supports dependency injection for testability:
    - Pass db parameter to use a custom DatabaseExecutor (e.g., FakeDatabaseExecutor)
    - Pass minio parameter to use a custom MinIOClient (e.g., FakeMinIOClient)
    """

    def __init__(
        self,
        db: "DatabaseExecutor | None" = None,
        minio: "MinIOClient | None" = None,
    ):
        """Initialize service with optional dependencies.

        Args:
            db: Database executor for SurrealDB operations. If None, uses RealDatabaseExecutor.
            minio: MinIO client for file storage. If None, uses create_minio_client().
        """
        self._db = db
        self._minio = minio

    @property
    def db(self) -> "DatabaseExecutor":
        """Get database executor (lazy-loaded if not injected)."""
        if self._db is None:
            self._db = RealDatabaseExecutor()
        return self._db

    @property
    def minio(self) -> "MinIOClient":
        """Get MinIO client (lazy-loaded if not injected)."""
        if self._minio is None:
            self._minio = create_minio_client()
        return self._minio

    def _minio_key(self, project_id: str, file_id: str, filename: str) -> str:
        """Generate MinIO object key for a file."""
        return f"projects/{project_id}/{file_id}_{filename}"

    async def list_projects(self) -> list[ProjectMeta]:
        """List all projects (metadata only).

        Returns projects sorted by updated_at descending.
        """
        result = await self.db.execute(
            "SELECT * FROM project ORDER BY updated_at DESC"
        )

        projects = []
        for row in result:
            conv_result = await self.db.execute(
                "SELECT count() FROM project_conversation WHERE project_id = $project_id GROUP ALL",
                {"project_id": row["id"]},
            )
            conv_count = conv_result[0].get("count", 0) if conv_result else 0

            file_result = await self.db.execute(
                "SELECT count() FROM project_file WHERE project_id = $project_id GROUP ALL",
                {"project_id": row["id"]},
            )
            file_count = file_result[0].get("count", 0) if file_result else 0

            projects.append(
                ProjectMeta(
                    id=_extract_id(row["id"]),
                    name=row.get("name", ""),
                    description=row.get("description", ""),
                    created_at=str(row.get("created_at", "")),
                    updated_at=str(row.get("updated_at", "")),
                    conversation_count=conv_count,
                    file_count=file_count,
                )
            )

        return projects

    async def create_project(
        self, name: str = "New Project", description: str = ""
    ) -> Project:
        """Create a new project."""
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            """
            CREATE project CONTENT {
                id: $id,
                name: $name,
                description: $description,
                custom_instructions: '',
                created_at: $created_at,
                updated_at: $updated_at
            }
            """,
            {
                "id": project_id,
                "name": name,
                "description": description,
                "created_at": now,
                "updated_at": now,
            },
        )

        return Project(
            id=project_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        result = await self.db.execute(
            "SELECT * FROM project WHERE id = $id",
            {"id": project_id},
        )

        if not result:
            return None

        row = result[0]

        file_result = await self.db.execute(
            "SELECT * FROM project_file WHERE project_id = $project_id ORDER BY uploaded_at DESC",
            {"project_id": project_id},
        )

        files = []
        for f in file_result:
            files.append(
                ProjectFile(
                    id=_extract_id(f["id"]),
                    filename=f.get("filename", ""),
                    original_filename=f.get("original_filename", ""),
                    content_type=f.get("content_type", ""),
                    size_bytes=f.get("size_bytes", 0),
                    uploaded_at=str(f.get("uploaded_at", "")),
                    processed=f.get("processed", False),
                    vector_indexed=f.get("vector_indexed", False),
                    processing_error=f.get("processing_error"),
                )
            )

        conv_result = await self.db.execute(
            "SELECT conversation_id FROM project_conversation WHERE project_id = $project_id",
            {"project_id": project_id},
        )
        conversation_ids = [str(c["conversation_id"]) for c in conv_result]

        return Project(
            id=_extract_id(row["id"]),
            name=row.get("name", ""),
            description=row.get("description", ""),
            custom_instructions=row.get("custom_instructions", ""),
            created_at=str(row.get("created_at", "")),
            updated_at=str(row.get("updated_at", "")),
            conversation_ids=conversation_ids,
            files=files,
        )

    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Optional[Project]:
        """Update project settings."""
        existing = await self.get_project(project_id)
        if not existing:
            return None

        now = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = $updated_at"]
        params = {"id": project_id, "updated_at": now}

        if name is not None:
            updates.append("name = $name")
            params["name"] = name
        if description is not None:
            updates.append("description = $description")
            params["description"] = description
        if custom_instructions is not None:
            updates.append("custom_instructions = $custom_instructions")
            params["custom_instructions"] = custom_instructions

        await self.db.execute(
            f"UPDATE project SET {', '.join(updates)} WHERE id = $id",
            params,
        )

        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its files."""
        existing = await self.get_project(project_id)
        if not existing:
            return False

        for file in existing.files:
            key = self._minio_key(project_id, file.id, file.filename)
            try:
                self.minio.delete(key)
            except Exception:
                pass

        await self.db.execute(
            "DELETE FROM project_file WHERE project_id = $project_id",
            {"project_id": project_id},
        )
        await self.db.execute(
            "DELETE FROM project_conversation WHERE project_id = $project_id",
            {"project_id": project_id},
        )
        await self.db.execute(
            "DELETE FROM project WHERE id = $id",
            {"id": project_id},
        )

        return True

    async def add_conversation_to_project(
        self, project_id: str, conversation_id: str
    ) -> Optional[Project]:
        """Add a conversation to a project."""
        existing = await self.get_project(project_id)
        if not existing:
            return None

        if conversation_id in existing.conversation_ids:
            return existing

        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            """
            CREATE project_conversation CONTENT {
                project_id: $project_id,
                conversation_id: $conversation_id,
                created_at: $created_at
            }
            """,
            {
                "project_id": project_id,
                "conversation_id": conversation_id,
                "created_at": now,
            },
        )

        await self.db.execute(
            "UPDATE project SET updated_at = $updated_at WHERE id = $id",
            {"id": project_id, "updated_at": now},
        )

        return await self.get_project(project_id)

    async def remove_conversation_from_project(
        self, project_id: str, conversation_id: str
    ) -> Optional[Project]:
        """Remove a conversation from a project."""
        existing = await self.get_project(project_id)
        if not existing:
            return None

        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            "DELETE FROM project_conversation WHERE project_id = $project_id AND conversation_id = $conversation_id",
            {"project_id": project_id, "conversation_id": conversation_id},
        )

        await self.db.execute(
            "UPDATE project SET updated_at = $updated_at WHERE id = $id",
            {"id": project_id, "updated_at": now},
        )

        return await self.get_project(project_id)

    async def add_file(
        self,
        project_id: str,
        filename: str,
        original_filename: str,
        content_type: str,
        file_data: bytes,
    ) -> Optional[ProjectFile]:
        """Add a file to a project."""
        existing = await self.get_project(project_id)
        if not existing:
            return None

        file_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        size_bytes = len(file_data)

        minio_key = self._minio_key(project_id, file_id, filename)
        self.minio.client.put_object(
            self.minio.bucket,
            minio_key,
            BytesIO(file_data),
            size_bytes,
            content_type=content_type,
        )

        await self.db.execute(
            """
            CREATE project_file CONTENT {
                id: $id,
                project_id: $project_id,
                filename: $filename,
                original_filename: $original_filename,
                content_type: $content_type,
                size_bytes: $size_bytes,
                minio_key: $minio_key,
                processed: false,
                vector_indexed: false,
                processing_error: NONE,
                uploaded_at: $uploaded_at
            }
            """,
            {
                "id": file_id,
                "project_id": project_id,
                "filename": filename,
                "original_filename": original_filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "minio_key": minio_key,
                "uploaded_at": now,
            },
        )

        await self.db.execute(
            "UPDATE project SET updated_at = $updated_at WHERE id = $id",
            {"id": project_id, "updated_at": now},
        )

        return ProjectFile(
            id=file_id,
            filename=filename,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_at=now,
        )

    async def get_file_content(self, project_id: str, file_id: str) -> Optional[bytes]:
        """Get the content of a project file from MinIO."""
        result = await self.db.execute(
            "SELECT * FROM project_file WHERE id = $id AND project_id = $project_id",
            {"id": file_id, "project_id": project_id},
        )

        if not result:
            return None

        minio_key = result[0].get("minio_key")
        if not minio_key:
            return None

        try:
            response = self.minio.client.get_object(self.minio.bucket, minio_key)
            return response.read()
        except Exception:
            return None

    async def get_file_path(self, project_id: str, file_id: str) -> Optional[str]:
        """Get the MinIO key for a project file.

        Note: Returns MinIO key, not filesystem path. Use get_file_content() for data.
        """
        result = await self.db.execute(
            "SELECT minio_key FROM project_file WHERE id = $id AND project_id = $project_id",
            {"id": file_id, "project_id": project_id},
        )

        if not result:
            return None

        return result[0].get("minio_key")

    async def delete_file(self, project_id: str, file_id: str) -> bool:
        """Delete a file from a project."""
        result = await self.db.execute(
            "SELECT * FROM project_file WHERE id = $id AND project_id = $project_id",
            {"id": file_id, "project_id": project_id},
        )

        if not result:
            return False

        minio_key = result[0].get("minio_key")

        if minio_key:
            try:
                self.minio.delete(minio_key)
            except Exception:
                pass

        await self.db.execute(
            "DELETE FROM project_file WHERE id = $id",
            {"id": file_id},
        )

        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE project SET updated_at = $updated_at WHERE id = $id",
            {"id": project_id, "updated_at": now},
        )

        return True

    async def mark_file_processed(
        self,
        project_id: str,
        file_id: str,
        vector_indexed: bool = False,
        error: Optional[str] = None,
    ) -> Optional[ProjectFile]:
        """Mark a file as processed."""
        result = await self.db.execute(
            "SELECT * FROM project_file WHERE id = $id AND project_id = $project_id",
            {"id": file_id, "project_id": project_id},
        )

        if not result:
            return None

        await self.db.execute(
            """
            UPDATE project_file SET
                processed = true,
                vector_indexed = $vector_indexed,
                processing_error = $error
            WHERE id = $id
            """,
            {"id": file_id, "vector_indexed": vector_indexed, "error": error},
        )

        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE project SET updated_at = $updated_at WHERE id = $id",
            {"id": project_id, "updated_at": now},
        )

        updated = await self.db.execute(
            "SELECT * FROM project_file WHERE id = $id",
            {"id": file_id},
        )

        if not updated:
            return None

        f = updated[0]
        return ProjectFile(
            id=_extract_id(f["id"]),
            filename=f.get("filename", ""),
            original_filename=f.get("original_filename", ""),
            content_type=f.get("content_type", ""),
            size_bytes=f.get("size_bytes", 0),
            uploaded_at=str(f.get("uploaded_at", "")),
            processed=f.get("processed", False),
            vector_indexed=f.get("vector_indexed", False),
            processing_error=f.get("processing_error"),
        )


# Singleton instance
_service: Optional[ProjectService] = None


def get_project_service() -> ProjectService:
    """Get or create the project service singleton."""
    global _service
    if _service is None:
        _service = ProjectService()
    return _service
