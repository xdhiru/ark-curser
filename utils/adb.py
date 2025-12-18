"""
ADB operations for Android device control with in-memory screenshot caching.
"""

import subprocess
import time
import cv2
import numpy as np
from typing import Optional, List, Tuple, Union
from utils.config_loader import get_config_value
from utils.logger import logger
from utils.adaptive_waits import wait_optimizer

# Configuration
ADB_PATH = get_config_value("adb_path", "adb")
DEVICE_IP = get_config_value("device_ip", "127.0.0.1:5555")

# Cache State
_current_screenshot = None
_last_screenshot_time = 0
_SCREENSHOT_CACHE_DURATION = 0.1  # 100ms cache

def adb_run(cmd: List[str], capture_output: bool = True) -> Union[str, bytes]:
    """Run an ADB command."""
    try:
        if capture_output:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return result.stdout
        else:
            subprocess.run(cmd, check=True)
            return ""
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB failed: {' '.join(cmd)} | Error: {e.stderr}")
        return b"" if capture_output else ""

def get_cached_screenshot(force_fresh: bool = False) -> Optional[np.ndarray]:
    """Get screenshot with short-lived caching."""
    global _current_screenshot, _last_screenshot_time
    
    current_time = time.time()
    
    if (not force_fresh and _current_screenshot is not None and 
        (current_time - _last_screenshot_time) < _SCREENSHOT_CACHE_DURATION):
        return _current_screenshot
    
    # Capture new
    try:
        result = subprocess.run(
            [ADB_PATH, "-s", DEVICE_IP, "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        image = cv2.imdecode(np.frombuffer(result.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        if image is not None:
            _current_screenshot = image
            _last_screenshot_time = current_time
            return image
            
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        
    return None

def clear_screenshot_cache():
    global _current_screenshot
    _current_screenshot = None

def adb_connect(device_ip: Optional[str] = None) -> str:
    target = device_ip or DEVICE_IP
    return adb_run([ADB_PATH, "connect", target], capture_output=False)

def adb_is_device_ready() -> bool:
    output = adb_run([ADB_PATH, "devices"])
    return b"device\n" in output or b"device\r\n" in output

def adb_tap(x: int, y: int) -> bool:
    """Tap coordinates and clear cache."""
    # Support list of tuples if passed by accident, though cleaner to enforce int
    if isinstance(x, list): x, y = x[0]
        
    logger.debug(f"Tap: ({x}, {y})")
    adb_run([ADB_PATH, "-s", DEVICE_IP, "shell", "input", "tap", str(x), str(y)], capture_output=False)
    clear_screenshot_cache()
    return True

def adb_swipe(x1, y1, x2, y2, duration=300):
    adb_run([ADB_PATH, "-s", DEVICE_IP, "shell", "input", "swipe", 
             str(x1), str(y1), str(x2), str(y2), str(duration)], capture_output=False)
    clear_screenshot_cache()

# --- Optimized Swipes ---
def swipe_left():
    logger.debug("Swiping left")
    adb_swipe(1650, 535, 700, 535)
    wait_optimizer.wait("swipe_completion")

def swipe_right():
    logger.debug("Swiping right")
    adb_swipe(700, 535, 1650, 535)
    wait_optimizer.wait("swipe_completion")

def slow_swipe_left():
    logger.debug("Slow swipe left")
    adb_swipe(1500, 550, 1000, 550, 700)
    wait_optimizer.wait("slow_swipe_completion")