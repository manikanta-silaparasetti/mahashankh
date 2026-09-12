"""
Textile, Saree & Vectorization API Endpoints.
Provides:
- Seamless Pattern Repeat generation (Straight grid, Half-drop brick, Mirror reflection).
- Auto-Vectorization to SVG and DXF (for CNC laser fabric cutting and embroidery).
"""

import os
import io
import base64
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Response
from fastapi.responses import Response

from ..services.image_validator import ImageValidator
from ..services.image_loader import ImageLoader
from ..services.pattern_engine import PatternEngine
from ..services.vectorizer import AutoVectorizer
from ..models.schemas import (
    PatternRepeatMode,
    PatternRepeatResponse,
    VectorizeFormat,
    VectorizeResponse
)

router = APIRouter(prefix="/textile", tags=["Textile & Saree Engine"])
validator = ImageValidator()
loader = ImageLoader(validator)
pattern_engine = PatternEngine()
vectorizer = AutoVectorizer()


@router.post("/pattern")
async def generate_textile_pattern(
    file: UploadFile = File(...),
    repeat_x: int = Form(3),
    repeat_y: int = Form(3),
    mode: PatternRepeatMode = Form(PatternRepeatMode.HALF_DROP),
    make_seamless: bool = Form(True),
    return_json: bool = Form(False)
):
    """
    Generates a continuous textile fabric repeat layout from a motif or tile.
    Modes: 'straight' (grid), 'half_drop' (saree brick 50% offset), 'mirror' (bilateral flip).
    """
    try:
        raw_bytes = await file.read()
        loaded = loader.load_from_bytes(raw_bytes, filename=file.filename)

        pattern_img, report = pattern_engine.generate_repeat(
            image=loaded.image,
            repeat_x=repeat_x,
            repeat_y=repeat_y,
            mode=mode.value,
            make_seamless=make_seamless
        )
        loaded.close()

        buf = io.BytesIO()
        pattern_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        if return_json:
            b64_img = base64.b64encode(png_bytes).decode("utf-8")
            return PatternRepeatResponse(
                mode=report["mode"],
                repeat_x=report["repeat_x"],
                repeat_y=report["repeat_y"],
                tile_dimensions=report["tile_dimensions"],
                total_dimensions=report["total_dimensions"],
                total_tiles=report["total_tiles"],
                seamless_blending_applied=report["seamless_blending_applied"],
                image_base64=b64_img
            )

        filename = f"{os.path.splitext(file.filename or 'pattern')[0]}_{mode.value}_{repeat_x}x{repeat_y}.png"
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern generation error: {str(e)}")


@router.post("/vectorize")
async def vectorize_image(
    file: UploadFile = File(...),
    format: VectorizeFormat = Form(VectorizeFormat.SVG),
    threshold: int = Form(128),
    invert: bool = Form(False),
    tolerance: float = Form(1.2),
    return_json: bool = Form(False)
):
    """
    Converts raster motifs, artwork, and silhouettes into scalable mathematical vector paths.
    Exports standard SVG (for design and web) or DXF (for CNC laser cutters and embroidery digitizing).
    """
    try:
        raw_bytes = await file.read()
        loaded = loader.load_from_bytes(raw_bytes, filename=file.filename)
        base_name = os.path.splitext(file.filename or "motif")[0]

        if format == VectorizeFormat.SVG:
            vector_content, report = vectorizer.vectorize_to_svg(
                image=loaded.image,
                threshold=threshold,
                invert=invert,
                tolerance=tolerance
            )
            media_type = "image/svg+xml"
            out_filename = f"{base_name}_vector.svg"
        else:
            vector_content, report = vectorizer.vectorize_to_dxf(
                image=loaded.image,
                threshold=threshold,
                invert=invert,
                tolerance=tolerance
            )
            media_type = "application/dxf"
            out_filename = f"{base_name}_vector.dxf"

        loaded.close()

        if return_json:
            return VectorizeResponse(
                format=report["format"],
                contours_traced=report.get("contours_traced") or report.get("closed_polylines", 0),
                total_vertices=report["total_vertices"],
                dimensions=report["dimensions"],
                file_size_bytes=report["file_size_bytes"],
                content=vector_content,
                filename=out_filename
            )

        return Response(
            content=vector_content.encode("utf-8"),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{out_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vectorization error: {str(e)}")
