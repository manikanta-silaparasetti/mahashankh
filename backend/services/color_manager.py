"""
Color Management Service.
Deterministic RGB -> CMYK, CMYK -> RGB, Grayscale, and ICC Profile transforms using Pillow & ImageCms.

NO generative AI is used for color space conversions.
"""

import io
import os
from typing import Tuple, Optional, Dict, Any
import numpy as np
from PIL import Image, ImageCms
from ..models.schemas import ColorModeOption


class ColorManager:
    """Manages color space transformations, alpha compositing, and ICC profile application."""

    def __init__(self, default_cmyk_profile_path: Optional[str] = None):
        self.default_cmyk_profile_path = default_cmyk_profile_path

    @staticmethod
    def flatten_alpha(
        image: Image.Image,
        matte_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """
        Composites an image with an alpha channel (RGBA/LA) onto a solid background color.
        Required before converting to CMYK or formats that do not support alpha (JPEG, BMP).
        """
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
            background = Image.new("RGBA", image.size, matte_color + (255,))
            composited = Image.alpha_composite(background, image)
            return composited.convert("RGB")
        return image

    def convert_color_mode(
        self,
        image: Image.Image,
        target_mode: ColorModeOption,
        custom_icc_profile_path: Optional[str] = None,
        matte_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Converts the image to the requested color mode.
        Returns the transformed PIL Image and a diagnostic report dict.
        """
        current_mode = image.mode
        report = {
            "source_mode": current_mode,
            "target_mode": target_mode.value,
            "alpha_flattened": False,
            "icc_profile_used": None,
            "conversion_method": "direct_pillow"
        }

        if target_mode == ColorModeOption.PRESERVE:
            report["final_mode"] = current_mode
            return image, report

        # Target: CMYK
        if target_mode == ColorModeOption.CMYK:
            # 1. Flatten alpha if present (CMYK cannot have transparency)
            if current_mode in ("RGBA", "LA") or "transparency" in image.info:
                image = self.flatten_alpha(image, matte_color)
                report["alpha_flattened"] = True
                current_mode = image.mode

            if current_mode == "CMYK":
                report["final_mode"] = "CMYK"
                report["conversion_method"] = "already_cmyk"
                return image, report

            # 2. Convert via ICC Profile if available
            icc_profile_to_use = custom_icc_profile_path or self.default_cmyk_profile_path
            if icc_profile_to_use and os.path.exists(icc_profile_to_use):
                try:
                    srgb_profile = ImageCms.createProfile("sRGB")
                    cmyk_profile = ImageCms.getOpenProfile(icc_profile_to_use)
                    transform = ImageCms.buildTransform(
                        srgb_profile, cmyk_profile, "RGB", "CMYK",
                        renderingIntent=ImageCms.Intent.PERCEPTUAL
                    )
                    cmyk_image = ImageCms.applyTransform(image.convert("RGB"), transform)
                    report["final_mode"] = "CMYK"
                    report["icc_profile_used"] = os.path.basename(icc_profile_to_use)
                    report["conversion_method"] = "littlecms_icc_transform"
                    return cmyk_image, report
                except Exception as e:
                    report["icc_warning"] = f"ICC transform failed ({str(e)}), falling back to standard Pillow CMYK"

            # 3. High-Fidelity GCR (Gray Component Replacement) RGB -> CMYK
            rgb_arr = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
            r, g, b = rgb_arr[:, :, 0], rgb_arr[:, :, 1], rgb_arr[:, :, 2]
            
            # Compute Key/Black (K)
            k = 1.0 - np.maximum(np.maximum(r, g), b)
            one_minus_k = 1.0 - k
            one_minus_k[one_minus_k == 0] = 1e-7

            # Compute Cyan, Magenta, Yellow with Under-Color Removal
            c = (1.0 - r - k) / one_minus_k
            m = (1.0 - g - k) / one_minus_k
            y = (1.0 - b - k) / one_minus_k

            c_byte = np.clip(c * 255.0, 0, 255).astype(np.uint8)
            m_byte = np.clip(m * 255.0, 0, 255).astype(np.uint8)
            y_byte = np.clip(y * 255.0, 0, 255).astype(np.uint8)
            k_byte = np.clip(k * 255.0, 0, 255).astype(np.uint8)

            cmyk_arr = np.stack([c_byte, m_byte, y_byte, k_byte], axis=2)
            cmyk_image = Image.fromarray(cmyk_arr, mode="CMYK")

            report["final_mode"] = "CMYK"
            report["conversion_method"] = "gcr_cmyk_transform"
            report["note"] = "High-fidelity GCR (Gray Component Replacement) applied for deep blacks and color press separation."
            return cmyk_image, report

        # Target: RGB
        elif target_mode == ColorModeOption.RGB:
            if current_mode == "RGB":
                report["final_mode"] = "RGB"
                return image, report
            elif current_mode == "RGBA":
                # Preserve RGBA unless explicitly told to strip
                report["final_mode"] = "RGBA"
                return image, report
            elif current_mode == "CMYK":
                rgb_image = image.convert("RGB")
                report["final_mode"] = "RGB"
                report["conversion_method"] = "cmyk_to_rgb_pillow"
                return rgb_image, report
            else:
                rgb_image = image.convert("RGB")
                report["final_mode"] = "RGB"
                return rgb_image, report

        # Target: Grayscale (L)
        elif target_mode == ColorModeOption.GRAYSCALE:
            if current_mode in ("RGBA", "LA"):
                image = self.flatten_alpha(image, matte_color)
                report["alpha_flattened"] = True
            gray_image = image.convert("L")
            report["final_mode"] = "L"
            report["conversion_method"] = "rgb_to_grayscale_luminance"
            return gray_image, report

        report["final_mode"] = image.mode
        return image, report
