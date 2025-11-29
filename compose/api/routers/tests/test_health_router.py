"""Tests for health router.

Run with: uv run pytest compose/api/routers/tests/test_health_router.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from pydantic import ValidationError

from compose.api.routers.health import check_surrealdb, check_minio, check_infinity, health_check
from compose.api.models import HealthCheckResponse


# -----------------------------------------------------------------------------
# HealthCheckResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthCheckResponseModel:
    """Verify Pydantic HealthCheckResponse model validation."""

    def test_valid_response(self):
        """Valid response with status and checks."""
        response = HealthCheckResponse(
            status="ok",
            checks={
                "surrealdb": {"status": "ok", "message": "Connected"},
                "infinity": {"status": "ok", "message": "Ready"},
            },
        )
        assert response.status == "ok"
        assert len(response.checks) == 2
        assert response.checks["surrealdb"]["status"] == "ok"

    def test_required_status_field(self):
        """status is required."""
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(checks={})
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) and e["type"] == "missing" for e in errors)

    def test_required_checks_field(self):
        """checks is required."""
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(status="ok")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("checks",) and e["type"] == "missing" for e in errors)

    def test_empty_checks_allowed(self):
        """Empty checks dict is valid."""
        response = HealthCheckResponse(status="ok", checks={})
        assert response.checks == {}

    def test_degraded_status(self):
        """Status can be 'degraded'."""
        response = HealthCheckResponse(
            status="degraded",
            checks={"surrealdb": {"status": "error", "message": "Connection failed"}},
        )
        assert response.status == "degraded"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"status", "checks"}
        actual_fields = set(HealthCheckResponse.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# check_surrealdb Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckSurrealDB:
    """Test SurrealDB health check."""

    @pytest.mark.asyncio
    async def test_success_returns_ok_status(self):
        """Successful SurrealDB connection returns status 'ok'."""
        with patch(
            "compose.services.surrealdb.verify_connection",
            new_callable=AsyncMock,
        ):
            result = await check_surrealdb()

        assert result["status"] == "ok"
        assert "SurrealDB accessible" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_connection_failure(self):
        """Connection failure returns status 'error'."""
        with patch(
            "compose.services.surrealdb.verify_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await check_surrealdb()

        assert result["status"] == "error"
        assert "SurrealDB check failed" in result["message"]
        assert "Connection refused" in result["message"]


# -----------------------------------------------------------------------------
# check_minio Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckMinIO:
    """Test MinIO health check."""

    @pytest.mark.asyncio
    async def test_success_returns_ok_status(self):
        """Successful MinIO connection returns status 'ok'."""
        mock_client = MagicMock()
        mock_client.ensure_bucket.return_value = None

        with patch(
            "compose.services.minio.create_minio_client",
            return_value=mock_client,
        ):
            result = await check_minio()

        assert result["status"] == "ok"
        assert "MinIO accessible" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_connection_failure(self):
        """Connection failure returns status 'error'."""
        with patch(
            "compose.services.minio.create_minio_client",
            side_effect=Exception("Connection refused"),
        ):
            result = await check_minio()

        assert result["status"] == "error"
        assert "MinIO check failed" in result["message"]
        assert "Connection refused" in result["message"]


# -----------------------------------------------------------------------------
# check_infinity Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckInfinity:
    """Test Infinity embedding service health check."""

    @pytest.mark.asyncio
    async def test_success_returns_ok_status(self):
        """Successful HTTP 200 response returns status 'ok'."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("compose.api.routers.health.httpx.AsyncClient", return_value=mock_client):
            result = await check_infinity()

        assert result["status"] == "ok"
        assert "Infinity embedding service accessible" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_non_200_response(self):
        """Non-200 HTTP status returns status 'error'."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("compose.api.routers.health.httpx.AsyncClient", return_value=mock_client):
            result = await check_infinity()

        assert result["status"] == "error"
        assert "Infinity returned 503" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_404_response(self):
        """HTTP 404 returns status 'error'."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("compose.api.routers.health.httpx.AsyncClient", return_value=mock_client):
            result = await check_infinity()

        assert result["status"] == "error"
        assert "Infinity returned 404" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_connection_failure(self):
        """Connection failure returns status 'error'."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("compose.api.routers.health.httpx.AsyncClient", return_value=mock_client):
            result = await check_infinity()

        assert result["status"] == "error"
        assert "Infinity check failed" in result["message"]
        assert "Connection refused" in result["message"]

    @pytest.mark.asyncio
    async def test_error_on_timeout(self):
        """Timeout returns status 'error'."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("compose.api.routers.health.httpx.AsyncClient", return_value=mock_client):
            result = await check_infinity()

        assert result["status"] == "error"
        assert "Infinity check failed" in result["message"]


# -----------------------------------------------------------------------------
# health_check Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthCheckEndpoint:
    """Test health_check endpoint logic."""

    @pytest.mark.asyncio
    async def test_all_services_ok_returns_status_ok(self):
        """When all services are OK, overall status is 'ok'."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "SurrealDB accessible"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "MinIO accessible"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "Infinity accessible"},
            ),
        ):
            result = await health_check()

        assert result.status == "ok"
        assert result.checks["surrealdb"]["status"] == "ok"
        assert result.checks["minio"]["status"] == "ok"
        assert result.checks["infinity"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_surrealdb_error_returns_status_degraded(self):
        """When SurrealDB fails, overall status is 'degraded'."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "error", "message": "SurrealDB connection failed"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "MinIO accessible"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "Infinity accessible"},
            ),
        ):
            result = await health_check()

        assert result.status == "degraded"
        assert result.checks["surrealdb"]["status"] == "error"
        assert result.checks["minio"]["status"] == "ok"
        assert result.checks["infinity"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_infinity_error_returns_status_degraded(self):
        """When Infinity fails, overall status is 'degraded'."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "SurrealDB accessible"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "MinIO accessible"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "error", "message": "Infinity connection failed"},
            ),
        ):
            result = await health_check()

        assert result.status == "degraded"
        assert result.checks["surrealdb"]["status"] == "ok"
        assert result.checks["infinity"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_all_services_error_returns_status_degraded(self):
        """When all services fail, overall status is 'degraded'."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "error", "message": "SurrealDB failed"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "error", "message": "MinIO failed"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "error", "message": "Infinity failed"},
            ),
        ):
            result = await health_check()

        assert result.status == "degraded"
        assert result.checks["surrealdb"]["status"] == "error"
        assert result.checks["minio"]["status"] == "error"
        assert result.checks["infinity"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_returns_health_check_response_model(self):
        """Endpoint returns HealthCheckResponse instance."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
        ):
            result = await health_check()

        assert isinstance(result, HealthCheckResponse)

    @pytest.mark.asyncio
    async def test_checks_dict_contains_expected_keys(self):
        """Result checks dict contains surrealdb, minio, and infinity."""
        with (
            patch(
                "compose.api.routers.health.check_surrealdb",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
            patch(
                "compose.api.routers.health.check_minio",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
            patch(
                "compose.api.routers.health.check_infinity",
                new_callable=AsyncMock,
                return_value={"status": "ok", "message": "OK"},
            ),
        ):
            result = await health_check()

        assert set(result.checks.keys()) == {"surrealdb", "minio", "infinity"}
