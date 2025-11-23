"""Image generation API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from compose.services.imagegen import (
    GeneratedImage,
    GenerationRequest,
    GenerationResponse,
    ImageSize,
    ImageStyle,
    get_imagegen_service,
)

router = APIRouter(prefix="/imagegen")


class ImageSizeInfo(BaseModel):
    """Information about an image size option."""

    id: str
    name: str
    dimensions: str


class ImageStyleInfo(BaseModel):
    """Information about an image style option."""

    id: str
    name: str


class SupportedOptionsResponse(BaseModel):
    """Response with supported sizes and styles."""

    sizes: list[ImageSizeInfo]
    styles: list[ImageStyleInfo]


class GenerateRequest(BaseModel):
    """Request to generate an image."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    size: str = "large"
    style: str = "natural"
    n: int = Field(default=1, ge=1, le=4)


class ImageListResponse(BaseModel):
    """Response with list of saved images."""

    images: list[str]
    count: int


@router.get("/options", response_model=SupportedOptionsResponse)
async def get_options():
    """Get supported image sizes and styles."""
    sizes = [
        ImageSizeInfo(id="small", name="Small", dimensions="256x256"),
        ImageSizeInfo(id="medium", name="Medium", dimensions="512x512"),
        ImageSizeInfo(id="large", name="Large", dimensions="1024x1024"),
        ImageSizeInfo(id="wide", name="Wide", dimensions="1792x1024"),
        ImageSizeInfo(id="tall", name="Tall", dimensions="1024x1792"),
    ]

    styles = [
        ImageStyleInfo(id="natural", name="Natural"),
        ImageStyleInfo(id="vivid", name="Vivid"),
        ImageStyleInfo(id="anime", name="Anime"),
        ImageStyleInfo(id="photographic", name="Photographic"),
        ImageStyleInfo(id="digital-art", name="Digital Art"),
        ImageStyleInfo(id="cinematic", name="Cinematic"),
    ]

    return SupportedOptionsResponse(sizes=sizes, styles=styles)


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(request: GenerateRequest):
    """Generate an image from a text prompt."""
    service = get_imagegen_service()

    # Map string size to enum
    size_map = {
        "small": ImageSize.SMALL,
        "medium": ImageSize.MEDIUM,
        "large": ImageSize.LARGE,
        "wide": ImageSize.WIDE,
        "tall": ImageSize.TALL,
    }
    size = size_map.get(request.size.lower(), ImageSize.LARGE)

    # Map string style to enum
    style_map = {
        "natural": ImageStyle.NATURAL,
        "vivid": ImageStyle.VIVID,
        "anime": ImageStyle.ANIME,
        "photographic": ImageStyle.PHOTOGRAPHIC,
        "digital-art": ImageStyle.DIGITAL_ART,
        "cinematic": ImageStyle.CINEMATIC,
    }
    style = style_map.get(request.style.lower(), ImageStyle.NATURAL)

    gen_request = GenerationRequest(
        prompt=request.prompt,
        size=size,
        style=style,
        n=request.n,
    )

    try:
        response = await service.generate(gen_request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/images", response_model=ImageListResponse)
async def list_images(limit: int = 50):
    """List saved images."""
    service = get_imagegen_service()
    images = service.list_images(limit=limit)
    return ImageListResponse(
        images=[str(p.name) for p in images],
        count=len(images),
    )
