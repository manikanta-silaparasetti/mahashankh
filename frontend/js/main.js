/**
 * MahaShankh Studio Pro — Main Application
 * App initialization, mode switcher, upload handling,
 * converter + all mode logic, event wiring.
 */

/* ═══════════════════════════════════════════════════════════
   APP INITIALIZATION
   ═══════════════════════════════════════════════════════════ */

async function initApp() {
  console.log('[MahaShankh] Initializing Studio Pro…');

  // Init tooltip system
  initTooltipSystem();

  // Init split slider
  initSplitSlider();

  // Check engine health
  const online = await apiCheckHealth();
  setEngineStatus(online);
  if (!online) {
    showToast('⚠ Backend engine offline. Start the server with START.bat', 'error', 6000);
  }

  // Wire upload zones (sidebar + canvas onboarding)
  wireUploadZones();

  // Wire format picker cards
  wireFormatPicker();

  // Wire DPI tiles
  wireDpiTiles();

  // Wire color space tiles
  wireColorTiles();

  // Wire bleed controls
  wireBleedControls();

  // Wire CMYK plate DPI tiles
  wireSepDpiTiles();

  // Wire mode tabs
  wireModeTabsBar();

  // Wire convert button
  document.getElementById('convertBtn')?.addEventListener('click', handleConvert);

  // Wire separation button
  document.getElementById('separateBtn')?.addEventListener('click', handleSeparate);

  // Wire pattern button
  document.getElementById('patternBtn')?.addEventListener('click', handlePattern);

  // Wire vectorize button
  document.getElementById('vectorBtn')?.addEventListener('click', handleVectorize);

  // Wire view tabs (original / split / proof)
  wireViewTabs();

  // Wire download button
  document.getElementById('downloadBtn')?.addEventListener('click', handleDownload);

  // Wire re-upload button
  document.querySelector('.btn-reupload')?.addEventListener('click', resetToUploadState);

  // Window resize — redraw bleed overlay
  window.addEventListener('resize', scheduleBleedRedraw);

  console.log('[MahaShankh] Ready.');
}

/* ═══════════════════════════════════════════════════════════
   UPLOAD ZONE WIRING
   ═══════════════════════════════════════════════════════════ */

function wireUploadZones() {
  const sidebarInput = document.getElementById('sidebarFileInput');
  const canvasInput = document.getElementById('canvasFileInput');

  // Both sidebar and canvas inputs trigger the same handler
  [sidebarInput, canvasInput].forEach(input => {
    input?.addEventListener('change', (e) => {
      if (e.target.files?.[0]) handleFileSelected(e.target.files[0]);
    });
  });

  // Drag-over visual feedback on canvas onboarding zone
  const dropZone = document.getElementById('canvasOnboarding');
  dropZone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.querySelector('.onboarding-drop-zone')?.classList.add('dragover');
  });
  dropZone?.addEventListener('dragleave', () => {
    dropZone.querySelector('.onboarding-drop-zone')?.classList.remove('dragover');
  });
  dropZone?.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.querySelector('.onboarding-drop-zone')?.classList.remove('dragover');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileSelected(file);
  });

  // Sidebar drag-over
  const sidebarZone = document.querySelector('.upload-zone');
  sidebarZone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    sidebarZone.classList.add('dragover');
  });
  sidebarZone?.addEventListener('dragleave', () => sidebarZone.classList.remove('dragover'));
  sidebarZone?.addEventListener('drop', (e) => {
    e.preventDefault();
    sidebarZone.classList.remove('dragover');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileSelected(file);
  });
}

