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
    app.run(debug=True, port=5001)
