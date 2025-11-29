"""Tests for project storage service (SurrealDB + MinIO implementation).

Run with: uv run pytest compose/services/tests/unit/test_projects.py -v
"""

import pytest

from compose.services.projects import (
    Project,
    ProjectFile,
    ProjectMeta,
    ProjectService,
)
from compose.services.tests.fakes import FakeDatabaseExecutor, FakeMinIOClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_db():
    """Create a fresh FakeDatabaseExecutor for each test."""
    return FakeDatabaseExecutor()


@pytest.fixture
def fake_minio():
    """Create a fresh FakeMinIOClient for each test."""
    return FakeMinIOClient()


@pytest.fixture
def service(fake_db, fake_minio):
    """Create ProjectService with injected fakes."""
    return ProjectService(db=fake_db, minio=fake_minio)


# =============================================================================
# Model Tests (no mocking needed - just Pydantic models)
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
        assert file.vector_indexed is False
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
# Service Tests (using DI with fakes)
# =============================================================================


@pytest.mark.unit
class TestCreateProject:
    """Tests for create_project method."""

    async def test_creates_project_with_default_values(self, service, fake_db):
        """Test creating project with default values."""
        project = await service.create_project()

        assert project.name == "New Project"
        assert project.description == ""
        assert project.id is not None

        # Verify database was called
        assert len(fake_db.query_log) == 1
        query, params = fake_db.query_log[0]
        assert "CREATE project" in query
        assert params["name"] == "New Project"

    async def test_creates_project_with_name_and_description(self, service, fake_db):
        """Test creating project with name and description."""
        project = await service.create_project(
            name="My Project",
            description="A test project",
        )

        assert project.name == "My Project"
        assert project.description == "A test project"

        query, params = fake_db.query_log[0]
        assert params["name"] == "My Project"
        assert params["description"] == "A test project"

    async def test_create_project_generates_uuid(self, service):
        """Test that create generates a valid UUID."""
        project = await service.create_project()

        assert len(project.id) == 36
        assert project.id.count("-") == 4  # UUID format


@pytest.mark.unit
class TestListProjects:
    """Tests for list_projects method."""

    async def test_list_projects_empty(self, service, fake_db):
        """Test listing when no projects exist."""
        projects = await service.list_projects()

        assert projects == []

    async def test_list_projects_returns_meta(self, service, fake_db):
        """Test that list returns ProjectMeta objects."""
        # Setup: Add a project to the fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Test Project",
                "description": "Desc",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        projects = await service.list_projects()

        assert len(projects) == 1
        assert isinstance(projects[0], ProjectMeta)
        assert projects[0].name == "Test Project"


@pytest.mark.unit
class TestGetProject:
    """Tests for get_project method."""

    async def test_get_project_not_found(self, service):
        """Test getting a non-existent project returns None."""
        project = await service.get_project("non-existent-id")

        assert project is None

    async def test_get_project_success(self, service, fake_db):
        """Test getting an existing project."""
        # Setup: Add project to fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Test Project",
                "description": "Desc",
                "custom_instructions": "Be helpful",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        project = await service.get_project("test-id")

        assert project is not None
        assert project.name == "Test Project"
        assert project.custom_instructions == "Be helpful"


@pytest.mark.unit
class TestUpdateProject:
    """Tests for update_project method."""

    async def test_update_project_not_found(self, service):
        """Test updating non-existent project returns None."""
        result = await service.update_project("non-existent", name="New Name")

        assert result is None

    async def test_update_project_name(self, service, fake_db):
        """Test updating project name."""
        # Setup: Add project to fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Original",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        updated = await service.update_project("test-id", name="Updated")

        # The fake DB should have been called with UPDATE
        update_queries = [q for q, _ in fake_db.query_log if "UPDATE" in q]
        assert len(update_queries) > 0


