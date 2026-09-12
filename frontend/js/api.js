/**
 * MahaShankh Studio Pro — API Layer
 * All fetch() calls to the backend REST API.
 * Base URL auto-detected (file:// → localhost:8000, served → relative)
 */

const API_BASE = (
  window.location.protocol === 'file:' || !window.location.port
) ? 'http://localhost:8000' : '';

/**
 * Check if the backend engine is online.
 * Returns true if healthy, false otherwise.
 */
async function apiCheckHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Inspect an image file — returns metadata without converting.
 * @param {File} file
 * @returns {Promise<object>} JSON inspection result
 */
async function apiInspect(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/api/v1/inspect`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || 'Inspection failed');
  }
  return res.json();
}

/**
 * Convert an image to the specified format/DPI/color settings.
 * Returns { blob, filename, quality, headers }
 */
async function apiConvert(file, payload) {
  const form = new FormData();
  form.append('file', file);

  // Append all conversion parameters
  Object.entries(payload).forEach(([k, v]) => {
    if (v !== null && v !== undefined) form.append(k, v);
  });

  const res = await fetch(`${API_BASE}/api/v1/convert`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    let errMsg = `Server error ${res.status}`;
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errJson.message || errMsg;
    } catch {}
    throw new Error(errMsg);
  }

  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const fnMatch = cd.match(/filename[^;=\n]*=(['"]?)([^'";\n]+)\1/);
  const filename = fnMatch ? fnMatch[2] : 'output.tif';
  const qualityHeader = res.headers.get('X-Quality-Report-B64');
  let quality = null;
  if (qualityHeader) {
    try { quality = JSON.parse(atob(qualityHeader)); } catch {}
  }

  return {
    blob,
    filename,
    quality,
    dpi:        res.headers.get('X-DPI'),
    colorMode:  res.headers.get('X-Color-Mode'),
    widthIn:    res.headers.get('X-Physical-Width-Inches'),
    heightIn:   res.headers.get('X-Physical-Height-Inches'),
  };
}

/**
 * Generate CMYK separation plates.
 * @param {File} file
 * @param {string} jobTitle — stamped on each plate film and used as ZIP/file prefix
 * @param {number} dpi — plate resolution (300 or 600)
 * @param {boolean} returnJson — if true, returns structured JSON with base64 plates and ink stats
 * Returns { blob, filename } or { json } depending on returnJson flag.
 */
async function apiSeparatePlates(file, jobTitle = 'MahaShankh-Job', dpi = 300, returnJson = false) {
  const form = new FormData();
  form.append('file', file);
  form.append('job_title', jobTitle);   // backend param name is job_title
  form.append('dpi', dpi);
  form.append('return_json', returnJson ? 'true' : 'false');

  const res = await fetch(`${API_BASE}/api/v1/separation/plates`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Separation failed');
  }

  if (returnJson) {
    const json = await res.json();
    return { json };
  }

  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const fnMatch = cd.match(/filename[^;=\n]*=(['"]?)([^'"\s;\n]+)\1/);
  const filename = fnMatch ? fnMatch[2] : `${jobTitle}_CMYK_Plates_${dpi}DPI.zip`;
  return { blob, filename };
}

/**
 * Generate seamless textile repeat pattern.
 * Returns { blob, filename }
 */
async function apiPatternRepeat(file, mode, cols, rows) {
  const form = new FormData();
  form.append('file', file);
  form.append('repeat_mode', mode);
  form.append('cols', cols);
  form.append('rows', rows);

  const res = await fetch(`${API_BASE}/api/v1/textile/pattern`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Pattern generation failed');
  }
  const blob = await res.blob();
  return { blob, filename: 'saree_pattern.png' };
}

/**
 * Vectorize raster to SVG/DXF.
 * Returns { blob, filename }
 */
async function apiVectorize(file, threshold, epsilon, exportFmt) {
  const form = new FormData();
  form.append('file', file);
  form.append('threshold', threshold);
  form.append('epsilon', epsilon);
  form.append('export_format', exportFmt);

  const res = await fetch(`${API_BASE}/api/v1/textile/vectorize`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Vectorization failed');
  }
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const fnMatch = cd.match(/filename[^;=\n]*=(['"]?)([^'";\n]+)\1/);
  const filename = fnMatch ? fnMatch[2] : 'vector.svg';
  return { blob, filename };
}
