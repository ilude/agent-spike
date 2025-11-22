"""Tests for image generation API router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from compose.api.main import app
from compose.services.imagegen import GeneratedImage, GenerationResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestOptionsEndpoint:
    """Tests for GET /imagegen/options."""

    def test_get_options(self, client):
        """Test getting supported options."""
        response = client.get("/imagegen/options")
        assert response.status_code == 200
        data = response.json()

        assert "sizes" in data
        assert "styles" in data
        assert len(data["sizes"]) == 5
        assert len(data["styles"]) == 6

    def test_options_size_structure(self, client):
        """Test size option structure."""
        response = client.get("/imagegen/options")
        data = response.json()

        large = next((s for s in data["sizes"] if s["id"] == "large"), None)
        assert large is not None
        assert large["name"] == "Large"
        assert large["dimensions"] == "1024x1024"

    def test_options_style_structure(self, client):
        """Test style option structure."""
        response = client.get("/imagegen/options")
        data = response.json()

        vivid = next((s for s in data["styles"] if s["id"] == "vivid"), None)
        assert vivid is not None
        assert vivid["name"] == "Vivid"


class TestGenerateEndpoint:
    """Tests for POST /imagegen/generate."""

    def test_generate_requires_prompt(self, client):
        """Test that prompt is required."""
        response = client.post("/imagegen/generate", json={})
        assert response.status_code == 422

    def test_generate_rejects_empty_prompt(self, client):
        """Test that empty prompt is rejected."""
        response = client.post("/imagegen/generate", json={"prompt": ""})
        assert response.status_code == 422

    def test_generate_validates_n_max(self, client):
        """Test n field max validation."""
        response = client.post(
            "/imagegen/generate",
            json={"prompt": "test", "n": 5},  # Max is 4
        )
        assert response.status_code == 422

    def test_generate_validates_n_min(self, client):
        """Test n field min validation."""
        response = client.post(
            "/imagegen/generate",
            json={"prompt": "test", "n": 0},  # Min is 1
        )
        assert response.status_code == 422

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_generate_success(self, mock_get_service, client):
        """Test successful generation."""
        mock_service = AsyncMock()
        mock_service.generate = AsyncMock(
            return_value=GenerationResponse(
                images=[
                    GeneratedImage(
                        id="test-id",
                        prompt="a sunset",
                        url="https://example.com/image.png",
                        size="1024x1024",
                        style="natural",
                        created_at="2024-01-01T00:00:00Z",
                        backend="dalle-3",
                    )
                ],
                prompt="a sunset",
                backend="dalle-3",
            )
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/imagegen/generate",
            json={"prompt": "a sunset"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "dalle-3"
        assert len(data["images"]) == 1
        assert data["images"][0]["url"] == "https://example.com/image.png"

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_generate_no_api_keys(self, mock_get_service, client):
        """Test generation when no API keys configured."""
        mock_service = AsyncMock()
        mock_service.generate = AsyncMock(
            side_effect=ValueError("No image generation API keys configured")
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/imagegen/generate",
            json={"prompt": "a sunset"},
        )

        assert response.status_code == 503
        assert "No image generation API keys" in response.json()["detail"]

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_generate_with_size(self, mock_get_service, client):
        """Test generation with size parameter."""
        mock_service = AsyncMock()
        mock_service.generate = AsyncMock(
            return_value=GenerationResponse(
                images=[
                    GeneratedImage(
                        id="test",
                        prompt="test",
                        url="https://example.com/img.png",
                        size="1792x1024",
                        style="natural",
                        created_at="2024-01-01T00:00:00Z",
                        backend="dalle-3",
                    )
                ],
                prompt="test",
                backend="dalle-3",
            )
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/imagegen/generate",
            json={"prompt": "test", "size": "wide"},
        )

        assert response.status_code == 200

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_generate_with_style(self, mock_get_service, client):
        """Test generation with style parameter."""
        mock_service = AsyncMock()
        mock_service.generate = AsyncMock(
            return_value=GenerationResponse(
                images=[
                    GeneratedImage(
                        id="test",
                        prompt="test",
                        url="https://example.com/img.png",
                        size="1024x1024",
                        style="anime",
                        created_at="2024-01-01T00:00:00Z",
                        backend="stability",
                    )
                ],
                prompt="test",
                backend="stability",
            )
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/imagegen/generate",
            json={"prompt": "test", "style": "anime"},
        )

        assert response.status_code == 200


class TestListImagesEndpoint:
    """Tests for GET /imagegen/images."""

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_list_images(self, mock_get_service, client, tmp_path):
        """Test listing images."""
        from pathlib import Path

        mock_service = MagicMock()
        mock_service.list_images.return_value = [
            Path("img1.png"),
            Path("img2.png"),
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/imagegen/images")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert "img1.png" in data["images"]

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_list_images_empty(self, mock_get_service, client):
        """Test listing images when none exist."""
        mock_service = MagicMock()
        mock_service.list_images.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/imagegen/images")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["images"] == []

    @patch("compose.api.routers.imagegen.get_imagegen_service")
    def test_list_images_with_limit(self, mock_get_service, client):
        """Test listing images with limit."""
        mock_service = MagicMock()
        mock_service.list_images.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/imagegen/images?limit=10")

        assert response.status_code == 200
        mock_service.list_images.assert_called_once_with(limit=10)
