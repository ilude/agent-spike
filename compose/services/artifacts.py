"""Artifact storage service for Canvas documents (SurrealDB backend).

Artifacts are documents created during conversations that can be:
- Standalone documents (markdown, code, etc.)
- Linked to conversations and/or projects
- Viewed and edited in the Canvas sidebar
- Browsed across all conversations in the artifacts browser
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .surrealdb.driver import execute_query


class ArtifactMeta(BaseModel):
    """Lightweight artifact metadata for listings."""

    id: str
    title: str
    artifact_type: str  # "document", "code", "markdown", etc.
    language: Optional[str] = None  # For code artifacts
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    preview: str = ""  # First 200 chars for preview


class Artifact(ArtifactMeta):
    """Full artifact with content."""

    content: str


def _parse_datetime(value) -> datetime:
    """Parse datetime from SurrealDB result."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now()


def _record_to_artifact(record: dict) -> Artifact:
    """Convert SurrealDB record to Artifact model."""
    # Handle SurrealDB record ID format (artifact:uuid)
    record_id = str(record.get("id", ""))
    if ":" in record_id:
        record_id = record_id.split(":", 1)[1]

    return Artifact(
        id=record_id,
        title=record.get("title", ""),
        artifact_type=record.get("artifact_type", "document"),
        language=record.get("language"),
        conversation_id=record.get("conversation_id"),
        project_id=record.get("project_id"),
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
        preview=record.get("preview", ""),
        content=record.get("content", ""),
    )


def _record_to_meta(record: dict) -> ArtifactMeta:
    """Convert SurrealDB record to ArtifactMeta model."""
    # Handle SurrealDB record ID format (artifact:uuid)
    record_id = str(record.get("id", ""))
    if ":" in record_id:
        record_id = record_id.split(":", 1)[1]

    return ArtifactMeta(
        id=record_id,
        title=record.get("title", ""),
        artifact_type=record.get("artifact_type", "document"),
        language=record.get("language"),
        conversation_id=record.get("conversation_id"),
        project_id=record.get("project_id"),
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
        preview=record.get("preview", ""),
    )


