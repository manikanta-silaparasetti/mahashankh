"""
TIFF Export Service for high-precision print production.
Supports configurable DPI metadata, RGB/CMYK color spaces, LZW / Deflate / PackBits / Uncompressed encoding,
and ICC color profile preservation.
"""

import os
import tempfile
from typing import Tuple, Dict, Any, Optional
from PIL import Image
from ..models.schemas import TIFFCompressionOption


class TIFFExporter:
    """Exports images to high-grade production TIFF format with full metadata control."""

    COMPRESSION_MAP = {
        TIFFCompressionOption.NONE: "raw",
        TIFFCompressionOption.RAW: "raw",
        TIFFCompressionOption.LZW: "tiff_lzw",
        TIFFCompressionOption.DEFLATE: "tiff_deflate",
        TIFFCompressionOption.PACKBITS: "packbits",
    }

    def export(
        self,
        image: Image.Image,
        output_path: Optional[str] = None,
        dpi: int = 300,
        compression: TIFFCompressionOption = TIFFCompressionOption.LZW,
        icc_profile_bytes: Optional[bytes] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Exports the PIL image to a production TIFF file.
        Returns the output file path and detailed export metrics.
        """
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".tiff", prefix="mahasankh_tiff_")
            os.close(fd)

        width, height = image.size
        mode = image.mode
        dpi_tuple = (float(dpi), float(dpi))

        # Map compression option
        pil_compression = self.COMPRESSION_MAP.get(compression, "tiff_lzw")
        if pil_compression == "none":
            pil_compression = "raw"

        save_kwargs = {
            "format": "TIFF",
            "dpi": dpi_tuple,
            "compression": pil_compression
        }

        if icc_profile_bytes:
            save_kwargs["icc_profile"] = icc_profile_bytes

        # Save to disk
        image.save(output_path, **save_kwargs)

        file_size = os.path.getsize(output_path)

        # Calculate bit depth and channels
        channels = len(mode)
        bit_depth = 8
        if mode in ("I;16", "RGB;16"):
            bit_depth = 16
        elif mode in ("I", "F"):
            bit_depth = 32

        uncompressed_raw_bytes = width * height * channels * (bit_depth // 8)
        compression_ratio = (
            round(uncompressed_raw_bytes / max(1, file_size), 2)
            if file_size > 0 else 1.0
        )

        metrics = {
            "format": "TIFF",
            "width": width,
            "height": height,
            "mode": mode,
            "dpi": dpi_tuple,
            "compression": compression.value,
            "pil_compression_tag": pil_compression,
            "size_bytes": file_size,
            "bit_depth": bit_depth,
            "channels": channels,
            "uncompressed_bytes": uncompressed_raw_bytes,
            "compression_ratio": f"{compression_ratio}:1",
            "icc_embedded": bool(icc_profile_bytes),
            "file_path": output_path
        }

        return output_path, metrics
