"""Tests for image generation service."""

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.services.imagegen import (
    GeneratedImage,
    GenerationRequest,
    GenerationResponse,
    ImageGenService,
    ImageSize,
    ImageStyle,
    get_imagegen_service,
)


class TestImageSizeEnum:
    """Tests for ImageSize enum."""

    def test_size_values(self):
        """Test that sizes have correct values."""
        assert ImageSize.SMALL.value == "256x256"
        assert ImageSize.MEDIUM.value == "512x512"
        assert ImageSize.LARGE.value == "1024x1024"
        assert ImageSize.WIDE.value == "1792x1024"
        assert ImageSize.TALL.value == "1024x1792"

    def test_size_count(self):
        """Test that we have expected number of sizes."""
        assert len(ImageSize) == 5


class TestImageStyleEnum:
    """Tests for ImageStyle enum."""

    def test_style_values(self):
        """Test that styles have correct values."""
        assert ImageStyle.NATURAL.value == "natural"
        assert ImageStyle.VIVID.value == "vivid"
        assert ImageStyle.ANIME.value == "anime"
        assert ImageStyle.PHOTOGRAPHIC.value == "photographic"
        assert ImageStyle.DIGITAL_ART.value == "digital-art"
        assert ImageStyle.CINEMATIC.value == "cinematic"

    def test_style_count(self):
        """Test that we have expected number of styles."""
        assert len(ImageStyle) == 6


class TestGenerationRequest:
    """Tests for GenerationRequest model."""

    def test_default_values(self):
        """Test default values for generation request."""
        request = GenerationRequest(prompt="test image")
        assert request.prompt == "test image"
        assert request.size == ImageSize.LARGE
        assert request.style == ImageStyle.NATURAL
        assert request.n == 1

    def test_custom_values(self):
        """Test custom values for generation request."""
        request = GenerationRequest(
            prompt="a sunset",
            size=ImageSize.WIDE,
            style=ImageStyle.CINEMATIC,
            n=2,
        )
        assert request.prompt == "a sunset"
        assert request.size == ImageSize.WIDE
        assert request.style == ImageStyle.CINEMATIC
        assert request.n == 2

    def test_prompt_min_length(self):
        """Test prompt minimum length validation."""
        with pytest.raises(ValueError):
            GenerationRequest(prompt="")

    def test_n_range_validation(self):
        """Test n field range validation."""
        with pytest.raises(ValueError):
            GenerationRequest(prompt="test", n=0)
        with pytest.raises(ValueError):
            GenerationRequest(prompt="test", n=5)


class TestGeneratedImage:
    """Tests for GeneratedImage model."""

    def test_url_based_image(self):
        """Test image with URL."""
        image = GeneratedImage(
            id="abc123",
            prompt="test",
            url="https://example.com/image.png",
            size="1024x1024",
            style="natural",
            created_at="2024-01-01T00:00:00Z",
            backend="dalle-3",
        )
        assert image.url == "https://example.com/image.png"
        assert image.b64_data is None

    def test_base64_based_image(self):
        """Test image with base64 data."""
        image = GeneratedImage(
            id="def456",
            prompt="test",
            b64_data="iVBORw0KGgoAAAANS...",
            size="512x512",
            style="vivid",
            created_at="2024-01-01T00:00:00Z",
            backend="stability",
        )
        assert image.b64_data == "iVBORw0KGgoAAAANS..."
        assert image.url is None


class TestGenerationResponse:
    """Tests for GenerationResponse model."""

    def test_response_structure(self):
        """Test response structure."""
        image = GeneratedImage(
            id="test",
            prompt="sunset",
            url="https://example.com/img.png",
            size="1024x1024",
            style="natural",
            created_at="2024-01-01T00:00:00Z",
            backend="dalle-3",
        )
        response = GenerationResponse(
            images=[image],
            prompt="sunset",
            backend="dalle-3",
        )
        assert len(response.images) == 1
        assert response.prompt == "sunset"
        assert response.backend == "dalle-3"


