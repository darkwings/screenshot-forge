# Screenshot Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask web app that composites a user-uploaded screenshot into an Apple iPhone bezel PNG and returns a transparent PNG.

**Architecture:** Flask backend exposes two routes — `/api/devices` (filesystem scan) and `/api/composite` (Pillow compositing). Frontend is a single HTML page with vanilla JS: cascading dropdowns, drag-and-drop upload, live preview, download button. No persistence — everything is in-memory.

**Tech Stack:** Python 3.9+, Flask, Pillow, NumPy, pytest; vanilla HTML/CSS/JS (no framework).

## Global Constraints

- Python 3.9+ required (uses `tuple[int,int,int,int]` type hints)
- Assets live at `iOS Assets/Bezel iPhone/{Model}/{Model} - {Color} - {Orientation}.png` — never move or rename them
- Output PNG must have transparent background (RGBA, no white fill)
- No authentication, no file storage on disk, no batch processing
- All paths are relative to project root

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `app.py` (skeleton only)
- Create: `composite.py` (skeleton only)
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: runnable Flask skeleton at `http://localhost:5000` returning 200 on `/`

- [ ] **Step 1: Create `requirements.txt`**

```
Flask>=3.0
Pillow>=10.0
numpy>=1.26
pytest>=8.0
```

- [ ] **Step 2: Create `app.py` skeleton**

```python
import io
import os

from flask import Flask, jsonify, request, send_file, send_from_directory

import composite

app = Flask(__name__, static_folder="static")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "iOS Assets", "Bezel iPhone")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/devices")
def devices():
    return jsonify(composite.list_devices(ASSETS_DIR))


@app.route("/api/composite", methods=["POST"])
def do_composite():
    if "screenshot" not in request.files:
        return jsonify({"error": "missing screenshot"}), 400
    model = request.form.get("model")
    color = request.form.get("color")
    orientation = request.form.get("orientation")
    if not all([model, color, orientation]):
        return jsonify({"error": "missing model, color, or orientation"}), 400
    frame_path = os.path.join(ASSETS_DIR, model, f"{model} - {color} - {orientation}.png")
    if not os.path.isfile(frame_path):
        return jsonify({"error": "frame not found"}), 400
    screenshot_bytes = request.files["screenshot"].read()
    try:
        result = composite.composite_screenshot(frame_path, screenshot_bytes)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return send_file(io.BytesIO(result), mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

- [ ] **Step 3: Create `composite.py` skeleton**

```python
from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image


def list_devices(assets_dir: str) -> dict:
    raise NotImplementedError


def find_screen_rect(frame_img: Image.Image) -> tuple[int, int, int, int]:
    raise NotImplementedError


def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    raise NotImplementedError


def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    raise NotImplementedError
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 5: Create `static/` directory and placeholder `index.html`**

```html
<!doctype html>
<html><body><h1>Screenshot Forge</h1></body></html>
```

- [ ] **Step 6: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.DS_Store
```

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: Flask, Pillow, numpy, pytest installed with no errors.

- [ ] **Step 8: Verify Flask starts**

```bash
python app.py
```

Expected: `Running on http://127.0.0.1:5000`. Ctrl+C to stop.

- [ ] **Step 9: Commit**

```bash
git add requirements.txt app.py composite.py tests/__init__.py static/index.html .gitignore
git commit -m "feat: scaffold Flask project with skeleton routes"
```

---

### Task 2: Asset discovery — `list_devices`

**Files:**
- Modify: `composite.py` — implement `list_devices`
- Create: `tests/test_composite.py`

**Interfaces:**
- Consumes: `assets_dir` string path to `iOS Assets/Bezel iPhone/`
- Produces: `list_devices(assets_dir: str) -> dict[str, dict[str, list[str]]]`
  - shape: `{"iPhone 17 Pro": {"Deep Blue": ["Portrait", "Landscape"], ...}, ...}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_composite.py`:

