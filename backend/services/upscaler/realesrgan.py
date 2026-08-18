"""
Real-ESRGAN AI Super-Resolution Upscaler Adapter (Optional/Modular).
Provides seamless fallback to high-quality Lanczos if neural weights/torch are not loaded.
"""

from typing import Tuple, Dict, Any
from PIL import Image
from .base import UpscalerInterface
from .pillow import PillowUpscaler
from ...models.schemas import UpscaleAlgorithm


class RealESRGANUpscaler(UpscalerInterface):
    """
    Optional deep-learning super-resolution module.
    Gracefully falls back to high-grade Lanczos interpolation if torch/realesrgan is unavailable.
    """

    def __init__(self, model_name: str = "RealESRGAN_x4plus", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._is_available = False
        self._fallback_upscaler = PillowUpscaler(UpscaleAlgorithm.LANCZOS)
        self._check_availability()

    def _check_availability(self):
        """Attempts to dynamically import and load RealESRGAN if present."""
        try:
            # Check if torch and realesrgan libraries exist
            import torch
            from realesrgan import RealESRGANer
            self._is_available = True
        except ImportError:
            self._is_available = False

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

        if self._is_available and self.model is not None:
            try:
                import numpy as np
                import cv2
                np_img = np.array(image.convert("RGB"))
                np_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
                output, _ = self.model.enhance(np_img, outscale=factor)
                output_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
                upscaled_image = Image.fromarray(output_rgb)

                return upscaled_image, {
                    "upscale_applied": True,
                    "factor": f"{factor}x",
                    "upscaler": f"Real-ESRGAN ({self.model_name})",
                    "original_dimensions": [orig_w, orig_h],
                    "output_dimensions": list(upscaled_image.size)
                }
            except Exception as e:
                # Fallback to Lanczos if neural execution fails
                res_img, report = self._fallback_upscaler.upscale(image, factor)
                report["upscaler_fallback_reason"] = f"Real-ESRGAN inference failed ({str(e)}), used Lanczos"
                return res_img, report
        else:
            # Safe deterministic fallback
            res_img, report = self._fallback_upscaler.upscale(image, factor)
            report["upscaler"] = "Pillow-Lanczos (Real-ESRGAN optional weights not loaded)"
            return res_img, report
