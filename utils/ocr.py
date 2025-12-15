
import easyocr
import cv2
import re
from pathlib import Path
from typing import Optional, List, Tuple
from difflib import SequenceMatcher
import yaml
from utils.adb import adb_screenshot
from utils.logger import logger

# Load configuration
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"

with open(CONFIG_PATH, "r") as f:
    _ocr_config = yaml.safe_load(f)

SCREENSHOT_PATH = _ocr_config["screenshot_path"]
USE_GPU = _ocr_config.get("use_gpu", False)

# Initialize EasyOCR reader once at module level
_easyocr_reader = easyocr.Reader(['en'], gpu=USE_GPU)


def _load_screenshot_region(x1: int, y1: int, x2: int, y2: int):
    """Helper to load and crop screenshot region"""
    adb_screenshot()
    img = cv2.imread(SCREENSHOT_PATH)
    if img is None:
        logger.error(f"Failed to load screenshot from {SCREENSHOT_PATH}")
        return None
    return img[y1:y2, x1:x2]


def read_timer_from_region(x1: int, y1: int, x2: int, y2: int) -> Optional[int]:
    """
    Read timer from screen region and convert to seconds.
    Expects format: HHMMSS (e.g., "012345" = 1h 23m 45s)
    
    Returns:
        int: Total seconds, or None if parsing fails
    """
    crop = _load_screenshot_region(x1, y1, x2, y2)
    if crop is None:
        return None
    
    # OCR with digits and colon only
    texts = _easyocr_reader.readtext(crop, detail=0, allowlist='0123456789:')
    
    if not texts:
        logger.warning("No OCR result for timer region")
        return None
    
    # Combine and clean OCR results
    raw_text = "".join(texts)
    logger.debug(f"Raw OCR timer text: {raw_text}")
    
    cleaned_text = re.sub(r'[^0-9]', '', raw_text)
    
    # Parse HHMMSS format
    if len(cleaned_text) != 6:
        logger.error(f"Invalid timer format: expected 6 digits, got {len(cleaned_text)} ('{cleaned_text}')")
        return None
    
    try:
        h = int(cleaned_text[:2])
        m = int(cleaned_text[2:4])
        s = int(cleaned_text[4:6])
        return h * 3600 + m * 60 + s
    except ValueError as e:
        logger.error(f"Failed to parse timer digits: {e}")
        return None


def read_text_from_region(x1: int, y1: int, x2: int, y2: int) -> Optional[str]:
    """
    Read alphanumeric text from screen region.
    
    Returns:
        str: Cleaned alphanumeric text, or None if no text found
    """
    crop = _load_screenshot_region(x1, y1, x2, y2)
    if crop is None:
        return None
    
    texts = _easyocr_reader.readtext(crop, detail=0)
    
    if not texts:
        logger.warning("No OCR result for text region")
        return None
    
    # Combine and keep only alphanumeric
    raw_text = "".join(texts)
    clean_text = re.sub(r'[^A-Za-z0-9]', '', raw_text)
    
    logger.debug(f"OCR text extracted: {clean_text}")
    return clean_text


def _preprocess_text(text: str) -> str:
    """Normalize text for better matching (lowercase, no special chars)"""
    return re.sub(r'[^\w\s]', '', text.lower().strip())


def _similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)"""
    return SequenceMatcher(None, a, b).ratio()


def find_text_coordinates(target_text: str, confidence_threshold: float = 0.6) -> Optional[List[Tuple[int, int]]]:
    """
    Find coordinates of text on screen using OCR.
    
    Args:
        target_text: Text to search for
        confidence_threshold: Minimum similarity ratio (0.0-1.0)
    
    Returns:
        List of (x, y) center points with highest similarity, or None if not found
        Multiple coordinates returned only when different occurrences have same highest similarity
    """
    adb_screenshot()
    image = cv2.imread(SCREENSHOT_PATH)
    
    if image is None:
        logger.error(f"Failed to load screenshot from {SCREENSHOT_PATH}")
        return None
    
    # Perform OCR
    results = _easyocr_reader.readtext(image)
    
    target_normalized = _preprocess_text(target_text)
    best_matches = []
    highest_similarity = 0.0
    
    for bbox, text, ocr_confidence in results:
        # Skip low confidence OCR results
        if ocr_confidence < 0.3:
            continue
        
        detected_normalized = _preprocess_text(text)
        similarity = _similarity_ratio(target_normalized, detected_normalized)
        
        # Only consider matches above threshold
        if similarity >= confidence_threshold:
            # Calculate center point of bounding box
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            center_x = int(sum(x_coords) / len(x_coords))
            center_y = int(sum(y_coords) / len(y_coords))
            
            # Track best matches
            if similarity > highest_similarity:
                best_matches = [(center_x, center_y)]
                highest_similarity = similarity
            elif similarity == highest_similarity:
                best_matches.append((center_x, center_y))
    
    if best_matches:
        logger.debug(f"Found '{target_text}' with similarity {highest_similarity:.2f}: {best_matches}")
    else:
        logger.debug(f"Text '{target_text}' not found (threshold: {confidence_threshold})")
    
    return best_matches if best_matches else None