"""
Deterministic Pillow-based upscaler using high-quality resampling filters (Lanczos/Bicubic).
"""

from typing import Tuple, Dict, Any
from PIL import Image
from .base import UpscalerInterface
from ...models.schemas import UpscaleAlgorithm


class PillowUpscaler(UpscalerInterface):
    """Deterministic, high-quality interpolation upscaler using Pillow."""

    def __init__(self, algorithm: UpscaleAlgorithm = UpscaleAlgorithm.LANCZOS):
        self.algorithm = algorithm

    def upscale(
        self,
        image: Image.Image,
        factor: int
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        if factor <= 1:
            return image, {
                "upscale_applied": False,
                "factor": "1x",
                "upscaler": "none",
                "original_dimensions": list(image.size),
                "output_dimensions": list(image.size)
            }

        orig_w, orig_h = image.size
        new_w = orig_w * factor
        new_h = orig_h * factor

        # Select filter
        resample_filter = Image.Resampling.LANCZOS
        algo_name = "Pillow-Lanczos"
        if self.algorithm == UpscaleAlgorithm.BICUBIC:
            resample_filter = Image.Resampling.BICUBIC
            algo_name = "Pillow-Bicubic"

        upscaled_image = image.resize((new_w, new_h), resample=resample_filter)

        return upscaled_image, {
            "upscale_applied": True,
            "factor": f"{factor}x",
            "upscaler": algo_name,
            "original_dimensions": [orig_w, orig_h],
            "output_dimensions": [new_w, new_h]
        }