async function handleFileSelected(file) {
  if (!file.type.startsWith('image/') && !file.name.match(/\.(tif|tiff|bmp|webp)$/i)) {
    showToast('Please upload an image file (JPEG, PNG, TIFF, BMP, WebP)', 'error');
    return;
  }

  AppState.uploadedFile = file;

  // Read preview
  const dataURL = await readFileAsDataURL(file);
  AppState.uploadedDataURL = dataURL;

  // Show preview in canvas
  showOriginalPreview(dataURL);

  // Hide onboarding, show canvas preview
  hideSection('canvasOnboarding');
  showSection('previewContainer');
  showSection('canvasToolbar');

  // Enable mode tabs
  document.querySelectorAll('.mode-tab').forEach(t => t.removeAttribute('disabled'));

  // Enable view tabs
  document.querySelectorAll('.view-tab').forEach(t => t.removeAttribute('disabled'));

  // Try to inspect file for metadata
  try {
    const stats = await apiInspect(file);
    AppState.fileStats = stats;
    updateSpecsInput(stats);
    showFileLoaded(file, stats);
    setConvertBtnState(true, 'Convert & Render');
  } catch (err) {
    // Inspection failed — still allow conversion with basic info
    AppState.fileStats = { width: '?', height: '?', file_size_bytes: file.size };
    showFileLoaded(file, AppState.fileStats);
    setConvertBtnState(true, 'Convert & Render');
  }

  // Show sidebar controls that were collapsed
  document.querySelectorAll('.drawer').forEach(d => {
    if (d.dataset.autoOpen === 'true') d.classList.add('open');
  });

  // Draw bleed overlay (if enabled)
  scheduleBleedRedraw();

  showToast(`✓ ${file.name} loaded`, 'success');
}

function showOriginalPreview(dataURL) {
  const img = document.getElementById('originalPreviewImg');
  if (!img) return;
  img.src = dataURL;
  img.onload = () => scheduleBleedRedraw();

  // Reset view to 'original'
  switchViewTab('original');
}

function resetToUploadState() {
  AppState.uploadedFile = null;
  AppState.uploadedDataURL = null;
  AppState.outputBlob = null;
  AppState.outputDataURL = null;
  AppState.fileStats = null;
  AppState.outputSizeBytes = 0;

  resetFileLoaded();
  hideSection('previewContainer');
  hideSection('canvasToolbar');
  showSection('canvasOnboarding');

  clearBleedOverlay();

  // Reset specs
  updateSpecsInput(null);
  updateSpecsOutput(null);
  setConvertBtnState(false, 'Convert & Render');

  // Disable output view tabs
  ['viewSplit', 'viewProof'].forEach(id => {
    document.getElementById(id)?.setAttribute('disabled', 'true');
  });

  // Hide rename + download section
  hideDownloadSection();

  // Hide ink coverage report
  const inkStats = document.getElementById('plateInkStats');
  if (inkStats) inkStats.style.display = 'none';

  // Hide size comparison
  const sc = document.getElementById('sizeComparison');
  if (sc) sc.style.display = 'none';
}

/* ═══════════════════════════════════════════════════════════
   MODE SWITCHER
   ═══════════════════════════════════════════════════════════ */

function wireModeTabsBar() {
  document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const mode = tab.dataset.mode;
      if (mode) switchMode(mode);
    });
  });
}

function switchMode(mode) {
  AppState.mode = mode;

  // Update tab active state
  document.querySelectorAll('.mode-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.mode === mode);
  });

  // Show correct sidebar mode panel
  document.querySelectorAll('.mode-panel').forEach(p => {
    p.classList.toggle('active', p.dataset.mode === mode);
  });

  // Update canvas view based on mode
  switch (mode) {
    case 'converter':
      showCanvasView('preview');
      break;
    case 'separation':
      showCanvasView('preview');
      break;
    case 'pattern':
      showCanvasView('pattern');
      break;
    case 'vector':
      showCanvasView('vector');
      break;
  }
}

function showCanvasView(view) {
  // Show/hide each view container
  const preview = document.getElementById('previewContainer');
  const pattern = document.getElementById('patternCanvas');
  const vector  = document.getElementById('vectorContainer');

  if (preview) preview.style.display = (view === 'preview') ? '' : 'none';
  if (pattern) pattern.style.display = (view === 'pattern') ? '' : 'none';
  if (vector)  vector.style.display  = (view === 'vector')  ? '' : 'none';
}

