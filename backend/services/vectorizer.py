"""
Auto-Vectorization Engine for CNC, Laser Cutting, and Embroidery.
Converts raster silhouettes, motifs, and contours into mathematical vector formats:
- Scalable Vector Graphics (SVG) with clean bezier paths.
- AutoCAD Drawing Exchange Format (DXF R12) with LWPOLYLINE entities for CNC/fabric cutters.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None
from PIL import Image


class AutoVectorizer:
    """
    Traces raster imagery to precision vector curves for CorelDRAW, CNC plotters, and embroidery.
    """

    @staticmethod
    def _trace_contours(
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        tolerance: float = 1.2
    ) -> Tuple[List[np.ndarray], int, int]:
        """Extracts and simplifies geometric polygon contours using OpenCV."""
        if cv2 is None:
            raise RuntimeError("OpenCV (opencv-python-headless) is required for vector tracing.")
        # Convert to grayscale
        gray = np.array(image.convert("L"))
        h, w = gray.shape

        # If image has alpha, use alpha channel directly as stencil mask
        if image.mode == "RGBA":
            alpha = np.array(image.split()[-1])
            if alpha.min() < 250:
                gray = alpha

        # Binary thresholding
        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        if threshold == 0:
            # Automatic Otsu thresholding
            _, binary = cv2.threshold(gray, 0, 255, thresh_type + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(gray, threshold, 255, thresh_type)

        # Morphological smoothing to eliminate single-pixel noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, hierarchy = cv2.findContours(cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        # Simplify contours to smooth vector polylines
        simplified = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 10:  # Filter microscopic speckles
                approx = cv2.approxPolyDP(cnt, epsilon=tolerance, closed=True)
                if len(approx) >= 3:
                    simplified.append(approx)

        return simplified, w, h

    def vectorize_to_svg(
        self,
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        tolerance: float = 1.2,
        fill_color: str = "#1e1e2f",
        stroke_color: str = "#a855f7"
    ) -> Tuple[str, Dict[str, Any]]:
        """Generates a clean, standard SVG XML string."""
        contours, w, h = self._trace_contours(image, threshold, invert, tolerance)

        path_elements = []
        total_points = 0

        for cnt in contours:
            points = cnt.reshape(-1, 2)
            total_points += len(points)
            if len(points) < 3:
                continue

            # M x,y L x,y ... Z
            d = f"M {points[0][0]},{points[0][1]} " + " ".join([f"L {pt[0]},{pt[1]}" for pt in points[1:]]) + " Z"
            path_elements.append(
                f'  <path d="{d}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="1" fill-rule="evenodd" />'
            )

        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <rect width="100%" height="100%" fill="none" />
  <g id="MahaShankh_Vector_Layer">
{chr(10).join(path_elements)}
  </g>
</svg>"""

        report = {
            "format": "SVG",
            "contours_traced": len(contours),
            "total_vector_vertices": total_points,
            "dimensions": [w, h],
            "file_size_bytes": len(svg_content.encode("utf-8"))
        }

        return svg_content, report

    def vectorize_to_dxf(
        self,
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        tolerance: float = 1.2
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generates standard AutoCAD R12 DXF string containing LWPOLYLINE entities.
        Compatible with CNC plasma/laser cutters, garment plotters, and embroidery software.
        """
        contours, w, h = self._trace_contours(image, threshold, invert, tolerance)

        lines = [
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER",
            "1", "AC1009",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "ENTITIES"
        ]

        total_points = 0

        for cnt in contours:
            points = cnt.reshape(-1, 2)
            total_points += len(points)
            if len(points) < 3:
                continue

            # Polyline header
            lines.extend([
                "0", "POLYLINE",
                "8", "MAHASHANKH_CUT",
                "66", "1",
                "70", "1"  # 1 = Closed polyline
            ])

            for pt in points:
                lines.extend([
                    "0", "VERTEX",
                    "8", "MAHASHANKH_CUT",
                    "10", f"{float(pt[0]):.2f}",
                    "20", f"{float(h - pt[1]):.2f}",  # Invert Y for CAD coordinate standard
                    "30", "0.0"
                ])

            lines.extend(["0", "SEQEND"])

        lines.extend([
            "0", "ENDSEC",
            "0", "EOF"
        ])

        dxf_content = "\n".join(lines) + "\n"

        report = {
            "format": "DXF",
            "cad_version": "AutoCAD R12",
            "closed_polylines": len(contours),
            "total_vertices": total_points,
            "dimensions": [w, h],
            "file_size_bytes": len(dxf_content.encode("utf-8"))
        }

        return dxf_content, report
