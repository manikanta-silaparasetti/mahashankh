"""
BMP Export Service for legacy manufacturing and print workflows.
BMP is uncompressed raster data often required by specific downstream textile machinery (e.g. jacquard looms),
CNC laser engraving tools, and older RIP controllers.
"""

import os
import tempfile
from typing import Tuple, Dict, Any, Optional
from PIL import Image


class BMPExporter:
    """Exports images to Windows Bitmap (BMP) format."""

    def export(
        self,
        image: Image.Image,
        output_path: Optional[str] = None,
        dpi: int = 300
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Exports the PIL image to standard BMP format.
        Flattens alpha to RGB and normalizes CMYK to RGB if needed (standard BMP requires RGB/L).
        """
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".bmp", prefix="mahasankh_bmp_")
            os.close(fd)

        # Standard BMP requires RGB, L, or 1
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            # Flatten alpha
            image = image.convert("RGBA")
            bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
            image = Image.alpha_composite(bg, image).convert("RGB")
        elif image.mode == "CMYK":
            image = image.convert("RGB")
        elif image.mode not in ("RGB", "L", "1"):
            image = image.convert("RGB")

        width, height = image.size
        dpi_tuple = (float(dpi), float(dpi))

        image.save(output_path, format="BMP", dpi=dpi_tuple)

        file_size = os.path.getsize(output_path)
        channels = len(image.mode)

        metrics = {
            "format": "BMP",
            "width": width,
            "height": height,
            "mode": image.mode,
            "dpi": dpi_tuple,
            "compression": "none_uncompressed_bitmap",
            "size_bytes": file_size,
            "bit_depth": 8,
            "channels": channels,
            "note": "Standard uncompressed BMP format exported for downstream manufacturing / RIP compatibility.",
            "file_path": output_path
        }

        return output_path, metrics
