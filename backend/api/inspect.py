"""
Image inspection endpoint.
Inspects headers, dimensions, bit depth, color mode, DPI, ICC profile, and returns physical print estimates.
"""

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Body
from pydantic import BaseModel

from ..models.schemas import InspectResponse
from ..services.image_validator import ImageValidator, ImageValidationError, DecompressionBombError
from ..services.image_loader import ImageLoader
from ..services.dpi_manager import DPIManager
from ..services.size_estimator import SizeEstimator

router = APIRouter()
validator = ImageValidator()
loader = ImageLoader(validator)


class InspectJSONRequest(BaseModel):
    image_base64: Optional[str] = None
    image_url: Optional[str] = None


@router.post("/inspect", response_model=InspectResponse)
async def inspect_image(
    file: Optional[UploadFile] = File(None),
    payload: Optional[InspectJSONRequest] = Body(None)
):
    """
    Inspects an uploaded image file, base64 payload, or image URL.
    Returns technical raster metadata and physical print dimension matrices without full in-memory rasterization.
    """
    try:
        if file is not None:
            raw_bytes = await file.read()
            loaded = loader.load_from_bytes(raw_bytes, filename=file.filename)
        elif payload and payload.image_base64:
            loaded = loader.load_from_base64(payload.image_base64)
        elif payload and payload.image_url:
            loaded = loader.load_from_url(payload.image_url)
        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide an image file (multipart upload), 'image_base64', or 'image_url'."
            )

        meta = loaded.metadata
        w, h = meta["width"], meta["height"]
        source_dpi = meta["dpi"][0] if meta["dpi"] else 72.0

        # Calculate print sizes matrix
        print_matrix = DPIManager.generate_print_matrix(w, h, source_dpi=source_dpi)

        # Estimate uncompressed memory
        channels = meta["channels"]
        bytes_per_sample = max(1, meta["bit_depth"] // 8)
        uncompressed_bytes = meta["total_pixels"] * channels * bytes_per_sample

        warnings = []
        if meta["total_pixels"] > 40_000_000:
            warnings.append("Very high resolution image (>40 Megapixels). Large TIFF export may require significant memory.")
        if meta["detected_format"] in ("BMP", "GIF"):
            warnings.append(f"{meta['detected_format']} format detected. Recommend converting to TIFF or PNG for modern production.")

        aspect_ratio_str = f"{w}:{h}"
        if h > 0:
            from math import gcd
            d = gcd(w, h)
            aspect_ratio_str = f"{w//d}:{h//d} ({w/h:.2f}:1)"

        response = InspectResponse(
            valid=True,
            filename=meta.get("filename"),
            detected_format=meta["detected_format"],
            mime_type=meta["mime_type"],
            file_signature=meta["file_signature"],
            width=w,
            height=h,
            aspect_ratio=aspect_ratio_str,
            total_pixels=meta["total_pixels"],
            color_mode=meta["mode"],
            bit_depth=meta["bit_depth"],
            channels=channels,
            has_alpha=meta["has_alpha"],
            dpi=meta["dpi"],
            icc_profile_present=meta["icc_profile_present"],
            icc_profile_name=meta["icc_profile_name"],
            exif_present=meta["exif_present"],
            file_size_bytes=meta["file_size_bytes"],
            file_size_human=SizeEstimator.format_bytes(meta["file_size_bytes"]),
            estimated_uncompressed_bytes=uncompressed_bytes,
            estimated_uncompressed_human=SizeEstimator.format_bytes(uncompressed_bytes),
            print_sizes=print_matrix,
            warnings=warnings
        )
        loaded.close()
        return response

    except DecompressionBombError as dbe:
        raise HTTPException(status_code=400, detail=f"Decompression Bomb Alert: {dbe.message}")
    except ImageValidationError as ive:
        raise HTTPException(status_code=422, detail=ive.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal inspection error: {str(e)}")
