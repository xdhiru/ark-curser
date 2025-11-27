
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import yaml
from utils.adb import adb_screenshot
from utils.logger import logger

# Load configuration
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"

with open(CONFIG_PATH, "r") as f:
    _vision_config = yaml.safe_load(f)

SCREENSHOT_PATH = _vision_config["screenshot_path"]

# Template paths
_USER_TEMPLATES_DIR = Path("config") / "user_templates"
_CORE_TEMPLATES_DIR = Path("Templates")


def _get_template_path(template_name: str) -> Optional[Path]:
    """
    Get template path with user override priority.
    Priority: config/user_templates/ → Templates/
    
    Returns:
        Path object or None if not found
    """
    user_path = _USER_TEMPLATES_DIR / f"{template_name}.png"
    core_path = _CORE_TEMPLATES_DIR / f"{template_name}.png"
    
    if user_path.exists():
        return user_path
    elif core_path.exists():
        return core_path
    else:
        return None


def _remove_duplicate_matches(matches: List[Dict], min_distance: float = 8) -> List[Dict]:
    """
    Remove duplicate nearby matches using clustering.
    
    Args:
        matches: List of match dictionaries with x, y, confidence
        min_distance: Minimum distance between unique matches
    
    Returns:
        List of unique matches sorted by confidence (highest first)
    """
    if not matches:
        return []
    
    unique_matches = []
    for match in matches:
        is_duplicate = any(
            ((match["x"] - u["x"])**2 + (match["y"] - u["y"])**2)**0.5 < min_distance
            for u in unique_matches
        )
        if not is_duplicate:
            unique_matches.append(match)
    
    # Sort by confidence (best first)
    unique_matches.sort(key=lambda x: x["confidence"], reverse=True)
    return unique_matches


def find_template(template_name: str, threshold: float = 0.8, min_distance: float = 8) -> List[Dict]:
    """
    Find template matches in current screenshot.
    
    Args:
        template_name: Template filename without extension
        threshold: Minimum confidence threshold (0.0-1.0)
        min_distance: Minimum pixel distance between unique matches
    
    Returns:
        List of match dictionaries: [{"x": int, "y": int, "confidence": float}, ...]
        Empty list if no matches found
    """
    adb_screenshot()
    
    # Get template path with override priority
    template_path = _get_template_path(template_name)
    if not template_path:
        logger.error(f"Template not found: {template_name}")
        raise FileNotFoundError(f"Template not found: {template_name}.png")
    
    # Load images in grayscale
    screen = cv2.imread(SCREENSHOT_PATH, cv2.IMREAD_GRAYSCALE)
    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
    
    if screen is None:
        logger.error(f"Failed to load screenshot: {SCREENSHOT_PATH}")
        return []
    
    if template is None:
        logger.error(f"Failed to load template: {template_path}")
        return []
    
    h, w = template.shape
    
    # Perform template matching
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(result >= threshold)
    
    # Create match dictionaries with center coordinates
    raw_matches = [
        {
            "x": int(x + w / 2),
            "y": int(y + h / 2),
            "confidence": float(result[y, x])
        }
        for x, y in zip(xs, ys)
    ]
    
    if not raw_matches:
        return []
    
    # Remove duplicate nearby matches
    unique_matches = _remove_duplicate_matches(raw_matches, min_distance)
    
    logger.debug(f"Template '{template_name}' found {len(unique_matches)} unique matches")
    return unique_matches