```python
import os
import pytest
from composite import list_devices

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "iOS Assets", "Bezel iPhone")


def test_list_devices_returns_nonempty_dict():
    result = list_devices(ASSETS_DIR)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_list_devices_structure():
    result = list_devices(ASSETS_DIR)
    for model, colors in result.items():
        assert isinstance(colors, dict), f"{model}: colors must be dict"
        for color, orientations in colors.items():
            assert isinstance(orientations, list), f"{model}/{color}: orientations must be list"
            for o in orientations:
                assert o in ("Portrait", "Landscape"), f"unexpected orientation: {o}"


def test_list_devices_known_model():
    result = list_devices(ASSETS_DIR)
    assert "iPhone 17 Pro" in result
    assert "Deep Blue" in result["iPhone 17 Pro"]
    assert "Portrait" in result["iPhone 17 Pro"]["Deep Blue"]
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_composite.py -v
```

Expected: 3 failures with `NotImplementedError`.

- [ ] **Step 3: Implement `list_devices` in `composite.py`**

Replace the `list_devices` stub:

```python
def list_devices(assets_dir: str) -> dict:
    result: dict[str, dict[str, list[str]]] = {}
    if not os.path.isdir(assets_dir):
        return result
    for model in sorted(os.listdir(assets_dir)):
        model_path = os.path.join(assets_dir, model)
        if not os.path.isdir(model_path) or model.startswith("."):
            continue
        result[model] = {}
        for filename in sorted(os.listdir(model_path)):
            if not filename.endswith(".png") or filename.startswith("."):
                continue
            stem = filename[:-4]          # strip .png
            parts = stem.split(" - ")     # e.g. ["iPhone 17 Pro", "Deep Blue", "Portrait"]
            if len(parts) < 3:
                continue
            color = parts[-2]
            orientation = parts[-1]
            result[model].setdefault(color, [])
            if orientation not in result[model][color]:
                result[model][color].append(orientation)
    return result
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_composite.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add composite.py tests/test_composite.py
git commit -m "feat: implement list_devices — scans iOS Assets folder"
```

---

### Task 3: Screen region detection — `find_screen_rect`

**Files:**
- Modify: `composite.py` — implement `find_screen_rect`
- Modify: `tests/test_composite.py` — add tests

**Interfaces:**
- Consumes: `frame_img: Image.Image` (RGBA)
- Produces: `find_screen_rect(frame_img) -> tuple[int, int, int, int]` — `(x, y, width, height)` in pixels

- [ ] **Step 1: Add failing tests to `tests/test_composite.py`**

Append:

```python
from PIL import Image
from composite import find_screen_rect

PORTRAIT_FRAME = os.path.join(
    ASSETS_DIR, "iPhone 17 Pro", "iPhone 17 Pro - Deep Blue - Portrait.png"
)
LANDSCAPE_FRAME = os.path.join(
    ASSETS_DIR, "iPhone 17 Pro", "iPhone 17 Pro - Deep Blue - Landscape.png"
)


def test_find_screen_rect_portrait_within_bounds():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert x >= 0 and y >= 0
    assert w > 0 and h > 0
    assert x + w <= frame.width
    assert y + h <= frame.height


def test_find_screen_rect_portrait_is_tall():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert h > w, "portrait screen rect must be taller than wide"


def test_find_screen_rect_landscape_is_wide():
    frame = Image.open(LANDSCAPE_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert w > h, "landscape screen rect must be wider than tall"


def test_find_screen_rect_screen_smaller_than_frame():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert w < frame.width
    assert h < frame.height
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_composite.py::test_find_screen_rect_portrait_within_bounds -v
```

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement `find_screen_rect` in `composite.py`**

Replace the `find_screen_rect` stub:

```python
def find_screen_rect(frame_img: Image.Image) -> tuple[int, int, int, int]:
    arr = np.array(frame_img)
    alpha = arr[:, :, 3]
    transparent = alpha < 50
    rows_with_transparent = np.any(transparent, axis=1)
    cols_with_transparent = np.any(transparent, axis=0)
    row_indices = np.where(rows_with_transparent)[0]
    col_indices = np.where(cols_with_transparent)[0]
    if len(row_indices) == 0 or len(col_indices) == 0:
        raise ValueError("No transparent region found in frame — cannot locate screen area")
    rmin, rmax = int(row_indices[0]), int(row_indices[-1])
    cmin, cmax = int(col_indices[0]), int(col_indices[-1])
    return cmin, rmin, cmax - cmin + 1, rmax - rmin + 1
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_composite.py -v
```