class TestImageGenService:
    """Tests for ImageGenService."""

    def test_init_default_directory(self):
        """Test service initialization with default directory."""
        service = ImageGenService()
        # Default should be compose/data/images
        assert "images" in str(service.image_dir)
        assert service.image_dir.exists()

    def test_init_custom_directory(self, tmp_path):
        """Test service initialization with custom directory."""
        custom_dir = tmp_path / "custom_images"
        service = ImageGenService(image_dir=str(custom_dir))
        assert service.image_dir == custom_dir
        assert custom_dir.exists()

    @pytest.mark.asyncio
    async def test_generate_no_api_keys(self, tmp_path, monkeypatch):
        """Test generate raises error when no API keys configured."""
        monkeypatch.setattr("compose.services.imagegen.OPENAI_API_KEY", "")
        monkeypatch.setattr("compose.services.imagegen.STABILITY_API_KEY", "")

        service = ImageGenService(image_dir=str(tmp_path))
        service.openai_key = ""
        service.stability_key = ""

        request = GenerationRequest(prompt="test image")

        with pytest.raises(ValueError, match="No image generation API keys"):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_dalle_success(self, tmp_path, monkeypatch):
        """Test successful DALL-E generation."""
        service = ImageGenService(image_dir=str(tmp_path))
        service.openai_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"url": "https://example.com/generated.png"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            request = GenerationRequest(prompt="a beautiful sunset")
            response = await service.generate(request)

            assert response.backend == "dalle-3"
            assert len(response.images) == 1
            assert response.images[0].url == "https://example.com/generated.png"

    @pytest.mark.asyncio
    async def test_generate_dalle_size_mapping(self, tmp_path):
        """Test DALL-E size mapping."""
        service = ImageGenService(image_dir=str(tmp_path))
        service.openai_key = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            # Test SMALL maps to 1024x1024
            request = GenerationRequest(prompt="test", size=ImageSize.SMALL)
            response = await service.generate(request)
            assert response.images[0].size == "1024x1024"

    @pytest.mark.asyncio
    async def test_generate_stability_fallback(self, tmp_path):
        """Test fallback to Stability AI when DALL-E fails."""
        service = ImageGenService(image_dir=str(tmp_path))
        service.openai_key = "dalle-key"
        service.stability_key = "stability-key"

        # Mock DALL-E to fail
        dalle_mock = AsyncMock(side_effect=Exception("DALL-E error"))

        # Mock Stability to succeed
        stability_response = MagicMock()
        stability_response.json.return_value = {
            "artifacts": [{"base64": "dGVzdGRhdGE="}]
        }
        stability_response.raise_for_status = MagicMock()
        stability_mock = AsyncMock(return_value=stability_response)

        with patch("httpx.AsyncClient") as mock_client:
            call_count = [0]

            async def mock_post(*args, **kwargs):
                call_count[0] += 1
                if "openai" in args[0]:
                    raise Exception("DALL-E error")
                return stability_response

            mock_client_instance = AsyncMock()
            mock_client_instance.post = mock_post
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            request = GenerationRequest(prompt="test image")
            response = await service.generate(request)

            assert response.backend == "stability"

    @pytest.mark.asyncio
    async def test_generate_stability_style_mapping(self, tmp_path):
        """Test Stability AI style preset mapping."""
        service = ImageGenService(image_dir=str(tmp_path))
        service.openai_key = ""  # Force Stability
        service.stability_key = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "artifacts": [{"base64": "dGVzdA=="}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            captured_payload = []

            async def capture_post(url, **kwargs):
                captured_payload.append(kwargs.get("json", {}))
                return mock_response

            mock_client_instance = AsyncMock()
            mock_client_instance.post = capture_post
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            # Test ANIME style
            request = GenerationRequest(prompt="test", style=ImageStyle.ANIME)
            await service.generate(request)

            assert captured_payload[0].get("style_preset") == "anime"

    def test_save_image(self, tmp_path):
        """Test saving image to disk."""
        service = ImageGenService(image_dir=str(tmp_path))

        # Create test image data
        test_data = b"\x89PNG\r\n\x1a\ntest"
        b64_data = base64.b64encode(test_data).decode()

        image = GeneratedImage(
            id="save-test",
            prompt="test",
            b64_data=b64_data,
            size="512x512",
            style="natural",
            created_at="2024-01-01T00:00:00Z",
            backend="stability",
        )

        path = service.save_image(image)

        assert path.exists()
        assert path.name == "save-test.png"
        with open(path, "rb") as f:
            assert f.read() == test_data

    def test_save_image_custom_filename(self, tmp_path):
        """Test saving image with custom filename."""
        service = ImageGenService(image_dir=str(tmp_path))

        test_data = b"fake png data"
        b64_data = base64.b64encode(test_data).decode()

        image = GeneratedImage(
            id="custom",
            prompt="test",
            b64_data=b64_data,
            size="512x512",
            style="natural",
            created_at="2024-01-01T00:00:00Z",
            backend="stability",
        )

        path = service.save_image(image, filename="my_image.png")

        assert path.name == "my_image.png"

    def test_save_image_no_data(self, tmp_path):
        """Test saving image raises error when no data."""
        service = ImageGenService(image_dir=str(tmp_path))

        image = GeneratedImage(
            id="no-data",
            prompt="test",
            url="https://example.com/img.png",  # URL only, no b64
            size="512x512",
            style="natural",
            created_at="2024-01-01T00:00:00Z",
            backend="dalle-3",
        )

        with pytest.raises(ValueError, match="no base64 data"):
            service.save_image(image)

    def test_list_images(self, tmp_path):
        """Test listing images."""
        service = ImageGenService(image_dir=str(tmp_path))

        # Create some test files
        (tmp_path / "img1.png").touch()
        (tmp_path / "img2.png").touch()
        (tmp_path / "img3.png").touch()
        (tmp_path / "not_an_image.txt").touch()

        images = service.list_images()

        assert len(images) == 3
        assert all(p.suffix == ".png" for p in images)

    def test_list_images_limit(self, tmp_path):
        """Test listing images with limit."""
        service = ImageGenService(image_dir=str(tmp_path))

        # Create test files
        for i in range(10):
            (tmp_path / f"img{i}.png").touch()

        images = service.list_images(limit=5)

        assert len(images) == 5


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_imagegen_service_returns_same_instance(self, monkeypatch):
        """Test that get_imagegen_service returns singleton."""
        # Reset singleton
        monkeypatch.setattr("compose.services.imagegen._service", None)

        service1 = get_imagegen_service()
        service2 = get_imagegen_service()

        assert service1 is service2
