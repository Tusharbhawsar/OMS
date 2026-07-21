
"""Branded, single-purpose upload page served at the backend root.

The only operator-facing backend UI we expose is "upload outage data". This
page posts to POST {API}/uploads/outage-data and renders a friendly result.
The {{API_BASE}} placeholder is substituted at request time with the configured
/api/v1 prefix, and {{LOGO_SRC}} with a base64 data URI of the Cognizant logo.
"""

import base64
from pathlib import Path

_LOGO_PATH = Path(__file__).parent / "cog_logo.jpg"
try:
    LOGO_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
except FileNotFoundError:
    LOGO_DATA_URI = ""

UPLOAD_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="theme-color" content="#000048" />
  <title>Outage Communication System · Data Upload — Cognizant</title>
  <style>
    /* ═══ COGNIZANT BRAND TOKENS ═══ */
    :root {
      --cog-navy: #000048;
      --cog-navy-hover: #0A0A6A;
      --cog-primary: #2E308E;
      --cog-primary-hover: #25267A;
      --cog-primary-light: #EEEEF9;
      --cog-accent: #06C7CC;
      --cog-accent-hover: #05A8AC;
      --cog-accent-light: #E4F9FA;
      --cog-bg: #F7F7F5;
      --cog-surface: #FFFFFF;
      --cog-surface-2: #F0F0EE;
      --cog-text-1: #000048;
      --cog-text-2: #53565A;
      --cog-text-3: #97999B;
      --cog-border: #D0D0CE;
      --cog-border-2: #ADADAB;
      --cog-danger: #B81F2D;
      --cog-danger-bg: #FFF0F0;
      --cog-success: #2DB81F;
      --cog-success-bg: #F0FDF0;
      --cog-warning: #D97706;
      --cog-warning-bg: #FFFBEB;

      --cog-shadow-sm: 0 1px 3px rgba(0, 0, 72, 0.07);
      --cog-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
      --cog-shadow-lg: 0 12px 32px rgba(0, 0, 72, 0.14);

      --cog-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

      --radius-sm: 6px;
      --radius:    10px;
      --radius-lg: 16px;

      /* Legacy aliases (any old class references resolve to brand colors) */
      --bg: var(--cog-bg);
      --panel: var(--cog-surface);
      --panel-2: var(--cog-surface-2);
      --line: var(--cog-border);
      --text: var(--cog-text-1);
      --muted: var(--cog-text-2);
      --brand: var(--cog-accent);
      --brand-2: var(--cog-primary);
      --ok: var(--cog-success);
      --err: var(--cog-danger);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--cog-font);
      color: var(--cog-text-1);
      background: var(--cog-bg);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    ::selection {
      background: var(--cog-primary-light);
      color: var(--cog-primary);
    }

    /* ═══ COGNIZANT TOP BAR ═══ */
    .cog-header {
      position: sticky;
      top: 0;
      z-index: 40;
      color: #fff;
      background: linear-gradient(90deg, #000048 0%, #0A0A6A 55%, #1A1B7A 100%);
      box-shadow: var(--cog-shadow-md);
    }
    .cog-header-inner {
      max-width: 1400px;
      margin: 0 auto;
      height: 64px;
      padding: 0 24px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .cog-mark {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: #fff;
    }
    .cog-mark svg { display: block; }
    .cog-logo-img {
      display: block;
      height: 36px;
      width: auto;
    }
    .cog-mark .cog-wordmark {
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      color: #fff;
    }
    .cog-header-divider {
      width: 1px;
      height: 28px;
      background: rgba(255, 255, 255, 0.25);
    }
    .cog-header-product {
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      color: #fff;
    }
    .cog-header-accent {
      height: 2px;
      width: 100%;
      background: linear-gradient(90deg, #06C7CC 0%, #2E308E 50%, #06C7CC 100%);
    }

    /* ═══ LAYOUT ═══ */
    main.shell-wrap {
      width: 100%;
      max-width: 760px;
      margin: 0 auto;
      padding: 28px 20px 56px;
    }

    /* ═══ WELCOME BANNER ═══ */
    .cog-banner {
      position: relative;
      overflow: hidden;
      border-radius: 12px;
      background: linear-gradient(120deg, #000048 0%, #1A1B7A 45%, #2E308E 100%);
      box-shadow: var(--cog-shadow-md);
      padding: 24px 28px;
      color: #fff;
      margin-bottom: 22px;
    }
    .cog-banner::before, .cog-banner::after {
      content: "";
      position: absolute;
      pointer-events: none;
      border-radius: 50%;
      filter: blur(12px);
    }
    .cog-banner::before {
      top: -6rem; right: -6rem;
      width: 18rem; height: 18rem;
      background: radial-gradient(circle at center, rgba(6, 199, 204, 0.55) 0%, rgba(6, 199, 204, 0) 70%);
    }
    .cog-banner::after {
      bottom: -6rem; left: 33%;
      width: 14rem; height: 14rem;
      background: radial-gradient(circle at center, rgba(46, 48, 142, 0.6) 0%, rgba(46, 48, 142, 0) 70%);
    }
    .cog-banner-inner { position: relative; }
    .cog-banner-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      background: rgba(255, 255, 255, 0.06);
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: rgba(255, 255, 255, 0.85);
    }
    .cog-banner-pill .dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #06C7CC;
      box-shadow: 0 0 8px #06C7CC;
    }
    .cog-banner h1 {
      margin: 10px 0 6px;
      font-size: 1.6rem;
      font-weight: 600;
      line-height: 1.25;
      letter-spacing: -0.025em;
      color: #fff;
    }
    .cog-banner h1 .cog-accent { color: var(--cog-accent); }
    .cog-banner p {
      margin: 6px 0 0;
      font-size: 0.875rem;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.8);
      max-width: 36rem;
    }

    /* ═══ CARD ═══ */
    .card {
      background: var(--cog-surface);
      border: 1px solid var(--cog-border);
      border-radius: var(--radius);
      padding: 24px 26px;
      box-shadow: var(--cog-shadow-sm);
    }

    /* ═══ DROPZONE ═══ */
    .dropzone {
      border: 2px dashed var(--cog-border-2);
      border-radius: var(--radius);
      padding: 36px 20px;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.15s ease, background 0.15s ease;
      background: var(--cog-surface-2);
    }
    .dropzone:hover {
      border-color: var(--cog-primary);
      background: var(--cog-primary-light);
    }
    .dropzone.drag {
      border-color: var(--cog-accent);
      background: var(--cog-accent-light);
    }
    .dz-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 52px;
      height: 52px;
      border-radius: 12px;
      background: #fff;
      color: var(--cog-primary);
      box-shadow: var(--cog-shadow-sm);
    }
    .dz-title {
      margin: 14px 0 4px;
      font-size: 15px;
      font-weight: 600;
      color: var(--cog-text-1);
    }
    .dz-sub { color: var(--cog-text-2); font-size: 13px; }

    /* ═══ FILE PILL ═══ */
    .file-pill {
      display: none;
      margin-top: 14px;
      align-items: center;
      gap: 10px;
      background: var(--cog-primary-light);
      border: 1px solid rgba(46, 48, 142, 0.25);
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      font-size: 13.5px;
      justify-content: space-between;
      color: var(--cog-text-1);
    }
    .file-pill .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
    .file-pill button {
      background: transparent;
      border: 1px solid transparent;
      color: var(--cog-text-3);
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
      padding: 2px 6px;
      border-radius: 4px;
      transition: color 0.15s ease, background 0.15s ease;
    }
    .file-pill button:hover {
      color: var(--cog-danger);
      background: var(--cog-danger-bg);
    }

    /* ═══ OPTION CHECKBOXES ═══ */
    .options { display: flex; flex-wrap: wrap; gap: 16px; margin: 20px 0 22px; }
    .opt {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      flex: 1 1 240px;
      padding: 12px 14px;
      background: var(--cog-surface-2);
      border: 1px solid var(--cog-border);
      border-radius: var(--radius-sm);
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    .opt:hover { border-color: var(--cog-primary); background: var(--cog-primary-light); }
    .opt input[type="checkbox"] {
      margin-top: 3px;
      width: 16px; height: 16px;
      accent-color: var(--cog-primary);
      cursor: pointer;
    }
    .opt label {
      font-size: 14px;
      font-weight: 600;
      color: var(--cog-text-1);
      cursor: pointer;
    }
    .opt .hint {
      display: block;
      color: var(--cog-text-2);
      font-size: 12px;
      font-weight: 400;
      margin-top: 3px;
      line-height: 1.45;
    }

    /* ═══ PRIMARY BUTTON ═══ */
    .btn {
      width: 100%;
      border: 1px solid transparent;
      cursor: pointer;
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      font-family: var(--cog-font);
      padding: 13px 18px;
      border-radius: var(--radius-sm);
      background: var(--cog-accent);
      box-shadow: var(--cog-shadow-sm);
      transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.05s ease;
    }
    .btn:hover {
      background: var(--cog-accent-hover);
      box-shadow: var(--cog-shadow-md);
      transform: translateY(-1px);
    }
    .btn:focus-visible {
      outline: none;
      box-shadow: 0 0 0 3px rgba(6, 199, 204, 0.3);
    }
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
      background: var(--cog-border);
      color: rgba(255, 255, 255, 0.85);
      box-shadow: none;
    }

    /* ═══ RESULT BANNERS ═══ */
    .result {
      margin-top: 20px;
      display: none;
      border-radius: var(--radius-sm);
      padding: 14px 16px;
      font-size: 13.5px;
      line-height: 1.55;
    }
    .result.ok {
      display: block;
      background: var(--cog-success-bg);
      border: 1px solid rgba(45, 184, 31, 0.3);
      color: #166534;
    }
    .result.err {
      display: block;
      background: var(--cog-danger-bg);
      border: 1px solid rgba(184, 31, 45, 0.3);
      color: var(--cog-danger);
    }
    .result h3 {
      margin: 0 0 8px;
      font-size: 14.5px;
      font-weight: 600;
    }
    .result.ok h3 { color: #166534; }
    .result.err h3 { color: var(--cog-danger); }

    /* ═══ CHIPS ═══ */
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .chip {
      background: #fff;
      border: 1px solid var(--cog-border);
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      color: var(--cog-text-1);
      font-weight: 500;
    }
    .chip b { color: var(--cog-primary); font-weight: 700; }

    /* ═══ FOOTER ═══ */
    .foot {
      margin-top: 22px;
      text-align: center;
      font-size: 13px;
      color: var(--cog-text-3);
    }
    .foot a {
      color: var(--cog-primary);
      text-decoration: none;
      font-weight: 500;
    }
    .foot a:hover {
      color: var(--cog-primary-hover);
      text-decoration: underline;
    }

    /* ═══ SPINNER ═══ */
    .spinner {
      width: 14px; height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.45);
      border-top-color: #fff;
      border-radius: 50%;
      display: inline-block;
      vertical-align: -2px;
      margin-right: 8px;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ═══ MOBILE ═══ */
    @media (max-width: 640px) {
      .cog-header-inner { padding: 0 16px; height: 56px; }
      .cog-header-product { font-size: 0.88rem; }
      main.shell-wrap { padding: 18px 14px 40px; }
      .cog-banner { padding: 20px; }
      .cog-banner h1 { font-size: 1.35rem; }
      .card { padding: 18px 18px; }
      .dropzone { padding: 28px 16px; }
    }
  </style>
</head>
<body>
  <header class="cog-header">
    <div class="cog-header-inner">
      <a href="/" class="cog-mark" aria-label="Cognizant home">
        <img src="{{LOGO_SRC}}" alt="Cognizant" class="cog-logo-img" />
      </a>
      <span class="cog-header-divider" aria-hidden="true"></span>
      <span class="cog-header-product">Outage Communication System</span>
    </div>
    <div class="cog-header-accent" aria-hidden="true"></div>
  </header>

  <main class="shell-wrap">

    <div class="cog-banner">
      <div class="cog-banner-inner">
        <span class="cog-banner-pill">
          <span class="dot" aria-hidden="true"></span>
          Phase 1 &middot; Data Upload
        </span>
        <h1>Upload <span class="cog-accent">Outage Data</span></h1>
      </div>
    </div>

    <div class="card">
      <div id="dropzone" class="dropzone">
        <div class="dz-icon" aria-hidden="true">
          <!-- Upload glyph -->
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div class="dz-title">Drag &amp; drop your workbook here</div>
        <div class="dz-sub">or click to browse &mdash; accepts .xlsx or .csv</div>
        <input id="file" type="file" accept=".xlsx,.csv" hidden />
      </div>

      <div id="filePill" class="file-pill">
        <span class="name" id="fileName"></span>
        <button id="clearFile" title="Remove">&times;</button>
      </div>

      <div class="options">
        <div class="opt">
          <input id="testMode" type="checkbox" checked />
          <label for="testMode">Update Data
            <span class="hint">Rebase outage times to "now + offset" so notifications fall due immediately.</span>
          </label>
        </div>
        <div class="opt">
          <input id="reset" type="checkbox" checked />
          <label for="reset">Reset Database
            <span class="hint">Wipe current data first so this upload fully replaces it.</span>
          </label>
        </div>
      </div>

      <button id="submit" class="btn" disabled>Upload data</button>

      <div id="result" class="result"></div>
    </div>

    <div class="foot">
      Looking for the raw endpoint? <a href="/docs">Open API docs &rarr;</a>
    </div>

  </main>

  <script>
    const API_BASE = "{{API_BASE}}";
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file");
    const filePill = document.getElementById("filePill");
    const fileName = document.getElementById("fileName");
    const clearFile = document.getElementById("clearFile");
    const submit = document.getElementById("submit");
    const result = document.getElementById("result");
    let selected = null;

    function setFile(f) {
      selected = f;
      if (f) {
        fileName.textContent = f.name;
        filePill.style.display = "flex";
        submit.disabled = false;
      } else {
        filePill.style.display = "none";
        submit.disabled = true;
        fileInput.value = "";
      }
    }

    dropzone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => setFile(fileInput.files[0] || null));
    clearFile.addEventListener("click", (e) => { e.stopPropagation(); setFile(null); result.className = "result"; });

    ["dragenter", "dragover"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); }));
    dropzone.addEventListener("drop", (e) => {
      const f = e.dataTransfer.files[0];
      if (f) setFile(f);
    });

    submit.addEventListener("click", async () => {
      if (!selected) return;
      const testMode = document.getElementById("testMode").checked;
      const reset = document.getElementById("reset").checked;
      const url = `${API_BASE}/uploads/outage-data?update_data=${testMode}&reset_database=${reset}`;
      const form = new FormData();
      form.append("file", selected);

      submit.disabled = true;
      submit.innerHTML = '<span class="spinner"></span>Uploading&hellip;';
      result.className = "result";

      try {
        const res = await fetch(url, { method: "POST", body: form });
        const body = await res.json();
        if (!res.ok) throw new Error(body.message || `Upload failed (${res.status})`);
        const tables = body.data && body.data.imported_tables ? body.data.imported_tables : {};
        const chips = Object.entries(tables)
          .map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`)
          .join("");
        result.className = "result ok";
        result.innerHTML = `<h3>&#9989; ${body.message || "Imported successfully"}</h3>
          <div>File: <b>${(body.data && body.data.file_name) || selected.name}</b></div>
          <div class="chips">${chips || '<span class="chip">No rows imported</span>'}</div>`;
      } catch (err) {
        result.className = "result err";
        result.innerHTML = `<h3>&#10060; Upload failed</h3><div>${err.message}</div>`;
      } finally {
        submit.disabled = false;
        submit.textContent = "Upload data";
      }
    });
  </script>
</body>
</html>
"""
