"""
Unit tests for Bleed Manager, edge mirroring, and printer crop marks.
"""

import pytest
from PIL import Image
from backend.services.bleed_manager import BleedManager
from backend.services.converter import ImageConverter
from backend.services.image_loader import ImageLoader
from backend.models.schemas import ConversionOptions, SupportedOutputFormat


def test_bleed_mirror_expansion():
    mgr = BleedManager()
    img = Image.new("RGB", (100, 80), color=(200, 100, 50))
    bleed_px = 12

    extended = mgr.extend_bleed(img, bleed_px=bleed_px, fill_mode="mirror")

    assert extended.size == (100 + 2 * bleed_px, 80 + 2 * bleed_px)
    assert extended.mode == "RGB"


def test_bleed_with_crop_marks():
    mgr = BleedManager()
    img = Image.new("RGB", (200, 150), color=(100, 150, 200))
    dpi = 300
    bleed_px = mgr.mm_to_pixels(3.0, dpi)

    extended = mgr.extend_bleed(img, bleed_px=bleed_px, fill_mode="mirror")
    sheet, report = mgr.add_printer_marks(
        extended,
        trim_w=200,
        trim_h=150,
        bleed_px=bleed_px,
        dpi=dpi
    )

    assert sheet.size[0] > extended.size[0]
    assert sheet.size[1] > extended.size[1]
    assert report["crop_marks_added"] is True
    assert report["registration_targets_added"] is True
    assert report["bleed_pixels"] == bleed_px


def test_converter_bleed_integration():
    converter = ImageConverter()
    loader = ImageLoader()

    import io
    buf = io.BytesIO()
    img = Image.new("RGB", (120, 100), color=(150, 50, 220))
    img.save(buf, format="PNG")
    loaded = loader.load_from_bytes(buf.getvalue(), filename="bleed_test.png")

    options = ConversionOptions(
        output_format=SupportedOutputFormat.TIFF,
        dpi=300,
        add_bleed=True,
        bleed_margin_mm=3.0,
        bleed_fill_mode="mirror",
        add_crop_marks=True
    )

    out_path, report = converter.process(loaded, options)
    loaded.close()

    assert report.processing.bleed_applied is not None
    assert report.processing.crop_marks_applied is True
    assert report.output.width > 120
    assert report.output.height > 100

    import os
    if os.path.exists(out_path):
        os.remove(out_path)
