"""
Image Conversion & Export Endpoint.
Accepts raster images and converts them deterministically to TIFF, BMP, PNG, or JPEG.
"""

import os
import json
import base64
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Body, BackgroundTasks, Response, Request
from fastapi.responses import FileResponse
from PIL import Image
import io

try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

from ..models.schemas import (
    SupportedOutputFormat,
    ColorModeOption,
    TIFFCompressionOption,
    UpscaleAlgorithm,
    DimensionUnit,
    ConversionOptions,
    ConversionRequest,
    ConversionResponse,
    QualityReport
)
from ..services.image_validator import ImageValidator, ImageValidationError, DecompressionBombError
from ..services.image_loader import ImageLoader
from ..services.converter import ImageConverter

router = APIRouter()
validator = ImageValidator()
loader = ImageLoader(validator)
converter = ImageConverter()


def cleanup_temp_file(file_path: str):
    """Background task to delete temporary exported file after download streaming completes."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"[WARN] Failed to cleanup temp file {file_path}: {e}")


@router.post("/convert")
async def convert_image(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    output_format: SupportedOutputFormat = Form(SupportedOutputFormat.TIFF),
    dpi: int = Form(300),
    color_mode: ColorModeOption = Form(ColorModeOption.PRESERVE),
    tiff_compression: TIFFCompressionOption = Form(TIFFCompressionOption.LZW),
    jpeg_quality: int = Form(95),
    png_compression_level: int = Form(6),
    upscale_factor: int = Form(1),
    upscale_algorithm: UpscaleAlgorithm = Form(UpscaleAlgorithm.LANCZOS),
    target_physical_width: Optional[float] = Form(None),
    target_physical_height: Optional[float] = Form(None),
    physical_unit: DimensionUnit = Form(DimensionUnit.INCHES),
    add_bleed: bool = Form(False),
    bleed_margin_mm: float = Form(3.0),
    bleed_fill_mode: str = Form("mirror"),
    add_crop_marks: bool = Form(False),
    return_json: bool = Form(False),
    remove_background: bool = Form(False)
):
    """
    Main conversion endpoint.
    Accepts an image file (or base64/URL via JSON), processes it according to production specifications,
    and returns either a streaming file download or a structured JSON response.
    """
    try:
        # Check content type
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Parse JSON body manually
            body_bytes = await request.body()
            if not body_bytes:
                raise HTTPException(status_code=400, detail="Empty JSON body")
            
            payload = json.loads(body_bytes)
            json_request = ConversionRequest(**payload)
            
            if json_request.image_base64:
                loaded = loader.load_from_base64(json_request.image_base64)
            elif json_request.image_url:
                loaded = loader.load_from_url(json_request.image_url)
            else:
                raise HTTPException(status_code=400, detail="Missing image data in JSON request.")
            options = json_request.options
            wants_json = True
            
        else:
            # Form data mode
            if file is not None:
                raw_bytes = await file.read()
                loaded = loader.load_from_bytes(raw_bytes, filename=file.filename)
                options = ConversionOptions(
                    output_format=output_format,
                    dpi=dpi,
                    color_mode=color_mode,
                    tiff_compression=tiff_compression,
                    jpeg_quality=jpeg_quality,
                    png_compression_level=png_compression_level,
                    upscale_factor=upscale_factor,
                    upscale_algorithm=upscale_algorithm,
                    target_physical_width=target_physical_width,
                    target_physical_height=target_physical_height,
                    physical_unit=physical_unit,
                    add_bleed=add_bleed,
                    bleed_margin_mm=bleed_margin_mm,
                    bleed_fill_mode=bleed_fill_mode,
                    add_crop_marks=add_crop_marks
                )
                wants_json = return_json
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Please provide an image file via multipart form or a JSON body with 'image_base64'/'image_url'."
                )

        # Apply background removal if requested
        if remove_background:
            if not HAS_REMBG:
                raise HTTPException(status_code=500, detail="Background removal (rembg) is not installed on the server.")
            
            # Use ultra-lightweight model u2netp (only ~4.7 MB instead of 1GB)
            from rembg import new_session
            session = new_session("u2netp")
            
            # rembg requires PIL image
            input_pil = loaded.image
            
            # Apply removal with lightweight session
            output_pil = remove(input_pil, session=session)
            
            # Update the loaded image
            loaded.image = output_pil
            
            # Change format to PNG if original was JPEG/BMP to preserve transparency
            if options.output_format in [SupportedOutputFormat.JPEG, SupportedOutputFormat.BMP]:
                options.output_format = SupportedOutputFormat.PNG

        # 2. Run deterministic conversion pipeline
        out_file_path, quality_report = converter.process(loaded, options)
        loaded.close()

        # Build clean download filename
        base_name = os.path.splitext(loaded.metadata.get("filename", "converted_design"))[0]
        base_name = ImageValidator.sanitize_filename(base_name)
        ext = options.output_format.value.lower()
        if ext == "jpeg":
            ext = "jpg"
        out_filename = f"{base_name}_{options.dpi}dpi_{options.color_mode.value.lower()}.{ext}"

        # 3. Return JSON if requested
        if wants_json:
            # Read converted file to base64 if small enough (< 100 MB)
            file_size = os.path.getsize(out_file_path)
            b64_output = None
            if file_size <= 100 * 1024 * 1024:
                with open(out_file_path, "rb") as f:
                    b64_output = base64.b64encode(f.read()).decode("utf-8")

            background_tasks.add_task(cleanup_temp_file, out_file_path)

            return ConversionResponse(
                success=True,
                filename=out_filename,
                output_format=options.output_format,
                quality_report=quality_report,
                image_base64=b64_output
            )

        # 4. Otherwise stream direct file download
        media_type_map = {
            SupportedOutputFormat.TIFF: "image/tiff",
            SupportedOutputFormat.BMP: "image/bmp",
            SupportedOutputFormat.PNG: "image/png",
            SupportedOutputFormat.JPEG: "image/jpeg",
            SupportedOutputFormat.JPG: "image/jpeg",
        }
        media_type = media_type_map.get(options.output_format, "application/octet-stream")

        # Encode quality report into custom response header
        report_json = quality_report.model_dump_json()
        report_header_b64 = base64.b64encode(report_json.encode("utf-8")).decode("utf-8")

        background_tasks.add_task(cleanup_temp_file, out_file_path)

        return FileResponse(
            path=out_file_path,
            filename=out_filename,
            media_type=media_type,
            headers={
                "X-Quality-Report-B64": report_header_b64,
                "X-DPI": str(options.dpi),
                "X-Color-Mode": quality_report.output.mode,
                "X-Physical-Width-Inches": str(quality_report.output.physical_width_in),
                "X-Physical-Height-Inches": str(quality_report.output.physical_height_in),
                "Access-Control-Expose-Headers": "X-Quality-Report-B64, X-DPI, X-Color-Mode, Content-Disposition"
            }
        )

    except DecompressionBombError as dbe:
        raise HTTPException(status_code=400, detail=f"Decompression Bomb: {dbe.message}")
    except ImageValidationError as ive:
        raise HTTPException(status_code=422, detail=ive.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