/* ═══════════════════════════════════════════════════════════
   VIEW TABS (Original / Split / Proof)
   ═══════════════════════════════════════════════════════════ */

function wireViewTabs() {
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const view = tab.dataset.view;
      if (!tab.disabled) switchViewTab(view);
    });
  });
}

function switchViewTab(view) {
  AppState.ui.activeViewTab = view;

  document.querySelectorAll('.view-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.view === view);
  });

  const previewContainer = document.getElementById('previewContainer');
  const splitWrapper = document.getElementById('splitWrapper');
  const singleImg = document.getElementById('originalPreviewImg');

  if (view === 'original') {
    if (singleImg) singleImg.style.display = '';
    if (splitWrapper) splitWrapper.style.display = 'none';
    drawBleedOverlay();
  } else if (view === 'split') {
    if (singleImg) singleImg.style.display = 'none';
    if (splitWrapper) splitWrapper.style.display = '';
    clearBleedOverlay();
  } else if (view === 'proof') {
    // Show output only
    if (singleImg) {
      singleImg.style.display = '';
      if (AppState.outputDataURL) singleImg.src = AppState.outputDataURL;
    }
    if (splitWrapper) splitWrapper.style.display = 'none';
    clearBleedOverlay();
  }
}

/* ═══════════════════════════════════════════════════════════
   FORMAT PICKER CARDS
   ═══════════════════════════════════════════════════════════ */

