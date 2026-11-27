import io
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
MAX_IMAGE_PIXELS = 60_000_000


def inspect_image(content: bytes, suffix: str) -> dict:
    expected_format = ALLOWED_IMAGE_FORMATS.get(suffix.lower())
    if expected_format is None:
        raise HTTPException(status_code=415, detail={"code": "unsupported_file_type", "message": "Supported images are PNG, JPG and JPEG."})
    try:
        with Image.open(io.BytesIO(content)) as image:
            detected_format = image.format
            width, height = image.size
            image.verify()
        if detected_format != expected_format:
            raise HTTPException(status_code=400, detail={"code": "image_format_mismatch", "message": "Image extension does not match the actual image format."})
        if width * height > MAX_IMAGE_PIXELS:
            raise HTTPException(status_code=413, detail={"code": "image_too_large", "message": "Image dimensions exceed the supported pixel limit."})
        return {"format": detected_format, "width": width, "height": height}
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail={"code": "invalid_image_content", "message": "The file content is not a valid supported image."}) from None
