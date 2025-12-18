"""
OCR utilities using EasyOCR.
"""

import easyocr
import re
import numpy as np
from typing import Optional, List, Tuple
from difflib import SequenceMatcher
from utils.config_loader import get_config_value
from utils.adb import get_cached_screenshot
from utils.logger import logger

# Init Reader
USE_GPU = get_config_value("use_gpu", False)
_reader = easyocr.Reader(['en'], gpu=USE_GPU)

# Regex
_DIGITS = re.compile(r'[^0-9]')
_ALPHANUM = re.compile(r'[^A-Za-z0-9]')

def read_timer_from_region(x1, y1, x2, y2) -> Optional[int]:
    """Reads HHMMSS timer and returns seconds."""
    screen = get_cached_screenshot()
    if screen is None: return None
    
    crop = screen[y1:y2, x1:x2]
    result = _reader.readtext(crop, detail=0, allowlist='0123456789')
    
    text = _DIGITS.sub('', "".join(result))
    if len(text) != 6: return None
    
    try:
        h, m, s = int(text[:2]), int(text[2:4]), int(text[4:6])
        return h * 3600 + m * 60 + s
    except ValueError:
        return None

def read_text_from_image(image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Optional[str]:
    """Reads text from a specific region of an image."""
    crop = image[y1:y2, x1:x2]
    result = _reader.readtext(crop, detail=0)
    
    clean = _ALPHANUM.sub('', "".join(result))
    return clean if clean else None

def find_text_coordinates(target: str, threshold: float = 0.6) -> Optional[List[Tuple[int, int]]]:
    """Finds screen coordinates of specific text."""
    screen = get_cached_screenshot()
    if screen is None: return None
    
    results = _reader.readtext(screen)
    target_clean = target.lower().strip()
    
    matches = []
    best_score = 0
    
    for bbox, text, conf in results:
        if conf < 0.3: continue
        
        score = SequenceMatcher(None, target_clean, text.lower().strip()).ratio()
        if score >= threshold:
            # Calculate Center
            (tl, tr, br, bl) = bbox
            center_x = int((tl[0] + br[0]) / 2)
            center_y = int((tl[1] + br[1]) / 2)
            
            if score > best_score:
                matches = [(center_x, center_y)]
                best_score = score
            elif score == best_score:
                matches.append((center_x, center_y))
                
    return matches if matches else None