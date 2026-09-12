"""
Executive Demonstration Asset Generator for MahaShankh Studio Pro.
Processes sample input and generates side-by-side comparison graphics,
print bleed sheets, CMYK separation plates, saree fabric repeats, and SVG vectors.
"""

import os
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.services.image_loader import ImageLoader
from backend.services.converter import ImageConverter
from backend.services.bleed_manager import BleedManager
from backend.services.color_separator import ColorSeparator
from backend.services.pattern_engine import PatternEngine
from backend.services.vectorizer import AutoVectorizer
from backend.services.upscaler.realesrgan import RealESRGANUpscaler
from backend.models.schemas import (
    ConversionOptions,
    SupportedOutputFormat,
    ColorModeOption,
    TIFFCompressionOption,
    UpscaleAlgorithm
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "demo_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
SAMPLE_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "ex images", "original test img 2.jpeg")

print(f"[1/5] Loading sample image: {SAMPLE_IMAGE_PATH}")
orig_img = Image.open(SAMPLE_IMAGE_PATH)
orig_w, orig_h = orig_img.size

# ─────────────────────────────────────────────
# 1. AI Super-Resolution Comparison (4x)
# ─────────────────────────────────────────────
print("[2/5] Running Real-ESRGAN 4x Super-Resolution...")
upscaler = RealESRGANUpscaler()
up_img, up_meta = upscaler.upscale(orig_img, factor=4)
up_w, up_h = up_img.size

# Create a side-by-side zoomed comparison card (800x400)
# Zoom into a 150x150 patch in the center
center_x, center_y = orig_w // 2, orig_h // 2
crop_r = 60
patch_orig = orig_img.crop((center_x - crop_r, center_y - crop_r, center_x + crop_r, center_y + crop_r))
# Nearest-neighbor zoom of original (showing real pixelation)
patch_orig_zoomed = patch_orig.resize((380, 380), Image.NEAREST)

# Same patch from 4x AI upscaled image
up_center_x, up_center_y = center_x * 4, center_y * 4
up_crop_r = crop_r * 4
patch_ai = up_img.crop((up_center_x - up_crop_r, up_center_y - up_crop_r, up_center_x + up_crop_r, up_center_y + up_crop_r))
patch_ai_zoomed = patch_ai.resize((380, 380), Image.LANCZOS)

comp_card = Image.new("RGB", (820, 440), (16, 20, 31))
draw = ImageDraw.Draw(comp_card)

comp_card.paste(patch_orig_zoomed, (20, 40))
comp_card.paste(patch_ai_zoomed, (420, 40))

draw.text((20, 15), f"ORIGINAL ({orig_w}x{orig_h}px) — Low-Res Pixelated", fill=(239, 68, 68))
draw.text((420, 15), f"REAL-ESRGAN AI 4x ({up_w}x{up_h}px) — Sharp Print Master", fill=(16, 185, 129))

comp_path = os.path.join(OUTPUT_DIR, "1_realesrgan_4x_comparison.png")
comp_card.save(comp_path)
print(f"  -> Saved: {comp_path}")

# ─────────────────────────────────────────────
# 2. Bleed Margin & Crop Marks Print Sheet
# ─────────────────────────────────────────────
print("[3/5] Generating 3mm Mirrored Bleed + Crop Marks Sheet...")
bleed_mgr = BleedManager()
dpi = 300
bleed_px = bleed_mgr.mm_to_pixels(3.0, dpi)
bleed_ext = bleed_mgr.extend_bleed(orig_img, bleed_px=bleed_px, fill_mode="mirror")
sheet_img, bleed_report = bleed_mgr.add_printer_marks(
    bleed_ext,
    trim_w=orig_w,
    trim_h=orig_h,
    bleed_px=bleed_px,
    dpi=dpi,
    job_slug=f"MahaShankh Studio Pro • Trim {orig_w}x{orig_h} • Bleed 3mm • 300 DPI"
)

sheet_tiff_path = os.path.join(OUTPUT_DIR, "2_print_ready_sheet_with_crop_marks.tiff")
sheet_img.save(sheet_tiff_path, format="TIFF", dpi=(dpi, dpi), compression="tiff_lzw")
sheet_png_path = os.path.join(OUTPUT_DIR, "2_print_ready_sheet_with_crop_marks.png")
sheet_img.save(sheet_png_path, format="PNG")
print(f"  -> Saved: {sheet_tiff_path}")

# ─────────────────────────────────────────────
# 3. 4-Color CMYK Separation Plates
# ─────────────────────────────────────────────
print("[4/5] Extracting 4-Color CMYK Screen Printing Plates...")
separator = ColorSeparator()
zip_bytes, sep_meta = separator.generate_separation_bundle_zip(orig_img, dpi=300, job_title="Sari_Sample")
zip_path = os.path.join(OUTPUT_DIR, "3_CMYK_Separation_Plates.zip")
with open(zip_path, "wb") as f:
    f.write(zip_bytes)
print(f"  -> Saved: {zip_path}")

# Also save individual plate PNGs for easy viewing in documents
plates = separator.separate_channels(orig_img, dpi=300, job_title="Sample")
plates_dir = os.path.join(OUTPUT_DIR, "3_plates_preview")
os.makedirs(plates_dir, exist_ok=True)
for ch_name, pl_img in plates.items():
    pl_path = os.path.join(plates_dir, f"plate_{ch_name}.png")
    pl_img.save(pl_path, format="PNG")
print(f"  -> Saved 4 individual plate previews in {plates_dir}")

# ─────────────────────────────────────────────
# 4. Saree Seamless Fabric Repeat & Vectorization
# ─────────────────────────────────────────────
print("[5/5] Generating Seamless Saree Repeat and SVG Vectors...")
pattern_eng = PatternEngine()
repeat_img, pat_rep = pattern_eng.generate_repeat(orig_img, repeat_x=3, repeat_y=3, mode="half_drop", make_seamless=True)
repeat_path = os.path.join(OUTPUT_DIR, "4_saree_seamless_half_drop_fabric.png")
repeat_img.save(repeat_path, format="PNG")
print(f"  -> Saved: {repeat_path}")

vectorizer = AutoVectorizer()
svg_content, vec_rep = vectorizer.vectorize_to_svg(orig_img, threshold=128, tolerance=1.2)
svg_path = os.path.join(OUTPUT_DIR, "5_vector_paths.svg")
with open(svg_path, "w", encoding="utf-8") as f:
    f.write(svg_content)
print(f"  -> Saved: {svg_path}")

dxf_content, dxf_rep = vectorizer.vectorize_to_dxf(orig_img, threshold=128, tolerance=1.2)
dxf_path = os.path.join(OUTPUT_DIR, "5_vector_cnc.dxf")
with open(dxf_path, "w", encoding="utf-8") as f:
    f.write(dxf_content)
print(f"  -> Saved: {dxf_path}")

print("\n============================================")
print("SUCCESS: All Executive Demo Assets Generated!")
print(f"Location: {OUTPUT_DIR}")
print("============================================")
