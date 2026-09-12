/**
 * MahaShankh Studio Pro — UI Utilities
 * Toast notifications, loading states, DOM helpers
 */

/* ─── Toast Notification ─── */
let toastTimeout = null;

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 * @param {number} duration ms to show (default 3500)
 */
function showToast(message, type = 'info', duration = 3500) {
  const toast = document.getElementById('toast');
  if (!toast) return;

  clearTimeout(toastTimeout);
  toast.textContent = message;
  toast.className = `show ${type}`;

  toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

/* ─── Loading Curtain ─── */
function showLoading(label = 'Processing…') {
  const curtain = document.getElementById('loadingCurtain');
  const lbl = document.getElementById('loadingLabel');
  if (!curtain) return;
  if (lbl) lbl.textContent = label;
  curtain.classList.add('active');
}

function hideLoading() {
  document.getElementById('loadingCurtain')?.classList.remove('active');
}

/* ─── Engine Status Indicator ─── */
function setEngineStatus(online) {
  const pill = document.getElementById('engineStatus');
  if (!pill) return;
  if (online) {
    pill.className = 'engine-status online';
    pill.innerHTML = `<span class="status-dot"></span><span>Engine Online</span>`;
  } else {
    pill.className = 'engine-status offline';
    pill.innerHTML = `<span class="status-dot"></span><span>Engine Offline</span>`;
  }
}

/* ─── Accordion Drawer Toggle ─── */
function toggleDrawer(drawerId) {
  const el = document.getElementById(drawerId);
  if (!el) return;
  el.classList.toggle('open');
}

/* ─── File Size Formatter ─── */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

/* ─── Populate Specs Panel: Input File ─── */
function updateSpecsInput(stats) {
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val || '—';
  };

  setVal('spec-in-format', stats?.format || '—');
  setVal('spec-in-color', stats?.color_mode || stats?.mode || '—');
  setVal('spec-in-dims', stats ? `${stats.width} × ${stats.height}` : '—');
  setVal('spec-in-dpi', stats?.dpi ? `${stats.dpi} DPI` : '—');
  setVal('spec-in-size', formatBytes(stats?.file_size_bytes));
}

/* ─── Populate Specs Panel: Output File ─── */
function updateSpecsOutput(info) {
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val || '—';
  };

  setVal('spec-out-format', info?.format || '—');
  setVal('spec-out-color', info?.colorMode || '—');
  setVal('spec-out-dpi', info?.dpi ? `${info.dpi} DPI` : '—');
  setVal('spec-out-bleed', info?.bleed || 'None');
  setVal('spec-out-marks', info?.marks || 'No');
  setVal('spec-out-size', formatBytes(AppState.outputSizeBytes));

  // Size comparison
  const sizeBefore = AppState.fileStats?.file_size_bytes || 0;
  const sizeAfter = AppState.outputSizeBytes || 0;
  if (sizeBefore > 0 && sizeAfter > 0) {
    const ratio = (sizeAfter / sizeBefore).toFixed(1);
    const compareEl = document.getElementById('sizeComparison');
    if (compareEl) {
      compareEl.style.display = 'flex';
      document.getElementById('sizeCompareFrom').textContent = formatBytes(sizeBefore);
      document.getElementById('sizeCompareTo').textContent = formatBytes(sizeAfter);
      document.getElementById('sizeCompareRatio').textContent = `${ratio}×`;
    }
  }
}

/* ─── Show/Hide Sections ─── */
function showSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = '';
    el.classList.add('visible');
  }
}
function hideSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = 'none';
    el.classList.remove('visible');
  }
}

/* ─── File Loaded State (sidebar upload zone ↔ file-loaded indicator) ─── */
function showFileLoaded(file, stats) {
  document.querySelector('.upload-zone')?.style.setProperty('display', 'none');
  const fl = document.querySelector('.file-loaded');
  if (fl) {
    fl.classList.add('visible');
    const nameEl = fl.querySelector('.file-loaded-name');
    const metaEl = fl.querySelector('.file-loaded-meta');
    if (nameEl) nameEl.textContent = file.name;
    if (metaEl && stats) {
      metaEl.textContent = `${stats.width}×${stats.height} · ${formatBytes(file.size)}`;
    }
  }
}

function resetFileLoaded() {
  document.querySelector('.upload-zone')?.style.removeProperty('display');
  document.querySelector('.file-loaded')?.classList.remove('visible');
}

/* ─── Enable/Disable Convert Button ─── */
function setConvertBtnState(enabled, label) {
  const btn = document.getElementById('convertBtn');
  if (!btn) return;
  btn.disabled = !enabled;
  if (label) btn.querySelector('.btn-label').textContent = label;
}

/* ─── Build download URL and trigger download ─── */
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/* ─── Read File as DataURL ─── */
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
