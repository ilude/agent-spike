"""Tests for projects router endpoint behavior.

Run with: uv run pytest compose/api/routers/tests/test_projects_endpoints.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from compose.api.routers.projects import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AddConversationRequest,
    SearchFilesRequest,
)


# -----------------------------------------------------------------------------
# Endpoint Behavior Tests (with mocked service)
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestListProjectsEndpoint:
    """Test list_projects endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_project_list(self):
        """Endpoint returns list of projects from service."""
        from compose.api.routers.projects import list_projects

        mock_service = MagicMock()
        mock_service.list_projects.return_value = []

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            result = await list_projects()
            assert result.projects == []
            mock_service.list_projects.assert_called_once()


@pytest.mark.unit
class TestCreateProjectEndpoint:
    """Test create_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_creates_project_with_defaults(self):
        """Endpoint creates project using request data."""
        from compose.api.routers.projects import create_project

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.create_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = CreateProjectRequest()
            result = await create_project(request)
            assert result == mock_project
            mock_service.create_project.assert_called_once_with(
                name="New Project",
                description="",
            )


@pytest.mark.unit
class TestGetProjectEndpoint:
    """Test get_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_project_when_found(self):
        """Endpoint returns project when it exists."""
        from compose.api.routers.projects import get_project

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.get_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            result = await get_project("proj-123")
            assert result == mock_project
            mock_service.get_project.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import get_project

        mock_service = MagicMock()
        mock_service.get_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_project("nonexistent")
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Project not found"


@pytest.mark.unit
class TestUpdateProjectEndpoint:
    """Test update_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_updates_project_when_found(self):
        """Endpoint updates project when it exists."""
        from compose.api.routers.projects import update_project

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.update_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = UpdateProjectRequest(name="Updated Name")
            result = await update_project("proj-123", request)
            assert result == mock_project
            mock_service.update_project.assert_called_once_with(
                "proj-123",
                name="Updated Name",
                description=None,
                custom_instructions=None,
            )

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import update_project

        mock_service = MagicMock()
        mock_service.update_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = UpdateProjectRequest(name="Test")
            with pytest.raises(HTTPException) as exc_info:
                await update_project("nonexistent", request)
            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestDeleteProjectEndpoint:
    """Test delete_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_deletes_project_when_found(self):
        """Endpoint deletes project when it exists."""
        from compose.api.routers.projects import delete_project

        mock_service = MagicMock()
        mock_service.delete_project.return_value = True

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            result = await delete_project("proj-123")
            assert result == {"status": "deleted", "id": "proj-123"}
            mock_service.delete_project.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import delete_project

        mock_service = MagicMock()
        mock_service.delete_project.return_value = False

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_project("nonexistent")
            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestAddConversationEndpoint:
    """Test add_conversation_to_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_adds_conversation_when_project_found(self):
        """Endpoint adds conversation when project exists."""
        from compose.api.routers.projects import add_conversation_to_project

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.add_conversation_to_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = AddConversationRequest(conversation_id="conv-456")
            result = await add_conversation_to_project("proj-123", request)
            assert result == mock_project
            mock_service.add_conversation_to_project.assert_called_once_with(
                "proj-123", "conv-456"
            )

    @pytest.mark.asyncio
    async def test_raises_404_when_project_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import add_conversation_to_project

        mock_service = MagicMock()
        mock_service.add_conversation_to_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = AddConversationRequest(conversation_id="conv-456")
            with pytest.raises(HTTPException) as exc_info:
                await add_conversation_to_project("nonexistent", request)
            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestRemoveConversationEndpoint:
    """Test remove_conversation_from_project endpoint behavior."""

    @pytest.mark.asyncio
    async def test_removes_conversation_when_found(self):
        """Endpoint removes conversation when project exists."""
        from compose.api.routers.projects import remove_conversation_from_project

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.remove_conversation_from_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            result = await remove_conversation_from_project("proj-123", "conv-456")
            assert result == {
                "status": "removed",
                "project_id": "proj-123",
                "conversation_id": "conv-456",
            }

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import remove_conversation_from_project

        mock_service = MagicMock()
        mock_service.remove_conversation_from_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await remove_conversation_from_project("nonexistent", "conv-456")
            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestGetFileInfoEndpoint:
    """Test get_file_info endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_file_when_found(self):
        """Endpoint returns file info when found."""
        from compose.api.routers.projects import get_file_info

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_project = MagicMock()
        mock_project.files = [mock_file]

        mock_service = MagicMock()
        mock_service.get_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            result = await get_file_info("proj-123", "file-123")
            assert result == mock_file

    @pytest.mark.asyncio
    async def test_raises_404_when_project_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import get_file_info

        mock_service = MagicMock()
        mock_service.get_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_file_info("nonexistent", "file-123")
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Project not found"

    @pytest.mark.asyncio
    async def test_raises_404_when_file_not_found(self):
        """Endpoint raises 404 when file not found in project."""
        from fastapi import HTTPException
        from compose.api.routers.projects import get_file_info

        mock_file = MagicMock()
        mock_file.id = "other-file"
        mock_project = MagicMock()
        mock_project.files = [mock_file]

        mock_service = MagicMock()
        mock_service.get_project.return_value = mock_project

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_file_info("proj-123", "nonexistent")
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "File not found"


@pytest.mark.unit
class TestDeleteFileEndpoint:
    """Test delete_file endpoint behavior."""

    @pytest.mark.asyncio
    async def test_deletes_file_when_found(self):
        """Endpoint deletes file when it exists."""
        from compose.api.routers.projects import delete_file

        mock_service = MagicMock()
        mock_service.delete_file.return_value = True

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with patch(
                "compose.api.routers.projects.delete_file_from_index"
            ) as mock_delete_index:
                result = await delete_file("proj-123", "file-456")
                assert result == {
                    "status": "deleted",
                    "project_id": "proj-123",
                    "file_id": "file-456",
                }
                mock_delete_index.assert_called_once_with("proj-123", "file-456")

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        """Endpoint raises 404 when file not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import delete_file

        mock_service = MagicMock()
        mock_service.delete_file.return_value = False

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_file("proj-123", "nonexistent")
            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestSearchFilesEndpoint:
    """Test search_files endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_search_results(self):
        """Endpoint returns search results when project exists."""
        from compose.api.routers.projects import search_files

        mock_service = MagicMock()
        mock_project = MagicMock()
        mock_service.get_project.return_value = mock_project

        mock_results = [
            {
                "score": 0.95,
                "text": "Result text",
                "filename": "doc.pdf",
                "file_id": "file-1",
                "chunk_index": 0,
            }
        ]

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            with patch(
                "compose.api.routers.projects.search_project_files",
                new_callable=AsyncMock,
                return_value=mock_results,
            ) as mock_search:
                request = SearchFilesRequest(query="test query", limit=10)
                result = await search_files("proj-123", request)

                assert len(result.results) == 1
                assert result.results[0].score == 0.95
                assert result.results[0].text == "Result text"
                mock_search.assert_called_once_with(
                    project_id="proj-123",
                    query="test query",
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_raises_404_when_project_not_found(self):
        """Endpoint raises 404 when project not found."""
        from fastapi import HTTPException
        from compose.api.routers.projects import search_files

        mock_service = MagicMock()
        mock_service.get_project.return_value = None

        with patch(
            "compose.api.routers.projects.get_project_service",
            return_value=mock_service,
        ):
            request = SearchFilesRequest(query="test")
            with pytest.raises(HTTPException) as exc_info:
                await search_files("nonexistent", request)
            assert exc_info.value.status_code == 404
