"""
Real-ESRGAN AI Super-Resolution Upscaler using ONNX Runtime.
Runs purely on CPU with low RAM footprint (~67MB ONNX model, tiled inference).
Gracefully falls back to high-grade Lanczos interpolation if ONNX model download/execution fails.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image

from .base import UpscalerInterface
from .pillow import PillowUpscaler
from ...models.schemas import UpscaleAlgorithm

logger = logging.getLogger("mahasankh.upscaler.realesrgan")

MODEL_URL = "https://huggingface.co/wide-video/real-esrgan-v1.0.0/resolve/main/real_esrgan_x4.onnx"
MODEL_HASH = "afa7fa42eed0315a3d7b2a54e79e4e44a672d3c0889c2828c4f84c9ab91edb0b"
MODEL_FILENAME = "real_esrgan_x4.onnx"


class RealESRGANUpscaler(UpscalerInterface):
    """
    Production-grade AI super-resolution using an ONNX-converted Real-ESRGAN x4 model.
    Optimized for CPU inference with automatic weight caching and tile-based memory bounding.
    """

    def __init__(self, model_name: str = "RealESRGAN_x4plus_ONNX", tile_size: int = 512, tile_pad: int = 16):
        self.model_name = model_name
        self.tile_size = tile_size
        self.tile_pad = tile_pad
        self._session = None
        self._session_failed = False
        self._fallback_upscaler = PillowUpscaler(UpscaleAlgorithm.LANCZOS)

    def _get_or_load_session(self):
        """Lazy-loads the ONNX Runtime inference session on first request."""
        if self._session is not None:
            return self._session

        if self._session_failed:
            return None

        try:
            import onnxruntime as ort
            import pooch

            model_path = pooch.retrieve(
                url=MODEL_URL,
                known_hash=MODEL_HASH,
                fname=MODEL_FILENAME,
                path=pooch.os_cache("mahasankh_models"),
                progressbar=False
            )

            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 2
            sess_options.inter_op_num_threads = 1
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                model_path,
                sess_options=sess_options,
                providers=["CPUExecutionProvider"]
            )
            logger.info("Loaded Real-ESRGAN ONNX session successfully from %s", model_path)
            return self._session
        except Exception as e:
            logger.error("Failed to initialize Real-ESRGAN ONNX session: %s", e)
            self._session_failed = True
            return None

    def _run_tile_inference(self, session, tile_rgb: Image.Image) -> Image.Image:
        """Runs the ONNX model on a single RGB PIL image tile."""
        np_tile = np.array(tile_rgb, dtype=np.float32) / 255.0  # HWC
        # Convert HWC -> NCHW
        np_tile = np.transpose(np_tile, (2, 0, 1))
        np_tile = np.expand_dims(np_tile, axis=0)

        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: np_tile})[0]  # Shape (1, 3, H*4, W*4)

        out_np = np.squeeze(output, axis=0)  # CHW
        out_np = np.clip(out_np * 255.0, 0, 255).astype(np.uint8)
        out_np = np.transpose(out_np, (1, 2, 0))  # HWC
        return Image.fromarray(out_np)

    def _upscale_4x_rgb(self, session, rgb_img: Image.Image) -> Image.Image:
        """Upscales an RGB image 4x using tiled processing to bound memory usage."""
        w, h = rgb_img.size

        # If small enough, run single-pass directly
        if w <= self.tile_size and h <= self.tile_size:
            return self._run_tile_inference(session, rgb_img)

        scale = 4
        out_w, out_h = w * scale, h * scale
        out_canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)

        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                x1 = max(x - self.tile_pad, 0)
                y1 = max(y - self.tile_pad, 0)
                x2 = min(x + self.tile_size + self.tile_pad, w)
                y2 = min(y + self.tile_size + self.tile_pad, h)

                crop = rgb_img.crop((x1, y1, x2, y2))
                up_crop = self._run_tile_inference(session, crop)
                up_crop_np = np.array(up_crop)

                # Offsets within upscaled crop
                in_x1 = (x - x1) * scale
                in_y1 = (y - y1) * scale
                in_x2 = in_x1 + min(self.tile_size, w - x) * scale
                in_y2 = in_y1 + min(self.tile_size, h - y) * scale

                # Target canvas coordinates
                out_x1 = x * scale
                out_y1 = y * scale
                out_x2 = out_x1 + min(self.tile_size, w - x) * scale
                out_y2 = out_y1 + min(self.tile_size, h - y) * scale

                out_canvas[out_y1:out_y2, out_x1:out_x2] = up_crop_np[in_y1:in_y2, in_x1:in_x2]

        return Image.fromarray(out_canvas)

    def upscale(
        self,
        image: Image.Image,
        factor: int
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        orig_w, orig_h = image.size

        if factor <= 1:
            return image, {
                "upscale_applied": False,
                "factor": "1x",
                "upscaler": "none",
                "original_dimensions": [orig_w, orig_h],
                "output_dimensions": [orig_w, orig_h]
            }

        session = self._get_or_load_session()
        if session is None:
            # Clean fallback to Lanczos if ONNX cannot be initialized
            res_img, report = self._fallback_upscaler.upscale(image, factor)
            report["upscaler"] = "Pillow-Lanczos (Real-ESRGAN weights unavailable)"
            report["upscaler_fallback_reason"] = "ONNX model session not initialized"
            return res_img, report

        try:
            # Preserve alpha mask if present
            orig_mode = image.mode
            alpha_channel = None
            if orig_mode == "RGBA":
                r, g, b, a = image.split()
                rgb_img = Image.merge("RGB", (r, g, b))
                alpha_channel = a
            elif orig_mode != "RGB":
                rgb_img = image.convert("RGB")
            else:
                rgb_img = image

            # Native 4x AI Upscale
            up_4x_rgb = self._upscale_4x_rgb(session, rgb_img)

            # Adjust to requested factor
            target_w = orig_w * factor
            target_h = orig_h * factor

            if factor == 4:
                final_rgb = up_4x_rgb
            else:
                # For 2x or custom factors, downsample or upscale with Lanczos
                final_rgb = up_4x_rgb.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

            # Re-attach Alpha channel if previously present
            if alpha_channel is not None:
                final_alpha = alpha_channel.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)
                final_image = Image.merge("RGBA", (*final_rgb.split(), final_alpha))
            elif orig_mode == "L":
                final_image = final_rgb.convert("L")
            else:
                final_image = final_rgb

            return final_image, {
                "upscale_applied": True,
                "factor": f"{factor}x",
                "upscaler": f"Real-ESRGAN AI ({self.model_name})",
                "original_dimensions": [orig_w, orig_h],
                "output_dimensions": list(final_image.size)
            }

        except Exception as e:
            logger.error("Real-ESRGAN inference failed with error: %s", e)
            res_img, report = self._fallback_upscaler.upscale(image, factor)
            report["upscaler_fallback_reason"] = f"Real-ESRGAN inference error ({str(e)}), used Lanczos"
            return res_img, report