Expected: all tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add composite.py tests/test_composite.py
git commit -m "feat: implement find_screen_rect — auto-detects transparent screen area"
```

---

### Task 4: Compositing — `crop_to_fit` + `composite_screenshot`

**Files:**
- Modify: `composite.py` — implement `crop_to_fit` and `composite_screenshot`
- Modify: `tests/test_composite.py` — add tests

**Interfaces:**
- Consumes: `find_screen_rect` (Task 3)
- Produces:
  - `crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image`
  - `composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes` — PNG bytes, RGBA, transparent background

- [ ] **Step 1: Add failing tests**

Append to `tests/test_composite.py`:

```python
import io
from composite import crop_to_fit, composite_screenshot


def test_crop_to_fit_returns_exact_size():
    img = Image.new("RGBA", (100, 200), (255, 0, 0, 255))
    result = crop_to_fit(img, 50, 80)
    assert result.size == (50, 80)


def test_crop_to_fit_upscale():
    img = Image.new("RGBA", (50, 100), (0, 255, 0, 255))
    result = crop_to_fit(img, 200, 400)
    assert result.size == (200, 400)


def test_crop_to_fit_landscape_to_portrait():
    img = Image.new("RGBA", (400, 200), (0, 0, 255, 255))
    result = crop_to_fit(img, 100, 300)
    assert result.size == (100, 300)


def _make_png(w: int = 400, h: int = 800, color=(100, 149, 237, 255)) -> bytes:
    img = Image.new("RGBA", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_composite_screenshot_returns_png_rgba():
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result))
    assert out.format == "PNG"
    assert out.mode == "RGBA"


def test_composite_screenshot_has_transparent_background():
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result)).convert("RGBA")
    # top-left corner is outside any device bezel — must be transparent
    assert out.getpixel((0, 0))[3] == 0, "top-left pixel must be transparent"


def test_composite_screenshot_output_matches_frame_size():
    frame = Image.open(PORTRAIT_FRAME)
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result))
    assert out.size == frame.size
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_composite.py -k "crop_to_fit or composite_screenshot" -v
```

Expected: 7 failures with `NotImplementedError`.

- [ ] **Step 3: Implement `crop_to_fit` in `composite.py`**

Replace stub:

```python
def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))
```

- [ ] **Step 4: Implement `composite_screenshot` in `composite.py`**

Replace stub:

```python
def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    frame = Image.open(frame_path).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    screenshot = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
    screenshot = crop_to_fit(screenshot, w, h)
    canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    canvas.paste(screenshot, (x, y))
    result = Image.alpha_composite(canvas, frame)
    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
```

- [ ] **Step 5: Run all tests — confirm they pass**

```bash
pytest tests/test_composite.py -v
```

Expected: all tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add composite.py tests/test_composite.py
git commit -m "feat: implement crop_to_fit and composite_screenshot"
```

---

### Task 5: Flask API — routes + API tests

**Files:**
- Modify: `app.py` — already complete from Task 1 (no changes needed)
- Create: `tests/test_api.py`

**Interfaces:**
- Consumes: `composite.list_devices`, `composite.composite_screenshot` (Tasks 2 & 4)
- Produces: tested HTTP API on `/api/devices` and `/api/composite`

- [ ] **Step 1: Create `tests/test_api.py`**

