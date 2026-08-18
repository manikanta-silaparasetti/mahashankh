"""
Master Converter Pipeline Service.
Coordinates: Input Validation -> Loading -> Upscaling -> Resizing -> Color Management -> Export -> Quality Check.
"""

import time
import tracemalloc
from typing import Tuple, Dict, Any, Optional
from PIL import Image

from ..models.schemas import (
    ConversionOptions,
    QualityReport,
    InputImageMetadata,
    ProcessingMetadata,
    OutputImageMetadata,
    SupportedOutputFormat,
    ColorModeOption,
    UpscaleAlgorithm
)
from .image_validator import ImageValidator
from .image_loader import ImageLoader, LoadedImage
from .dpi_manager import DPIManager
from .color_manager import ColorManager
from .size_estimator import SizeEstimator
from .tiff_exporter import TIFFExporter
from .bmp_exporter import BMPExporter
from .png_jpeg_exporter import PNGJPEGExporter
from .quality_checker import QualityChecker
from .upscaler.pillow import PillowUpscaler
from .upscaler.realesrgan import RealESRGANUpscaler


class ImageConverter:
    """Master pipeline orchestrating deterministic image conversions and quality verification."""

    def __init__(self):
        self.validator = ImageValidator()
        self.loader = ImageLoader(self.validator)
        self.dpi_manager = DPIManager()
        self.color_manager = ColorManager()
        self.tiff_exporter = TIFFExporter()
        self.bmp_exporter = BMPExporter()
        self.png_jpeg_exporter = PNGJPEGExporter()
        self.quality_checker = QualityChecker()
        self.pillow_upscaler = PillowUpscaler()
        self.realesrgan_upscaler = RealESRGANUpscaler()

    def process(
        self,
        loaded_image: LoadedImage,
        options: ConversionOptions,
        output_file_path: Optional[str] = None
    ) -> Tuple[str, QualityReport]:
        """
        Executes the full production image processing pipeline.
        Returns the output file path on disk and a comprehensive QualityReport.
        """
        start_time = time.perf_counter()
        tracemalloc.start()

        img: Image.Image = loaded_image.image
        input_meta = loaded_image.metadata
        resizing_applied = None

        # 1. Capture Input Metadata
        in_w, in_h = img.size
        input_report = InputImageMetadata(
            format=input_meta["detected_format"],
            mime_type=input_meta["mime_type"],
            width=in_w,
            height=in_h,
            mode=input_meta["mode"],
            dpi=input_meta["dpi"],
            size_bytes=input_meta["file_size_bytes"],
            channels=input_meta["channels"],
            has_alpha=input_meta["has_alpha"],
            icc_profile=input_meta["icc_profile_name"]
        )

        # 2. Optional Resolution Upscaling
        upscale_factor = options.upscale_factor
        upscale_str = f"{upscale_factor}x" if upscale_factor > 1 else "1x"
        upscaler_name = "none"

        if upscale_factor > 1:
            if options.upscale_algorithm == UpscaleAlgorithm.REAL_ESRGAN:
                img, up_meta = self.realesrgan_upscaler.upscale(img, upscale_factor)
                upscaler_name = up_meta.get("upscaler", "Real-ESRGAN")
            else:
                img, up_meta = self.pillow_upscaler.upscale(img, upscale_factor)
                upscaler_name = up_meta.get("upscaler", "Pillow-Lanczos")

        # 3. Optional Physical Target Dimension Resizing
        if options.target_physical_width is not None or options.target_physical_height is not None:
            aspect = (img.size[0] / img.size[1]) if img.size[1] > 0 else 1.0
            req_w, req_h = self.dpi_manager.calculate_required_pixels(
                target_width=options.target_physical_width or (options.target_physical_height * aspect),
                target_height=options.target_physical_height,
                unit=options.physical_unit,
                target_dpi=options.dpi,
                original_aspect_ratio=aspect
            )
            if (req_w, req_h) != img.size:
                resizing_applied = f"Resized to target physical size: {req_w}x{req_h} px ({options.dpi} DPI)"
                img = img.resize((req_w, req_h), resample=Image.Resampling.LANCZOS)

        # 4. Color Management & Alpha Handling
        target_color = options.color_mode
        img, color_report = self.color_manager.convert_color_mode(
            image=img,
            target_mode=target_color,
            custom_icc_profile_path=options.custom_icc_profile_path,
            matte_color=options.matte_color
        )

        # 5. Export to Target Raster Format
        target_fmt = options.output_format
        target_dpi = options.dpi
        icc_bytes = loaded_image.raw_bytes if loaded_image.metadata["icc_profile_present"] else None

        if target_fmt == SupportedOutputFormat.TIFF:
            out_path, export_metrics = self.tiff_exporter.export(
                image=img,
                output_path=output_file_path,
                dpi=target_dpi,
                compression=options.tiff_compression,
                icc_profile_bytes=icc_bytes
            )
            compression_str = options.tiff_compression.value
        elif target_fmt == SupportedOutputFormat.BMP:
            out_path, export_metrics = self.bmp_exporter.export(
                image=img,
                output_path=output_file_path,
                dpi=target_dpi
            )
            compression_str = "uncompressed"
        elif target_fmt == SupportedOutputFormat.PNG:
            out_path, export_metrics = self.png_jpeg_exporter.export_png(
                image=img,
                output_path=output_file_path,
                dpi=target_dpi,
                compress_level=options.png_compression_level,
                icc_profile_bytes=icc_bytes
            )
            compression_str = f"png_deflate_{options.png_compression_level}"
        elif target_fmt in (SupportedOutputFormat.JPEG, SupportedOutputFormat.JPG):
            out_path, export_metrics = self.png_jpeg_exporter.export_jpeg(
                image=img,
                output_path=output_file_path,
                dpi=target_dpi,
                quality=options.jpeg_quality,
                icc_profile_bytes=icc_bytes,
                matte_color=options.matte_color
            )
            compression_str = f"jpeg_q{options.jpeg_quality}"
        else:
            raise ValueError(f"Unsupported output format: {target_fmt}")

        # 6. Quality Assessment on Output File
        quality_assessment = self.quality_checker.verify_output_file(
            file_path=out_path,
            expected_format=target_fmt,
            expected_dpi=target_dpi,
            expected_mode=color_report["final_mode"]
        )

        # 7. Compute Timing & Peak Memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 8. Compute Output Metadata
        out_w, out_h = export_metrics["width"], export_metrics["height"]
        phys_dims = self.dpi_manager.calculate_physical_dimensions(out_w, out_h, target_dpi)

        output_report = OutputImageMetadata(
            format=export_metrics["format"],
            width=out_w,
            height=out_h,
            mode=export_metrics["mode"],
            dpi=export_metrics["dpi"],
            compression=compression_str,
            size_bytes=export_metrics["size_bytes"],
            size_human=SizeEstimator.format_bytes(export_metrics["size_bytes"]),
            bit_depth=export_metrics.get("bit_depth", 8),
            channels=export_metrics.get("channels", len(export_metrics["mode"])),
            physical_width_in=phys_dims["width_inches"],
            physical_height_in=phys_dims["height_inches"],
            physical_width_cm=phys_dims["width_cm"],
            physical_height_cm=phys_dims["height_cm"]
        )

        processing_report = ProcessingMetadata(
            upscale=upscale_str,
            upscaler=upscaler_name,
            color_conversion=f"{color_report['source_mode']}->{color_report['final_mode']} ({color_report.get('conversion_method', 'direct')})",
            icc_profile_used=color_report.get("icc_profile_used"),
            target_dpi=target_dpi,
            resizing_applied=resizing_applied,
            compression=compression_str,
            alpha_flattened=color_report.get("alpha_flattened", False),
            processing_time_ms=round(elapsed_ms, 2),
            peak_memory_mb=round(peak_mem / (1024 * 1024), 2)
        )

        full_quality_report = QualityReport(
            input=input_report,
            processing=processing_report,
            output=output_report,
            quality=quality_assessment
        )

        return out_path, full_quality_report
