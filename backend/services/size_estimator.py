"""
Size and Memory Estimator Service.
Calculates exact uncompressed memory footprints and expected compressed disk sizes for raster files.
"""

from typing import Dict, Any
from ..models.schemas import (
    EstimateRequest,
    EstimateResponse,
    SupportedOutputFormat,
    TIFFCompressionOption,
    ColorModeOption
)
from .dpi_manager import DPIManager


class SizeEstimator:
    """Calculates memory footprints, disk size bounds, and print size estimates."""

    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Converts raw byte count into human-readable string (B, KB, MB, GB)."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @classmethod
    def estimate(cls, req: EstimateRequest) -> EstimateResponse:
        """Computes comprehensive memory, disk, and physical print size estimates."""
        out_w = int(round(req.width * req.upscale_factor))
        out_h = int(round(req.height * req.upscale_factor))
        total_pixels = out_w * out_h

        # Determine channels based on color mode
        channels = 3
        if req.color_mode == ColorModeOption.CMYK:
            channels = 4
        elif req.color_mode == ColorModeOption.GRAYSCALE:
            channels = 1

        bytes_per_sample = max(1, req.bit_depth // 8)
        uncompressed_bytes = total_pixels * channels * bytes_per_sample

        # Estimate disk range depending on target format & compression
        fmt = req.target_format
        if fmt == SupportedOutputFormat.BMP:
            # BMP is always uncompressed + 54 byte header
            min_disk = uncompressed_bytes + 54
            max_disk = uncompressed_bytes + 1024
        elif fmt == SupportedOutputFormat.TIFF:
            if req.compression in (TIFFCompressionOption.NONE, TIFFCompressionOption.RAW):
                min_disk = uncompressed_bytes
                max_disk = int(uncompressed_bytes * 1.01)
            elif req.compression == TIFFCompressionOption.LZW:
                # LZW typically compresses natural images 1.2x - 3x (or slight expansion for noisy data)
                min_disk = int(uncompressed_bytes * 0.35)
                max_disk = int(uncompressed_bytes * 0.95)
            elif req.compression == TIFFCompressionOption.DEFLATE:
                min_disk = int(uncompressed_bytes * 0.30)
                max_disk = int(uncompressed_bytes * 0.85)
            else:
                min_disk = int(uncompressed_bytes * 0.40)
                max_disk = int(uncompressed_bytes * 0.95)
        elif fmt == SupportedOutputFormat.PNG:
            # Lossless PNG
            min_disk = int(uncompressed_bytes * 0.20)
            max_disk = int(uncompressed_bytes * 0.70)
        elif fmt in (SupportedOutputFormat.JPEG, SupportedOutputFormat.JPG):
            # Lossy JPEG (typically 10:1 to 20:1 compression)
            min_disk = int(uncompressed_bytes * 0.05)
            max_disk = int(uncompressed_bytes * 0.25)
        else:
            min_disk = int(uncompressed_bytes * 0.5)
            max_disk = uncompressed_bytes

        physical_dims = DPIManager.calculate_physical_dimensions(out_w, out_h, req.dpi)

        # Safety check: Direct synchronous processing safe up to ~300MB uncompressed in memory
        is_safe = uncompressed_bytes <= (300 * 1024 * 1024)
        rec_mode = (
            "synchronous_direct" if is_safe
            else "asynchronous_background_worker_recommended"
        )

        return EstimateResponse(
            input_width=req.width,
            input_height=req.height,
            output_width=out_w,
            output_height=out_h,
            total_pixels=total_pixels,
            dpi=req.dpi,
            color_mode=req.color_mode.value,
            bit_depth=req.bit_depth,
            channels=channels,
            uncompressed_memory_bytes=uncompressed_bytes,
            uncompressed_memory_human=cls.format_bytes(uncompressed_bytes),
            estimated_disk_bytes_min=min_disk,
            estimated_disk_bytes_max=max_disk,
            estimated_disk_human_range=f"{cls.format_bytes(min_disk)} - {cls.format_bytes(max_disk)}",
            physical_print_size=physical_dims,
            is_safe_for_direct_processing=is_safe,
            recommended_processing_mode=rec_mode
        )
