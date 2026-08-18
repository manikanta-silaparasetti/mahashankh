"""
Base abstract class for image upscaling services.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from PIL import Image


class UpscalerInterface(ABC):
    """Abstract base class defining the upscaler interface."""

    @abstractmethod
    def upscale(
        self,
        image: Image.Image,
        factor: int
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Upscales the input image by the specified integer factor (e.g. 2x, 4x).
        Returns the upscaled PIL Image and diagnostic metadata.
        """
        pass
