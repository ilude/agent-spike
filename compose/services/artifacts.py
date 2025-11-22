"""Artifact storage service for Canvas documents.

Artifacts are documents created during conversations that can be:
- Standalone documents (markdown, code, etc.)
- Linked to conversations and/or projects
- Viewed and edited in the Canvas sidebar
- Browsed across all conversations in the artifacts browser
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


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


class ArtifactIndex(BaseModel):
    """Index of all artifacts for fast listing."""

    artifacts: dict[str, ArtifactMeta] = Field(default_factory=dict)


class ArtifactService:
    """Service for managing artifact storage."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize artifact service with data directory."""
        if data_dir is None:
            # Default to compose/data/artifacts
            base = Path(__file__).parent.parent / "data" / "artifacts"
        else:
            base = data_dir
        self.data_dir = base
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"
        self._index: Optional[ArtifactIndex] = None

    def _load_index(self) -> ArtifactIndex:
        """Load artifact index from disk."""
        if self._index is not None:
            return self._index

        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                # Parse datetime strings
                for artifact_id, meta in data.get("artifacts", {}).items():
                    meta["created_at"] = datetime.fromisoformat(meta["created_at"])
                    meta["updated_at"] = datetime.fromisoformat(meta["updated_at"])
                self._index = ArtifactIndex(**data)
            except Exception as e:
                print(f"Error loading artifact index: {e}")
                self._index = ArtifactIndex()
        else:
            self._index = ArtifactIndex()

        return self._index

    def _save_index(self) -> None:
        """Save artifact index to disk."""
        if self._index is None:
            return

        data = {
            "artifacts": {
                k: {
                    **v.model_dump(),
                    "created_at": v.created_at.isoformat(),
                    "updated_at": v.updated_at.isoformat(),
                }
                for k, v in self._index.artifacts.items()
            }
        }
        self.index_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def _artifact_path(self, artifact_id: str) -> Path:
        """Get path to artifact content file."""
        return self.data_dir / f"{artifact_id}.json"

    def list_artifacts(
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
        index = self._load_index()
        artifacts = list(index.artifacts.values())

        if conversation_id:
            artifacts = [a for a in artifacts if a.conversation_id == conversation_id]

        if project_id:
            artifacts = [a for a in artifacts if a.project_id == project_id]

        # Sort by most recently updated
        artifacts.sort(key=lambda a: a.updated_at, reverse=True)
        return artifacts

    def create_artifact(
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
        now = datetime.utcnow()

        # Generate preview (first 200 chars, strip whitespace)
        preview = content[:200].strip() if content else ""
        if len(content) > 200:
            preview += "..."

        artifact = Artifact(
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

        # Save content
        artifact_data = {
            **artifact.model_dump(),
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
        }
        self._artifact_path(artifact_id).write_text(
            json.dumps(artifact_data, indent=2), encoding="utf-8"
        )

        # Update index
        index = self._load_index()
        index.artifacts[artifact_id] = ArtifactMeta(
            id=artifact.id,
            title=artifact.title,
            artifact_type=artifact.artifact_type,
            language=artifact.language,
            conversation_id=artifact.conversation_id,
            project_id=artifact.project_id,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            preview=preview,
        )
        self._save_index()

        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID.

        Args:
            artifact_id: Artifact ID

        Returns:
            Artifact or None if not found
        """
        path = self._artifact_path(artifact_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            return Artifact(**data)
        except Exception as e:
            print(f"Error loading artifact {artifact_id}: {e}")
            return None

    def update_artifact(
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
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None

        # Update fields
        if title is not None:
            artifact.title = title
        if content is not None:
            artifact.content = content
            # Update preview
            artifact.preview = content[:200].strip() if content else ""
            if len(content) > 200:
                artifact.preview += "..."
        if artifact_type is not None:
            artifact.artifact_type = artifact_type
        if language is not None:
            artifact.language = language

        artifact.updated_at = datetime.utcnow()

        # Save content
        artifact_data = {
            **artifact.model_dump(),
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
        }
        self._artifact_path(artifact_id).write_text(
            json.dumps(artifact_data, indent=2), encoding="utf-8"
        )

        # Update index
        index = self._load_index()
        if artifact_id in index.artifacts:
            index.artifacts[artifact_id] = ArtifactMeta(
                id=artifact.id,
                title=artifact.title,
                artifact_type=artifact.artifact_type,
                language=artifact.language,
                conversation_id=artifact.conversation_id,
                project_id=artifact.project_id,
                created_at=artifact.created_at,
                updated_at=artifact.updated_at,
                preview=artifact.preview,
            )
            self._save_index()

        return artifact

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: Artifact ID

        Returns:
            True if deleted, False if not found
        """
        path = self._artifact_path(artifact_id)
        if not path.exists():
            return False

        # Remove file
        path.unlink()

        # Remove from index
        index = self._load_index()
        if artifact_id in index.artifacts:
            del index.artifacts[artifact_id]
            self._save_index()

        return True

    def link_to_conversation(
        self, artifact_id: str, conversation_id: str
    ) -> Optional[Artifact]:
        """Link an artifact to a conversation.

        Args:
            artifact_id: Artifact ID
            conversation_id: Conversation ID

        Returns:
            Updated artifact or None if not found
        """
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None

        artifact.conversation_id = conversation_id
        artifact.updated_at = datetime.utcnow()

        # Save
        artifact_data = {
            **artifact.model_dump(),
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
        }
        self._artifact_path(artifact_id).write_text(
            json.dumps(artifact_data, indent=2), encoding="utf-8"
        )

        # Update index
        index = self._load_index()
        if artifact_id in index.artifacts:
            index.artifacts[artifact_id].conversation_id = conversation_id
            index.artifacts[artifact_id].updated_at = artifact.updated_at
            self._save_index()

        return artifact

    def link_to_project(
        self, artifact_id: str, project_id: str
    ) -> Optional[Artifact]:
        """Link an artifact to a project.

        Args:
            artifact_id: Artifact ID
            project_id: Project ID

        Returns:
            Updated artifact or None if not found
        """
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None

        artifact.project_id = project_id
        artifact.updated_at = datetime.utcnow()

        # Save
        artifact_data = {
            **artifact.model_dump(),
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
        }
        self._artifact_path(artifact_id).write_text(
            json.dumps(artifact_data, indent=2), encoding="utf-8"
        )

        # Update index
        index = self._load_index()
        if artifact_id in index.artifacts:
            index.artifacts[artifact_id].project_id = project_id
            index.artifacts[artifact_id].updated_at = artifact.updated_at
            self._save_index()

        return artifact


# Singleton service instance
_artifact_service: Optional[ArtifactService] = None


def get_artifact_service() -> ArtifactService:
    """Get artifact service singleton."""
    global _artifact_service
    if _artifact_service is None:
        _artifact_service = ArtifactService()
    return _artifact_service
