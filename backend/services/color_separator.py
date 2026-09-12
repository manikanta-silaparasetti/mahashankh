"""
CMYK Color Separation Plate Generator.
Splits multi-color designs into 4 individual high-contrast separation plates
(Cyan, Magenta, Yellow, Black) with corner registration crosshairs and plate slugs.
Ready for screen printing silk burning and offset litho plate exposure.
"""

import os
import io
import zipfile
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image, ImageDraw

from .color_manager import ColorManager
from .bleed_manager import BleedManager
from ..models.schemas import ColorModeOption


class ColorSeparator:
    """Generates production-grade C, M, Y, K separation plates for screen and textile printing."""

    def __init__(self):
        self.color_manager = ColorManager()
        self.bleed_manager = BleedManager()

    def separate_channels(
        self,
        image: Image.Image,
        dpi: int = 300,
        job_title: str = "Artwork"
    ) -> Dict[str, Image.Image]:
        """
        Converts the image to CMYK and extracts individual plates.
        Returns dict with keys 'cyan', 'magenta', 'yellow', 'black', and 'composite'.
        Each plate is rendered in film-positive mode (dense black ink on white film).
        """
        # Ensure image is in CMYK
        if image.mode != "CMYK":
            cmyk_img, _ = self.color_manager.convert_color_mode(image, ColorModeOption.CMYK)
        else:
            cmyk_img = image

        c, m, y, k = cmyk_img.split()
        plates_raw = {
            "Cyan": c,
            "Magenta": m,
            "Yellow": y,
            "Black": k
        }

        w, h = cmyk_img.size
        border_px = max(20, int(round(dpi * 0.25)))  # ~6mm border for registration marks
        plate_w = w + 2 * border_px
        plate_h = h + 2 * border_px

        processed_plates = {}

        for name, channel in plates_raw.items():
            # In CMYK channel: 0 = 0% ink, 255 = 100% ink.
            # In film positive transparency for burning screens:
            # 100% ink must be opaque black (0 in Grayscale), 0% ink must be transparent/white (255 in Grayscale).
            channel_arr = np.array(channel)
            film_arr = 255 - channel_arr  # Invert: dense ink is black
            film_img = Image.fromarray(film_arr, mode="L")

            # Place on bordered plate sheet
            plate_sheet = Image.new("L", (plate_w, plate_h), color=255)
            plate_sheet.paste(film_img, (border_px, border_px))

            # Draw registration crosshairs in all 4 corners
            draw = ImageDraw.Draw(plate_sheet)
            target_r = max(6, int(round(dpi * 0.04)))
            hairline = max(1, int(round(dpi / 300.0)))

            corner_centers = [
                (border_px // 2, border_px // 2),
                (plate_w - border_px // 2, border_px // 2),
                (border_px // 2, plate_h - border_px // 2),
                (plate_w - border_px // 2, plate_h - border_px // 2)
            ]
            for cx, cy in corner_centers:
                draw.ellipse([(cx - target_r, cy - target_r), (cx + target_r, cy + target_r)], outline=0, width=hairline)
                draw.line([(cx - target_r - 4, cy), (cx + target_r + 4, cy)], fill=0, width=hairline)
                draw.line([(cx, cy - target_r - 4), (cx, cy + target_r + 4)], fill=0, width=hairline)

            # Draw Plate Title Slug at top and bottom
            slug = f"MahaShankh Plate • {name.upper()} CHANNEL • {job_title} • {dpi} DPI"
            try:
                draw.text((border_px, border_px // 3), slug, fill=0)
            except Exception:
                pass

            processed_plates[name.lower()] = plate_sheet

        return processed_plates

    def generate_separation_bundle_zip(
        self,
        image: Image.Image,
        dpi: int = 300,
        job_title: str = "Artwork"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Creates all 4 separation plates, saves each as a high-density TIFF with DPI metadata,
        and packages them into a download-ready in-memory ZIP archive.
        """
        plates = self.separate_channels(image, dpi=dpi, job_title=job_title)

        zip_buffer = io.BytesIO()
        channel_stats = {}

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for ch_name, plate_img in plates.items():
                plate_buf = io.BytesIO()
                plate_img.save(
                    plate_buf,
                    format="TIFF",
                    dpi=(dpi, dpi),
                    compression="tiff_lzw"
                )
                filename = f"{job_title}_{ch_name}_plate_{dpi}dpi.tiff"
                zf.writestr(filename, plate_buf.getvalue())

                # Channel ink coverage metrics
                np_p = np.array(plate_img)
                ink_coverage_pct = round(float((255 - np_p).mean() / 255.0) * 100, 2)
                channel_stats[ch_name] = {
                    "filename": filename,
                    "ink_coverage_percent": ink_coverage_pct,
                    "resolution": list(plate_img.size)
                }

            # Add RGB preview
            preview_buf = io.BytesIO()
            image.convert("RGB").save(preview_buf, format="PNG")
            zf.writestr(f"{job_title}_original_preview.png", preview_buf.getvalue())

        zip_bytes = zip_buffer.getvalue()
        metadata = {
            "job_title": job_title,
            "dpi": dpi,
            "plates_generated": list(plates.keys()),
            "channel_stats": channel_stats,
            "zip_size_bytes": len(zip_bytes),
            "suitable_for_screen_printing": True
        }

        return zip_bytes, metadata
