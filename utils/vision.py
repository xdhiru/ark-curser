"""
Template matching utilities.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from utils.adb import get_cached_screenshot
from utils.logger import logger
from utils.config_loader import get_config_value

# Dynamic Paths
BASE_DIR = Path(__file__).resolve().parents[1]
USER_TEMPLATES = BASE_DIR / "config" / "user_templates"
CORE_TEMPLATES = BASE_DIR / "Templates"

_CACHE = {}

def _load_template(name: str) -> Optional[np.ndarray]:
    if name in _CACHE: return _CACHE[name]
    
    # Try User, then Core
    for folder in [USER_TEMPLATES, CORE_TEMPLATES]:
        path = folder / f"{name}.png"
        if path.exists():
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                _CACHE[name] = img
                return img
                
    logger.error(f"Template missing: {name}")
    return None

def find_template_in_image(screen: np.ndarray, name: str, threshold: float = 0.8) -> List[Dict]:
    """Find matches in provided image."""
    template = _load_template(name)
    if template is None: return []
    
    # Ensure Grayscale
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY) if len(screen.shape) == 3 else screen
    
    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    
    h, w = template.shape
    matches = []
    
    # Convert to list of dicts
    for y, x in zip(*loc):
        matches.append({
            "x": int(x + w/2),
            "y": int(y + h/2),
            "confidence": float(res[y, x])
        })
    
    # Filter duplicates (Simple distance check)
    unique = []
    for m in sorted(matches, key=lambda k: k['confidence'], reverse=True):
        if not any(abs(m['x'] - u['x']) < 10 and abs(m['y'] - u['y']) < 10 for u in unique):
            unique.append(m)
            
    return unique

def find_template(name: str, threshold: float = 0.8) -> List[Dict]:
    """Capture screen and find template."""
    screen = get_cached_screenshot()
    if screen is None: return []
    return find_template_in_image(screen, name, threshold)