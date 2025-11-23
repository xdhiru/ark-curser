import cv2
import numpy as np
from pathlib import Path
import yaml
from utils.adb import adb_screenshot

# Load settings.yaml
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"

with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

SCREENSHOT_PATH = cfg.get("screenshot_path")

def find_template(template_name, threshold=0.8, min_distance=8):
    """
    Looks for a template inside the screenshot.
    template_name = file WITHOUT extension (e.g. 'ok', 'start_button')
    Returns unique matches only.
    """
    adb_screenshot()
    # Construct the template file path
    template_path = Path("Templates") / f"{template_name}.png"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    screen = cv2.imread(SCREENSHOT_PATH, 0)
    template = cv2.imread(str(template_path), 0)

    if screen is None:
        print("ERROR: Screenshot path invalid or not found:", SCREENSHOT_PATH)
        return []

    if template is None:
        print("ERROR: Template invalid:", template_path)
        return []

    h, w = template.shape

    # Perform template matching
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(result >= threshold)

    raw_matches = []
    for (x, y) in zip(xs, ys):
        raw_matches.append({
            "x": int(x + w / 2),
            "y": int(y + h / 2),
            "confidence": float(result[y, x])
        })

    if not raw_matches:
        return []

    # ---- Remove duplicate close matches (clustering) ----
    unique_matches = []
    for m in raw_matches:
        too_close = False
        for u in unique_matches:
            dist = ((m["x"] - u["x"])**2 + (m["y"] - u["y"])**2) ** 0.5
            if dist < min_distance:     # collapse duplicate points
                too_close = True
                break
        if not too_close:
            unique_matches.append(m)

    # Sort final matches by confidence (best first)
    unique_matches.sort(key=lambda x: x["confidence"], reverse=True)
    print(f"find_template '{template_name}' results:", unique_matches)
    return unique_matches
