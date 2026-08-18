"""
Unit tests for DPI calculations and physical dimension conversions.
"""

import pytest
from backend.services.dpi_manager import DPIManager
from backend.models.schemas import DimensionUnit


def test_dpi_physical_dimension_calculation():
    # 3000 x 3000 pixels at 300 DPI should be exactly 10.0 x 10.0 inches
    dims = DPIManager.calculate_physical_dimensions(3000, 3000, 300)
    assert dims["width_inches"] == 10.0
    assert dims["height_inches"] == 10.0
    assert dims["width_cm"] == 25.4
    assert dims["height_cm"] == 25.4
    assert dims["width_mm"] == 254.0
    assert dims["height_mm"] == 254.0


def test_dpi_print_matrix():
    # 1500 x 3000 pixels
    matrix = DPIManager.generate_print_matrix(1500, 3000, source_dpi=72)
    dpis = [item.dpi for item in matrix]
    assert 72 in dpis
    assert 150 in dpis
    assert 300 in dpis
    assert 600 in dpis

    # At 300 DPI: 1500 / 300 = 5.0 inches, 3000 / 300 = 10.0 inches
    item_300 = next(item for item in matrix if item.dpi == 300)
    assert item_300.width_inches == 5.0
    assert item_300.height_inches == 10.0
    assert item_300.is_print_quality is True

    # At 72 DPI: 1500 / 72 = 20.8333 inches
    item_72 = next(item for item in matrix if item.dpi == 72)
    assert item_72.is_print_quality is False


def test_calculate_required_pixels_a4():
    # A4 is 8.27 x 11.69 inches. At 300 DPI: ~2481 x 3507 pixels
    w_px, h_px = DPIManager.calculate_required_pixels(
        target_width=8.27,
        target_height=11.69,
        unit=DimensionUnit.INCHES,
        target_dpi=300
    )
    assert w_px == 2481
    assert h_px == 3507


def test_calculate_required_pixels_cm():
    # 10 cm at 300 DPI: 10 / 2.54 * 300 = 1181.1 -> 1181 px
    w_px, h_px = DPIManager.calculate_required_pixels(
        target_width=10.0,
        target_height=10.0,
        unit=DimensionUnit.CENTIMETERS,
        target_dpi=300
    )
    assert w_px == 1181
    assert h_px == 1181
