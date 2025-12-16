"""
Template matching utilities with in-memory image processing.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from .adb import get_cached_screenshot  # CHANGED: relative import
from .logger import logger  # CHANGED: relative import

# Template paths
_USER_TEMPLATES_DIR = Path("config") / "user_templates"
_CORE_TEMPLATES_DIR = Path("Templates")

# Cache for loaded templates
_TEMPLATE_CACHE: Dict[str, Optional[np.ndarray]] = {}
_TEMPLATE_PATHS: Dict[str, Optional[Path]] = {}


def _get_template_image(template_name: str) -> Optional[np.ndarray]:
    """
    Get template image with user override priority.
    Priority: config/user_templates/ → Templates/
    
    Returns:
        numpy.ndarray: Template as grayscale image, or None if not found
    """
    # Check cache first
    if template_name in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[template_name]
    
    # Find template path
    if template_name not in _TEMPLATE_PATHS:
        user_path = _USER_TEMPLATES_DIR / f"{template_name}.png"
        core_path = _CORE_TEMPLATES_DIR / f"{template_name}.png"
        
        if user_path.exists():
            _TEMPLATE_PATHS[template_name] = user_path
        elif core_path.exists():
            _TEMPLATE_PATHS[template_name] = core_path
        else:
            _TEMPLATE_PATHS[template_name] = None
    
    template_path = _TEMPLATE_PATHS[template_name]
    if not template_path:
        return None
    
    # Load template in grayscale
    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
    _TEMPLATE_CACHE[template_name] = template
    return template


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
    min_distance_sq = min_distance ** 2  # Pre-compute for performance
    
    for match in matches:
        is_duplicate = False
        x, y = match["x"], match["y"]
        
        for u in unique_matches:
            dx = x - u["x"]
            dy = y - u["y"]
            if dx*dx + dy*dy < min_distance_sq:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_matches.append(match)
    
    # Sort by confidence (best first)
    unique_matches.sort(key=lambda x: x["confidence"], reverse=True)
    return unique_matches


def find_template_in_image(
    screen_image: np.ndarray,
    template_name: str, 
    threshold: float = 0.8, 
    min_distance: float = 8
) -> List[Dict[str, float]]:
    """
    Find template matches in given screenshot image.
    
    Args:
        screen_image: Screenshot as numpy array (BGR or grayscale)
        template_name: Template filename without extension
        threshold: Minimum confidence threshold (0.0-1.0)
        min_distance: Minimum pixel distance between unique matches
    
    Returns:
        List of match dictionaries: [{"x": int, "y": int, "confidence": float}, ...]
        Empty list if no matches found
    """
    # Convert to grayscale if needed
    if len(screen_image.shape) == 3:
        screen = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
    else:
        screen = screen_image
    
    # Get template image
    template = _get_template_image(template_name)
    if template is None:
        logger.error(f"Template not found: {template_name}")
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
    
    # Remove duplicate matches
    unique_matches = _remove_duplicate_matches(raw_matches, min_distance)
    
    # Sort matches by y then x when we have multiple matches
    if len(unique_matches) > 1:
        unique_matches.sort(key=lambda m: (m["y"], m["x"]))
    
    logger.debug(f"Template '{template_name}' found {len(unique_matches)} unique matches")
    return unique_matches


def find_template(
    template_name: str, 
    threshold: float = 0.8, 
    min_distance: float = 8
) -> List[Dict[str, float]]:
    """
    Convenience function: Find template matches in current screenshot.
    Takes a new screenshot automatically.
    
    Args:
        template_name: Template filename without extension
        threshold: Minimum confidence threshold (0.0-1.0)
        min_distance: Minimum pixel distance between unique matches
    
    Returns:
        List of match dictionaries: [{"x": int, "y": int, "confidence": float}, ...]
        Empty list if no matches found
    """
    # Get screenshot
    screen = get_cached_screenshot()
    if screen is None:
        logger.error("Failed to capture screenshot")
        return []
    
    return find_template_in_image(screen, template_name, threshold, min_distance)