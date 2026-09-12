"""
Pydantic schemas and enums for the Image Format Conversion & Production Processing API.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator


class SupportedOutputFormat(str, Enum):
    TIFF = "TIFF"
    BMP = "BMP"
    PNG = "PNG"
    JPEG = "JPEG"
    JPG = "JPG"


class ColorModeOption(str, Enum):
    PRESERVE = "preserve"
    RGB = "RGB"
    CMYK = "CMYK"
    GRAYSCALE = "L"


class TIFFCompressionOption(str, Enum):
    NONE = "none"
    RAW = "raw"
    LZW = "tiff_lzw"
    DEFLATE = "tiff_deflate"
    PACKBITS = "packbits"


class UpscaleAlgorithm(str, Enum):
    NONE = "none"
    LANCZOS = "lanczos"
    BICUBIC = "bicubic"
    REAL_ESRGAN = "realesrgan"


class DimensionUnit(str, Enum):
    PIXELS = "px"
    INCHES = "in"
    CENTIMETERS = "cm"
    MILLIMETERS = "mm"


class PrintSizeEstimate(BaseModel):
    dpi: int = Field(..., description="DPI value evaluated")
    width_inches: float
    height_inches: float
    width_cm: float
    height_cm: float
    width_mm: float
    height_mm: float
    is_print_quality: bool = Field(
        ..., description="True if DPI is >= 300 (standard high-res commercial print quality)"
    )


class InspectResponse(BaseModel):
    valid: bool
    filename: Optional[str] = None
    detected_format: str
    mime_type: str
    file_signature: str
    width: int
    height: int
    aspect_ratio: str
    total_pixels: int
    color_mode: str
    bit_depth: int
    channels: int
    has_alpha: bool
    dpi: Tuple[float, float]
    icc_profile_present: bool
    icc_profile_name: Optional[str] = None
    exif_present: bool
    file_size_bytes: int
    file_size_human: str
    estimated_uncompressed_bytes: int
    estimated_uncompressed_human: str
    print_sizes: List[PrintSizeEstimate]
    warnings: List[str] = []


class EstimateRequest(BaseModel):
    width: int = Field(..., gt=0, le=50000, description="Pixel width")
    height: int = Field(..., gt=0, le=50000, description="Pixel height")
    color_mode: ColorModeOption = Field(default=ColorModeOption.RGB)
    bit_depth: int = Field(default=8, description="Bits per channel (8 or 16)")
    dpi: int = Field(default=300, ge=1, le=2400)
    target_format: SupportedOutputFormat = Field(default=SupportedOutputFormat.TIFF)
    compression: TIFFCompressionOption = Field(default=TIFFCompressionOption.LZW)
    upscale_factor: float = Field(default=1.0, ge=1.0, le=8.0)


class EstimateResponse(BaseModel):
    input_width: int
    input_height: int
    output_width: int
    output_height: int
    total_pixels: int
    dpi: int
    color_mode: str
    bit_depth: int
    channels: int
    uncompressed_memory_bytes: int
    uncompressed_memory_human: str
    estimated_disk_bytes_min: int
    estimated_disk_bytes_max: int
    estimated_disk_human_range: str
    physical_print_size: Dict[str, Any]
    is_safe_for_direct_processing: bool
    recommended_processing_mode: str


class ConversionOptions(BaseModel):
    output_format: SupportedOutputFormat = Field(
        default=SupportedOutputFormat.TIFF,
        description="Target raster export format (TIFF, BMP, PNG, JPEG)"
    )
    dpi: int = Field(
        default=300,
        ge=1,
        le=2400,
        description="Target DPI metadata to embed"
    )
    color_mode: ColorModeOption = Field(
        default=ColorModeOption.PRESERVE,
        description="Target color space (preserve, RGB, CMYK, L)"
    )
    tiff_compression: TIFFCompressionOption = Field(
        default=TIFFCompressionOption.LZW,
        description="Compression for TIFF exports (none, tiff_lzw, tiff_deflate, packbits)"
    )
    jpeg_quality: int = Field(
        default=95,
        ge=1,
        le=100,
        description="Quality setting for JPEG export (1-100)"
    )
    png_compression_level: int = Field(
        default=6,
        ge=0,
        le=9,
        description="ZLIB compression level for PNG (0-9)"
    )
    upscale_factor: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Optional resolution upscaling factor (1=none, 2=2x, 4=4x, 8=8x)"
    )
    upscale_algorithm: UpscaleAlgorithm = Field(
        default=UpscaleAlgorithm.LANCZOS,
        description="Algorithm for upscaling: lanczos, bicubic, or realesrgan (if installed)"
    )
    target_physical_width: Optional[float] = Field(
        default=None,
        gt=0,
        description="Optional physical target width (combined with physical_unit and DPI to compute target pixel width)"
    )
    target_physical_height: Optional[float] = Field(
        default=None,
        gt=0,
        description="Optional physical target height"
    )
    physical_unit: DimensionUnit = Field(
        default=DimensionUnit.INCHES,
        description="Unit for target_physical_width/height (in, cm, mm)"
    )
    strip_alpha_for_cmyk_or_jpeg: bool = Field(
        default=True,
        description="Composite alpha channel onto white background for formats/modes without alpha support (CMYK, JPEG, BMP)"
    )
    matte_color: Tuple[int, int, int] = Field(
        default=(255, 255, 255),
        description="RGB background color when flattening alpha channels"
    )
    custom_icc_profile_path: Optional[str] = Field(
        default=None,
        description="Optional file path to custom destination CMYK or RGB ICC profile"
    )
    add_bleed: bool = Field(
        default=False,
        description="Extend image with mirrored/clamped bleed margin for blade guillotine cutting"
    )
    bleed_margin_mm: float = Field(
        default=3.0,
        ge=0.0,
        le=50.0,
        description="Bleed margin width in millimeters (standard: 3.0mm / 0.125 in)"
    )
    bleed_fill_mode: str = Field(
        default="mirror",
        description="Bleed fill algorithm: 'mirror' (edge reflection), 'clamp', or 'matte'"
    )
    add_crop_marks: bool = Field(
        default=False,
        description="Draw corner hairline crop marks, center registration targets, and calibration swatches"
    )


class ConversionRequest(BaseModel):
    image_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded image input (alternative to multipart file upload)"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL of upstream image to fetch and process"
    )
    options: ConversionOptions = Field(default_factory=ConversionOptions)


class InputImageMetadata(BaseModel):
    format: str
    mime_type: str
    width: int
    height: int
    mode: str
    dpi: Tuple[float, float]
    size_bytes: int
    channels: int
    has_alpha: bool
    icc_profile: Optional[str] = None


class ProcessingMetadata(BaseModel):
    upscale: str
    upscaler: str
    color_conversion: str
    icc_profile_used: Optional[str] = None
    target_dpi: int
    resizing_applied: Optional[str] = None
    compression: str
    alpha_flattened: bool
    processing_time_ms: float
    bleed_applied: Optional[str] = None
    crop_marks_applied: bool = False
    peak_memory_mb: float


class OutputImageMetadata(BaseModel):
    format: str
    width: int
    height: int
    mode: str
    dpi: Tuple[float, float]
    compression: str
    size_bytes: int
    size_human: str
    bit_depth: int
    channels: int
    physical_width_in: float
    physical_height_in: float
    physical_width_cm: float
    physical_height_cm: float


class QualityAssessment(BaseModel):
    resolution_ok: bool
    color_profile_ok: bool
    format_valid: bool
    suitable_for_commercial_print: bool
    notes: List[str] = []
    warnings: List[str] = []


class QualityReport(BaseModel):
    input: InputImageMetadata
    processing: ProcessingMetadata
    output: OutputImageMetadata
    quality: QualityAssessment


class ConversionResponse(BaseModel):
    success: bool
    filename: str
    output_format: SupportedOutputFormat
    quality_report: QualityReport
    download_url: Optional[str] = None
    image_base64: Optional[str] = None


class BatchConversionItem(BaseModel):
    identifier: str
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    options: ConversionOptions = Field(default_factory=ConversionOptions)


class BatchConversionRequest(BaseModel):
    items: List[BatchConversionItem]


class BatchConversionResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: List[Dict[str, Any]]


# ─────────────────────────────────────────────
#  Phase 3 & 4: Separation, Pattern & Vector Models
# ─────────────────────────────────────────────

class SeparationChannelStats(BaseModel):
    filename: str
    ink_coverage_percent: float
    resolution: List[int]


class SeparationResponse(BaseModel):
    job_title: str
    dpi: int
    plates_generated: List[str]
    channel_stats: Dict[str, SeparationChannelStats]
    zip_size_bytes: int
    suitable_for_screen_printing: bool
    zip_base64: Optional[str] = None


class PatternRepeatMode(str, Enum):
    STRAIGHT = "straight"
    HALF_DROP = "half_drop"
    MIRROR = "mirror"


class PatternRepeatResponse(BaseModel):
    mode: str
    repeat_x: int
    repeat_y: int
    tile_dimensions: List[int]
    total_dimensions: List[int]
    total_tiles: int
    seamless_blending_applied: bool
    image_base64: Optional[str] = None


class VectorizeFormat(str, Enum):
    SVG = "svg"
    DXF = "dxf"


class VectorizeResponse(BaseModel):
    format: str
    contours_traced: int
    total_vertices: int
    dimensions: List[int]
    file_size_bytes: int
    content: str
    filename: str
