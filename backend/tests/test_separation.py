"""
Unit tests for ColorSeparator and 4-channel plate generation.
"""

import zipfile
import io
import pytest
from PIL import Image
from backend.services.color_separator import ColorSeparator


def test_channel_separation_plates():
    separator = ColorSeparator()
    # Create colorful test image
    img = Image.new("RGB", (100, 100), color=(180, 70, 240))
    plates = separator.separate_channels(img, dpi=300, job_title="TestPrint")

    assert "cyan" in plates
    assert "magenta" in plates
    assert "yellow" in plates
    assert "black" in plates

    # Verify plates are monochrome film positives
    for name, plate in plates.items():
        assert plate.mode == "L"
        assert plate.size[0] > 100
        assert plate.size[1] > 100


def test_separation_zip_archive():
    separator = ColorSeparator()
    img = Image.new("RGB", (60, 60), color=(10, 200, 100))
    zip_bytes, meta = separator.generate_separation_bundle_zip(img, dpi=300, job_title="SariMotif")

    assert len(zip_bytes) > 0
    assert len(meta["plates_generated"]) == 4

    # Verify zip content
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert any("cyan" in n for n in names)
        assert any("magenta" in n for n in names)
        assert any("yellow" in n for n in names)
        assert any("black" in n for n in names)
