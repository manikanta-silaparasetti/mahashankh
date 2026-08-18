"""
Image loader service.
Handles robust loading from raw bytes, base64 strings, file streams, and URLs,
with automatic EXIF orientation normalization and resource management.
"""

import io
import base64
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any
from PIL import Image, ImageOps

from .image_validator import ImageValidator, ImageValidationError


@dataclass
class LoadedImage:
    """Represents a validated and loaded PIL Image with original metadata."""
    image: Image.Image
    raw_bytes: bytes
    metadata: Dict[str, Any]

    def close(self):
        """Releases underlying PIL image memory."""
        try:
            self.image.close()
        except Exception:
            pass


class ImageLoader:
    """Service to load and normalize image inputs."""

    def __init__(self, validator: Optional[ImageValidator] = None):
        self.validator = validator or ImageValidator()

    def load_from_bytes(self, data: bytes, filename: Optional[str] = None) -> LoadedImage:
        """Validates and opens image bytes, applying EXIF orientation correction."""
        metadata = self.validator.validate_raw_bytes(data, filename)

        # Open PIL Image
        pil_img = Image.open(io.BytesIO(data))

        # Auto-orient based on EXIF tag if present
        try:
            pil_img = ImageOps.exif_transpose(pil_img) or pil_img
        except Exception:
            pass  # Fall back to original orientation if EXIF is malformed

        return LoadedImage(
            image=pil_img,
            raw_bytes=data,
            metadata=metadata
        )

    def load_from_base64(self, b64_string: str, filename: Optional[str] = None) -> LoadedImage:
        """Decodes base64 string (handles data URL prefixes like data:image/png;base64,...)"""
        if not b64_string:
            raise ImageValidationError("Base64 image string is empty.")

        # Strip data URL prefix if present
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]

        try:
            raw_bytes = base64.b64decode(b64_string)
        except Exception as e:
            raise ImageValidationError(f"Invalid base64 encoding: {str(e)}")

        return self.load_from_bytes(raw_bytes, filename=filename or "base64_image")

    def load_from_url(self, url: str, timeout: int = 15) -> LoadedImage:
        """Fetches an image from a URL safely."""
        if not url.startswith(("http://", "https://")):
            raise ImageValidationError("URL must start with http:// or https://")

        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "MahaSankh-ImageConverter/1.0"})
            if resp.status_code != 200:
                raise ImageValidationError(f"Failed to fetch image from URL. HTTP status {resp.status_code}")
            data = resp.content
        except requests.RequestException as e:
            raise ImageValidationError(f"Network error while fetching image URL: {str(e)}")

        filename = url.split("/")[-1].split("?")[0] or "remote_image"
        return self.load_from_bytes(data, filename=filename)
