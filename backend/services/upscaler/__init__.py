"""
Upscaler service package.
"""

from .base import UpscalerInterface
from .pillow import PillowUpscaler
from .realesrgan import RealESRGANUpscaler

__all__ = [
    "UpscalerInterface",
    "PillowUpscaler",
    "RealESRGANUpscaler",
]
