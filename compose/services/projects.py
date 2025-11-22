"""Project storage service for organizing conversations and files.

Projects group conversations together with shared:
- Custom instructions (system prompt)
- Uploaded files (RAG-indexed)
- Memory (conversation context within project)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


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
    qdrant_indexed: bool = False
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
    """Service for managing project storage."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize service with data directory.

        Args:
            data_dir: Path to projects directory.
                      Defaults to compose/data/projects/
        """
        if data_dir is None:
            base = Path(__file__).parent.parent / "data" / "projects"
            self.data_dir = base
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"

        # Ensure index exists
        if not self.index_path.exists():
            self._save_index(ProjectIndex())

    def _load_index(self) -> ProjectIndex:
        """Load the project index."""
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
                return ProjectIndex(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return ProjectIndex()

    def _save_index(self, index: ProjectIndex) -> None:
        """Save the project index."""
        with open(self.index_path, "w") as f:
            json.dump(index.model_dump(), f, indent=2)

    def _project_dir(self, project_id: str) -> Path:
        """Get directory for a project."""
        return self.data_dir / project_id

    def _project_path(self, project_id: str) -> Path:
        """Get path to project JSON file."""
        return self._project_dir(project_id) / "project.json"

    def _files_dir(self, project_id: str) -> Path:
        """Get directory for project files."""
        return self._project_dir(project_id) / "files"

    def list_projects(self) -> list[ProjectMeta]:
        """List all projects (metadata only).

        Returns projects sorted by updated_at descending.
        """
        index = self._load_index()
        return sorted(index.projects, key=lambda p: p.updated_at, reverse=True)

    def create_project(
        self, name: str = "New Project", description: str = ""
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            description: Optional description

        Returns:
            The created project
        """
        project = Project(name=name, description=description)

        # Create project directory structure
        project_dir = self._project_dir(project.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        self._files_dir(project.id).mkdir(exist_ok=True)

        # Save project file
        with open(self._project_path(project.id), "w") as f:
            json.dump(project.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        index.projects.append(project.to_meta())
        self._save_index(index)

        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: The project ID

        Returns:
            The project or None if not found
        """
        path = self._project_path(project_id)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)
                return Project(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Optional[Project]:
        """Update project settings.

        Args:
            project_id: The project ID
            name: New name (optional)
            description: New description (optional)
            custom_instructions: New custom instructions (optional)

        Returns:
            Updated project or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if custom_instructions is not None:
            project.custom_instructions = custom_instructions

        project.updated_at = datetime.now(timezone.utc).isoformat()

        # Save project file
        with open(self._project_path(project_id), "w") as f:
            json.dump(project.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        for i, meta in enumerate(index.projects):
            if meta.id == project_id:
                index.projects[i] = project.to_meta()
                break
        self._save_index(index)

        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its files.

        Args:
            project_id: The project ID

        Returns:
            True if deleted, False if not found
        """
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            return False

        # Delete all files in project
        import shutil

        shutil.rmtree(project_dir)

        # Update index
        index = self._load_index()
        index.projects = [p for p in index.projects if p.id != project_id]
        self._save_index(index)

        return True

    def add_conversation_to_project(
        self, project_id: str, conversation_id: str
    ) -> Optional[Project]:
        """Add a conversation to a project.

        Args:
            project_id: The project ID
            conversation_id: The conversation ID to add

        Returns:
            Updated project or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        if conversation_id not in project.conversation_ids:
            project.conversation_ids.append(conversation_id)
            project.updated_at = datetime.now(timezone.utc).isoformat()

            with open(self._project_path(project_id), "w") as f:
                json.dump(project.model_dump(), f, indent=2)

            # Update index
            index = self._load_index()
            for i, meta in enumerate(index.projects):
                if meta.id == project_id:
                    index.projects[i] = project.to_meta()
                    break
            self._save_index(index)

        return project

    def remove_conversation_from_project(
        self, project_id: str, conversation_id: str
    ) -> Optional[Project]:
        """Remove a conversation from a project.

        Args:
            project_id: The project ID
            conversation_id: The conversation ID to remove

        Returns:
            Updated project or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        if conversation_id in project.conversation_ids:
            project.conversation_ids.remove(conversation_id)
            project.updated_at = datetime.now(timezone.utc).isoformat()

            with open(self._project_path(project_id), "w") as f:
                json.dump(project.model_dump(), f, indent=2)

            # Update index
            index = self._load_index()
            for i, meta in enumerate(index.projects):
                if meta.id == project_id:
                    index.projects[i] = project.to_meta()
                    break
            self._save_index(index)

        return project

    def add_file(
        self,
        project_id: str,
        filename: str,
        original_filename: str,
        content_type: str,
        file_data: bytes,
    ) -> Optional[ProjectFile]:
        """Add a file to a project.

        Args:
            project_id: The project ID
            filename: Stored filename (sanitized)
            original_filename: Original uploaded filename
            content_type: MIME type
            file_data: File contents

        Returns:
            The created ProjectFile or None if project not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        file_record = ProjectFile(
            filename=filename,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=len(file_data),
        )

        # Save file to disk
        files_dir = self._files_dir(project_id)
        files_dir.mkdir(exist_ok=True)
        file_path = files_dir / f"{file_record.id}_{filename}"
        with open(file_path, "wb") as f:
            f.write(file_data)

        # Update project
        project.files.append(file_record)
        project.updated_at = datetime.now(timezone.utc).isoformat()

        with open(self._project_path(project_id), "w") as f:
            json.dump(project.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        for i, meta in enumerate(index.projects):
            if meta.id == project_id:
                index.projects[i] = project.to_meta()
                break
        self._save_index(index)

        return file_record

    def get_file_path(self, project_id: str, file_id: str) -> Optional[Path]:
        """Get the filesystem path to a project file.

        Args:
            project_id: The project ID
            file_id: The file ID

        Returns:
            Path to the file or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        for file_record in project.files:
            if file_record.id == file_id:
                file_path = (
                    self._files_dir(project_id)
                    / f"{file_record.id}_{file_record.filename}"
                )
                if file_path.exists():
                    return file_path
                break

        return None

    def delete_file(self, project_id: str, file_id: str) -> bool:
        """Delete a file from a project.

        Args:
            project_id: The project ID
            file_id: The file ID

        Returns:
            True if deleted, False if not found
        """
        project = self.get_project(project_id)
        if not project:
            return False

        file_record = None
        for f in project.files:
            if f.id == file_id:
                file_record = f
                break

        if not file_record:
            return False

        # Delete file from disk
        file_path = (
            self._files_dir(project_id)
            / f"{file_record.id}_{file_record.filename}"
        )
        if file_path.exists():
            file_path.unlink()

        # Update project
        project.files = [f for f in project.files if f.id != file_id]
        project.updated_at = datetime.now(timezone.utc).isoformat()

        with open(self._project_path(project_id), "w") as f:
            json.dump(project.model_dump(), f, indent=2)

        # Update index
        index = self._load_index()
        for i, meta in enumerate(index.projects):
            if meta.id == project_id:
                index.projects[i] = project.to_meta()
                break
        self._save_index(index)

        return True

    def mark_file_processed(
        self,
        project_id: str,
        file_id: str,
        qdrant_indexed: bool = False,
        error: Optional[str] = None,
    ) -> Optional[ProjectFile]:
        """Mark a file as processed.

        Args:
            project_id: The project ID
            file_id: The file ID
            qdrant_indexed: Whether the file was indexed in Qdrant
            error: Any processing error

        Returns:
            Updated file record or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        file_record = None
        for f in project.files:
            if f.id == file_id:
                f.processed = True
                f.qdrant_indexed = qdrant_indexed
                f.processing_error = error
                file_record = f
                break

        if not file_record:
            return None

        project.updated_at = datetime.now(timezone.utc).isoformat()

        with open(self._project_path(project_id), "w") as f:
            json.dump(project.model_dump(), f, indent=2)

        return file_record


# Singleton instance
_service: Optional[ProjectService] = None


def get_project_service() -> ProjectService:
    """Get or create the project service singleton."""
    global _service
    if _service is None:
        # Check for container path first, fall back to local
        container_path = Path("/app/src/compose/data/projects")
        if container_path.exists():
            _service = ProjectService(str(container_path))
        else:
            _service = ProjectService()
    return _service
