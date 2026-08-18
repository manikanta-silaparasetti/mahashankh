"""
PNG and JPEG Exporter Service.
Lossless PNG with alpha support, and JPEG with configurable quality & alpha flattening.
"""

import os
import tempfile
from typing import Tuple, Dict, Any, Optional
from PIL import Image


class PNGJPEGExporter:
    """Exports images to PNG or JPEG format with full parameter control."""

    def export_png(
        self,
        image: Image.Image,
        output_path: Optional[str] = None,
        dpi: int = 300,
        compress_level: int = 6,
        icc_profile_bytes: Optional[bytes] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Exports lossless PNG with optional alpha channel and DPI tags."""
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".png", prefix="mahasankh_png_")
            os.close(fd)

        # PNG supports L, LA, P, RGB, RGBA. Convert CMYK to RGB
        if image.mode == "CMYK":
            image = image.convert("RGB")

        width, height = image.size
        dpi_tuple = (float(dpi), float(dpi))

        save_kwargs = {
            "format": "PNG",
            "dpi": dpi_tuple,
            "compress_level": max(0, min(9, compress_level)),
            "optimize": True
        }
        if icc_profile_bytes:
            save_kwargs["icc_profile"] = icc_profile_bytes

        image.save(output_path, **save_kwargs)

        file_size = os.path.getsize(output_path)
        metrics = {
            "format": "PNG",
            "width": width,
            "height": height,
            "mode": image.mode,
            "dpi": dpi_tuple,
            "compression": f"deflate_level_{compress_level}",
            "size_bytes": file_size,
            "bit_depth": 8,
            "channels": len(image.mode),
            "file_path": output_path
        }
        return output_path, metrics

    def export_jpeg(
        self,
        image: Image.Image,
        output_path: Optional[str] = None,
        dpi: int = 300,
        quality: int = 95,
        icc_profile_bytes: Optional[bytes] = None,
        matte_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Tuple[str, Dict[str, Any]]:
        """Exports JPEG with configurable quality and proper alpha flattening."""
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".jpg", prefix="mahasankh_jpg_")
            os.close(fd)

        # Flatten alpha if present (JPEG has no alpha channel)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
            bg = Image.new("RGBA", image.size, matte_color + (255,))
            image = Image.alpha_composite(bg, image).convert("RGB")
        elif image.mode == "CMYK":
            # CMYK JPEG is technically supported in print, but standard web/general JPEG is RGB
            # If user chose JPEG output, convert to RGB for universal viewer safety
            image = image.convert("RGB")
        elif image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        width, height = image.size
        dpi_tuple = (float(dpi), float(dpi))

        save_kwargs = {
            "format": "JPEG",
            "dpi": dpi_tuple,
            "quality": max(1, min(100, quality)),
            "optimize": True,
            "progressive": True
        }
        if icc_profile_bytes:
            save_kwargs["icc_profile"] = icc_profile_bytes

        image.save(output_path, **save_kwargs)

        file_size = os.path.getsize(output_path)
        metrics = {
            "format": "JPEG",
            "width": width,
            "height": height,
            "mode": image.mode,
            "dpi": dpi_tuple,
            "compression": f"dct_quality_{quality}",
            "size_bytes": file_size,
            "bit_depth": 8,
            "channels": len(image.mode),
            "file_path": output_path
        }
        return output_path, metrics
