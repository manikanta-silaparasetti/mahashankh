"""
MahaSankh Design Intelligence Cloud
API Integration Module - AI Image Generation Service
Author: API Integration Team
"""

import os
import io
import base64
import requests
import time
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from PIL import Image
import pathlib

app = FastAPI(
    title="MahaSankh AI Image Generation API",
    description="AI-powered design image generation for textile, sari, carpenter & more modules",
    version="1.0.0"
)

# Allow all origins for prototype (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ─────────────────────────────────────────────
#  Hugging Face Free Inference API
#  Model options (all free/open-source):
#    1. stabilityai/stable-diffusion-2-1   ← best quality, free
#    2. black-forest-labs/FLUX.1-schnell   ← very fast, free
#    3. runwayml/stable-diffusion-v1-5     ← lightweight fallback
# ─────────────────────────────────────────────
HF_API_KEY = os.getenv("HF_API_KEY", "")  # Set your free HF token here or via env var

MODELS = {
    "stable-diffusion-2-1": "stabilityai/stable-diffusion-2-1",
    "flux-schnell": "black-forest-labs/FLUX.1-schnell",
    "stable-diffusion-1-5": "runwayml/stable-diffusion-v1-5",
}

HF_API_URL = "https://api-inference.huggingface.co/models/{model}"

# ─────────────────────────────────────────────
#  Request & Response schemas
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    module: str = "sari"          # sari | textile | carpenter | general
    model: str = "stable-diffusion-2-1"
    negative_prompt: str = "blurry, low quality, distorted, watermark"
    width: int = 768
    height: int = 768
    dpi: int = 300                # for TIFF export
    convert_tiff: bool = True     # auto-convert to TIFF
    color_mode: str = "RGB"       # RGB or CMYK (CMYK done post-processing)

class GenerateResponse(BaseModel):
    success: bool
    image_base64: str             # PNG preview (for browser display)
    tiff_base64: str = ""         # TIFF version (high quality)
    metadata: dict = {}

# ─────────────────────────────────────────────
#  Module-specific prompt enhancers
# ─────────────────────────────────────────────

MODULE_PROMPTS = {
    "sari": (
        "Indian sari textile design, intricate silk fabric pattern, traditional motifs, "
        "high-resolution fabric texture, professional textile photography, vibrant colors, "
        "pallu design, zari border, weave detail"
    ),
    "textile": (
        "fabric textile pattern, professional textile design, seamless weave, "
        "high-resolution cloth texture, fashion industry quality"
    ),
    "carpenter": (
        "woodwork design, furniture blueprint, carpenter design, wood grain texture, "
        "detailed woodworking pattern, professional craftsmanship"
    ),
    "flex": (
        "banner design, flex print design, vibrant colors, commercial print quality, "
        "high DPI print-ready design"
    ),
    "general": ""
}

def build_enhanced_prompt(prompt: str, module: str) -> str:
    """Enhance user prompt with module-specific context."""
    enhancer = MODULE_PROMPTS.get(module, "")
    if enhancer:
        return f"{prompt}, {enhancer}, ultra detailed, 4K quality, professional design"
    return f"{prompt}, ultra detailed, 4K quality, professional design"


# ─────────────────────────────────────────────
#  Core Image Generation
#  Primary:  Pollinations.ai  (free, no key, FLUX model, no DNS issues)
#  Fallback: HuggingFace Inference API
# ─────────────────────────────────────────────

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

def generate_via_pollinations(prompt: str, width: int, height: int, seed: int = 42) -> bytes:
    """
    Call Pollinations.ai - completely free, no API key, uses FLUX model.
    Returns raw image bytes (JPEG).
    """
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&model=flux&nologo=true&seed={seed}&enhance=true"
    )
    print(f"[INFO] Calling Pollinations.ai: {url[:120]}...")
    resp = requests.get(url, timeout=120)
    if resp.status_code == 200:
        return resp.content
    raise HTTPException(
        status_code=resp.status_code,
        detail=f"Pollinations.ai error: {resp.text[:300]}"
    )


