"""
Unit tests for deterministic format conversions and quality reports.
"""

import io
import os
import pytest
from PIL import Image
from backend.services.image_loader import ImageLoader
from backend.services.converter import ImageConverter
from backend.models.schemas import (
    ConversionOptions,
    SupportedOutputFormat,
    ColorModeOption,
    TIFFCompressionOption,
    UpscaleAlgorithm
)


@pytest.fixture
def converter():
    return ImageConverter()


@pytest.fixture
def loader():
    return ImageLoader()


def create_sample_png_bytes(width=100, height=80, mode="RGB", color=(200, 50, 100)) -> bytes:
    buf = io.BytesIO()
    img = Image.new(mode, (width, height), color=color)
    img.save(buf, format="PNG", dpi=(72, 72))
    return buf.getvalue()


def test_png_to_tiff_lzw_300dpi(converter, loader):
    raw_png = create_sample_png_bytes(width=200, height=150)
    loaded = loader.load_from_bytes(raw_png, filename="sample.png")

    options = ConversionOptions(
        output_format=SupportedOutputFormat.TIFF,
        dpi=300,
        color_mode=ColorModeOption.RGB,
        tiff_compression=TIFFCompressionOption.LZW
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert os.path.exists(out_path)
    assert report.input.format == "PNG"
    assert report.output.format == "TIFF"
    assert report.output.dpi == (300.0, 300.0)
    assert report.output.mode == "RGB"
    assert report.quality.format_valid is True
    assert report.quality.resolution_ok is True
    assert report.quality.suitable_for_commercial_print is True

    # Verify directly with PIL
    with Image.open(out_path) as verify_img:
        assert verify_img.format == "TIFF"
        assert verify_img.size == (200, 150)
        assert verify_img.info.get("dpi") == (300.0, 300.0)

    os.remove(out_path)


def test_png_to_cmyk_tiff(converter, loader):
    raw_png = create_sample_png_bytes(width=120, height=120)
    loaded = loader.load_from_bytes(raw_png)

    options = ConversionOptions(
        output_format=SupportedOutputFormat.TIFF,
        dpi=600,
        color_mode=ColorModeOption.CMYK,
        tiff_compression=TIFFCompressionOption.DEFLATE
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert report.output.mode == "CMYK"
    assert report.output.channels == 4
    assert report.output.dpi == (600.0, 600.0)

    with Image.open(out_path) as verify_img:
        assert verify_img.mode == "CMYK"

    os.remove(out_path)


def test_rgba_to_bmp_flattens_alpha(converter, loader):
    # RGBA image with alpha channel
    raw_rgba = create_sample_png_bytes(width=100, height=100, mode="RGBA", color=(100, 200, 50, 128))
    loaded = loader.load_from_bytes(raw_rgba, filename="transparent.png")

    options = ConversionOptions(
        output_format=SupportedOutputFormat.BMP,
        dpi=300
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert report.output.format == "BMP"
    assert report.output.mode == "RGB"

    with Image.open(out_path) as verify_img:
        assert verify_img.format == "BMP"
        assert verify_img.mode == "RGB"

    os.remove(out_path)


def test_upscale_2x_conversion(converter, loader):
    raw_png = create_sample_png_bytes(width=100, height=50)
    loaded = loader.load_from_bytes(raw_png)

    options = ConversionOptions(
        output_format=SupportedOutputFormat.PNG,
        dpi=300,
        upscale_factor=2,
        upscale_algorithm=UpscaleAlgorithm.LANCZOS
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert report.output.width == 200
    assert report.output.height == 100
    assert report.processing.upscale == "2x"

    os.remove(out_path)


def test_realesrgan_upscale_4x_conversion(converter, loader):
    raw_png = create_sample_png_bytes(width=50, height=40)
    loaded = loader.load_from_bytes(raw_png)

    options = ConversionOptions(
        output_format=SupportedOutputFormat.PNG,
        dpi=300,
        upscale_factor=4,
        upscale_algorithm=UpscaleAlgorithm.REAL_ESRGAN
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert report.output.width == 200
    assert report.output.height == 160
    assert report.processing.upscale == "4x"
    assert "Real-ESRGAN" in report.processing.upscaler

    with Image.open(out_path) as verify_img:
        assert verify_img.size == (200, 160)

    os.remove(out_path)
