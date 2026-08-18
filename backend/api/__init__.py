"""
API router package.
"""

from fastapi import APIRouter
from .inspect import router as inspect_router
from .estimate import router as estimate_router
from .convert import router as convert_router
from .batch import router as batch_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(inspect_router, tags=["Inspect"])
api_v1_router.include_router(estimate_router, tags=["Estimate"])
api_v1_router.include_router(convert_router, tags=["Convert"])
api_v1_router.include_router(batch_router, tags=["Batch"])

__all__ = ["api_v1_router"]
