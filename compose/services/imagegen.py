"""Image generation service supporting multiple AI backends.

Supports OpenAI DALL-E, Stability AI, and other image generation APIs.
"""

import base64
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field


# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")


class ImageSize(str, Enum):
    """Supported image sizes."""

    SMALL = "256x256"
    MEDIUM = "512x512"
    LARGE = "1024x1024"
    WIDE = "1792x1024"
    TALL = "1024x1792"


class ImageStyle(str, Enum):
    """Image generation styles."""

    NATURAL = "natural"
    VIVID = "vivid"
    ANIME = "anime"
    PHOTOGRAPHIC = "photographic"
    DIGITAL_ART = "digital-art"
    CINEMATIC = "cinematic"


class GenerationRequest(BaseModel):
    """Request to generate an image."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    size: ImageSize = ImageSize.LARGE
    style: ImageStyle = ImageStyle.NATURAL
    n: int = Field(default=1, ge=1, le=4)


class GeneratedImage(BaseModel):
    """A generated image."""

    id: str
    prompt: str
    url: str | None = None  # URL if hosted externally
    b64_data: str | None = None  # Base64 data if returned inline
    size: str
    style: str
    created_at: str
    backend: str


class GenerationResponse(BaseModel):
    """Response from image generation."""

    images: list[GeneratedImage]
    prompt: str
    backend: str


class ImageGenService:
    """Service for generating images using AI."""

    def __init__(self, image_dir: Optional[str] = None):
        """Initialize the image generation service.

        Args:
            image_dir: Directory to save generated images.
                      Defaults to compose/data/images/
        """
        if image_dir is None:
            base = Path(__file__).parent.parent / "data" / "images"
            self.image_dir = base
        else:
            self.image_dir = Path(image_dir)

        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.openai_key = OPENAI_API_KEY
        self.stability_key = STABILITY_API_KEY

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate images from a text prompt.

        Uses available backends in order: DALL-E 3 > Stability AI

        Args:
            request: Generation request with prompt and options

        Returns:
            GenerationResponse with generated images
        """
        # Try OpenAI DALL-E first (best quality)
        if self.openai_key:
            try:
                return await self._generate_dalle(request)
            except Exception as e:
                print(f"DALL-E generation failed: {e}")

        # Try Stability AI
        if self.stability_key:
            try:
                return await self._generate_stability(request)
            except Exception as e:
                print(f"Stability AI generation failed: {e}")

        # No backends available
        raise ValueError("No image generation API keys configured")

    async def _generate_dalle(self, request: GenerationRequest) -> GenerationResponse:
        """Generate images using OpenAI DALL-E 3."""
        # DALL-E 3 only supports these sizes
        size_map = {
            ImageSize.SMALL: "1024x1024",
            ImageSize.MEDIUM: "1024x1024",
            ImageSize.LARGE: "1024x1024",
            ImageSize.WIDE: "1792x1024",
            ImageSize.TALL: "1024x1792",
        }
        dalle_size = size_map.get(request.size, "1024x1024")

        # DALL-E 3 styles
        dalle_style = "vivid" if request.style == ImageStyle.VIVID else "natural"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": request.prompt,
                    "n": 1,  # DALL-E 3 only supports n=1
                    "size": dalle_size,
                    "style": dalle_style,
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            data = response.json()

        images = []
        for item in data.get("data", []):
            image_id = str(uuid.uuid4())[:8]
            images.append(
                GeneratedImage(
                    id=image_id,
                    prompt=request.prompt,
                    url=item.get("url"),
                    size=dalle_size,
                    style=dalle_style,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    backend="dalle-3",
                )
            )

        return GenerationResponse(
            images=images, prompt=request.prompt, backend="dalle-3"
        )

    async def _generate_stability(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        """Generate images using Stability AI."""
        # Stability AI size mapping
        width, height = request.size.value.split("x")
        width, height = int(width), int(height)

        # Style preset mapping
        style_map = {
            ImageStyle.NATURAL: None,
            ImageStyle.VIVID: "enhance",
            ImageStyle.ANIME: "anime",
            ImageStyle.PHOTOGRAPHIC: "photographic",
            ImageStyle.DIGITAL_ART: "digital-art",
            ImageStyle.CINEMATIC: "cinematic",
        }
        style_preset = style_map.get(request.style)

        payload = {
            "text_prompts": [{"text": request.prompt, "weight": 1}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": request.n,
            "steps": 30,
        }
        if style_preset:
            payload["style_preset"] = style_preset

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.stability_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        images = []
        for artifact in data.get("artifacts", []):
            image_id = str(uuid.uuid4())[:8]
            images.append(
                GeneratedImage(
                    id=image_id,
                    prompt=request.prompt,
                    b64_data=artifact.get("base64"),
                    size=request.size.value,
                    style=request.style.value,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    backend="stability",
                )
            )

        return GenerationResponse(
            images=images, prompt=request.prompt, backend="stability"
        )

    def save_image(self, image: GeneratedImage, filename: str | None = None) -> Path:
        """Save a generated image to disk.

        Args:
            image: Generated image with b64_data
            filename: Optional filename, defaults to image ID

        Returns:
            Path to saved image
        """
        if not image.b64_data:
            raise ValueError("Image has no base64 data to save")

        filename = filename or f"{image.id}.png"
        path = self.image_dir / filename

        # Decode and save
        image_data = base64.b64decode(image.b64_data)
        with open(path, "wb") as f:
            f.write(image_data)

        return path

    def list_images(self, limit: int = 50) -> list[Path]:
        """List generated images in the image directory.

        Args:
            limit: Maximum number of images to return

        Returns:
            List of image paths, most recent first
        """
        images = list(self.image_dir.glob("*.png"))
        images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return images[:limit]


# Singleton instance
_service: Optional[ImageGenService] = None


def get_imagegen_service() -> ImageGenService:
    """Get or create the image generation service singleton."""
    global _service
    if _service is None:
        _service = ImageGenService()
    return _service