@pytest.mark.unit
class TestDeleteProject:
    """Tests for delete_project method."""

    async def test_delete_project_not_found(self, service):
        """Test deleting non-existent project returns False."""
        result = await service.delete_project("non-existent")

        assert result is False

    async def test_delete_project_success(self, service, fake_db):
        """Test deleting an existing project."""
        # Setup: Add project to fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "To Delete",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        result = await service.delete_project("test-id")

        assert result is True
        # Verify DELETE queries were issued
        delete_queries = [q for q, _ in fake_db.query_log if "DELETE" in q]
        assert len(delete_queries) >= 1


@pytest.mark.unit
class TestConversationManagement:
    """Tests for conversation add/remove methods."""

    async def test_add_conversation_project_not_found(self, service):
        """Test adding conversation to non-existent project."""
        result = await service.add_conversation_to_project("non-existent", "conv-123")

        assert result is None

    async def test_add_conversation_to_project(self, service, fake_db):
        """Test adding a conversation to a project."""
        # Setup: Add project to fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Test",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        result = await service.add_conversation_to_project("test-id", "conv-123")

        assert result is not None
        # Verify CREATE project_conversation was called
        create_queries = [
            q for q, _ in fake_db.query_log if "CREATE project_conversation" in q
        ]
        assert len(create_queries) == 1

    async def test_remove_conversation_project_not_found(self, service):
        """Test removing conversation from non-existent project."""
        result = await service.remove_conversation_from_project("non-existent", "conv-123")

        assert result is None


@pytest.mark.unit
class TestFileManagement:
    """Tests for file add/get/delete methods."""

    async def test_add_file_project_not_found(self, service):
        """Test adding file to non-existent project."""
        result = await service.add_file(
            project_id="non-existent",
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_data=b"Content",
        )

        assert result is None

    async def test_add_file(self, service, fake_db, fake_minio):
        """Test adding a file to a project."""
        # Setup: Add project to fake DB
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Test",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        file = await service.add_file(
            project_id="test-id",
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

        # Verify file was stored in MinIO
        assert len(fake_minio.objects) == 1

    async def test_delete_file_not_found(self, service):
        """Test deleting non-existent file."""
        result = await service.delete_file("project-id", "non-existent-file")

        assert result is False


@pytest.mark.unit
class TestMarkFileProcessed:
    """Tests for mark_file_processed method."""

    async def test_mark_file_processed_not_found(self, service):
        """Test marking non-existent file as processed."""
        result = await service.mark_file_processed("project-id", "non-existent-file")

        assert result is None

    async def test_mark_file_processed_success(self, service, fake_db):
        """Test marking file as processed."""
        # Setup: Add project and file to fake DB
        fake_db.tables["project"] = [
            {
                "id": "project-id",
                "name": "Test",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]
        fake_db.tables["project_file"] = [
            {
                "id": "file-id",
                "project_id": "project-id",
                "filename": "test.txt",
                "original_filename": "test.txt",
                "content_type": "text/plain",
                "size_bytes": 100,
                "uploaded_at": "2024-01-01T00:00:00Z",
                "processed": False,
                "vector_indexed": False,
                "processing_error": None,
            }
        ]

        result = await service.mark_file_processed(
            "project-id", "file-id", vector_indexed=True
        )

        # The fake DB should have been called with UPDATE
        update_queries = [q for q, _ in fake_db.query_log if "UPDATE project_file" in q]
        assert len(update_queries) >= 1


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases."""

    async def test_special_characters_in_name(self, service, fake_db):
        """Test project with special characters in name."""
        project = await service.create_project(
            name='Test "Project" with <special> & chars!'
        )

        assert project.name == 'Test "Project" with <special> & chars!'

    async def test_empty_file_data(self, service, fake_db, fake_minio):
        """Test adding a file with empty content."""
        fake_db.tables["project"] = [
            {
                "id": "test-id",
                "name": "Test",
                "description": "",
                "custom_instructions": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        file = await service.add_file(
            project_id="test-id",
            filename="empty.txt",
            original_filename="empty.txt",
            content_type="text/plain",
            file_data=b"",
        )

        assert file is not None
        assert file.size_bytes == 0
