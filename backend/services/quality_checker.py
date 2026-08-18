"""
Quality Checker Service.
Validates the generated output file independently, ensuring correct headers, DPI tags,
color space verification, and print-suitability assessment.
"""

import os
from typing import Dict, Any, Tuple
from PIL import Image
from ..models.schemas import QualityAssessment, SupportedOutputFormat


class QualityChecker:
    """Verifies output file integrity, metadata accuracy, and print-readiness."""

    @staticmethod
    def verify_output_file(
        file_path: str,
        expected_format: SupportedOutputFormat,
        expected_dpi: int,
        expected_mode: str
    ) -> QualityAssessment:
        """
        Re-opens the exported file from disk, inspects actual tags and returns quality evaluation.
        """
        notes = []
        warnings = []
        resolution_ok = True
        color_profile_ok = True
        format_valid = True

        if not os.path.exists(file_path):
            return QualityAssessment(
                resolution_ok=False,
                color_profile_ok=False,
                format_valid=False,
                suitable_for_commercial_print=False,
                notes=["Output file was not found on disk."],
                warnings=["File creation failed."]
            )

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return QualityAssessment(
                resolution_ok=False,
                color_profile_ok=False,
                format_valid=False,
                suitable_for_commercial_print=False,
                notes=["Exported file is 0 bytes."],
                warnings=["Corrupted 0-byte output."]
            )

        try:
            with Image.open(file_path) as img:
                actual_format = img.format
                actual_mode = img.mode
                actual_dpi = (72.0, 72.0)
                if "dpi" in img.info:
                    dpi_info = img.info["dpi"]
                    if isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
                        actual_dpi = (float(dpi_info[0]), float(dpi_info[1]))

                # 1. Format validation
                expected_fmt_str = expected_format.value.upper()
                if expected_fmt_str in ("JPEG", "JPG"):
                    format_valid = actual_format in ("JPEG", "JPG")
                else:
                    format_valid = (actual_format == expected_fmt_str)

                if not format_valid:
                    warnings.append(f"Format mismatch: expected {expected_fmt_str}, detected {actual_format}")
                else:
                    notes.append(f"Format verified: {actual_format}")

                # 2. DPI validation
                if expected_format in (SupportedOutputFormat.TIFF, SupportedOutputFormat.PNG, SupportedOutputFormat.JPEG):
                    if abs(actual_dpi[0] - expected_dpi) > 1.0:
                        warnings.append(
                            f"Embedded DPI ({actual_dpi[0]:.1f}) differs from requested target DPI ({expected_dpi})"
                        )
                        resolution_ok = False
                    else:
                        notes.append(f"DPI metadata verified at {int(actual_dpi[0])} DPI")
                elif expected_format == SupportedOutputFormat.BMP:
                    notes.append("BMP format: Note that some legacy BMP decoders do not read embedded DPI tags.")

                # 3. Color profile & mode validation
                if expected_mode in ("CMYK", "RGB", "L"):
                    if actual_mode != expected_mode:
                        warnings.append(f"Color mode mismatch: expected {expected_mode}, got {actual_mode}")
                        color_profile_ok = False
                    else:
                        notes.append(f"Color space verified: {actual_mode}")

                # 4. Print suitability check
                is_print_suitable = (expected_dpi >= 300) and resolution_ok and format_valid
                if expected_dpi < 300:
                    warnings.append(
                        f"Target DPI is {expected_dpi}. Standard commercial print presses (offset, textile, flex) recommend 300+ DPI."
                    )
                else:
                    notes.append("High-resolution print standard satisfied (>= 300 DPI).")

                return QualityAssessment(
                    resolution_ok=resolution_ok,
                    color_profile_ok=color_profile_ok,
                    format_valid=format_valid,
                    suitable_for_commercial_print=is_print_suitable,
                    notes=notes,
                    warnings=warnings
                )

        except Exception as e:
            return QualityAssessment(
                resolution_ok=False,
                color_profile_ok=False,
                format_valid=False,
                suitable_for_commercial_print=False,
                notes=[f"Failed to inspect output file: {str(e)}"],
                warnings=["Output verification encountered an exception."]
            )
