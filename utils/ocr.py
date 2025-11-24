import easyocr
import cv2
import re
from pathlib import Path
import yaml
from utils.adb import adb_screenshot
from utils.logger import logger
from difflib import SequenceMatcher



# Load settings.yaml
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"

with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

SCREENSHOT_PATH = cfg.get("screenshot_path")
USE_GPU = cfg.get("use_gpu", False)

easyocr_reader = easyocr.Reader(['en'], gpu=USE_GPU)

def read_timer_from_region(x1, y1, x2, y2):
    # Read the image
    adb_screenshot()
    img = cv2.imread(SCREENSHOT_PATH)

    # crop region
    crop = img[y1:y2, x1:x2]
    
    # OCR numbers + colon from the whole image
    texts = easyocr_reader.readtext(crop, detail=0, allowlist='0123456789:')
    
    if not texts:
        logger.warning("No OCR result for timer region")
        return None
    
    # Combine OCR results into a single string (in case the colon is misread or split)
    raw_text = "".join(texts)
    logger.info(f"Raw OCR timer text: {raw_text}")
    
    # Strip out any non-digit characters (just in case OCR added weird characters)
    cleaned_text = re.sub(r'[^0-9]', '', raw_text)
    
    # If the text has 6 digits, treat it as HHMMSS
    if len(cleaned_text) == 6:
        h = int(cleaned_text[:2])  # First two digits are hours
        m = int(cleaned_text[2:4])  # Middle two digits are minutes
        s = int(cleaned_text[4:])  # Last two digits are seconds
    else:
        logger.error(f"Invalid OCR result for timer (expected 6 digits, got {len(cleaned_text)})")
        return None
    
    # Calculate total time in seconds
    timer_seconds = h * 3600 + m * 60 + s
    logger.info(f"Timer parsed: {timer_seconds} seconds ({h:02d}h {m:02d}m {s:02d}s)")
    return timer_seconds


def read_text_from_region(x1, y1, x2, y2):
    # Read the image
    adb_screenshot()
    img = cv2.imread(SCREENSHOT_PATH)

    # crop region
    crop = img[y1:y2, x1:x2]
    
    # OCR numbers + colon from the whole image
    texts = easyocr_reader.readtext(crop, detail=0)
    
    if not texts:
        logger.warning("No OCR result for text region")
        return None
    
    # Combine OCR results into a single string
    raw_text = "".join(texts)
    # Keep only A–Z, a–z, 0–9
    alnum_text = re.sub(r'[^A-Za-z0-9]', '', raw_text)

    logger.info(f"OCR text extracted: {alnum_text}")
    return alnum_text


def preprocess_text(text):
    """Normalize text for better matching"""
    return re.sub(r'[^\w\s]', '', text.lower().strip())

def similarity_ratio(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def find_text_coordinates(target_text, confidence_threshold=0.6):
    """
    Find coordinates of text in an image using EasyOCR
    
    Args:
        target_text: Text to search for
        confidence_threshold: Similarity threshold (0-1), lower = more tolerant
    
    Returns:
        List of clickable center points [(x, y), ...] with highest similarity
        Returns multiple coordinates only when different occurrences have same highest similarity
    """
    adb_screenshot()
    # Read the image
    image = cv2.imread(SCREENSHOT_PATH)
    
    # Perform OCR
    results = easyocr_reader.readtext(image)
    
    target_text_normalized = preprocess_text(target_text)
    best_matches = []
    highest_similarity = 0
    
    for (bbox, text, confidence) in results:
        # Skip low confidence detections
        if confidence < 0.3:
            continue
            
        # Normalize the detected text
        detected_text_normalized = preprocess_text(text)
        
        # Calculate similarity
        similarity = similarity_ratio(target_text_normalized, detected_text_normalized)
        
        # Only consider matches above threshold
        if similarity >= confidence_threshold:
            # Calculate center point
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            
            center_x = int(sum(x_coords) / len(x_coords))
            center_y = int(sum(y_coords) / len(y_coords))
            
            # Update best matches
            if similarity > highest_similarity:
                best_matches = [(center_x, center_y)]
                highest_similarity = similarity
            elif similarity == highest_similarity:
                best_matches.append((center_x, center_y))
    
    return best_matches if best_matches else None



