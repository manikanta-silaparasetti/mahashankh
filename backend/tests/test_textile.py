"""
Unit tests for Textile Pattern Engine and AutoVectorizer.
"""

import pytest
from PIL import Image
from backend.services.pattern_engine import PatternEngine
from backend.services.vectorizer import AutoVectorizer


def test_straight_pattern_repeat():
    engine = PatternEngine()
    tile = Image.new("RGB", (50, 40), color=(120, 80, 200))
    pattern, report = engine.generate_repeat(tile, repeat_x=3, repeat_y=2, mode="straight")

    assert pattern.size == (150, 80)
    assert report["total_tiles"] == 6


def test_half_drop_saree_repeat():
    engine = PatternEngine()
    tile = Image.new("RGB", (60, 60), color=(220, 100, 50))
    pattern, report = engine.generate_repeat(tile, repeat_x=4, repeat_y=3, mode="half_drop")

    assert pattern.size == (240, 180)
    assert report["mode"] == "half_drop"


def test_mirror_pattern_repeat():
    engine = PatternEngine()
    tile = Image.new("RGB", (40, 40), color=(50, 150, 250))
    pattern, report = engine.generate_repeat(tile, repeat_x=2, repeat_y=2, mode="mirror")

    assert pattern.size == (80, 80)
    assert report["mode"] == "mirror"


def test_auto_vectorization_svg():
    vectorizer = AutoVectorizer()
    # Simple image with a dark circle
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.ellipse([(30, 30), (70, 70)], fill=(0, 0, 0))

    svg_str, report = vectorizer.vectorize_to_svg(img, threshold=128)

    assert "<svg" in svg_str
    assert "</svg>" in svg_str
    assert "<path" in svg_str
    assert report["contours_traced"] >= 1
    assert report["total_vector_vertices"] > 0


def test_auto_vectorization_dxf():
    vectorizer = AutoVectorizer()
    img = Image.new("RGB", (80, 80), color=(255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (60, 60)], fill=(0, 0, 0))

    dxf_str, report = vectorizer.vectorize_to_dxf(img, threshold=128)

    assert "SECTION" in dxf_str
    assert "ENTITIES" in dxf_str
    assert "POLYLINE" in dxf_str
    assert "EOF" in dxf_str
    assert report["closed_polylines"] >= 1
