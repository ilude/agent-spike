"""Characterization tests for compose/api/routers/youtube_rag.py.

These tests capture the CURRENT behavior of the YouTube RAG router,
including Pydantic models for search and query endpoints.
"""

import pytest
from pydantic import ValidationError

from compose.api.routers.youtube_rag import (
    SearchRequest,
    SearchResult,
    SearchResponse,
    QueryRequest,
    QuerySource,
    QueryResponse,
)


# -----------------------------------------------------------------------------
# SearchRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchRequestModel:
    """Verify Pydantic SearchRequest model fields and validation."""

    def test_required_query_field(self):
        """query is required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("query",) and e["type"] == "missing" for e in errors)

    def test_valid_request_with_query_only(self):
        """Request with only query uses default limit."""
        req = SearchRequest(query="AI agents")
        assert req.query == "AI agents"
        assert req.limit == 10  # default value
        assert req.channel is None  # default value

    def test_limit_default(self):
        """Default limit is 10."""
        req = SearchRequest(query="test")
        assert req.limit == 10

    def test_limit_min_value(self):
        """limit must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="test", limit=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_limit_max_value(self):
        """limit cannot exceed 100."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="test", limit=101)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_limit_valid_range(self):
        """limit accepts values in valid range [1, 100]."""
        for limit in [1, 50, 100]:
            req = SearchRequest(query="test", limit=limit)
            assert req.limit == limit

    def test_query_min_length(self):
        """query must have at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("query",) for e in errors)

    def test_query_max_length(self):
        """query cannot exceed 1000 characters."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="x" * 1001)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("query",) for e in errors)

    def test_channel_optional(self):
        """channel is optional."""
        req = SearchRequest(query="test")
        assert req.channel is None

    def test_channel_accepts_string(self):
        """channel accepts string values."""
        req = SearchRequest(query="test", channel="AI Explained")
        assert req.channel == "AI Explained"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"query", "limit", "channel"}
        actual_fields = set(SearchRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# SearchResult Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchResultModel:
    """Verify Pydantic SearchResult model structure."""

    def test_required_fields(self):
        """All fields are required in SearchResult."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "video_id" in error_locs
        assert "title" in error_locs
        assert "channel" in error_locs
        assert "score" in error_locs
        assert "transcript_preview" in error_locs
        assert "url" in error_locs

    def test_valid_result(self):
        """SearchResult with all required fields."""
        result = SearchResult(
            video_id="abc123def45",
            title="Test Video",
            channel="Test Channel",
            score=0.95,
            transcript_preview="This is a preview...",
            url="https://youtube.com/watch?v=abc123def45",
        )
        assert result.video_id == "abc123def45"
        assert result.title == "Test Video"
        assert result.channel == "Test Channel"
        assert result.score == 0.95
        assert result.transcript_preview == "This is a preview..."
        assert result.url == "https://youtube.com/watch?v=abc123def45"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"video_id", "title", "channel", "score", "transcript_preview", "url"}
        actual_fields = set(SearchResult.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# SearchResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchResponseModel:
    """Verify Pydantic SearchResponse model structure."""

    def test_required_fields(self):
        """query, results, and total_found are required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResponse()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "query" in error_locs
        assert "results" in error_locs
        assert "total_found" in error_locs

    def test_valid_response_empty_results(self):
        """Response with empty results list."""
        resp = SearchResponse(query="test", results=[], total_found=0)
        assert resp.query == "test"
        assert resp.results == []
        assert resp.total_found == 0

    def test_valid_response_with_results(self):
        """Response with search results."""
        result = SearchResult(
            video_id="abc123",
            title="Video",
            channel="Channel",
            score=0.9,
            transcript_preview="Preview",
            url="https://youtube.com/watch?v=abc123",
        )
        resp = SearchResponse(query="AI", results=[result], total_found=1)
        assert resp.query == "AI"
        assert len(resp.results) == 1
        assert resp.results[0].video_id == "abc123"
        assert resp.total_found == 1

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"query", "results", "total_found"}
        actual_fields = set(SearchResponse.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# QueryRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryRequestModel:
    """Verify Pydantic QueryRequest model fields and validation."""

    def test_required_question_field(self):
        """question is required."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("question",) and e["type"] == "missing" for e in errors)

    def test_valid_request_with_question_only(self):
        """Request with only question uses default limit."""
        req = QueryRequest(question="What is RAG?")
        assert req.question == "What is RAG?"
        assert req.limit == 5  # default value
        assert req.channel is None  # default value

    def test_limit_default(self):
        """Default limit is 5."""
        req = QueryRequest(question="test")
        assert req.limit == 5

    def test_limit_min_value(self):
        """limit must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(question="test", limit=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_limit_max_value(self):
        """limit cannot exceed 20."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(question="test", limit=21)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_limit_valid_range(self):
        """limit accepts values in valid range [1, 20]."""
        for limit in [1, 10, 20]:
            req = QueryRequest(question="test", limit=limit)
            assert req.limit == limit

    def test_question_min_length(self):
        """question must have at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(question="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("question",) for e in errors)

    def test_question_max_length(self):
        """question cannot exceed 2000 characters."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(question="x" * 2001)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("question",) for e in errors)

    def test_channel_optional(self):
        """channel is optional."""
        req = QueryRequest(question="test")
        assert req.channel is None

    def test_channel_accepts_string(self):
        """channel accepts string values."""
        req = QueryRequest(question="test", channel="AI Explained")
        assert req.channel == "AI Explained"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"question", "limit", "channel"}
        actual_fields = set(QueryRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# QuerySource Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestQuerySourceModel:
    """Verify Pydantic QuerySource model structure."""

    def test_required_fields(self):
        """All fields are required in QuerySource."""
        with pytest.raises(ValidationError) as exc_info:
            QuerySource()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "video_id" in error_locs
        assert "title" in error_locs
        assert "url" in error_locs
        assert "relevance_score" in error_locs

    def test_valid_source(self):
        """QuerySource with all required fields."""
        source = QuerySource(
            video_id="abc123def45",
            title="Test Video",
            url="https://youtube.com/watch?v=abc123def45",
            relevance_score=0.85,
        )
        assert source.video_id == "abc123def45"
        assert source.title == "Test Video"
        assert source.url == "https://youtube.com/watch?v=abc123def45"
        assert source.relevance_score == 0.85

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"video_id", "title", "url", "relevance_score"}
        actual_fields = set(QuerySource.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# QueryResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryResponseModel:
    """Verify Pydantic QueryResponse model structure."""

    def test_required_fields(self):
        """question, answer, sources, and context_used are required."""
        with pytest.raises(ValidationError) as exc_info:
            QueryResponse()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "question" in error_locs
        assert "answer" in error_locs
        assert "sources" in error_locs
        assert "context_used" in error_locs

    def test_valid_response_no_sources(self):
        """Response with empty sources list."""
        resp = QueryResponse(
            question="What is AI?",
            answer="No relevant content found.",
            sources=[],
            context_used=False,
        )
        assert resp.question == "What is AI?"
        assert resp.answer == "No relevant content found."
        assert resp.sources == []
        assert resp.context_used is False

    def test_valid_response_with_sources(self):
        """Response with sources."""
        source = QuerySource(
            video_id="abc123",
            title="AI Video",
            url="https://youtube.com/watch?v=abc123",
            relevance_score=0.9,
        )
        resp = QueryResponse(
            question="What is RAG?",
            answer="RAG stands for Retrieval Augmented Generation...",
            sources=[source],
            context_used=True,
        )
        assert resp.question == "What is RAG?"
        assert "Retrieval Augmented Generation" in resp.answer
        assert len(resp.sources) == 1
        assert resp.sources[0].video_id == "abc123"
        assert resp.context_used is True

    def test_context_used_required(self):
        """context_used is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            QueryResponse(
                question="test",
                answer="answer",
                sources=[],
                # context_used missing
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("context_used",) for e in errors)

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"question", "answer", "sources", "context_used"}
        actual_fields = set(QueryResponse.model_fields.keys())
        assert actual_fields == expected_fields

    def test_context_used_field_description(self):
        """context_used field has proper description."""
        field_info = QueryResponse.model_fields["context_used"]
        assert field_info.description is not None
        assert "RAG" in field_info.description or "context" in field_info.description
