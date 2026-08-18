"""
Resource and dimension estimation endpoint.
Computes estimated memory consumption, compressed disk footprints, and print sizes before processing.
"""

from fastapi import APIRouter
from ..models.schemas import EstimateRequest, EstimateResponse
from ..services.size_estimator import SizeEstimator

router = APIRouter()


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_dimensions_and_size(request: EstimateRequest):
    """
    Calculates estimated uncompressed memory requirements, projected disk size ranges,
    and physical print dimensions for given pixel/DPI targets.
    """
    return SizeEstimator.estimate(request)
