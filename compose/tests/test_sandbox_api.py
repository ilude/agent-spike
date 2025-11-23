"""Tests for sandbox API router."""

import pytest
from fastapi.testclient import TestClient

from compose.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestLanguagesEndpoint:
    """Tests for GET /sandbox/languages."""

    def test_list_languages(self, client):
        """Test listing supported languages."""
        response = client.get("/sandbox/languages")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert len(data["languages"]) == 3

        # Check Python is included
        python = next((l for l in data["languages"] if l["id"] == "python"), None)
        assert python is not None
        assert python["name"] == "Python"


class TestExecuteEndpoint:
    """Tests for POST /sandbox/execute."""

    def test_execute_python_print(self, client):
        """Test executing simple Python print."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "print('hello')", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hello" in data["stdout"]
        assert data["exit_code"] == 0

    def test_execute_python_math(self, client):
        """Test executing Python math."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "print(2 + 2)", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "4" in data["stdout"]

    def test_execute_blocks_dangerous_code(self, client):
        """Test blocking dangerous code."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "import os", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exit_code"] == 1
        assert data["error"] is not None
        assert "Blocked" in data["error"]

    def test_execute_requires_code(self, client):
        """Test that code is required."""
        response = client.post("/sandbox/execute", json={"language": "python"})
        assert response.status_code == 422  # Validation error

    def test_execute_validates_timeout_max(self, client):
        """Test timeout validation max."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "print('test')", "timeout": 60},  # Max is 30
        )
        assert response.status_code == 422

    def test_execute_validates_timeout_min(self, client):
        """Test timeout validation min."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "print('test')", "timeout": 0.5},  # Min is 1
        )
        assert response.status_code == 422

    def test_execute_returns_execution_id(self, client):
        """Test that execution returns ID."""
        response = client.post(
            "/sandbox/execute",
            json={"code": "print('test')", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data
        assert len(data["execution_id"]) > 0


class TestValidateEndpoint:
    """Tests for POST /sandbox/validate."""

    def test_validate_safe_code(self, client):
        """Test validating safe code."""
        response = client.post(
            "/sandbox/validate",
            json={"code": "print('hello')", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["error"] is None

    def test_validate_dangerous_code(self, client):
        """Test validating dangerous code."""
        response = client.post(
            "/sandbox/validate",
            json={"code": "import subprocess", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error"] is not None

    def test_validate_returns_language(self, client):
        """Test that validation returns language."""
        response = client.post(
            "/sandbox/validate",
            json={"code": "console.log('hi')", "language": "javascript"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "javascript"