```python
import io
import os
import pytest
from PIL import Image
from app import app as flask_app

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "iOS Assets", "Bezel iPhone")


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _make_png(w: int = 400, h: int = 800) -> bytes:
    img = Image.new("RGB", (w, h), (100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_devices_returns_200_json(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "iPhone 17 Pro" in data


def test_composite_missing_screenshot_returns_400(client):
    resp = client.post("/api/composite", data={
        "model": "iPhone 17 Pro",
        "color": "Deep Blue",
        "orientation": "Portrait",
    })
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_composite_missing_fields_returns_400(client):
    resp = client.post(
        "/api/composite",
        data={"screenshot": (io.BytesIO(_make_png()), "ss.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_composite_invalid_frame_returns_400(client):
    resp = client.post(
        "/api/composite",
        data={
            "screenshot": (io.BytesIO(_make_png()), "ss.png"),
            "model": "iPhone 99 Fake",
            "color": "Invisible",
            "orientation": "Portrait",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_composite_returns_png(client):
    resp = client.post(
        "/api/composite",
        data={
            "screenshot": (io.BytesIO(_make_png()), "ss.png"),
            "model": "iPhone 17 Pro",
            "color": "Deep Blue",
            "orientation": "Portrait",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    out = Image.open(io.BytesIO(resp.data))
    assert out.mode == "RGBA"
```

- [ ] **Step 2: Run tests — confirm they pass**

```bash
pytest tests/test_api.py -v
```

Expected: 5 PASSED.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "feat: add API integration tests"
```

---

### Task 6: Frontend — HTML + CSS

**Files:**
- Modify: `static/index.html` (replace placeholder)
- Create: `static/style.css`

**Interfaces:**
- Produces: styled page with upload zone, three `<select>` elements, `<img id="preview">`, `<button id="download">`; all wired via `id` attributes that `app.js` (Task 7) will reference

- [ ] **Step 1: Write `static/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  gap: 2rem;
}

h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  align-items: flex-end;
}

.control-group { display: flex; flex-direction: column; gap: 0.3rem; }

label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6e6e73; }

select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  font-size: 0.95rem;
  background: #fff;
  min-width: 160px;
  cursor: pointer;
}

select:disabled { opacity: 0.4; cursor: not-allowed; }

#upload-zone {
  width: 100%;
  max-width: 420px;
  border: 2px dashed #d2d2d7;
  border-radius: 16px;
  padding: 2.5rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: #fff;
}

#upload-zone.drag-over { border-color: #0071e3; background: #f0f6ff; }
#upload-zone p { color: #6e6e73; font-size: 0.9rem; margin-top: 0.5rem; }

#preview-area {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

#preview {
  max-width: 100%;
  max-height: 520px;
  display: none;
  border-radius: 4px;
  /* checkerboard background to show transparency */
  background-image:
    linear-gradient(45deg, #ccc 25%, transparent 25%),
    linear-gradient(-45deg, #ccc 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #ccc 75%),
    linear-gradient(-45deg, transparent 75%, #ccc 75%);
  background-size: 16px 16px;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0px;
}

#download {
  display: none;
  padding: 0.6rem 1.5rem;
  background: #0071e3;
  color: #fff;
  border: none;
  border-radius: 980px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

#download:hover { background: #0077ed; }

#error-msg {
  color: #ff3b30;
  font-size: 0.875rem;
  min-height: 1.2em;
}

#spinner {
  display: none;
  font-size: 0.875rem;
  color: #6e6e73;
}
```

- [ ] **Step 2: Write `static/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Screenshot Forge</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <h1>Screenshot Forge</h1>

  <div id="upload-zone">
    <input type="file" id="file-input" accept="image/png,image/jpeg" hidden />
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#6e6e73" stroke-width="1.5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
    <p>Drop screenshot here or click to browse</p>
  </div>

  <div class="controls">
    <div class="control-group">
      <label for="sel-model">Model</label>
      <select id="sel-model"><option value="">— select —</option></select>
    </div>
    <div class="control-group">
      <label for="sel-color">Color</label>
      <select id="sel-color" disabled><option value="">— select —</option></select>
    </div>
    <div class="control-group">
      <label for="sel-orientation">Orientation</label>
      <select id="sel-orientation" disabled><option value="">— select —</option></select>
    </div>
  </div>

  <div id="preview-area">
    <span id="spinner">Compositing…</span>
    <span id="error-msg"></span>
    <img id="preview" alt="Preview" />
    <button id="download">Download PNG</button>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Start app and verify page loads**

```bash
python app.py
```

