"""
Batch image conversion endpoint.
Processes multiple images with individual configuration options.
"""

import os
import base64
from fastapi import APIRouter, HTTPException
from ..models.schemas import BatchConversionRequest, BatchConversionResponse
from ..services.image_validator import ImageValidator
from ..services.image_loader import ImageLoader
from ..services.converter import ImageConverter

router = APIRouter()
validator = ImageValidator()
loader = ImageLoader(validator)
converter = ImageConverter()


@router.post("/batch-convert", response_model=BatchConversionResponse)
async def batch_convert_images(request: BatchConversionRequest):
    """
    Processes a list of image items in a batch.
    Returns per-item conversion reports and base64-encoded output assets.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Batch list is empty.")

    if len(request.items) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 items per batch request allowed in synchronous mode.")

    results = []
    succeeded = 0
    failed = 0

    for item in request.items:
        try:
            if item.image_base64:
                loaded = loader.load_from_base64(item.image_base64, filename=item.identifier)
            elif item.image_url:
                loaded = loader.load_from_url(item.image_url)
            else:
                results.append({
                    "identifier": item.identifier,
                    "success": False,
                    "error": "No image data provided (requires image_base64 or image_url)"
                })
                failed += 1
                continue

            out_path, quality_report = converter.process(loaded, item.options)
            loaded.close()

            # Read result base64
            with open(out_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            if os.path.exists(out_path):
                os.remove(out_path)

            results.append({
                "identifier": item.identifier,
                "success": True,
                "quality_report": quality_report.model_dump(),
                "output_format": item.options.output_format.value,
                "image_base64": b64_data
            })
            succeeded += 1

        except Exception as e:
            results.append({
                "identifier": item.identifier,
                "success": False,
                "error": str(e)
            })
            failed += 1

    return BatchConversionResponse(
        total=len(request.items),
        succeeded=succeeded,
        failed=failed,
        results=results
    )
