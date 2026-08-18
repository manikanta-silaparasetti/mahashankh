"""
Image validation service.
Validates magic numbers / file signatures, MIME types, dimensions, pixel count,
decompression bomb thresholds, color modes, and file size before processing.
"""

import io
import re
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image

# Enforce reasonable default safety limits
# 100 Megapixels max for standard synchronous pipeline (~10000x10000 or equivalent)
DEFAULT_MAX_PIXELS = 100_000_000
# 200 MB maximum upload file size
DEFAULT_MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024


class ImageValidationError(Exception):
    """Custom exception raised when image validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DecompressionBombError(ImageValidationError):
    """Raised when an image exceeds safe decompression limits."""
    pass


class ImageValidator:
    """
    Validates image headers, signatures, and safety constraints.
    """

    # File magic numbers / signatures table
    SIGNATURES = [
        (b"\xFF\xD8\xFF", "JPEG", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "PNG", "image/png"),
        (b"BM", "BMP", "image/bmp"),
        (b"II*\x00", "TIFF", "image/tiff"),  # Little-endian TIFF
        (b"MM\x00*", "TIFF", "image/tiff"),  # Big-endian TIFF
        (b"GIF87a", "GIF", "image/gif"),
        (b"GIF89a", "GIF", "image/gif"),
        (b"RIFF", "WEBP", "image/webp"),  # Starts with RIFF .... WEBP
    ]

    def __init__(
        self,
        max_pixels: int = DEFAULT_MAX_PIXELS,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    ):
        self.max_pixels = max_pixels
        self.max_file_size_bytes = max_file_size_bytes
        # Configure PIL's decompression bomb limit
        Image.MAX_IMAGE_PIXELS = self.max_pixels

    def detect_signature(self, data_prefix: bytes) -> Tuple[Optional[str], Optional[str]]:
        """
        Inspect raw file header bytes to identify format independently of filename.
        Returns (format_name, mime_type).
        """
        if len(data_prefix) < 4:
            return None, None

        # Check WebP specifically (RIFF header with WEBP at offset 8)
        if data_prefix.startswith(b"RIFF") and len(data_prefix) >= 12:
            if data_prefix[8:12] == b"WEBP":
                return "WEBP", "image/webp"

        for sig, fmt, mime in self.SIGNATURES:
            if data_prefix.startswith(sig):
                return fmt, mime

        return None, None

    def validate_raw_bytes(
        self,
        data: bytes,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs full validation on raw image bytes before loading.
        Returns a dictionary of validated metadata.
        """
        size_bytes = len(data)
        if size_bytes == 0:
            raise ImageValidationError("Uploaded file is empty (0 bytes).")

        if size_bytes > self.max_file_size_bytes:
            raise ImageValidationError(
                f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed limit "
                f"({self.max_file_size_bytes / (1024*1024):.2f} MB)."
            )

        # 1. Check magic bytes
        detected_format, detected_mime = self.detect_signature(data[:16])
        if not detected_format:
            # Fallback: check if PIL can recognize it
            try:
                with Image.open(io.BytesIO(data)) as test_img:
                    detected_format = test_img.format
                    detected_mime = Image.MIME.get(test_img.format, "application/octet-stream")
            except Exception as e:
                raise ImageValidationError(
                    f"File format not recognized or unsupported. Signature check failed: {str(e)}"
                )

        # 2. Inspect dimensions safely using Pillow header inspection
        try:
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                mode = img.mode
                format_from_pil = img.format
                info = dict(img.info)

                total_pixels = width * height
                if total_pixels > self.max_pixels:
                    raise DecompressionBombError(
                        f"Image pixel count ({width}x{height} = {total_pixels:,} px) exceeds safe limit "
                        f"({self.max_pixels:,} px). Possible decompression bomb."
                    )

                # Get DPI if present in metadata
                dpi = (72.0, 72.0)
                if "dpi" in info:
                    dpi_info = info["dpi"]
                    if isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
                        dpi = (float(dpi_info[0]), float(dpi_info[1]))

                # Check ICC profile
                icc_present = "icc_profile" in info and bool(info["icc_profile"])
                icc_name = None
                if icc_present:
                    try:
                        from PIL import ImageCms
                        profile_bytes = info["icc_profile"]
                        icc_obj = ImageCms.ImageCmsProfile(io.BytesIO(profile_bytes))
                        icc_name = ImageCms.getProfileName(icc_obj)
                    except Exception:
                        icc_name = "Embedded ICC Profile (Raw)"

                # Bit depth & channels calculation
                bit_depth = 8
                channels = len(mode)
                if mode == "1":
                    bit_depth = 1
                    channels = 1
                elif mode == "L":
                    bit_depth = 8
                    channels = 1
                elif mode in ("I", "F"):
                    bit_depth = 32
                    channels = 1
                elif mode == "RGB":
                    bit_depth = 8
                    channels = 3
                elif mode == "RGBA":
                    bit_depth = 8
                    channels = 4
                elif mode == "CMYK":
                    bit_depth = 8
                    channels = 4
                elif mode == "RGB;16" or mode == "I;16":
                    bit_depth = 16

                has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in info

                return {
                    "valid": True,
                    "filename": filename or "image",
                    "detected_format": detected_format or format_from_pil,
                    "mime_type": detected_mime or "application/octet-stream",
                    "file_signature": data[:8].hex().upper(),
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "bit_depth": bit_depth,
                    "channels": channels,
                    "total_pixels": total_pixels,
                    "has_alpha": has_alpha,
                    "dpi": dpi,
                    "icc_profile_present": icc_present,
                    "icc_profile_name": icc_name,
                    "exif_present": "exif" in info,
                    "file_size_bytes": size_bytes,
                }
        except Image.DecompressionBombError as dbe:
            raise DecompressionBombError(str(dbe))
        except DecompressionBombError:
            raise
        except Exception as e:
            raise ImageValidationError(f"Invalid or corrupted image data: {str(e)}")

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes filename to prevent directory traversal and special character issues."""
        clean = re.sub(r'[^\w\.\-\_]', '_', filename)
        return clean.strip('._') or "unnamed_image"
