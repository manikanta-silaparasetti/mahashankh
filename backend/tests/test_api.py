"""
FastAPI integration tests for API endpoints.
"""

import io
import json
import base64
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.main import app

client = TestClient(app)


def create_in_memory_image_bytes(fmt="PNG", size=(150, 100), color=(50, 150, 250)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=fmt, dpi=(72, 72))
    return buf.getvalue()


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "TIFF" in data["supported_outputs"]
    assert "BMP" in data["supported_outputs"]


def test_inspect_endpoint_multipart():
    png_data = create_in_memory_image_bytes(fmt="PNG", size=(300, 200))
    files = {"file": ("banner.png", png_data, "image/png")}
    resp = client.post("/api/v1/inspect", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["detected_format"] == "PNG"
    assert data["width"] == 300
    assert data["height"] == 200
    assert len(data["print_sizes"]) >= 4


def test_estimate_endpoint():
    payload = {
        "width": 3000,
        "height": 2000,
        "color_mode": "CMYK",
        "bit_depth": 8,
        "dpi": 300,
        "target_format": "TIFF",
        "compression": "tiff_lzw",
        "upscale_factor": 1.0
    }
    resp = client.post("/api/v1/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pixels"] == 6_000_000
    assert data["channels"] == 4
    # 6,000,000 * 4 = 24,000,000 bytes uncompressed
    assert data["uncompressed_memory_bytes"] == 24_000_000
    assert "MB" in data["uncompressed_memory_human"]


def test_convert_endpoint_multipart_tiff_download():
    png_data = create_in_memory_image_bytes(fmt="PNG", size=(200, 200))
    files = {"file": ("sari_pattern.png", png_data, "image/png")}
    data = {
        "output_format": "TIFF",
        "dpi": 300,
        "color_mode": "CMYK",
        "tiff_compression": "tiff_lzw"
    }
    resp = client.post("/api/v1/convert", files=files, data=data)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/tiff"
    assert "attachment" in resp.headers["content-disposition"]
    assert "X-Quality-Report-B64" in resp.headers

    # Decode and verify header quality report
    report_raw = base64.b64decode(resp.headers["X-Quality-Report-B64"]).decode("utf-8")
    report = json.loads(report_raw)
    assert report["output"]["format"] == "TIFF"
    assert report["output"]["mode"] == "CMYK"
    assert report["quality"]["format_valid"] is True


def test_convert_endpoint_json_mode():
    png_data = create_in_memory_image_bytes(fmt="PNG", size=(100, 100))
    b64_str = base64.b64encode(png_data).decode("utf-8")

    payload = {
        "image_base64": b64_str,
        "options": {
            "output_format": "BMP",
            "dpi": 150,
            "color_mode": "RGB"
        }
    }
    resp = client.post("/api/v1/convert", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["output_format"] == "BMP"
    assert data["image_base64"] is not None
    assert data["quality_report"]["output"]["format"] == "BMP"
