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
