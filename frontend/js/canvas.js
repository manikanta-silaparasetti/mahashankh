/**
 * MahaShankh Studio Pro — Canvas Interactions
 * Split before/after slider, live bleed overlay drawing
 */

/* ═══════════════════════════════════════════════════════════
   BEFORE / AFTER SPLIT SLIDER
   ═══════════════════════════════════════════════════════════ */

let splitDragging = false;
let splitRatio = 0.5; // 0=all original, 1=all output

function initSplitSlider() {
  const wrapper = document.getElementById('splitWrapper');
  if (!wrapper) return;

  const handle = document.getElementById('splitHandle');

  function updateSplit(clientX) {
    const rect = wrapper.getBoundingClientRect();
    let ratio = (clientX - rect.left) / rect.width;
    ratio = Math.max(0.05, Math.min(0.95, ratio));
    splitRatio = ratio;

    const overlay = document.getElementById('splitOverlay');
    const handleEl = document.getElementById('splitHandle');
    if (overlay) overlay.style.width = (ratio * 100) + '%';
    if (handleEl) {
      handleEl.style.left = (ratio * 100) + '%';
    }
  }

  handle?.addEventListener('mousedown', (e) => {
    e.preventDefault();
    splitDragging = true;
  });

  document.addEventListener('mousemove', (e) => {
    if (!splitDragging) return;
    updateSplit(e.clientX);
  });

  document.addEventListener('mouseup', () => { splitDragging = false; });

  // Touch support
  handle?.addEventListener('touchstart', (e) => {
    e.preventDefault();
    splitDragging = true;
  }, { passive: false });

  document.addEventListener('touchmove', (e) => {
    if (!splitDragging) return;
    updateSplit(e.touches[0].clientX);
  }, { passive: true });

  document.addEventListener('touchend', () => { splitDragging = false; });
}

/**
 * Load images into the split slider.
 * @param {string} originalURL - DataURL of original input
 * @param {string} outputURL   - DataURL of converted output
 */
function loadSplitImages(originalURL, outputURL) {
  const baseImg = document.getElementById('splitBaseImg');
  const overlayImg = document.getElementById('splitOverlayImg');
  if (baseImg) baseImg.src = outputURL;   // base = output (right)
  if (overlayImg) overlayImg.src = originalURL; // overlay = original (left)
  splitRatio = 0.5;
  const overlay = document.getElementById('splitOverlay');
  const handleEl = document.getElementById('splitHandle');
  if (overlay) overlay.style.width = '50%';
  if (handleEl) handleEl.style.left = '50%';
}

/* ═══════════════════════════════════════════════════════════
   LIVE BLEED OVERLAY — draws on #bleedOverlayCanvas
   Shows red dashed trim line + green safe zone
   ═══════════════════════════════════════════════════════════ */

function drawBleedOverlay() {
  const canvas = document.getElementById('bleedOverlayCanvas');
  if (!canvas) return;

  const imgEl = document.getElementById('originalPreviewImg');
  if (!imgEl || !imgEl.naturalWidth) return;

  // Match canvas to displayed image size
  const rect = imgEl.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const enabled = AppState.settings.addBleed && AppState.ui.bleedOverlayEnabled;
  if (!enabled || !AppState.uploadedFile) {
    return;
  }

  const bleedMm = AppState.settings.bleedMarginMm;
  const dpi = AppState.settings.dpi;
  // Convert mm to pixels at output DPI, then scale to display size
  const bleedPx_output = (bleedMm / 25.4) * dpi;
  const scaleX = rect.width / (AppState.fileStats?.width || rect.width);
  const scaleY = rect.height / (AppState.fileStats?.height || rect.height);
  const bleedPx_display_x = bleedPx_output * scaleX;
  const bleedPx_display_y = bleedPx_output * scaleY;

  const W = canvas.width;
  const H = canvas.height;

  // Draw bleed zone overlay (semi-transparent dark sides)
  ctx.fillStyle = 'rgba(139, 92, 246, 0.12)';
  // Top
  ctx.fillRect(0, 0, W, bleedPx_display_y);
  // Bottom
  ctx.fillRect(0, H - bleedPx_display_y, W, bleedPx_display_y);
  // Left
  ctx.fillRect(0, bleedPx_display_y, bleedPx_display_x, H - 2 * bleedPx_display_y);
  // Right
  ctx.fillRect(W - bleedPx_display_x, bleedPx_display_y, bleedPx_display_x, H - 2 * bleedPx_display_y);

  // Green safe zone inner rectangle (3mm inside trim)
  const safePx_x = bleedPx_display_x + 8;
  const safePx_y = bleedPx_display_y + 8;
  ctx.beginPath();
  ctx.rect(safePx_x, safePx_y, W - 2 * safePx_x, H - 2 * safePx_y);
  ctx.setLineDash([5, 4]);
  ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Red dashed trim cut line
  ctx.beginPath();
  ctx.rect(bleedPx_display_x, bleedPx_display_y, W - 2 * bleedPx_display_x, H - 2 * bleedPx_display_y);
  ctx.setLineDash([6, 5]);
  ctx.strokeStyle = 'rgba(244, 63, 94, 0.9)';
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.setLineDash([]);

  // Labels
  ctx.font = '600 9px "JetBrains Mono", monospace';
  ctx.fillStyle = 'rgba(244, 63, 94, 0.9)';
  ctx.fillText(`Trim Edge (${bleedMm}mm bleed)`, bleedPx_display_x + 4, bleedPx_display_y - 4);

  ctx.fillStyle = 'rgba(16, 185, 129, 0.8)';
  ctx.fillText('Safe Zone', safePx_x + 4, safePx_y + 12);
}

function clearBleedOverlay() {
  const canvas = document.getElementById('bleedOverlayCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/* Re-draw on image resize (debounced) */
let _bleedRedrawTimer = null;
function scheduleBleedRedraw() {
  clearTimeout(_bleedRedrawTimer);
  _bleedRedrawTimer = setTimeout(drawBleedOverlay, 120);
}
