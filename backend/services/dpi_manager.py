"""
DPI (Dots Per Inch) and Physical Dimension Management.

Mathematical definitions:
- Pixel Dimensions = Physical Size (Inches) * DPI
- Physical Size (Inches) = Pixel Dimensions / DPI
- Physical Size (cm) = Physical Size (Inches) * 2.54
- Physical Size (mm) = Physical Size (Inches) * 25.4

Explicit separation:
1. Pixel dimensions (Actual image data size)
2. Physical print dimensions (Calculated output at given DPI)
3. DPI metadata tags (Instructions embedded in file for RIP/printers)
"""

from typing import Tuple, List, Dict, Any, Optional
from ..models.schemas import PrintSizeEstimate, DimensionUnit


class DPIManager:
    """Manages DPI calculations, physical print dimension estimates, and target pixel scaling."""

    STANDARD_DPI_LEVELS = [72, 150, 300, 600]

    @staticmethod
    def calculate_physical_dimensions(
        pixel_width: int,
        pixel_height: int,
        dpi: float
    ) -> Dict[str, float]:
        """Calculates physical dimensions in inches, cm, and mm for a given pixel size and DPI."""
        if dpi <= 0:
            dpi = 72.0

        width_in = pixel_width / dpi
        height_in = pixel_height / dpi
        width_cm = width_in * 2.54
        height_cm = height_in * 2.54
        width_mm = width_in * 25.4
        height_mm = height_in * 25.4

        return {
            "width_inches": round(width_in, 4),
            "height_inches": round(height_in, 4),
            "width_cm": round(width_cm, 3),
            "height_cm": round(height_cm, 3),
            "width_mm": round(width_mm, 2),
            "height_mm": round(height_mm, 2),
            "dpi": dpi
        }

    @classmethod
    def generate_print_matrix(
        cls,
        pixel_width: int,
        pixel_height: int,
        source_dpi: Optional[float] = None
    ) -> List[PrintSizeEstimate]:
        """Generates a comparison matrix of physical print dimensions across standard DPI levels."""
        dpis_to_test = list(cls.STANDARD_DPI_LEVELS)
        if source_dpi and int(source_dpi) not in dpis_to_test and source_dpi > 0:
            dpis_to_test.append(int(source_dpi))
            dpis_to_test.sort()

        results = []
        for dpi in dpis_to_test:
            dims = cls.calculate_physical_dimensions(pixel_width, pixel_height, dpi)
            results.append(
                PrintSizeEstimate(
                    dpi=dpi,
                    width_inches=dims["width_inches"],
                    height_inches=dims["height_inches"],
                    width_cm=dims["width_cm"],
                    height_cm=dims["height_cm"],
                    width_mm=dims["width_mm"],
                    height_mm=dims["height_mm"],
                    is_print_quality=(dpi >= 300)
                )
            )
        return results

    @staticmethod
    def calculate_required_pixels(
        target_width: float,
        target_height: Optional[float],
        unit: DimensionUnit,
        target_dpi: int,
        original_aspect_ratio: Optional[float] = None
    ) -> Tuple[int, int]:
        """
        Calculates required pixel dimensions when a user specifies a target physical print size.
        Example: A4 (8.27 in x 11.69 in) at 300 DPI -> 2481 x 3507 pixels.
        """
        # Convert width to inches
        if unit == DimensionUnit.INCHES:
            width_inches = target_width
        elif unit == DimensionUnit.CENTIMETERS:
            width_inches = target_width / 2.54
        elif unit == DimensionUnit.MILLIMETERS:
            width_inches = target_width / 25.4
        else:  # Pixels
            width_inches = target_width / target_dpi

        calc_pixel_width = int(round(width_inches * target_dpi))

        if target_height is not None:
            if unit == DimensionUnit.INCHES:
                height_inches = target_height
            elif unit == DimensionUnit.CENTIMETERS:
                height_inches = target_height / 2.54
            elif unit == DimensionUnit.MILLIMETERS:
                height_inches = target_height / 25.4
            else:
                height_inches = target_height / target_dpi
            calc_pixel_height = int(round(height_inches * target_dpi))
        elif original_aspect_ratio and original_aspect_ratio > 0:
            # Maintain aspect ratio
            calc_pixel_height = int(round(calc_pixel_width / original_aspect_ratio))
        else:
            calc_pixel_height = calc_pixel_width

        return max(1, calc_pixel_width), max(1, calc_pixel_height)
