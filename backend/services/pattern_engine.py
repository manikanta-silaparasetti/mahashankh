"""
Seamless Textile & Saree Pattern Repeat Engine.
Generates production-grade fabric roll repeat layouts:
- Straight Grid Repeat (standard continuous tile)
- Half-Drop Repeat (brick 50% staggered — gold standard for sarees & wallpapers)
- Mirror Repeat (bilateral & vertical flip for symmetrical mandala/border patterns)
Includes intelligent boundary edge blending to synthesize seamless tile seams.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageOps


class PatternEngine:
    """
    Industrial textile repeat generator for digital fabric, rotary screen, and saree printing.
    """

    @staticmethod
    def synthesize_seamless_edges(image: Image.Image, blend_fraction: float = 0.15) -> Image.Image:
        """
        Synthesizes seamless tile boundaries using linear / cosine cross-fading of edges.
        Eliminates harsh line cuts when repeating arbitrary non-seamless photos.
        """
        w, h = image.size
        blend_w = max(2, int(w * blend_fraction))
        blend_h = max(2, int(h * blend_fraction))

        # Work in float32 RGBA or RGB
        orig_mode = image.mode
        work_img = image.convert("RGBA") if orig_mode == "RGBA" else image.convert("RGB")
        arr = np.array(work_img, dtype=np.float32)

        # Horizontal edge blending: wrap right edge into left edge with gradient
        for x in range(blend_w):
            alpha = 0.5 * (1.0 - np.cos(np.pi * x / blend_w))  # Smooth cosine ease [0, 1]
            left_col = arr[:, x].copy()
            right_col = arr[:, w - blend_w + x].copy()
            arr[:, x] = (1.0 - alpha) * right_col + alpha * left_col
            arr[:, w - blend_w + x] = alpha * right_col + (1.0 - alpha) * left_col

        # Vertical edge blending: wrap bottom edge into top edge
        for y in range(blend_h):
            alpha = 0.5 * (1.0 - np.cos(np.pi * y / blend_h))
            top_row = arr[y, :].copy()
            bottom_row = arr[h - blend_h + y, :].copy()
            arr[y, :] = (1.0 - alpha) * bottom_row + alpha * top_row
            arr[h - blend_h + y, :] = alpha * bottom_row + (1.0 - alpha) * top_row

        blended = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode=work_img.mode)
        return blended if orig_mode in ("RGB", "RGBA") else blended.convert(orig_mode)

    def generate_repeat(
        self,
        image: Image.Image,
        repeat_x: int = 3,
        repeat_y: int = 3,
        mode: str = "half_drop",
        make_seamless: bool = True
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Generates a continuous fabric roll repeat.
        mode: 'straight' | 'half_drop' | 'mirror'
        """
        base_tile = self.synthesize_seamless_edges(image) if make_seamless else image
        tile_w, tile_h = base_tile.size

        repeat_x = max(1, min(repeat_x, 10))
        repeat_y = max(1, min(repeat_y, 10))

        out_w = tile_w * repeat_x
        out_h = tile_h * repeat_y

        canvas = Image.new(base_tile.mode, (out_w, out_h))

        if mode == "straight":
            # Standard continuous grid
            for r in range(repeat_y):
                for c in range(repeat_x):
                    canvas.paste(base_tile, (c * tile_w, r * tile_h))

        elif mode == "half_drop":
            # Brick / 50% vertical offset on alternating columns
            # Eliminates visible horizontal eye tracking on repeating fabric
            offset_y = tile_h // 2
            for c in range(repeat_x):
                shift = (c % 2) * offset_y
                for r in range(-1, repeat_y + 1):
                    paste_y = r * tile_h + shift
                    paste_x = c * tile_w
                    # Clip and paste within canvas bounds
                    box_top = max(0, paste_y)
                    box_bottom = min(out_h, paste_y + tile_h)
                    if box_top < box_bottom:
                        crop_top = box_top - paste_y
                        crop_bottom = crop_top + (box_bottom - box_top)
                        tile_crop = base_tile.crop((0, crop_top, tile_w, crop_bottom))
                        canvas.paste(tile_crop, (paste_x, box_top))

        elif mode == "mirror":
            # Alternating mirror reflection (kaleidoscopic fabric)
            tile_h_flip = ImageOps.mirror(base_tile)
            tile_v_flip = ImageOps.flip(base_tile)
            tile_hv_flip = ImageOps.flip(tile_h_flip)

            tiles = [
                [base_tile, tile_h_flip],
                [tile_v_flip, tile_hv_flip]
            ]
            for r in range(repeat_y):
                for c in range(repeat_x):
                    cur_tile = tiles[r % 2][c % 2]
                    canvas.paste(cur_tile, (c * tile_w, r * tile_h))

        else:
            # Default straight
            for r in range(repeat_y):
                for c in range(repeat_x):
                    canvas.paste(base_tile, (c * tile_w, r * tile_h))

        report = {
            "mode": mode,
            "repeat_x": repeat_x,
            "repeat_y": repeat_y,
            "tile_dimensions": [tile_w, tile_h],
            "total_dimensions": [out_w, out_h],
            "total_tiles": repeat_x * repeat_y,
            "seamless_blending_applied": make_seamless
        }

        return canvas, report