Open `http://localhost:5000` — page should display with upload zone and disabled dropdowns. Ctrl+C to stop.

- [ ] **Step 4: Commit**

```bash
git add static/index.html static/style.css
git commit -m "feat: add frontend HTML and CSS"
```

---

### Task 7: Frontend JS — `app.js`

**Files:**
- Create: `static/app.js`

**Interfaces:**
- Consumes: `/api/devices` (GET), `/api/composite` (POST multipart)
- Consumes DOM ids: `file-input`, `upload-zone`, `sel-model`, `sel-color`, `sel-orientation`, `preview`, `download`, `error-msg`, `spinner`

- [ ] **Step 1: Create `static/app.js`**

```javascript
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
  const resp = await fetch('/api/devices');
  devicesData = await resp.json();
  populateSelect(selModel, Object.keys(devicesData).sort(), true);
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
```

- [ ] **Step 2: Start app and test manually**

```bash
python app.py
```

Manual test steps:
1. Open `http://localhost:5000`
2. Model dropdown should be populated (iPhone 17, iPhone 17 Pro, etc.)
3. Drag a PNG screenshot onto the upload zone
4. Select model → color → orientation
5. Preview should appear with checkerboard background
6. Download button should trigger PNG download
7. Open downloaded PNG — transparent background, device bezel, screenshot inside

- [ ] **Step 3: Commit**

```bash
git add static/app.js
git commit -m "feat: add frontend JS — device selection, live preview, download"
```

---

### Task 8: README

**Files:**
- Create: `README.md`

**Interfaces:**
- None (documentation only)

- [ ] **Step 1: Create `README.md`**

```markdown
# Screenshot Forge

Local web app: composite your iOS app screenshots into official Apple iPhone device frames.

## Getting Apple's Device Assets

1. Go to **[Apple Design Resources](https://developer.apple.com/design/resources/)** on Apple's developer site
2. Scroll to **iPhone** under the *Product Bezels* section
3. Download the Bezel PNG packages for the models you want (e.g. *iPhone 17 Pro Bezels*)
4. Unzip each package

After unzipping, you will find PNG files named like:
```
iPhone 17 Pro - Deep Blue - Portrait.png
iPhone 17 Pro - Deep Blue - Landscape.png
```

Save them inside this project following this exact structure:

```
iOS Assets/
└── Bezel iPhone/
    ├── iPhone 17/
    │   ├── iPhone 17 - Black - Portrait.png
    │   ├── iPhone 17 - Black - Landscape.png
    │   └── ...
    ├── iPhone 17 Pro/
    │   ├── iPhone 17 Pro - Deep Blue - Portrait.png
    │   └── ...
    └── iPhone 17 Pro Max/
        └── ...
```

The app auto-discovers any PNG placed here — no config needed.

## Requirements

- Python 3.9 or later
- pip

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open your browser at **http://localhost:5000**.

## Usage

1. Drop your app screenshot (PNG or JPG) onto the upload zone
2. Select the iPhone model, color, and orientation
3. The composited image appears as a live preview
4. Click **Download PNG** to save the result (transparent background)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with asset download instructions and setup guide"
```

---

## Self-Review

**Spec coverage:**
- ✅ Flask backend with `/api/devices` and `/api/composite`
- ✅ Pillow compositing with auto-detect screen rect
- ✅ Python + Flask + Pillow + NumPy
- ✅ Cascading dropdowns populated from filesystem
- ✅ Drag & drop upload
- ✅ Live preview with checkerboard transparency indicator
- ✅ Download PNG with meaningful filename
- ✅ Transparent PNG output (RGBA)
- ✅ README with asset download instructions and folder structure

**Placeholder scan:** No TBD, TODO, or vague steps found. All code blocks are complete.

**Type consistency:**
- `list_devices` → `dict[str, dict[str, list[str]]]` — consistent across Task 2 and Task 5 tests
- `find_screen_rect(frame_img: Image.Image)` — Task 3 produces it; Task 4's `composite_screenshot` calls it internally (not exposed across task boundary)
- `composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes` — Task 4 produces; Task 5 (`app.py`) already calls it via the route

All consistent. ✅
