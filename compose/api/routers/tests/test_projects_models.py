"""Tests for projects router request/response models.

Run with: uv run pytest compose/api/routers/tests/test_projects_models.py
"""

import pytest
from pydantic import ValidationError

from compose.api.routers.projects import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AddConversationRequest,
    SearchFilesRequest,
    SearchResult,
    SearchFilesResponse,
)


# -----------------------------------------------------------------------------
# CreateProjectRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateProjectRequestModel:
    """Verify Pydantic CreateProjectRequest model fields and validation."""

    def test_default_values(self):
        """Request uses defaults when no values provided."""
        req = CreateProjectRequest()
        assert req.name == "New Project"
        assert req.description == ""

    def test_custom_name(self):
        """Request accepts custom name."""
        req = CreateProjectRequest(name="My Project")
        assert req.name == "My Project"
        assert req.description == ""

    def test_custom_description(self):
        """Request accepts custom description."""
        req = CreateProjectRequest(description="A test project")
        assert req.name == "New Project"
        assert req.description == "A test project"

    def test_all_custom_values(self):
        """Request accepts all custom values."""
        req = CreateProjectRequest(name="Custom", description="Custom desc")
        assert req.name == "Custom"
        assert req.description == "Custom desc"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"name", "description"}
        actual_fields = set(CreateProjectRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# UpdateProjectRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateProjectRequestModel:
    """Verify Pydantic UpdateProjectRequest model fields and validation."""

    def test_all_optional(self):
        """All fields are optional."""
        req = UpdateProjectRequest()
        assert req.name is None
        assert req.description is None
        assert req.custom_instructions is None

    def test_name_only(self):
        """Can set only name."""
        req = UpdateProjectRequest(name="New Name")
        assert req.name == "New Name"
        assert req.description is None
        assert req.custom_instructions is None

    def test_description_only(self):
        """Can set only description."""
        req = UpdateProjectRequest(description="Updated desc")
        assert req.name is None
        assert req.description == "Updated desc"
        assert req.custom_instructions is None

    def test_custom_instructions_only(self):
        """Can set only custom_instructions."""
        req = UpdateProjectRequest(custom_instructions="Be helpful")
        assert req.name is None
        assert req.description is None
        assert req.custom_instructions == "Be helpful"

    def test_all_fields(self):
        """Can set all fields."""
        req = UpdateProjectRequest(
            name="Name",
            description="Desc",
            custom_instructions="Instructions",
        )
        assert req.name == "Name"
        assert req.description == "Desc"
        assert req.custom_instructions == "Instructions"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"name", "description", "custom_instructions"}
        actual_fields = set(UpdateProjectRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# AddConversationRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestAddConversationRequestModel:
    """Verify Pydantic AddConversationRequest model fields and validation."""

    def test_required_conversation_id(self):
        """conversation_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            AddConversationRequest()
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("conversation_id",) and e["type"] == "missing" for e in errors
        )

    def test_valid_conversation_id(self):
        """Request accepts valid conversation_id."""
        req = AddConversationRequest(conversation_id="conv-123-abc")
        assert req.conversation_id == "conv-123-abc"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"conversation_id"}
        actual_fields = set(AddConversationRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# SearchFilesRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchFilesRequestModel:
    """Verify Pydantic SearchFilesRequest model fields and validation."""

    def test_required_query(self):
        """query is required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilesRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("query",) and e["type"] == "missing" for e in errors)

    def test_valid_query_with_default_limit(self):
        """Request with query uses default limit."""
        req = SearchFilesRequest(query="search term")
        assert req.query == "search term"
        assert req.limit == 5

    def test_custom_limit(self):
        """Request accepts custom limit."""
        req = SearchFilesRequest(query="test", limit=10)
        assert req.query == "test"
        assert req.limit == 10

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"query", "limit"}
        actual_fields = set(SearchFilesRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# SearchResult Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchResultModel:
    """Verify Pydantic SearchResult model fields and validation."""

    def test_required_fields(self):
        """All fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "score" in error_locs
        assert "text" in error_locs
        assert "filename" in error_locs
        assert "file_id" in error_locs
        assert "chunk_index" in error_locs

    def test_valid_result(self):
        """Valid result with all required fields."""
        result = SearchResult(
            score=0.95,
            text="Sample text content",
            filename="document.pdf",
            file_id="file-123",
            chunk_index=0,
        )
        assert result.score == 0.95
        assert result.text == "Sample text content"
        assert result.filename == "document.pdf"
        assert result.file_id == "file-123"
        assert result.chunk_index == 0

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"score", "text", "filename", "file_id", "chunk_index"}
        actual_fields = set(SearchResult.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# SearchFilesResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchFilesResponseModel:
    """Verify Pydantic SearchFilesResponse model fields and validation."""

    def test_required_results(self):
        """results is required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilesResponse()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("results",) and e["type"] == "missing" for e in errors)

    def test_empty_results(self):
        """Response accepts empty results list."""
        resp = SearchFilesResponse(results=[])
        assert resp.results == []

    def test_results_with_items(self):
        """Response accepts list of SearchResult items."""
        results = [
            SearchResult(
                score=0.95,
                text="First result",
                filename="doc1.pdf",
                file_id="file-1",
                chunk_index=0,
            ),
            SearchResult(
                score=0.85,
                text="Second result",
                filename="doc2.pdf",
                file_id="file-2",
                chunk_index=1,
            ),
        ]
        resp = SearchFilesResponse(results=results)
        assert len(resp.results) == 2
        assert resp.results[0].score == 0.95
        assert resp.results[1].filename == "doc2.pdf"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"results"}
        actual_fields = set(SearchFilesResponse.model_fields.keys())
        assert actual_fields == expected_fields
