"""Tests for project storage service.

Run with: uv run pytest compose/services/tests/unit/test_projects.py
"""

import json
import time
from pathlib import Path

import pytest

from compose.services.projects import (
    Project,
    ProjectFile,
    ProjectMeta,
    ProjectService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service(tmp_path):
    """Create service with temp directory."""
    return ProjectService(data_dir=str(tmp_path))


@pytest.fixture
def project_with_files(service):
    """Create a project with some test files."""
    project = service.create_project(name="Test Project", description="A test project")

    # Add a text file
    service.add_file(
        project_id=project.id,
        filename="test.txt",
        original_filename="test.txt",
        content_type="text/plain",
        file_data=b"Hello, world!",
    )

    # Add a PDF file
    service.add_file(
        project_id=project.id,
        filename="document.pdf",
        original_filename="document.pdf",
        content_type="application/pdf",
        file_data=b"%PDF-1.4 fake pdf content",
    )

    return service.get_project(project.id)


# =============================================================================
# Model Tests
# =============================================================================


@pytest.mark.unit
class TestProjectModels:
    """Tests for Pydantic models."""

    def test_project_default_values(self):
        """Test Project model with default values."""
        project = Project()

        assert project.id is not None
        assert len(project.id) == 36  # UUID format
        assert project.name == "New Project"
        assert project.description == ""
        assert project.custom_instructions == ""
        assert project.conversation_ids == []
        assert project.files == []
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_with_values(self):
        """Test Project model with explicit values."""
        project = Project(
            id="test-id",
            name="My Project",
            description="A description",
            custom_instructions="Be helpful",
            conversation_ids=["conv1", "conv2"],
        )

        assert project.id == "test-id"
        assert project.name == "My Project"
        assert project.description == "A description"
        assert project.custom_instructions == "Be helpful"
        assert project.conversation_ids == ["conv1", "conv2"]

    def test_project_to_meta(self):
        """Test Project.to_meta() conversion."""
        project = Project(
            id="test-id",
            name="My Project",
            description="A description",
            conversation_ids=["conv1", "conv2", "conv3"],
            files=[
                ProjectFile(
                    filename="test.txt",
                    original_filename="test.txt",
                    content_type="text/plain",
                    size_bytes=100,
                )
            ],
        )

        meta = project.to_meta()

        assert isinstance(meta, ProjectMeta)
        assert meta.id == "test-id"
        assert meta.name == "My Project"
        assert meta.description == "A description"
        assert meta.conversation_count == 3
        assert meta.file_count == 1

    def test_project_file_default_values(self):
        """Test ProjectFile model with default values."""
        file = ProjectFile(
            filename="test.txt",
            original_filename="original_test.txt",
            content_type="text/plain",
            size_bytes=1024,
        )

        assert file.id is not None
        assert len(file.id) == 36  # UUID format
        assert file.filename == "test.txt"
        assert file.original_filename == "original_test.txt"
        assert file.content_type == "text/plain"
        assert file.size_bytes == 1024
        assert file.processed is False
        assert file.qdrant_indexed is False
        assert file.processing_error is None
        assert file.uploaded_at is not None

    def test_project_meta(self):
        """Test ProjectMeta model."""
        meta = ProjectMeta(
            id="test-id",
            name="Test Project",
            description="Description",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            conversation_count=5,
            file_count=3,
        )

        assert meta.id == "test-id"
        assert meta.name == "Test Project"
        assert meta.conversation_count == 5
        assert meta.file_count == 3


# =============================================================================
# Service Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestServiceInit:
    """Tests for ProjectService initialization."""

    def test_init_creates_directory(self, tmp_path):
        """Test that __init__ creates the data directory."""
        data_dir = tmp_path / "projects"
        assert not data_dir.exists()

        service = ProjectService(data_dir=str(data_dir))

        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_init_creates_index_file(self, tmp_path):
        """Test that __init__ creates the index.json file."""
        data_dir = tmp_path / "projects"

        service = ProjectService(data_dir=str(data_dir))

        index_path = data_dir / "index.json"
        assert index_path.exists()

        # Verify index structure
        with open(index_path) as f:
            data = json.load(f)
        assert "projects" in data
        assert data["projects"] == []

    def test_init_preserves_existing_index(self, tmp_path):
        """Test that __init__ doesn't overwrite existing index."""
        data_dir = tmp_path / "projects"
        data_dir.mkdir(parents=True)

        # Create existing index with data
        index_path = data_dir / "index.json"
        existing_data = {
            "projects": [
                {
                    "id": "existing-id",
                    "name": "Existing Project",
                    "description": "",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "conversation_count": 0,
                    "file_count": 0,
                }
            ]
        }
        with open(index_path, "w") as f:
            json.dump(existing_data, f)

        # Init service
        service = ProjectService(data_dir=str(data_dir))

        # Verify index wasn't overwritten
        with open(index_path) as f:
            data = json.load(f)
        assert len(data["projects"]) == 1
        assert data["projects"][0]["id"] == "existing-id"

    def test_init_creates_nested_directories(self, tmp_path):
        """Test that __init__ creates nested directory structure."""
        data_dir = tmp_path / "deep" / "nested" / "projects"

        service = ProjectService(data_dir=str(data_dir))

        assert data_dir.exists()


# =============================================================================
# List Projects Tests
# =============================================================================


@pytest.mark.unit
class TestListProjects:
    """Tests for list_projects method."""

    def test_list_projects_empty(self, service):
        """Test listing when no projects exist."""
        projects = service.list_projects()

        assert projects == []

    def test_list_projects_returns_meta(self, service):
        """Test that list returns ProjectMeta objects."""
        service.create_project(name="Test Project")

        projects = service.list_projects()

        assert len(projects) == 1
        assert isinstance(projects[0], ProjectMeta)

    def test_list_projects_sorted_by_updated_at_desc(self, service):
        """Test that projects are sorted by updated_at descending."""
        # Create projects with slight delays to get different timestamps
        p1 = service.create_project(name="First")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        p2 = service.create_project(name="Second")
        time.sleep(0.01)
        p3 = service.create_project(name="Third")

        projects = service.list_projects()

        assert len(projects) == 3
        # Most recently updated should be first
        assert projects[0].name == "Third"
        assert projects[1].name == "Second"
        assert projects[2].name == "First"

    def test_list_projects_reflects_updates(self, service):
        """Test that updated project moves to top of list."""
        p1 = service.create_project(name="First")
        time.sleep(0.01)
        p2 = service.create_project(name="Second")
        time.sleep(0.01)

        # Update first project
        service.update_project(p1.id, name="First Updated")

        projects = service.list_projects()

        assert projects[0].name == "First Updated"
        assert projects[1].name == "Second"


# =============================================================================
# Create Project Tests
# =============================================================================


@pytest.mark.unit
class TestCreateProject:
    """Tests for create_project method."""

    def test_create_project_default_values(self, service):
        """Test creating project with default values."""
        project = service.create_project()

        assert project.name == "New Project"
        assert project.description == ""
        assert project.id is not None

    def test_create_project_with_name_and_description(self, service):
        """Test creating project with name and description."""
        project = service.create_project(
            name="My Project",
            description="A test project",
        )

        assert project.name == "My Project"
        assert project.description == "A test project"

    def test_create_project_creates_directory(self, service, tmp_path):
        """Test that create_project creates project directory."""
        project = service.create_project(name="Test")

        project_dir = tmp_path / project.id
        assert project_dir.exists()
        assert project_dir.is_dir()

    def test_create_project_creates_files_directory(self, service, tmp_path):
        """Test that create_project creates files subdirectory."""
        project = service.create_project(name="Test")

        files_dir = tmp_path / project.id / "files"
        assert files_dir.exists()
        assert files_dir.is_dir()

    def test_create_project_saves_json(self, service, tmp_path):
        """Test that create_project saves project.json file."""
        project = service.create_project(name="Test", description="Desc")

        project_path = tmp_path / project.id / "project.json"
        assert project_path.exists()

        with open(project_path) as f:
            data = json.load(f)

        assert data["name"] == "Test"
        assert data["description"] == "Desc"

    def test_create_project_updates_index(self, service, tmp_path):
        """Test that create_project updates the index."""
        project = service.create_project(name="Test")

        index_path = tmp_path / "index.json"
        with open(index_path) as f:
            data = json.load(f)

        assert len(data["projects"]) == 1
        assert data["projects"][0]["id"] == project.id
        assert data["projects"][0]["name"] == "Test"

    def test_create_multiple_projects(self, service):
        """Test creating multiple projects."""
        p1 = service.create_project(name="Project 1")
        p2 = service.create_project(name="Project 2")
        p3 = service.create_project(name="Project 3")

        projects = service.list_projects()

        assert len(projects) == 3
        assert {p.id for p in projects} == {p1.id, p2.id, p3.id}


# =============================================================================
# Get Project Tests
# =============================================================================


@pytest.mark.unit
class TestGetProject:
    """Tests for get_project method."""

    def test_get_project_success(self, service):
        """Test getting an existing project."""
        created = service.create_project(name="Test", description="Desc")

        project = service.get_project(created.id)

        assert project is not None
        assert project.id == created.id
        assert project.name == "Test"
        assert project.description == "Desc"

    def test_get_project_not_found(self, service):
        """Test getting a non-existent project returns None."""
        project = service.get_project("non-existent-id")

        assert project is None

    def test_get_project_returns_full_data(self, service):
        """Test that get_project returns complete project data."""
        created = service.create_project(name="Test")
        service.update_project(
            created.id,
            custom_instructions="Be helpful",
        )
        service.add_conversation_to_project(created.id, "conv1")

        project = service.get_project(created.id)

        assert project.custom_instructions == "Be helpful"
        assert "conv1" in project.conversation_ids


# =============================================================================
# Update Project Tests
# =============================================================================


@pytest.mark.unit
class TestUpdateProject:
    """Tests for update_project method."""

    def test_update_project_name(self, service):
        """Test updating project name."""
        project = service.create_project(name="Original")

        updated = service.update_project(project.id, name="Updated")

        assert updated is not None
        assert updated.name == "Updated"

    def test_update_project_description(self, service):
        """Test updating project description."""
        project = service.create_project(description="Original")

        updated = service.update_project(project.id, description="Updated")

        assert updated.description == "Updated"

    def test_update_project_custom_instructions(self, service):
        """Test updating project custom instructions."""
        project = service.create_project()

        updated = service.update_project(
            project.id,
            custom_instructions="You are a helpful assistant.",
        )

        assert updated.custom_instructions == "You are a helpful assistant."

    def test_update_project_multiple_fields(self, service):
        """Test updating multiple fields at once."""
        project = service.create_project()

        updated = service.update_project(
            project.id,
            name="New Name",
            description="New Description",
            custom_instructions="New Instructions",
        )

        assert updated.name == "New Name"
        assert updated.description == "New Description"
        assert updated.custom_instructions == "New Instructions"

    def test_update_project_preserves_unchanged_fields(self, service):
        """Test that update preserves fields not being changed."""
        project = service.create_project(
            name="Original Name",
            description="Original Description",
        )

        updated = service.update_project(project.id, name="New Name")

        assert updated.name == "New Name"
        assert updated.description == "Original Description"

    def test_update_project_updates_timestamp(self, service):
        """Test that update changes updated_at timestamp."""
        project = service.create_project()
        original_updated_at = project.updated_at

        time.sleep(0.01)  # Small delay
        updated = service.update_project(project.id, name="New Name")

        assert updated.updated_at > original_updated_at

    def test_update_project_not_found(self, service):
        """Test updating non-existent project returns None."""
        result = service.update_project("non-existent-id", name="New Name")

        assert result is None

    def test_update_project_persists(self, service):
        """Test that updates are persisted to disk."""
        project = service.create_project()
        service.update_project(project.id, name="Persisted Name")

        # Get fresh from disk
        fetched = service.get_project(project.id)

        assert fetched.name == "Persisted Name"

    def test_update_project_updates_index(self, service, tmp_path):
        """Test that updates are reflected in the index."""
        project = service.create_project(name="Original")
        service.update_project(project.id, name="Updated")

        index_path = tmp_path / "index.json"
        with open(index_path) as f:
            data = json.load(f)

        assert data["projects"][0]["name"] == "Updated"


# =============================================================================
# Delete Project Tests
# =============================================================================


@pytest.mark.unit
class TestDeleteProject:
    """Tests for delete_project method."""

    def test_delete_project_success(self, service):
        """Test deleting an existing project."""
        project = service.create_project(name="To Delete")

        result = service.delete_project(project.id)

        assert result is True

    def test_delete_project_removes_from_list(self, service):
        """Test that deleted project is removed from list."""
        project = service.create_project(name="To Delete")
        service.delete_project(project.id)

        projects = service.list_projects()

        assert len(projects) == 0

    def test_delete_project_removes_directory(self, service, tmp_path):
        """Test that delete removes the project directory."""
        project = service.create_project(name="To Delete")
        project_dir = tmp_path / project.id
        assert project_dir.exists()

        service.delete_project(project.id)

        assert not project_dir.exists()

    def test_delete_project_removes_files(self, project_with_files, tmp_path):
        """Test that delete removes all project files."""
        # Get project ID before we lose the reference
        project_id = project_with_files.id
        files_dir = tmp_path / project_id / "files"
        assert files_dir.exists()
        assert len(list(files_dir.iterdir())) > 0

        # Create new service to delete
        service = ProjectService(data_dir=str(tmp_path))
        service.delete_project(project_id)

        project_dir = tmp_path / project_id
        assert not project_dir.exists()

    def test_delete_project_not_found(self, service):
        """Test deleting non-existent project returns False."""
        result = service.delete_project("non-existent-id")

        assert result is False

    def test_delete_project_updates_index(self, service, tmp_path):
        """Test that delete updates the index file."""
        project = service.create_project()
        service.delete_project(project.id)

        index_path = tmp_path / "index.json"
        with open(index_path) as f:
            data = json.load(f)

        assert len(data["projects"]) == 0

    def test_delete_project_preserves_others(self, service):
        """Test that deleting one project preserves others."""
        p1 = service.create_project(name="Keep")
        p2 = service.create_project(name="Delete")

        service.delete_project(p2.id)

        projects = service.list_projects()
        assert len(projects) == 1
        assert projects[0].id == p1.id


# =============================================================================
# Conversation Management Tests
# =============================================================================


@pytest.mark.unit
class TestConversationManagement:
    """Tests for conversation add/remove methods."""

    def test_add_conversation_to_project(self, service):
        """Test adding a conversation to a project."""
        project = service.create_project()

        updated = service.add_conversation_to_project(project.id, "conv-123")

        assert updated is not None
        assert "conv-123" in updated.conversation_ids

    def test_add_conversation_persists(self, service):
        """Test that added conversation is persisted."""
        project = service.create_project()
        service.add_conversation_to_project(project.id, "conv-123")

        fetched = service.get_project(project.id)

        assert "conv-123" in fetched.conversation_ids

    def test_add_conversation_no_duplicates(self, service):
        """Test that adding same conversation twice doesn't create duplicates."""
        project = service.create_project()

        service.add_conversation_to_project(project.id, "conv-123")
        service.add_conversation_to_project(project.id, "conv-123")

        fetched = service.get_project(project.id)
        assert fetched.conversation_ids.count("conv-123") == 1

    def test_add_conversation_updates_timestamp(self, service):
        """Test that adding conversation updates timestamp."""
        project = service.create_project()
        original_updated_at = project.updated_at

        time.sleep(0.01)
        updated = service.add_conversation_to_project(project.id, "conv-123")

        assert updated.updated_at > original_updated_at

    def test_add_conversation_project_not_found(self, service):
        """Test adding conversation to non-existent project."""
        result = service.add_conversation_to_project("non-existent", "conv-123")

        assert result is None

    def test_add_multiple_conversations(self, service):
        """Test adding multiple conversations."""
        project = service.create_project()

        service.add_conversation_to_project(project.id, "conv-1")
        service.add_conversation_to_project(project.id, "conv-2")
        service.add_conversation_to_project(project.id, "conv-3")

        fetched = service.get_project(project.id)
        assert len(fetched.conversation_ids) == 3

    def test_remove_conversation_from_project(self, service):
        """Test removing a conversation from a project."""
        project = service.create_project()
        service.add_conversation_to_project(project.id, "conv-123")

        updated = service.remove_conversation_from_project(project.id, "conv-123")

        assert updated is not None
        assert "conv-123" not in updated.conversation_ids

    def test_remove_conversation_persists(self, service):
        """Test that removed conversation is persisted."""
        project = service.create_project()
        service.add_conversation_to_project(project.id, "conv-123")
        service.remove_conversation_from_project(project.id, "conv-123")

        fetched = service.get_project(project.id)
        assert "conv-123" not in fetched.conversation_ids

    def test_remove_nonexistent_conversation(self, service):
        """Test removing a conversation that doesn't exist."""
        project = service.create_project()

        # Should not raise, just return project unchanged
        updated = service.remove_conversation_from_project(project.id, "non-existent")

        assert updated is not None

    def test_remove_conversation_project_not_found(self, service):
        """Test removing conversation from non-existent project."""
        result = service.remove_conversation_from_project("non-existent", "conv-123")

        assert result is None

    def test_remove_conversation_updates_timestamp(self, service):
        """Test that removing conversation updates timestamp."""
        project = service.create_project()
        service.add_conversation_to_project(project.id, "conv-123")

        fetched = service.get_project(project.id)
        original_updated_at = fetched.updated_at

        time.sleep(0.01)
        updated = service.remove_conversation_from_project(project.id, "conv-123")

        assert updated.updated_at > original_updated_at

    def test_add_conversation_updates_index_count(self, service, tmp_path):
        """Test that adding conversation updates index conversation_count."""
        project = service.create_project()
        service.add_conversation_to_project(project.id, "conv-1")
        service.add_conversation_to_project(project.id, "conv-2")

        index_path = tmp_path / "index.json"
        with open(index_path) as f:
            data = json.load(f)

        assert data["projects"][0]["conversation_count"] == 2


# =============================================================================
# File Management Tests
# =============================================================================


@pytest.mark.unit
class TestFileManagement:
    """Tests for file add/get/delete methods."""

    def test_add_file(self, service):
        """Test adding a file to a project."""
        project = service.create_project()

        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="original_test.txt",
            content_type="text/plain",
            file_data=b"Hello, world!",
        )

        assert file is not None
        assert file.filename == "test.txt"
        assert file.original_filename == "original_test.txt"
        assert file.content_type == "text/plain"
        assert file.size_bytes == 13  # len(b"Hello, world!")

    def test_add_file_creates_file_on_disk(self, service, tmp_path):
        """Test that add_file creates the file on disk."""
        project = service.create_project()

        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Test content",
        )

        files_dir = tmp_path / project.id / "files"
        file_path = files_dir / f"{file.id}_test.txt"

        assert file_path.exists()
        assert file_path.read_bytes() == b"Test content"

    def test_add_file_updates_project(self, service):
        """Test that add_file updates the project's file list."""
        project = service.create_project()

        service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        fetched = service.get_project(project.id)
        assert len(fetched.files) == 1

    def test_add_file_project_not_found(self, service):
        """Test adding file to non-existent project."""
        result = service.add_file(
            project_id="non-existent",
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        assert result is None

    def test_add_file_default_processed_false(self, service):
        """Test that new files have processed=False."""
        project = service.create_project()

        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        assert file.processed is False
        assert file.qdrant_indexed is False

    def test_add_multiple_files(self, service):
        """Test adding multiple files to a project."""
        project = service.create_project()

        service.add_file(
            project_id=project.id,
            filename="file1.txt",
            original_filename="file1.txt",
            content_type="text/plain",
            file_data=b"Content 1",
        )
        service.add_file(
            project_id=project.id,
            filename="file2.txt",
            original_filename="file2.txt",
            content_type="text/plain",
            file_data=b"Content 2",
        )

        fetched = service.get_project(project.id)
        assert len(fetched.files) == 2

    def test_add_file_updates_index_count(self, service, tmp_path):
        """Test that adding file updates index file_count."""
        project = service.create_project()
        service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        index_path = tmp_path / "index.json"
        with open(index_path) as f:
            data = json.load(f)

        assert data["projects"][0]["file_count"] == 1

    def test_get_file_path(self, service, tmp_path):
        """Test getting file path for an existing file."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        path = service.get_file_path(project.id, file.id)

        assert path is not None
        assert isinstance(path, Path)
        assert path.exists()
        assert path.read_bytes() == b"Content"

    def test_get_file_path_project_not_found(self, service):
        """Test get_file_path with non-existent project."""
        path = service.get_file_path("non-existent", "file-id")

        assert path is None

    def test_get_file_path_file_not_found(self, service):
        """Test get_file_path with non-existent file."""
        project = service.create_project()

        path = service.get_file_path(project.id, "non-existent-file")

        assert path is None

    def test_delete_file(self, service):
        """Test deleting a file from a project."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        result = service.delete_file(project.id, file.id)

        assert result is True

    def test_delete_file_removes_from_project(self, service):
        """Test that deleted file is removed from project."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        service.delete_file(project.id, file.id)

        fetched = service.get_project(project.id)
        assert len(fetched.files) == 0

    def test_delete_file_removes_from_disk(self, service, tmp_path):
        """Test that deleted file is removed from disk."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        file_path = tmp_path / project.id / "files" / f"{file.id}_test.txt"
        assert file_path.exists()

        service.delete_file(project.id, file.id)

        assert not file_path.exists()

    def test_delete_file_project_not_found(self, service):
        """Test deleting file from non-existent project."""
        result = service.delete_file("non-existent", "file-id")

        assert result is False

    def test_delete_file_not_found(self, service):
        """Test deleting non-existent file."""
        project = service.create_project()

        result = service.delete_file(project.id, "non-existent-file")

        assert result is False

    def test_delete_file_preserves_others(self, service):
        """Test that deleting one file preserves others."""
        project = service.create_project()
        file1 = service.add_file(
            project_id=project.id,
            filename="file1.txt",
            original_filename="file1.txt",
            content_type="text/plain",
            file_data=b"Content 1",
        )
        file2 = service.add_file(
            project_id=project.id,
            filename="file2.txt",
            original_filename="file2.txt",
            content_type="text/plain",
            file_data=b"Content 2",
        )

        service.delete_file(project.id, file1.id)

        fetched = service.get_project(project.id)
        assert len(fetched.files) == 1
        assert fetched.files[0].id == file2.id


# =============================================================================
# Mark File Processed Tests
# =============================================================================


@pytest.mark.unit
class TestMarkFileProcessed:
    """Tests for mark_file_processed method."""

    def test_mark_file_processed_basic(self, service):
        """Test marking a file as processed."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        result = service.mark_file_processed(project.id, file.id)

        assert result is not None
        assert result.processed is True

    def test_mark_file_processed_with_qdrant(self, service):
        """Test marking file as processed with qdrant_indexed=True."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        result = service.mark_file_processed(
            project.id, file.id, qdrant_indexed=True
        )

        assert result.processed is True
        assert result.qdrant_indexed is True

    def test_mark_file_processed_with_error(self, service):
        """Test marking file as processed with an error."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        result = service.mark_file_processed(
            project.id, file.id, error="Failed to parse file"
        )

        assert result.processed is True
        assert result.qdrant_indexed is False
        assert result.processing_error == "Failed to parse file"

    def test_mark_file_processed_persists(self, service):
        """Test that processing status is persisted."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        service.mark_file_processed(project.id, file.id, qdrant_indexed=True)

        fetched = service.get_project(project.id)
        assert fetched.files[0].processed is True
        assert fetched.files[0].qdrant_indexed is True

    def test_mark_file_processed_project_not_found(self, service):
        """Test marking file processed in non-existent project."""
        result = service.mark_file_processed("non-existent", "file-id")

        assert result is None

    def test_mark_file_processed_file_not_found(self, service):
        """Test marking non-existent file as processed."""
        project = service.create_project()

        result = service.mark_file_processed(project.id, "non-existent-file")

        assert result is None

    def test_mark_file_processed_updates_timestamp(self, service):
        """Test that marking file processed updates project timestamp."""
        project = service.create_project()
        file = service.add_file(
            project_id=project.id,
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        fetched = service.get_project(project.id)
        original_updated_at = fetched.updated_at

        time.sleep(0.01)
        service.mark_file_processed(project.id, file.id)

        fetched = service.get_project(project.id)
        assert fetched.updated_at > original_updated_at


# =============================================================================
# Integration / Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_concurrent_index_updates(self, service):
        """Test that multiple operations don't corrupt index."""
        # Create several projects
        projects = [
            service.create_project(name=f"Project {i}")
            for i in range(5)
        ]

        # Update them
        for p in projects:
            service.update_project(p.id, description=f"Updated {p.name}")

        # Verify all exist
        listed = service.list_projects()
        assert len(listed) == 5

    def test_empty_file_data(self, service):
        """Test adding a file with empty content."""
        project = service.create_project()

        file = service.add_file(
            project_id=project.id,
            filename="empty.txt",
            original_filename="empty.txt",
            content_type="text/plain",
            file_data=b"",
        )

        assert file is not None
        assert file.size_bytes == 0

    def test_large_custom_instructions(self, service):
        """Test project with large custom instructions."""
        project = service.create_project()
        large_instructions = "x" * 10000

        updated = service.update_project(
            project.id,
            custom_instructions=large_instructions,
        )

        assert len(updated.custom_instructions) == 10000

        # Verify persisted
        fetched = service.get_project(project.id)
        assert len(fetched.custom_instructions) == 10000

    def test_special_characters_in_name(self, service):
        """Test project with special characters in name."""
        project = service.create_project(
            name='Test "Project" with <special> & chars!'
        )

        fetched = service.get_project(project.id)
        assert fetched.name == 'Test "Project" with <special> & chars!'

    def test_unicode_in_description(self, service):
        """Test project with unicode in description."""
        project = service.create_project(
            description="Test with unicode: emoji test, Chinese: zhongwen"
        )

        fetched = service.get_project(project.id)
        assert "emoji" in fetched.description
        assert "zhongwen" in fetched.description

    def test_binary_file_content(self, service, tmp_path):
        """Test storing binary file content."""
        project = service.create_project()
        binary_data = bytes(range(256))  # All possible byte values

        file = service.add_file(
            project_id=project.id,
            filename="binary.bin",
            original_filename="binary.bin",
            content_type="application/octet-stream",
            file_data=binary_data,
        )

        path = service.get_file_path(project.id, file.id)
        assert path.read_bytes() == binary_data

    def test_get_project_after_service_recreation(self, tmp_path):
        """Test that data persists across service instances."""
        # Create project with first service instance
        service1 = ProjectService(data_dir=str(tmp_path))
        project = service1.create_project(name="Persistent")
        project_id = project.id

        # Create new service instance
        service2 = ProjectService(data_dir=str(tmp_path))

        # Should be able to get the project
        fetched = service2.get_project(project_id)
        assert fetched is not None
        assert fetched.name == "Persistent"

    def test_list_projects_after_service_recreation(self, tmp_path):
        """Test that list works after service recreation."""
        service1 = ProjectService(data_dir=str(tmp_path))
        service1.create_project(name="Project 1")
        service1.create_project(name="Project 2")

        service2 = ProjectService(data_dir=str(tmp_path))
        projects = service2.list_projects()

        assert len(projects) == 2
