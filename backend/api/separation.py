"""
CMYK Color Separation Plate API Endpoint.
Splits designs into Cyan, Magenta, Yellow, and Black high-contrast printing plates
packaged as an archival ZIP bundle with registration targets.
"""

import os
import base64
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Response
from fastapi.responses import Response

from ..services.image_validator import ImageValidator
from ..services.image_loader import ImageLoader
from ..services.color_separator import ColorSeparator
from ..models.schemas import SeparationResponse

router = APIRouter(prefix="/separation", tags=["Print Prepress & Separation"])
validator = ImageValidator()
loader = ImageLoader(validator)
separator = ColorSeparator()


@router.post("/plates")
async def generate_separation_plates(
    file: UploadFile = File(...),
    dpi: int = Form(300),
    job_title: Optional[str] = Form(None),
    return_json: bool = Form(False)
):
    """
    Separates the uploaded image into individual C, M, Y, and K plates.
    Returns either a direct downloadable ZIP archive or structured JSON with base64 data.
    """
    try:
        raw_bytes = await file.read()
        loaded = loader.load_from_bytes(raw_bytes, filename=file.filename)
        title = job_title or os.path.splitext(file.filename or "artwork")[0]

        zip_bytes, metadata = separator.generate_separation_bundle_zip(
            image=loaded.image,
            dpi=dpi,
            job_title=title
        )
        loaded.close()

        if return_json:
            b64_zip = base64.b64encode(zip_bytes).decode("utf-8")
            return SeparationResponse(
                job_title=title,
                dpi=dpi,
                plates_generated=metadata["plates_generated"],
                channel_stats=metadata["channel_stats"],
                zip_size_bytes=len(zip_bytes),
                suitable_for_screen_printing=True,
                zip_base64=b64_zip
            )

        # Stream direct ZIP download
        zip_filename = f"{title}_CMYK_Separation_Plates_{dpi}DPI.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Separation plate error: {str(e)}")