def generate_via_huggingface(prompt: str, model_key: str, width: int, height: int, extra_token: str = "") -> bytes:
    """Call Hugging Face Inference API and return raw image bytes (fallback)."""
    model_id = MODELS.get(model_key, MODELS["stable-diffusion-2-1"])
    url = HF_API_URL.format(model=model_id)

    token = extra_token or HF_API_KEY
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": "blurry, low quality, distorted, deformed, watermark, text",
            "width": width,
            "height": height,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
        }
    }

    for attempt in range(3):
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            return response.content
        elif response.status_code == 503:
            wait = response.json().get("estimated_time", 20)
            print(f"Model loading, waiting {wait}s...")
            time.sleep(min(wait, 30))
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"HuggingFace API error: {response.text}"
            )

    raise HTTPException(status_code=503, detail="Model still loading after retries. Please try again in 30 seconds.")




def convert_to_tiff(image: Image.Image, dpi: int, color_mode: str) -> bytes:
    """Convert PIL image to TIFF bytes with DPI metadata and optional CMYK."""
    if color_mode == "CMYK":
        image = image.convert("CMYK")
    else:
        image = image.convert("RGB")

    tiff_buffer = io.BytesIO()
    image.save(
        tiff_buffer,
        format="TIFF",
        dpi=(dpi, dpi),
        compression="tiff_lzw",   # lossless LZW compression
    )
    tiff_buffer.seek(0)
    return tiff_buffer.read()


# ─────────────────────────────────────────────
#  API Endpoints
# ─────────────────────────────────────────────

# Serve frontend HTML at root
FRONTEND_PATH = pathlib.Path(__file__).parent.parent / "frontend" / "index.html"

@app.get("/")
def root():
    """Serve the frontend UI."""
    if FRONTEND_PATH.exists():
        return FileResponse(str(FRONTEND_PATH), media_type="text/html")
    return {"message": "MahaSankh AI Design API is running", "version": "1.0.0"}


@app.get("/ui")
def serve_ui():
    """Alternative route to serve frontend."""
    if FRONTEND_PATH.exists():
        return FileResponse(str(FRONTEND_PATH), media_type="text/html")
    return {"error": "Frontend not found"}


@app.get("/health")
def health():
    return {"status": "ok", "models_available": list(MODELS.keys())}


@app.get("/ping-hf")
def ping_hf():
    """Test connectivity to HuggingFace main site."""
    try:
        resp = requests.get("https://huggingface.co", timeout=8)
        return {"huggingface_co": True, "status_code": resp.status_code}
    except Exception as e:
        return {"huggingface_co": False, "error": str(e)}


@app.get("/ping-inference")
def ping_inference():
    """Test connectivity to HuggingFace INFERENCE API specifically."""
    results = {}
    # Test main HF
    try:
        r = requests.get("https://huggingface.co", timeout=6)
        results["huggingface_co"] = {"ok": True, "status": r.status_code}
    except Exception as e:
        results["huggingface_co"] = {"ok": False, "error": str(e)}

    # Test inference API host
    try:
        r = requests.get("https://api-inference.huggingface.co", timeout=6)
        results["api_inference"] = {"ok": True, "status": r.status_code}
    except Exception as e:
        results["api_inference"] = {"ok": False, "error": str(e)}

    return results


@app.get("/test-token")
def test_token(token: str):
    """Test if HuggingFace token is valid and can access inference API."""
    try:
        # Call the inference API with a tiny text model (instant, no GPU needed)
        url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, json={"inputs": "Hello"}, headers=headers, timeout=15)
        if resp.status_code == 200:
            return {"token_valid": True, "inference_api_reachable": True}
        elif resp.status_code == 401:
            return {"token_valid": False, "error": "Invalid token / unauthorized"}
        elif resp.status_code == 503:
            # Model loading — means API IS reachable and token IS valid
            return {"token_valid": True, "inference_api_reachable": True, "note": "Model loading (normal)"}
        else:
            return {"token_valid": "unknown", "status_code": resp.status_code, "response": resp.text[:300]}
    except Exception as e:
        return {"inference_api_reachable": False, "error": str(e)}