class ArtifactService:
    """Service for managing artifact storage in SurrealDB."""

    async def list_artifacts(
        self,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> list[ArtifactMeta]:
        """List artifacts, optionally filtered by conversation or project.

        Args:
            conversation_id: Filter by conversation
            project_id: Filter by project

        Returns:
            List of artifact metadata sorted by updated_at desc
        """
        # Build query with optional filters
        conditions = []
        params = {}

        if conversation_id:
            conditions.append("conversation_id = $conversation_id")
            params["conversation_id"] = conversation_id

        if project_id:
            conditions.append("project_id = $project_id")
            params["project_id"] = project_id

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        SELECT id, title, artifact_type, language, conversation_id, project_id,
               created_at, updated_at, preview
        FROM artifact
        {where_clause}
        ORDER BY updated_at DESC;
        """

        results = await execute_query(query, params)
        return [_record_to_meta(r) for r in results]

    async def create_artifact(
        self,
        title: str,
        content: str,
        artifact_type: str = "document",
        language: Optional[str] = None,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Artifact:
        """Create a new artifact.

        Args:
            title: Artifact title
            content: Artifact content (markdown, code, etc.)
            artifact_type: Type of artifact
            language: Programming language (for code)
            conversation_id: Associated conversation
            project_id: Associated project

        Returns:
            Created artifact
        """
        artifact_id = str(uuid.uuid4())

        # Generate preview (first 200 chars, strip whitespace)
        preview = content[:200].strip() if content else ""
        if len(content) > 200:
            preview += "..."

        query = """
        CREATE artifact SET
            id = $id,
            title = $title,
            artifact_type = $artifact_type,
            language = $language,
            content = $content,
            preview = $preview,
            conversation_id = $conversation_id,
            project_id = $project_id,
            created_at = time::now(),
            updated_at = time::now();
        """

        params = {
            "id": artifact_id,
            "title": title,
            "artifact_type": artifact_type,
            "language": language,
            "content": content,
            "preview": preview,
            "conversation_id": conversation_id,
            "project_id": project_id,
        }

        results = await execute_query(query, params)

        if results:
            return _record_to_artifact(results[0])

        # Return constructed artifact if no result returned
        now = datetime.utcnow()
        return Artifact(
            id=artifact_id,
            title=title,
            artifact_type=artifact_type,
            language=language,
            conversation_id=conversation_id,
            project_id=project_id,
            created_at=now,
            updated_at=now,
            preview=preview,
            content=content,
        )

    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID.

        Args:
            artifact_id: Artifact ID

        Returns:
            Artifact or None if not found
        """
        query = "SELECT * FROM artifact WHERE id = $id LIMIT 1;"

        results = await execute_query(query, {"id": artifact_id})

        if not results:
            return None

        return _record_to_artifact(results[0])

    async def update_artifact(
        self,
        artifact_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        artifact_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[Artifact]:
        """Update an existing artifact.

        Args:
            artifact_id: Artifact ID
            title: New title (optional)
            content: New content (optional)
            artifact_type: New type (optional)
            language: New language (optional)

        Returns:
            Updated artifact or None if not found
        """
        # Build SET clause dynamically based on provided fields
        set_parts = ["updated_at = time::now()"]
        params = {"id": artifact_id}

        if title is not None:
            set_parts.append("title = $title")
            params["title"] = title

        if content is not None:
            set_parts.append("content = $content")
            params["content"] = content
            # Update preview
            preview = content[:200].strip() if content else ""
            if len(content) > 200:
                preview += "..."
            set_parts.append("preview = $preview")
            params["preview"] = preview

        if artifact_type is not None:
            set_parts.append("artifact_type = $artifact_type")
            params["artifact_type"] = artifact_type

        if language is not None:
            set_parts.append("language = $language")
            params["language"] = language

        query = f"""
        UPDATE artifact SET {", ".join(set_parts)}
        WHERE id = $id;
        """

        results = await execute_query(query, params)

        if not results:
            return None

        return _record_to_artifact(results[0])

    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: Artifact ID

        Returns:
            True if deleted, False if not found
        """
        # Check if exists first
        check_query = "SELECT id FROM artifact WHERE id = $id LIMIT 1;"
        exists = await execute_query(check_query, {"id": artifact_id})

        if not exists:
            return False

        query = "DELETE artifact WHERE id = $id;"
        await execute_query(query, {"id": artifact_id})
        return True

    async def link_to_conversation(
        self, artifact_id: str, conversation_id: str
    ) -> Optional[Artifact]:
        """Link an artifact to a conversation.

        Args:
            artifact_id: Artifact ID
            conversation_id: Conversation ID

        Returns:
            Updated artifact or None if not found
        """
        query = """
        UPDATE artifact SET
            conversation_id = $conversation_id,
            updated_at = time::now()
        WHERE id = $id;
        """

        results = await execute_query(query, {
            "id": artifact_id,
            "conversation_id": conversation_id,
        })

        if not results:
            return None

        return _record_to_artifact(results[0])

    async def link_to_project(
        self, artifact_id: str, project_id: str
    ) -> Optional[Artifact]:
        """Link an artifact to a project.

        Args:
            artifact_id: Artifact ID
            project_id: Project ID

        Returns:
            Updated artifact or None if not found
        """
        query = """
        UPDATE artifact SET
            project_id = $project_id,
            updated_at = time::now()
        WHERE id = $id;
        """

        results = await execute_query(query, {
            "id": artifact_id,
            "project_id": project_id,
        })

        if not results:
            return None

        return _record_to_artifact(results[0])


# Singleton service instance
_artifact_service: Optional[ArtifactService] = None


def get_artifact_service() -> ArtifactService:
    """Get artifact service singleton."""
    global _artifact_service
    if _artifact_service is None:
        _artifact_service = ArtifactService()
    return _artifact_service
