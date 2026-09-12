"""
Bleed Margin and Printer Marks Manager.
Adds standard industrial bleed margins (mirrored, clamped, or solid matte)
and draws hairline crop marks, center registration targets, CMYK density test swatches,
and job metadata slugs for commercial printing presses.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFont


class BleedManager:
    """
    Automates print-production bleed extension and prepress registration marks.
    Prevents white edges during blade guillotine trimming.
    """

    @staticmethod
    def mm_to_pixels(mm: float, dpi: int) -> int:
        """Converts millimeters to pixels at target DPI."""
        inches = mm / 25.4
        return max(1, int(round(inches * dpi)))

    def extend_bleed(
        self,
        image: Image.Image,
        bleed_px: int,
        fill_mode: str = "mirror",
        matte_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """
        Extends image boundaries by bleed_px on all 4 sides.
        fill_mode: 'mirror' (default, best for print), 'clamp' (replicate edge), or 'matte' (solid color).
        """
        if bleed_px <= 0:
            return image

        w, h = image.size

        if fill_mode == "mirror":
            # Industry standard: mirror edges to avoid blank white cutting slips
            arr = np.array(image)
            is_cmyk = (image.mode == "CMYK")
            
            # np.pad with 'reflect'
            if arr.ndim == 3:
                padded = np.pad(arr, ((bleed_px, bleed_px), (bleed_px, bleed_px), (0, 0)), mode="reflect")
            else:
                padded = np.pad(arr, ((bleed_px, bleed_px), (bleed_px, bleed_px)), mode="reflect")
            
            return Image.fromarray(padded, mode=image.mode)

        elif fill_mode == "clamp":
            arr = np.array(image)
            if arr.ndim == 3:
                padded = np.pad(arr, ((bleed_px, bleed_px), (bleed_px, bleed_px), (0, 0)), mode="edge")
            else:
                padded = np.pad(arr, ((bleed_px, bleed_px), (bleed_px, bleed_px)), mode="edge")
            return Image.fromarray(padded, mode=image.mode)

        else:
            # Solid color fill
            target_mode = image.mode
            color = (0, 0, 0, 0) if target_mode == "CMYK" else matte_color
            new_img = Image.new(target_mode, (w + 2 * bleed_px, h + 2 * bleed_px), color)
            new_img.paste(image, (bleed_px, bleed_px))
            return new_img

    def add_printer_marks(
        self,
        bleed_image: Image.Image,
        trim_w: int,
        trim_h: int,
        bleed_px: int,
        dpi: int,
        job_slug: Optional[str] = None
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Creates a prepress sheet placing the artwork inside a quiet zone
        surrounded by hairline crop marks, center registration targets,
        CMYK density calibration bars, and a job information slug.
        """
        # Marks margin: standard 6mm margin beyond bleed for marks
        marks_margin_px = self.mm_to_pixels(7.0, dpi)
        mark_len_px = self.mm_to_pixels(5.0, dpi)
        mark_gap_px = self.mm_to_pixels(1.5, dpi)

        full_w = trim_w + 2 * bleed_px + 2 * marks_margin_px
        full_h = trim_h + 2 * bleed_px + 2 * marks_margin_px

        mode = bleed_image.mode
        canvas_bg = (0, 0, 0, 0) if mode == "CMYK" else (255, 255, 255)
        sheet = Image.new(mode, (full_w, full_h), canvas_bg)

        # Paste bleed image at center
        origin_x = marks_margin_px
        origin_y = marks_margin_px
        sheet.paste(bleed_image, (origin_x, origin_y))

        # Trim boundary offsets on sheet
        trim_left = origin_x + bleed_px
        trim_top = origin_y + bleed_px
        trim_right = trim_left + trim_w
        trim_bottom = trim_top + trim_h

        draw = ImageDraw.Draw(sheet)
        mark_color = (255, 255, 255, 255) if mode == "CMYK" else (0, 0, 0)  # Registration black
        hairline = max(1, int(round(dpi / 300.0)))

        # 1. Corner Crop Marks (L-shaped ticks showing exact blade cut line)
        # Top-Left
        draw.line([(trim_left, trim_top - mark_gap_px), (trim_left, trim_top - mark_gap_px - mark_len_px)], fill=mark_color, width=hairline)
        draw.line([(trim_left - mark_gap_px, trim_top), (trim_left - mark_gap_px - mark_len_px, trim_top)], fill=mark_color, width=hairline)

        # Top-Right
        draw.line([(trim_right, trim_top - mark_gap_px), (trim_right, trim_top - mark_gap_px - mark_len_px)], fill=mark_color, width=hairline)
        draw.line([(trim_right + mark_gap_px, trim_top), (trim_right + mark_gap_px + mark_len_px, trim_top)], fill=mark_color, width=hairline)

        # Bottom-Left
        draw.line([(trim_left, trim_bottom + mark_gap_px), (trim_left, trim_bottom + mark_gap_px + mark_len_px)], fill=mark_color, width=hairline)
        draw.line([(trim_left - mark_gap_px, trim_bottom), (trim_left - mark_gap_px - mark_len_px, trim_bottom)], fill=mark_color, width=hairline)

        # Bottom-Right
        draw.line([(trim_right, trim_bottom + mark_gap_px), (trim_right, trim_bottom + mark_gap_px + mark_len_px)], fill=mark_color, width=hairline)
        draw.line([(trim_right + mark_gap_px, trim_bottom), (trim_right + mark_gap_px + mark_len_px, trim_bottom)], fill=mark_color, width=hairline)

        # 2. Center Registration Targets (Crosshairs + Circle for press alignment)
        target_r = max(4, int(round(mark_len_px * 0.4)))
        centers = [
            ((trim_left + trim_right) // 2, trim_top - mark_gap_px - mark_len_px // 2),        # Top
            ((trim_left + trim_right) // 2, trim_bottom + mark_gap_px + mark_len_px // 2),     # Bottom
            (trim_left - mark_gap_px - mark_len_px // 2, (trim_top + trim_bottom) // 2),        # Left
            (trim_right + mark_gap_px + mark_len_px // 2, (trim_top + trim_bottom) // 2)       # Right
        ]
        for cx, cy in centers:
            draw.ellipse([(cx - target_r, cy - target_r), (cx + target_r, cy + target_r)], outline=mark_color, width=hairline)
            draw.line([(cx - target_r - 3, cy), (cx + target_r + 3, cy)], fill=mark_color, width=hairline)
            draw.line([(cx, cy - target_r - 3), (cx, cy + target_r + 3)], fill=mark_color, width=hairline)

        # 3. CMYK Density Calibration Swatches (Top margin)
        if mode == "CMYK":
            swatch_w = max(10, self.mm_to_pixels(3.0, dpi))
            swatch_h = max(6, self.mm_to_pixels(2.0, dpi))
            swatch_y = 4
            swatches = [
                (255, 0, 0, 0),    # 100% C
                (0, 255, 0, 0),    # 100% M
                (0, 0, 255, 0),    # 100% Y
                (0, 0, 0, 255),    # 100% K
                (128, 0, 0, 0),    # 50% C
                (0, 128, 0, 0),    # 50% M
                (0, 0, 128, 0),    # 50% Y
                (0, 0, 0, 128),    # 50% K
            ]
            start_x = trim_left + (trim_w - len(swatches) * (swatch_w + 2)) // 2
            for i, col in enumerate(swatches):
                sx = start_x + i * (swatch_w + 2)
                draw.rectangle([sx, swatch_y, sx + swatch_w, swatch_y + swatch_h], fill=col, outline=(0, 0, 0, 255), width=1)

        # 4. Job Slug text in bottom margin
        slug_text = job_slug or f"MahaShankh Studio Pro • Trim: {trim_w}x{trim_h}px • Bleed: {bleed_px}px • {dpi} DPI"
        try:
            draw.text((trim_left, full_h - marks_margin_px + mark_gap_px + 2), slug_text, fill=mark_color)
        except Exception:
            pass

        report = {
            "trim_dimensions": [trim_w, trim_h],
            "bleed_pixels": bleed_px,
            "bleed_margin_mm": round((bleed_px / dpi) * 25.4, 2),
            "sheet_dimensions": [full_w, full_h],
            "crop_marks_added": True,
            "registration_targets_added": True,
            "trim_box": [trim_left, trim_top, trim_right, trim_bottom]
        }

        return sheet, report