function wireFormatPicker() {
  document.querySelectorAll('input[name="output_format"]').forEach(radio => {
    radio.addEventListener('change', () => {
      AppState.settings.outputFormat = radio.value;
      // Auto-set compression hint
      if (radio.value === 'TIFF') AppState.settings.compression = 'tiff_lzw';
      else if (radio.value === 'PNG') AppState.settings.compression = 'png_deflate';
      else if (radio.value === 'JPEG') AppState.settings.compression = 'jpeg_dct';

      // Sync the extension badge in Rename Before Save (if visible)
      const extBadge = document.getElementById('outputExtBadge');
      const section = document.getElementById('downloadSection');
      if (extBadge && section && section.style.display !== 'none') {
        extBadge.textContent = getExtForFormat(radio.value);
      }

      // Update the rename input suffix hint if visible
      const nameInput = document.getElementById('outputFilenameInput');
      if (nameInput && section && section.style.display !== 'none') {
        // If user hasn't custom-named yet, auto-update based on original filename + new format
        const currentVal = nameInput.value;
        // Replace known format suffixes at end if they match a format name
        const cleaned = currentVal.replace(/_(TIFF|PNG|BMP|JPEG|tiff|png|bmp|jpeg)$/i, '');
        nameInput.value = cleaned;
      }
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   DPI TILE SELECTOR
   ═══════════════════════════════════════════════════════════ */

function wireDpiTiles() {
  // Only target converter DPI tiles (data-dpi, not data-sep-dpi)
  document.querySelectorAll('.dpi-tile[data-dpi]').forEach(tile => {
    tile.addEventListener('click', () => {
      const dpi = parseInt(tile.dataset.dpi, 10);
      AppState.settings.dpi = dpi;

      // Deactivate only converter DPI tiles
      document.querySelectorAll('.dpi-tile[data-dpi]').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');

      scheduleBleedRedraw();
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   COLOR SPACE TILES
   ═══════════════════════════════════════════════════════════ */

function wireColorTiles() {
  document.querySelectorAll('.color-tile').forEach(tile => {
    tile.addEventListener('click', () => {
      AppState.settings.colorMode = tile.dataset.colorMode;
      document.querySelectorAll('.color-tile').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   BLEED CONTROLS
   ═══════════════════════════════════════════════════════════ */

function wireBleedControls() {
  // Bleed toggle switch
  document.getElementById('bleedToggle')?.addEventListener('change', (e) => {
    AppState.settings.addBleed = e.target.checked;
    scheduleBleedRedraw();
  });

  // Bleed margin slider
  document.getElementById('bleedSlider')?.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    AppState.settings.bleedMarginMm = val;
    const lbl = document.getElementById('bleedSliderVal');
    if (lbl) lbl.textContent = val.toFixed(1) + ' mm';
    scheduleBleedRedraw();
  });

  // Fill mode select
  document.getElementById('bleedFillMode')?.addEventListener('change', (e) => {
    AppState.settings.bleedFillMode = e.target.value;
  });

  // Crop marks toggle
  document.getElementById('cropMarksToggle')?.addEventListener('change', (e) => {
    AppState.settings.addCropMarks = e.target.checked;
  });

  // Live overlay toggle
  document.getElementById('bleedOverlayToggle')?.addEventListener('change', (e) => {
    AppState.ui.bleedOverlayEnabled = e.target.checked;
    e.target.checked ? scheduleBleedRedraw() : clearBleedOverlay();
  });

  // Background removal toggle
  document.getElementById('bgRemovalToggle')?.addEventListener('change', (e) => {
    AppState.settings.removeBackground = e.target.checked;
  });

  // Upscale factor select
  document.getElementById('upscaleFactor')?.addEventListener('change', (e) => {
    AppState.settings.upscaleFactor = parseInt(e.target.value, 10);
  });

  // Upscale algorithm select
  document.getElementById('upscaleAlgorithm')?.addEventListener('change', (e) => {
    AppState.settings.upscaleAlgorithm = e.target.value;
  });
}

/* ═══════════════════════════════════════════════════════════
   CMYK PLATE DPI TILES
   ═══════════════════════════════════════════════════════════ */

function wireSepDpiTiles() {
  document.querySelectorAll('.dpi-tile[data-sep-dpi]').forEach(tile => {
    tile.addEventListener('click', () => {
      const dpi = parseInt(tile.dataset.sepDpi, 10);
      AppState.separationSettings.dpi = dpi;
      document.querySelectorAll('.dpi-tile[data-sep-dpi]').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   APPLY QUICK PRESET
   ═══════════════════════════════════════════════════════════ */

function applyPreset(format, dpi, colorMode) {
  // Update state
  AppState.settings.outputFormat = format;
  AppState.settings.dpi = dpi;
  AppState.settings.colorMode = colorMode;

  // Update format card
  const radio = document.querySelector(`input[name="output_format"][value="${format}"]`);
  if (radio) radio.checked = true;

  // Update DPI tile
  document.querySelectorAll('.dpi-tile').forEach(t => {
    t.classList.toggle('active', parseInt(t.dataset.dpi) === dpi);
  });

  // Update color tile
  document.querySelectorAll('.color-tile').forEach(t => {
    t.classList.toggle('active', t.dataset.colorMode === colorMode);
  });

  scheduleBleedRedraw();
  showToast(`Preset applied: ${format} · ${dpi} DPI · ${colorMode}`, 'info');
}

/* ═══════════════════════════════════════════════════════════
   CONVERT ACTION
   ═══════════════════════════════════════════════════════════ */

async function handleConvert() {
  if (!AppState.uploadedFile) {
    showToast('Please upload an image first', 'error');
    return;
  }
  if (AppState.isProcessing) return;

  AppState.isProcessing = true;
  setConvertBtnState(false, 'Processing…');
  showLoading('Converting image…');

  try {
    const payload = getConverterPayload();
    const result = await apiConvert(AppState.uploadedFile, payload);

    // Store output
    AppState.outputBlob = result.blob;
    AppState.outputSizeBytes = result.blob.size;
    AppState.outputFilename = result.filename;

    // Generate output preview
    const outputDataURL = await new Promise(resolve => {
      const reader = new FileReader();
      reader.onload = e => resolve(e.target.result);
      reader.readAsDataURL(result.blob);
    });
    AppState.outputDataURL = outputDataURL;

    // Load split slider
    if (AppState.uploadedDataURL) {
      loadSplitImages(AppState.uploadedDataURL, outputDataURL);
    }

    // Update specs
    updateSpecsOutput({
      format: AppState.settings.outputFormat,
      colorMode: AppState.settings.colorMode,
      dpi: AppState.settings.dpi,
      bleed: AppState.settings.addBleed ? `${AppState.settings.bleedMarginMm}mm` : 'None',
      marks: AppState.settings.addCropMarks ? 'Yes' : 'No',
    });

    // Enable output view tabs
    document.getElementById('viewSplit')?.removeAttribute('disabled');
    document.getElementById('viewProof')?.removeAttribute('disabled');

    // Show download section with filename and extension
    const ext = getExtForFormat(AppState.settings.outputFormat);
    showDownloadSection(result.filename, ext, result.blob);

    // Switch to split view
    switchViewTab('split');

    hideLoading();
    setConvertBtnState(true, 'Convert & Render');
    AppState.isProcessing = false;

    showToast(`✓ Converted → ${result.filename} (${formatBytes(result.blob.size)})`, 'success', 5000);

  } catch (err) {
    hideLoading();
    setConvertBtnState(true, 'Convert & Render');
    AppState.isProcessing = false;
    showToast(`✗ ${err.message}`, 'error', 6000);
    console.error('[MahaShankh] Convert error:', err);
  }
}


/* ═══════════════════════════════════════════════════════════
   SEPARATE (CMYK PLATES)
   ═══════════════════════════════════════════════════════════ */

async function handleSeparate() {
  if (!AppState.uploadedFile) {
    showToast('Please upload an image first', 'error');
    return;
  }
  if (AppState.isProcessing) return;

  AppState.isProcessing = true;
  showLoading('Generating CMYK separation plates…');

  try {
    const jobTitle = document.getElementById('sepJobName')?.value.trim() || 'MahaShankh-Job';
    const dpi = AppState.separationSettings.dpi || 300;

    // First pass: get JSON response for ink coverage stats
    let inkJson = null;
    try {
      const jsonResult = await apiSeparatePlates(AppState.uploadedFile, jobTitle, dpi, true);
      inkJson = jsonResult.json;
    } catch {} // JSON report is optional, don't fail on it

    // Second pass: get the actual ZIP download
    const result = await apiSeparatePlates(AppState.uploadedFile, jobTitle, dpi, false);

    AppState.outputBlob = result.blob;
    AppState.outputFilename = result.filename;
    AppState.outputSizeBytes = result.blob.size;

    hideLoading();
    AppState.isProcessing = false;

    // Show ink coverage report if available
    if (inkJson && inkJson.channel_stats) {
      showInkCoverageReport(inkJson.channel_stats, dpi);
    }

    // Show download section with rename
    showDownloadSection(result.filename, '.zip', result.blob);

    showToast(`✓ 4 CMYK plates ready → ${result.filename} (${formatBytes(result.blob.size)})`, 'success', 5000);

  } catch (err) {
    hideLoading();
    AppState.isProcessing = false;
    showToast(`✗ ${err.message}`, 'error', 6000);
  }
}

/* ═══════════════════════════════════════════════════════════
   PATTERN REPEAT
   ═══════════════════════════════════════════════════════════ */

async function handlePattern() {
  if (!AppState.uploadedFile) {
    showToast('Please upload an image first', 'error');
    return;
  }
  if (AppState.isProcessing) return;

  AppState.isProcessing = true;
  showLoading('Generating saree pattern repeat…');

  try {
    const ps = AppState.patternSettings;
    const result = await apiPatternRepeat(
      AppState.uploadedFile, ps.repeatMode, ps.cols, ps.rows
    );

    AppState.outputBlob = result.blob;
    AppState.outputSizeBytes = result.blob.size;
    AppState.outputFilename = result.filename;

    // Display pattern on canvas
    const patCanvas = document.getElementById('patternCanvas');
    if (patCanvas) {
      const url = URL.createObjectURL(result.blob);
      patCanvas.src = url;
      patCanvas.style.display = '';
    }

    hideLoading();
    AppState.isProcessing = false;

    // Show download section with rename
    showDownloadSection(result.filename || 'saree_pattern.png', '.png', result.blob);

    showToast('✓ Saree pattern generated', 'success');

  } catch (err) {
    hideLoading();
    AppState.isProcessing = false;
    showToast(`✗ ${err.message}`, 'error', 6000);
  }
}

/* ═══════════════════════════════════════════════════════════
   VECTORIZE
   ═══════════════════════════════════════════════════════════ */

async function handleVectorize() {
  if (!AppState.uploadedFile) {
    showToast('Please upload an image first', 'error');
    return;
  }
  if (AppState.isProcessing) return;

  AppState.isProcessing = true;
  showLoading('Tracing vector paths…');

  try {
    const vs = AppState.vectorSettings;
    const result = await apiVectorize(
      AppState.uploadedFile, vs.threshold, vs.epsilon, vs.exportFormat
    );

    AppState.outputBlob = result.blob;
    AppState.outputFilename = result.filename;
    AppState.outputSizeBytes = result.blob.size;

    // Display SVG
    if (result.blob.type === 'image/svg+xml' || result.filename.endsWith('.svg')) {
      const text = await result.blob.text();
      const vecContainer = document.getElementById('vectorContainer');
      if (vecContainer) {
        vecContainer.innerHTML = text;
        vecContainer.style.display = '';
      }
    }

    hideLoading();
    AppState.isProcessing = false;

    // Show download section with rename
    const vecExt = AppState.vectorSettings.exportFormat === 'dxf' ? '.dxf' : '.svg';
    showDownloadSection(result.filename, vecExt, result.blob);

    showToast(`✓ Vector paths traced → ${result.filename}`, 'success');

  } catch (err) {
    hideLoading();
    AppState.isProcessing = false;
    showToast(`✗ ${err.message}`, 'error', 6000);
  }
}

/* ═══════════════════════════════════════════════════════════
   SHOW DOWNLOAD SECTION WITH RENAME FIELD
   ═══════════════════════════════════════════════════════════ */

/**
 * Shows the rename + download section with editable filename.
 * @param {string} suggestedName - full suggested filename (with ext)
 * @param {string} ext - e.g. '.tif', '.zip', '.png', '.svg'
 * @param {Blob} blob - the output blob to download
 */
function showDownloadSection(suggestedName, ext, blob) {
  AppState.outputBlob = blob;
  AppState.outputSizeBytes = blob ? blob.size : 0;

  const section = document.getElementById('downloadSection');
  const nameInput = document.getElementById('outputFilenameInput');
  const extBadge = document.getElementById('outputExtBadge');

  if (!section) return;

  // Strip extension from suggested name for the input
  const baseName = suggestedName
    ? suggestedName.replace(/\.[^.]+$/, '') // remove last extension
    : 'output';

  if (nameInput) nameInput.value = baseName;
  if (extBadge) extBadge.textContent = ext;

  section.style.display = 'flex';
}

function hideDownloadSection() {
  const section = document.getElementById('downloadSection');
  if (section) section.style.display = 'none';
}

/**
 * Get the file extension for a given output format.
 */
function getExtForFormat(fmt) {
  const map = { TIFF: '.tif', BMP: '.bmp', PNG: '.png', JPEG: '.jpg' };
  return map[fmt] || '.tif';
}

/**
 * Show ink coverage report in the CMYK panel after separation.
 */
function showInkCoverageReport(channelStats, dpi) {
  const container = document.getElementById('plateInkStats');
  const body = document.getElementById('plateInkStatsBody');
  if (!container || !body) return;

  const colorMap = {
    cyan:    { color: '#00BFFF', label: 'Cyan' },
    magenta: { color: '#FF00A0', label: 'Magenta' },
    yellow:  { color: '#FFD700', label: 'Yellow' },
    black:   { color: '#9CA3AF', label: 'Black (K)' },
  };

  body.innerHTML = Object.entries(channelStats).map(([ch, info]) => {
    const cfg = colorMap[ch.toLowerCase()] || { color: '#94A3B8', label: ch };
    const pct = info.ink_coverage_percent || 0;
    const barW = Math.min(100, Math.max(2, pct));
    return `<div style="display:flex; flex-direction:column; gap:3px; margin-bottom:5px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="display:flex; align-items:center; gap:5px;">
          <span style="width:8px;height:8px;border-radius:50%;background:${cfg.color};flex-shrink:0;"></span>
          <span style="font-size:0.68rem; color:var(--col-text-secondary); font-weight:600;">${cfg.label}</span>
        </div>
        <span style="font-family:var(--font-mono); font-size:0.65rem; color:var(--col-cyan);">${pct.toFixed(1)}%</span>
      </div>
      <div style="height:3px; background:rgba(255,255,255,0.07); border-radius:3px;">
        <div style="height:100%; width:${barW}%; background:${cfg.color}; border-radius:3px; opacity:0.7;"></div>
      </div>
    </div>`;
  }).join('');

  container.style.display = 'flex';
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD HANDLER
   ═══════════════════════════════════════════════════════════ */

function handleDownload() {
  if (!AppState.outputBlob) return;

  // Build filename from rename input + extension badge
  const nameInput = document.getElementById('outputFilenameInput');
  const extBadge = document.getElementById('outputExtBadge');
  const baseName = (nameInput?.value.trim() || AppState.outputFilename?.replace(/\.[^.]+$/, '') || 'output');
  const ext = extBadge?.textContent || '';
  // Sanitize: remove any illegal chars, trim spaces
  const safeName = baseName.replace(/[<>:"/\\|?*]+/g, '_').replace(/\s+/g, '_').trim() || 'output';
  const finalName = safeName + ext;

  triggerDownload(AppState.outputBlob, finalName);
  showToast(`✓ Saved as "${finalName}"`, 'success', 3000);
}

/* ═══════════════════════════════════════════════════════════
   PATTERN / VECTOR SETTINGS WIRING
   ═══════════════════════════════════════════════════════════ */

function wirePatternSettings() {
  document.getElementById('repeatMode')?.addEventListener('change', (e) => {
    AppState.patternSettings.repeatMode = e.target.value;
  });
  document.getElementById('repeatCols')?.addEventListener('input', (e) => {
    AppState.patternSettings.cols = parseInt(e.target.value, 10) || 3;
    document.getElementById('repeatColsVal').textContent = e.target.value;
  });
  document.getElementById('repeatRows')?.addEventListener('input', (e) => {
    AppState.patternSettings.rows = parseInt(e.target.value, 10) || 3;
    document.getElementById('repeatRowsVal').textContent = e.target.value;
  });
}

function wireVectorSettings() {
  document.getElementById('vecThreshold')?.addEventListener('input', (e) => {
    AppState.vectorSettings.threshold = parseInt(e.target.value, 10);
    document.getElementById('vecThresholdVal').textContent = e.target.value;
  });
  document.getElementById('vecEpsilon')?.addEventListener('input', (e) => {
    AppState.vectorSettings.epsilon = parseFloat(e.target.value);
    document.getElementById('vecEpsilonVal').textContent = parseFloat(e.target.value).toFixed(1);
  });
  document.getElementById('vecFormat')?.addEventListener('change', (e) => {
    AppState.vectorSettings.exportFormat = e.target.value;
  });
}

/* ═══════════════════════════════════════════════════════════
   BOOT
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  wirePatternSettings();
  wireVectorSettings();
});
