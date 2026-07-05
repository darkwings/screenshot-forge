# Screenshot Forge — Design Spec
**Date:** 2026-07-05

## Overview

Personal web app: upload an app screenshot, select an iPhone device frame (from Apple's official bezel assets), get back a transparent PNG with the device border composited around the screenshot.

## Tech Stack

- **Backend:** Python 3 + Flask
- **Image processing:** Pillow
- **Frontend:** Vanilla HTML + CSS + JS (single page, no framework)
- **Assets:** existing `iOS Assets/Bezel iPhone/` folder (untouched)

## File Structure

```
screenshot-forge/
├── app.py              # Flask server, API routes
├── composite.py        # Pillow compositing logic
├── requirements.txt
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── iOS Assets/         # Apple bezel PNGs — read-only
    └── Bezel iPhone/
        ├── iPhone 17/
        ├── iPhone 17 Pro/
        ├── iPhone 17 Pro Max/
        └── iPhone Air/
```

## API

### `GET /api/devices`

Returns JSON tree of available assets, parsed dynamically from the filesystem. No hardcoded device list.

```json
{
  "iPhone 17 Pro": {
    "Deep Blue": ["Portrait", "Landscape"],
    "Silver": ["Portrait", "Landscape"],
    "Cosmic Orange": ["Portrait", "Landscape"]
  },
  ...
}
```

### `POST /api/composite`

Multipart form:
- `screenshot`: image file (PNG/JPG)
- `model`: e.g. `"iPhone 17 Pro"`
- `color`: e.g. `"Deep Blue"`
- `orientation`: `"Portrait"` or `"Landscape"`

Response: PNG file (Content-Type: image/png), transparent background.

## Compositing Algorithm

1. Load frame PNG as RGBA
2. Find bounding box of all pixels where `alpha < 50` → `screen_rect (x, y, w, h)`
3. Load user screenshot, convert to RGBA
4. Resize screenshot to `(w, h)` using centered crop (maintain aspect ratio; crop excess rather than letterbox)
5. Create blank RGBA canvas sized to frame dimensions
6. Paste screenshot at `(x, y)` on canvas
7. Alpha-composite frame PNG over canvas
8. Return result as PNG bytes

The output PNG has a transparent background — only the device bezel and the screenshot inside are opaque.

## Frontend

Single HTML page:

- **Upload zone:** drag & drop or click-to-browse, accepts PNG/JPG
- **Cascading dropdowns:** Model → Color → Orientation (populated from `/api/devices`; Color and Orientation reset on Model change)
- **Live preview:** on upload or dropdown change, POST to `/api/composite`, display result in `<img>` tag (checkerboard background to show transparency)
- **Download button:** saves the composited PNG; filename pattern: `{model}-{color}-{orientation}.png`

Preview updates are debounced — only fire when all three selections and a screenshot are present.

## Error Handling

- Backend returns HTTP 400 with JSON `{"error": "..."}` for missing fields or unsupported files
- Frontend shows inline error message below preview area
- No transparent-region found → 500 with descriptive error (signals corrupt/unexpected asset)

## Out of Scope

- No authentication (personal tool, local use)
- No file persistence (in-memory processing only)
- No support for non-iPhone assets (iPad, Mac) unless added to `iOS Assets/` folder later
- No batch processing
