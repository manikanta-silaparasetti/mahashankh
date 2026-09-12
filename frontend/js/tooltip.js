/**
 * MahaShankh Studio Pro — Tooltip System
 * Full-screen backdrop + frosted glass card
 * Click anywhere to open data-driven tooltip, ESC / backdrop to close.
 */

/* ───────────────────────────────────────────────
   TOOLTIP DATA DEFINITIONS
   Each key = data-tooltip attribute on .info-btn
   ─────────────────────────────────────────────── */
const TOOLTIPS = {
  'output-format': {
    badge: 'Output Container',
    title: 'Target File Format',
    what: 'Defines the file format (container) of your converted output image.',
    when: `Use <strong>TIFF</strong> for any commercial print job — sarees, packaging, offset sheets.
Use <strong>PNG</strong> when you need web images with a transparent background (alpha channel).
Use <strong>BMP</strong> for legacy RIP software or vinyl cutters that require raw uncompressed bitmap.
Use <strong>JPEG</strong> for digital delivery or email previews only — never for printing masters.`,
    proTip: 'TIFF with LZW compression is the universal industry standard for prepress. It is lossless, embeds DPI metadata, and supports CMYK 4-channel ink gamut.',
  },
  'dpi': {
    badge: 'Physical Print Density',
    title: 'Dots Per Inch (DPI)',
    what: 'DPI defines how many ink dots are placed per inch of printed paper or fabric. Higher DPI = finer detail visible to the eye.',
    when: `<strong>72 DPI</strong> — Digital screens and monitors only. Never print at 72 DPI.
<strong>150 DPI</strong> — Large outdoor banners, flex hoardings, and wall wraps (viewed from 2+ meters).
<strong>300 DPI</strong> — Commercial standard for sarees, books, offset print, and all normal printing jobs.
<strong>600 DPI</strong> — Precision packaging, fine embroidery line art, jewelry catalogues, and film positives for screen printing.`,
    proTip: 'Print shops will reject files under 300 DPI. Always use 300 DPI minimum for sarees and garment printing.',
  },
  'color-mode': {
    badge: 'Ink Gamut Separation',
    title: 'Color Space (RGB vs CMYK)',
    what: 'Defines whether the output file uses RGB (screen light mixing) or CMYK (physical ink channels).',
    when: `<strong>Preserve Original</strong> — Best for digital viewing in Windows Photos, web, or social media.
<strong>Force CMYK</strong> — Mandatory for any physical printing press, rotary textile screen, or 4-color offset machine. Uses High-Fidelity GCR for deep black ink coverage.
<strong>Force RGB</strong> — Use only for digital inkjet proofing where the printer driver converts internally.`,
    proTip: 'CMYK TIFFs look washed out in Windows Photos — this is normal! The viewer cannot render 4-channel ink gamuts. Open in Adobe Photoshop, CorelDRAW, or a RIP to see true print colors.',
  },
  'upscale-factor': {
    badge: 'Deep Learning Upscale',
    title: 'AI Resolution Multiplier',
    what: 'Multiplies the pixel dimensions of your image using AI neural inference. 4× turns a 500px image into a 2000px print-ready master.',
    when: `<strong>1× (Off)</strong> — Use when the source file is already high-resolution (3000px or more).
<strong>2× HD</strong> — For medium-quality images that need slight sharpness boost.
<strong>4× Ultra HD</strong> — Most common choice. Turns WhatsApp-quality photos into printable 300 DPI artwork.
<strong>8× Maximum</strong> — For very low-res logos or stamps that need extreme enlargement.`,
    proTip: 'Real-ESRGAN AI runs entirely on CPU using only 67MB RAM — no GPU required. It reconstructs realistic textures rather than just blurring.',
  },
  'neural-engine': {
    badge: 'Inference Backend',
    title: 'Real-ESRGAN AI vs Lanczos',
    what: 'The algorithm used to generate new pixels when enlarging the image.',
    when: `<strong>Real-ESRGAN AI</strong> — Generates realistic sharp textures, removes JPEG compression artifacts, and restores fine details. Recommended for all saree and garment artwork.
<strong>Lanczos (Classical)</strong> — Fast mathematical resampling. Use only when you need speed and the source is already sharp.`,
    proTip: 'Real-ESRGAN processes the image in 512×512 tiles with overlap padding to prevent visible seam lines.',
  },
  'add-bleed': {
    badge: 'Prepress Safeguard',
    title: 'Industrial Bleed Extension',
    what: 'Extends the artwork boundary outward past the trim cut line by mirroring edge pixels. Prevents white unprinted margins after cutting.',
    when: `<strong>Always enable</strong> for any physical print job that will be cut — brochures, saree borders, hang tags, packaging boxes.
<strong>Disable</strong> only for digital-only outputs (social media, screen display) that will never be physically cut.`,
    proTip: '3mm is the universal bleed requirement specified by virtually all commercial print shops and textile mills worldwide. Never send a print file to a shop without bleed.',
  },
  'bleed-margin': {
    badge: 'Cut Safety Zone',
    title: 'Bleed Margin Width',
    what: 'Controls how many millimeters of mirrored artwork are added beyond the trim cut line on all 4 sides.',
    when: `<strong>3mm</strong> — Universal standard for offset, digital, and screen printing.
<strong>5mm</strong> — Recommended for large-format textile and flex banners.
<strong>8-10mm</strong> — For thick material cuts like acrylic, wood, or thick card stock.`,
    proTip: 'Bleed adds actual pixel area to the output file — a 3mm bleed at 300 DPI adds 35 pixels on each side.',
  },
  'crop-marks': {
    badge: 'Printer Registration',
    title: 'Corner Crop & Registration Marks',
    what: 'Places L-shaped hairline ticks at all 4 corners and circular crosshair targets at the center of each edge. Used by operators to align cutting blades and press plates.',
    when: `<strong>Enable</strong> for any job that will be cut on a guillotine or die-cutter, or printed on a 4-color press.
<strong>Disable</strong> if the printer says "no marks needed" or for digital-only exports.`,
    proTip: 'Registration crosshairs are essential for 4-color CMYK screen printing to align each ink plate precisely.',
  },
  'bg-removal': {
    badge: 'Subject Isolation',
    title: 'AI Background Removal',
    what: 'Automatically detects and removes the image background using AI segmentation, leaving only the main subject with a transparent PNG alpha channel.',
    when: `<strong>Enable</strong> for product photography, logo extraction, motif isolation for pattern design, and any compositing workflow.
<strong>Disable</strong> for full-scene artwork, landscape photos, or fabric designs where the background is part of the design.`,
    proTip: 'After background removal, use the PNG format to preserve transparency. TIFF also supports alpha channels for prepress workflows.',
  },
  'repeat-mode': {
    badge: 'Fabric Tiling Engine',
    title: 'Saree Pattern Repeat Mode',
    what: 'Defines how the motif tile is arranged when repeating across the fabric width and length.',
    when: `<strong>Half-Drop (50% Brick)</strong> — Staggers alternating rows by 50% vertically. Prevents the eye from tracking horizontal repetition lines. Best for saree pallus and floral motifs.
<strong>Straight Grid</strong> — Rows and columns align in a perfect grid. Best for geometric or chevron patterns.
<strong>Mirror Reflection</strong> — Alternates between normal and flipped tiles for bilateral symmetry. Best for border prints.`,
    proTip: 'Half-Drop is the standard repeat mode used by over 80% of Kanchipuram and Banarasi silk weaving units.',
  },
  'vectorize-threshold': {
    badge: 'Edge Detection',
    title: 'Raster-to-Vector Threshold',
    what: 'Controls the brightness cutoff when converting pixel data into vector contour paths. Pixels brighter than the threshold become background; darker pixels become ink paths.',
    when: `<strong>127 (default)</strong> — Good for clean black-and-white line art and motifs with clear edges.
<strong>Lower value (60-100)</strong> — Captures only the darkest, most defined lines. Good for thin embroidery designs.
<strong>Higher value (160-220)</strong> — Captures more midtone detail. Good for charcoal sketches or faded prints.`,
    proTip: 'For CNC laser cutting, use a low threshold (80-100) to ensure only solid cutting paths are generated — stray paths waste machine time.',
  },
  'sep-job-name': {
    badge: 'Print Identity',
    title: 'Job / Print Run Name',
    what: 'A label string that identifies this print job. It is used in two places simultaneously.',
    when: `<strong>ZIP File Name</strong> — The downloaded archive will be named <em>YourJobName_CMYK_Separation_Plates_300DPI.zip</em>.
<strong>Plate Film Slug</strong> — Each of the 4 TIFF plate films will have your job name stamped in the plate slug area (the white border outside the artwork) so print operators can identify which plate belongs to which job.
<strong>Individual Plate Files</strong> — Inside the ZIP, each file is named <em>YourJobName_cyan_plate_300dpi.tiff</em>, etc.`,
    proTip: 'Use a descriptive name like <em>Kanchipuram-Summer-2024</em> or <em>Client-Logo-V3</em>. Avoid spaces — use hyphens or underscores. The name is written directly on the film.',
  },
};

