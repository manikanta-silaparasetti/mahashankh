"""
Unit tests for ImageValidator and security limits.
"""

import io
import pytest
from PIL import Image
from backend.services.image_validator import (
    ImageValidator,
    ImageValidationError,
    DecompressionBombError
)


@pytest.fixture
def validator():
    return ImageValidator(max_pixels=1_000_000, max_file_size_bytes=5 * 1024 * 1024)


def test_magic_byte_signatures(validator):
    # PNG signature
    png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    fmt, mime = validator.detect_signature(png_header)
    assert fmt == "PNG"
    assert mime == "image/png"

    # JPEG signature
    jpeg_header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF"
    fmt, mime = validator.detect_signature(jpeg_header)
    assert fmt == "JPEG"
    assert mime == "image/jpeg"

    # BMP signature
    bmp_header = b"BM\x36\x00\x00\x00\x00\x00"
    fmt, mime = validator.detect_signature(bmp_header)
    assert fmt == "BMP"
    assert mime == "image/bmp"

    # TIFF signature (Little-endian)
    tiff_header = b"II*\x00\x08\x00\x00\x00"
    fmt, mime = validator.detect_signature(tiff_header)
    assert fmt == "TIFF"
    assert mime == "image/tiff"


def test_valid_image_bytes_inspection(validator):
    # Generate in-memory PNG
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 150), color=(255, 0, 0))
    img.save(buf, format="PNG", dpi=(300, 300))
    raw_data = buf.getvalue()

    meta = validator.validate_raw_bytes(raw_data, filename="test.png")
    assert meta["valid"] is True
    assert meta["detected_format"] == "PNG"
    assert meta["width"] == 200
    assert meta["height"] == 150
    assert meta["total_pixels"] == 30000
    assert meta["channels"] == 3
    assert meta["has_alpha"] is False


def test_decompression_bomb_prevention():
    # Set small limit of 10,000 pixels
    strict_validator = ImageValidator(max_pixels=10_000)

    buf = io.BytesIO()
    # 200 x 200 = 40,000 pixels (> 10,000)
    img = Image.new("RGB", (200, 200), color=(0, 255, 0))
    img.save(buf, format="PNG")

    with pytest.raises(DecompressionBombError):
        strict_validator.validate_raw_bytes(buf.getvalue())


def test_empty_file_rejection(validator):
    with pytest.raises(ImageValidationError) as exc:
        validator.validate_raw_bytes(b"")
    assert "empty" in str(exc.value)


def test_filename_sanitization():
    unsafe_name = "../../etc/passwd/evil#file$name.png"
    safe = ImageValidator.sanitize_filename(unsafe_name)
    assert ".." not in safe
    assert "/" not in safe
    assert "#" not in safe