@app.get("/models")
def list_models():
    return {
        "models": [
            {"key": "stable-diffusion-2-1", "name": "Stable Diffusion 2.1", "description": "Best quality, free, open-source"},
            {"key": "flux-schnell", "name": "FLUX.1 Schnell", "description": "Very fast, free, open-source by Black Forest Labs"},
            {"key": "stable-diffusion-1-5", "name": "Stable Diffusion 1.5", "description": "Lightweight, fast fallback"},
        ]
    }


@app.get("/ping-pollinations")
def ping_pollinations():
    """Test connectivity to Pollinations.ai."""
    try:
        r = requests.get("https://pollinations.ai", timeout=8)
        return {"pollinations_ai": True, "status": r.status_code}
    except Exception as e:
        return {"pollinations_ai": False, "error": str(e)}


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest, x_hf_token: Optional[str] = Header(default=None)):
    """
    Main endpoint: Generate design image from prompt.
    Primary: Pollinations.ai (FLUX model, free, no key)
    Fallback: HuggingFace Inference API
    Returns PNG (base64) for browser preview + TIFF (base64) for high-quality export.
    """
    try:
        # 1. Build enhanced prompt
        enhanced_prompt = build_enhanced_prompt(req.prompt, req.module)
        print(f"[INFO] Generating for module='{req.module}', model='{req.model}'")
        print(f"[INFO] Prompt: {enhanced_prompt[:120]}...")

        # 2. Try Pollinations.ai first (free, no DNS issues)
        image_bytes = None
        model_used = "pollinations-flux"
        try:
            import random
            seed = random.randint(1, 99999)
            image_bytes = generate_via_pollinations(
                prompt=enhanced_prompt,
                width=req.width,
                height=req.height,
                seed=seed
            )
            print("[INFO] ✅ Generated via Pollinations.ai")
        except Exception as poll_err:
            print(f"[WARN] Pollinations failed: {poll_err}. Trying HuggingFace...")
            # Fallback to HuggingFace
            image_bytes = generate_via_huggingface(
                prompt=enhanced_prompt,
                model_key=req.model,
                width=req.width,
                height=req.height,
                extra_token=x_hf_token or ""
            )
            model_used = req.model
            print("[INFO] ✅ Generated via HuggingFace")

        # 3. Load image
        pil_image = Image.open(io.BytesIO(image_bytes))

        # 4. PNG for browser display
        png_buffer = io.BytesIO()
        pil_image.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        png_b64 = base64.b64encode(png_buffer.read()).decode("utf-8")

        # 5. TIFF conversion
        tiff_b64 = ""
        if req.convert_tiff:
            tiff_bytes = convert_to_tiff(pil_image, req.dpi, req.color_mode)
            tiff_b64 = base64.b64encode(tiff_bytes).decode("utf-8")

        return GenerateResponse(
            success=True,
            image_base64=png_b64,
            tiff_base64=tiff_b64,
            metadata={
                "module": req.module,
                "model_used": model_used,
                "prompt_sent": enhanced_prompt,
                "dpi": req.dpi,
                "color_mode": req.color_mode,
                "dimensions": f"{req.width}x{req.height}",
                "tiff_generated": req.convert_tiff,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/convert-tiff")
async def convert_image_to_tiff(
    image_base64: str,
    dpi: int = 300,
    color_mode: str = "RGB"
):
    """
    Standalone TIFF converter endpoint.
    Send any base64 PNG/JPG image and get back a TIFF.
    """
    try:
        image_bytes = base64.b64decode(image_base64)
        pil_image = Image.open(io.BytesIO(image_bytes))
        tiff_bytes = convert_to_tiff(pil_image, dpi, color_mode)
        tiff_b64 = base64.b64encode(tiff_bytes).decode("utf-8")
        return {"success": True, "tiff_base64": tiff_b64, "dpi": dpi, "color_mode": color_mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
