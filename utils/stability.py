"""
Motion and stability detection.
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, Dict
from utils.adb import get_cached_screenshot
from utils.config_loader import get_config_value
from utils.logger import logger

# Load Configs
MOTION_INTERVAL = get_config_value("stability_detection_interval_ms", 250) / 1000.0

def detect_motion(prev: np.ndarray, curr: np.ndarray, threshold: float = 0.98) -> bool:
    """True if moving."""
    if prev is None or curr is None or prev.shape != curr.shape:
        return True
        
    gray1 = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(gray1, gray2)
    non_zero = np.count_nonzero(diff > 25)
    
    similarity = 1.0 - (non_zero / diff.size)
    return similarity < threshold

def wait_for_screen_stabilization(timeout: float = 3.0, stable_time: float = 0.3) -> bool:
    """Waits until screen stops moving."""
    start = time.time()
    last_stable = None
    prev = get_cached_screenshot(force_fresh=True)
    
    while time.time() - start < timeout:
        curr = get_cached_screenshot(force_fresh=True)
        is_moving = detect_motion(prev, curr)
        
        if not is_moving:
            if last_stable is None: last_stable = time.time()
            if time.time() - last_stable >= stable_time:
                return True
        else:
            last_stable = None
            
        prev = curr
        time.sleep(MOTION_INTERVAL)
        
    return False