/* ───────────────────────────────────────────────
   SINGLETON TOOLTIP ENGINE
   ─────────────────────────────────────────────── */
let tooltipOpen = false;

/**
 * Open the global tooltip card with the given data key.
 * Positions card near the trigger button, or centered on small screens.
 */
function openTooltip(key, triggerEl) {
  const data = TOOLTIPS[key];
  if (!data) return;

  const backdrop = document.getElementById('tooltipBackdrop');
  const card = document.getElementById('tooltipCard');
  if (!backdrop || !card) return;

  // Populate card
  card.querySelector('.tt-badge').textContent = data.badge;
  card.querySelector('.tt-title').textContent = data.title;

  const body = card.querySelector('.tt-body');
  body.innerHTML = '';

  if (data.what) {
    const sec = createTTSection('What it is', data.what);
    body.appendChild(sec);
  }
  if (data.when) {
    const sec = createTTSection('When to use', data.when);
    body.appendChild(sec);
  }
  if (data.proTip) {
    const tip = document.createElement('div');
    tip.className = 'tt-pro-tip';
    tip.textContent = data.proTip;
    body.appendChild(tip);
  }

  // Position card near trigger
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const CARD_W = 340;
  const CARD_MAX_H = 320;

  let top, left;
  if (triggerEl) {
    const rect = triggerEl.getBoundingClientRect();
    // Try right of trigger first
    left = rect.right + 10;
    top = rect.top - 10;
    // Clamp to viewport
    if (left + CARD_W > vw - 10) left = rect.left - CARD_W - 10;
    if (left < 10) left = (vw - CARD_W) / 2;
    if (top + CARD_MAX_H > vh - 10) top = vh - CARD_MAX_H - 10;
    if (top < 10) top = 10;
  } else {
    left = (vw - CARD_W) / 2;
    top = (vh - CARD_MAX_H) / 2;
  }

  card.style.left = left + 'px';
  card.style.top = top + 'px';

  // Show
  backdrop.classList.add('visible');
  card.classList.add('visible');
  tooltipOpen = true;
}

function createTTSection(label, htmlContent) {
  const div = document.createElement('div');
  div.className = 'tt-section';
  div.innerHTML = `<div class="tt-section-label">${label}</div><div class="tt-section-text">${htmlContent}</div>`;
  return div;
}

function closeTooltip() {
  const backdrop = document.getElementById('tooltipBackdrop');
  const card = document.getElementById('tooltipCard');
  if (!backdrop || !card) return;
  backdrop.classList.remove('visible');
  card.classList.remove('visible');
  tooltipOpen = false;
}

function initTooltipSystem() {
  // Close on backdrop click
  document.getElementById('tooltipBackdrop')?.addEventListener('click', closeTooltip);

  // Close on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && tooltipOpen) closeTooltip();
  });

  // Close button inside card
  document.getElementById('tooltipCloseBtn')?.addEventListener('click', closeTooltip);

  // Wire up all .info-btn buttons
  document.querySelectorAll('.info-btn[data-tooltip]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const key = btn.getAttribute('data-tooltip');
      if (tooltipOpen) {
        // If same tooltip is open, close it; otherwise switch
        closeTooltip();
        setTimeout(() => openTooltip(key, btn), 50);
      } else {
        openTooltip(key, btn);
      }
    });
  });
}
