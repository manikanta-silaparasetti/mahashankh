/**
 * MahaShankh Studio Pro — Global App State
 * Single source of truth for all runtime data
 */

const AppState = {
  /* ─── File Input ─── */
  uploadedFile: null,       // File object from input
  uploadedDataURL: null,    // base64 preview URL for canvas
  fileStats: null,          // { name, size, type, width, height, dpi, colorMode }

  /* ─── Output ─── */
  outputBlob: null,         // Blob of converted file
  outputDataURL: null,      // base64 preview of output
  outputFilename: null,     // suggested filename for download
  outputSizeBytes: 0,
  qualityReport: null,      // JSON quality report from API

  /* ─── Mode ─── */
  mode: 'converter',        // 'converter' | 'separation' | 'pattern' | 'vector'

  /* ─── Processing State ─── */
  isProcessing: false,

  /* ─── Converter Settings ─── */
  settings: {
    outputFormat:    'TIFF',
    dpi:             300,
    colorMode:       'PRESERVE',
    compression:     'tiff_lzw',
    upscaleFactor:   1,
    upscaleAlgorithm:'realesrgan',
    addBleed:        false,
    bleedMarginMm:   3.0,
    bleedFillMode:   'mirror',
    addCropMarks:    false,
    removeBackground:false,
  },

  /* ─── Pattern Settings ─── */
  patternSettings: {
    repeatMode: 'halfdrop',  // 'halfdrop' | 'straight' | 'mirror'
    cols: 3,
    rows: 3,
  },

  /* ─── Vectorize Settings ─── */
  vectorSettings: {
    threshold:      127,
    epsilon:        2.0,
    exportFormat:  'svg',    // 'svg' | 'dxf' | 'both'
  },

  /* ——— CMYK Plate Settings ——— */
  separationSettings: {
    jobTitle: 'MahaShankh-Job',
    selectedPlate: 'composite',
    dpi: 300,
  },

  /* ─── UI State ─── */
  ui: {
    activeViewTab: 'original',   // 'original' | 'split' | 'proof'
    bleedOverlayEnabled: true,
    isDraggingOverDrop: false,
  },
};

/**
 * Update a nested path in settings.
 * e.g. setSetting('settings.dpi', 300)
 */
function setSetting(path, value) {
  const parts = path.split('.');
  let obj = AppState;
  for (let i = 0; i < parts.length - 1; i++) {
    obj = obj[parts[i]];
  }
  obj[parts[parts.length - 1]] = value;
}

/**
 * Serialize current settings into a flat object for API calls.
 */
function getConverterPayload() {
  const s = AppState.settings;
  return {
    output_format:      s.outputFormat,
    dpi:                s.dpi,
    color_mode:         s.colorMode,
    compression:        s.compression,
    upscale_factor:     s.upscaleFactor,
    upscale_algorithm:  s.upscaleAlgorithm,
    add_bleed:          s.addBleed,
    bleed_margin_mm:    s.bleedMarginMm,
    bleed_fill_mode:    s.bleedFillMode,
    add_crop_marks:     s.addCropMarks,
    remove_background:  s.removeBackground,
  };
}
