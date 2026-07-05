const uploadZone    = document.getElementById('upload-zone');
const fileInput     = document.getElementById('file-input');
const selModel      = document.getElementById('sel-model');
const selColor      = document.getElementById('sel-color');
const selOrientation= document.getElementById('sel-orientation');
const preview       = document.getElementById('preview');
const downloadBtn   = document.getElementById('download');
const errorMsg      = document.getElementById('error-msg');
const spinner       = document.getElementById('spinner');

let devicesData = {};
let currentFile = null;
let currentObjectUrl = null;

// ── Upload zone ──────────────────────────────────────────────────────────────

uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  currentFile = file;
  maybeComposite();
}

// ── Device selection ─────────────────────────────────────────────────────────

async function loadDevices() {
  try {
    const resp = await fetch('/api/devices');
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    devicesData = await resp.json();
    populateSelect(selModel, Object.keys(devicesData).sort(), true);
  } catch (err) {
    errorMsg.textContent = `Failed to load devices: ${err.message}`;
  }
}

function populateSelect(sel, options, enabled) {
  sel.innerHTML = '<option value="">— select —</option>';
  options.forEach(opt => {
    const o = document.createElement('option');
    o.value = opt;
    o.textContent = opt;
    sel.appendChild(o);
  });
  sel.disabled = !enabled;
}

selModel.addEventListener('change', () => {
  const model = selModel.value;
  if (!model) {
    populateSelect(selColor, [], false);
    populateSelect(selOrientation, [], false);
    return;
  }
  const colors = Object.keys(devicesData[model]).sort();
  populateSelect(selColor, colors, true);
  populateSelect(selOrientation, [], false);
  maybeComposite();
});

selColor.addEventListener('change', () => {
  const model = selModel.value;
  const color = selColor.value;
  if (!model || !color) {
    populateSelect(selOrientation, [], false);
    return;
  }
  const orientations = devicesData[model][color].sort();
  populateSelect(selOrientation, orientations, true);
  maybeComposite();
});

selOrientation.addEventListener('change', () => maybeComposite());

// ── Compositing ──────────────────────────────────────────────────────────────

function maybeComposite() {
  const ready = currentFile && selModel.value && selColor.value && selOrientation.value;
  if (!ready) return;
  runComposite();
}

async function runComposite() {
  errorMsg.textContent = '';
  spinner.style.display = 'inline';
  preview.style.display = 'none';
  downloadBtn.style.display = 'none';

  const form = new FormData();
  form.append('screenshot', currentFile);
  form.append('model', selModel.value);
  form.append('color', selColor.value);
  form.append('orientation', selOrientation.value);

  try {
    const resp = await fetch('/api/composite', { method: 'POST', body: form });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({ error: 'Unknown error' }));
      errorMsg.textContent = data.error || 'Compositing failed';
      return;
    }
    const blob = await resp.blob();
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = URL.createObjectURL(blob);
    preview.src = currentObjectUrl;
    preview.style.display = 'block';
    downloadBtn.style.display = 'inline-block';
    downloadBtn.dataset.filename =
      `${selModel.value}-${selColor.value}-${selOrientation.value}.png`;
  } catch (err) {
    errorMsg.textContent = 'Network error — is the server running?';
  } finally {
    spinner.style.display = 'none';
  }
}

downloadBtn.addEventListener('click', () => {
  if (!currentObjectUrl) return;
  const a = document.createElement('a');
  a.href = currentObjectUrl;
  a.download = downloadBtn.dataset.filename || 'screenshot-forge.png';
  a.click();
});

// ── Init ─────────────────────────────────────────────────────────────────────
loadDevices();
