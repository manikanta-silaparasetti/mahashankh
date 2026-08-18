"""
MahaSankh Vision AI — Image Processing & Production Format Conversion Engine.
FastAPI Application Entry Point.
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .api import api_v1_router
from .services.image_validator import ImageValidationError, DecompressionBombError

app = FastAPI(
    title="MahaShankh Image Processing & Production Conversion Engine",
    description=(
        "Deterministic raster image transformation service for print-production workflows. "
        "Converts any common raster input (JPEG, PNG, WebP, BMP, TIFF, GIF) to production-ready "
        "TIFF, BMP, PNG, or JPEG formats with DPI control, CMYK color management, and quality verification."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ─────────────────────────────────────────────
#  CORS Configuration
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Quality-Report-B64",
        "X-DPI",
        "X-Color-Mode",
        "X-Physical-Width-Inches",
        "X-Physical-Height-Inches",
        "Content-Disposition"
    ]
)

# ─────────────────────────────────────────────
#  Global Exception Handlers
# ─────────────────────────────────────────────
@app.exception_handler(DecompressionBombError)
async def decompression_bomb_handler(request: Request, exc: DecompressionBombError):
    return JSONResponse(
        status_code=400,
        content={"error": "DecompressionBombError", "message": exc.message, "details": exc.details}
    )


@app.exception_handler(ImageValidationError)
async def validation_error_handler(request: Request, exc: ImageValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "ImageValidationError", "message": exc.message, "details": exc.details}
    )


# ─────────────────────────────────────────────
#  API Routes Mount
# ─────────────────────────────────────────────
app.include_router(api_v1_router)


# ─────────────────────────────────────────────
#  Health & System Endpoints
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """System health check and capability status."""
    return {
        "status": "healthy",
        "engine": "MahaSankh-Image-Processor",
        "version": "2.0.0",
        "supported_inputs": ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF"],
        "supported_outputs": ["TIFF", "BMP", "PNG", "JPEG"],
        "color_management": ["RGB", "CMYK", "Grayscale", "ICC-Profile"],
        "compression_algorithms": ["tiff_lzw", "tiff_deflate", "packbits", "raw", "png_deflate", "jpeg_dct"],
        "dpi_support": [72, 150, 300, 600, "custom"]
    }


# ─────────────────────────────────────────────
#  Static Frontend UI Mount
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    @app.get("/", tags=["UI"], include_in_schema=False)
    def serve_frontend():
        """Serves the Production Image Format Studio UI."""
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
