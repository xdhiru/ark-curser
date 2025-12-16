"""
ADB operations for Android device control with in-memory screenshot caching.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional, List, Tuple, Union
import cv2
import numpy as np
from .config_loader import get_config_value
from .logger import logger

# Configuration
ADB_PATH = get_config_value("adb_path")
DEVICE_ID = get_config_value("device_ip")

# Constants
_SWIPE_SLEEP = 0.2

# Screenshot caching
_current_screenshot = None
_last_screenshot_time = 0
_SCREENSHOT_CACHE_DURATION = 0.1  # Cache for 100ms


def adb_run(cmd: List[str], capture_output: bool = True) -> Union[str, bytes]:
    """Run an ADB command and return output."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return result.stdout
        else:
            result = subprocess.run(cmd, check=True)
            return ""
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB command failed: {' '.join(cmd)}")
        logger.error(f"Error: {e.stderr}")
        return b"" if capture_output else ""


def get_cached_screenshot() -> Optional[np.ndarray]:
    """
    Get screenshot with short-lived caching.
    Useful when multiple operations need the same screen state.
    """
    global _current_screenshot, _last_screenshot_time
    
    current_time = time.time()
    
    # Return cached screenshot if it's fresh enough
    if (_current_screenshot is not None and 
        (current_time - _last_screenshot_time) < _SCREENSHOT_CACHE_DURATION):
        return _current_screenshot
    
    # Take new screenshot
    _current_screenshot = _take_screenshot()
    _last_screenshot_time = current_time
    return _current_screenshot


def _take_screenshot() -> Optional[np.ndarray]:
    """Internal: Take screenshot and return as numpy array."""
    try:
        result = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ID, "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        image_bytes = np.frombuffer(result.stdout, dtype=np.uint8)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        
        if image is None:
            logger.error("Failed to decode screenshot")
            return None
        
        logger.debug(f"Screenshot captured: {image.shape[1]}x{image.shape[0]}")
        return image
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Screenshot failed: {e.stderr.decode()}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during screenshot: {e}")
        return None


def adb_screenshot() -> Optional[np.ndarray]:
    """
    Take screenshot and return as numpy array in memory.
    Always takes a fresh screenshot (clears cache).
    """
    global _current_screenshot
    _current_screenshot = None  # Clear cache to force fresh screenshot
    return get_cached_screenshot()


def clear_screenshot_cache():
    """Clear cached screenshot to free memory."""
    global _current_screenshot
    _current_screenshot = None


def adb_connect(device_ip: Optional[str] = None) -> str:
    """Connect to Android device via ADB."""
    target_ip = device_ip or DEVICE_ID
    
    if target_ip:
        return adb_run([ADB_PATH, "connect", target_ip], capture_output=False)
    return adb_run([ADB_PATH, "devices"], capture_output=False)


def adb_is_device_ready() -> bool:
    """Check if ADB detects a connected device."""
    output = adb_run([ADB_PATH, "devices"])
    lines = output.decode().strip().split('\n')
    return len(lines) > 1 and "device" in lines[-1]


def adb_tap(x: Union[int, List[Tuple[int, int]]], y: Optional[int] = None) -> bool:
    """
    Tap on screen at specified coordinates.
    Does not require a screenshot.
    """
    if x is None:
        logger.error("No coordinates provided (x is None)")
        return False
    
    # Handle direct coordinate input: adb_tap(x, y)
    if y is not None:
        x_coord, y_coord = x, y
    else:
        # Handle list input: adb_tap([(x, y)])
        if not isinstance(x, list) or not x or not isinstance(x[0], tuple):
            logger.error("When using single parameter, must provide list of coordinate tuples")
            return False
        
        # Check for multiple coordinates
        if len(x) > 1:
            logger.error(f"adb_tap found {len(x)} coordinates. Halting. Coordinates: {x}")
            return False
        
        x_coord, y_coord = x[0]
    
    logger.debug(f"Tapping at coordinates: ({x_coord}, {y_coord})")
    adb_run([ADB_PATH, "-s", DEVICE_ID, "shell", "input", "tap", str(x_coord), str(y_coord)], 
            capture_output=False)
    return True


def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
    """Perform swipe gesture from (x1, y1) to (x2, y2)."""
    adb_run([
        ADB_PATH, "-s", DEVICE_ID, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration_ms)
    ], capture_output=False)


# Swipe presets
def swipe_left():
    """Swipe left on screen."""
    logger.debug("Swiping left")
    adb_swipe(1650, 535, 700, 535)
    time.sleep(_SWIPE_SLEEP)


def swipe_right():
    """Swipe right on screen."""
    logger.debug("Swiping right")
    adb_swipe(700, 535, 1650, 535)
    time.sleep(_SWIPE_SLEEP)


def slow_swipe_left():
    """Slow swipe left on screen."""
    logger.debug("Slow swiping left")
    adb_swipe(1500, 550, 1000, 550, 700)
    time.sleep(_SWIPE_SLEEP)


def slow_swipe_right():
    """Slow swipe right on screen."""
    logger.debug("Slow swiping right")
    adb_swipe(1000, 550, 1500, 550, 700)
    time.sleep(_SWIPE_SLEEP)


def slow_swipe_up():
    """Slow swipe up on screen."""
    logger.debug("Slow swiping up")
    adb_swipe(1200, 870, 1200, 500, 650)
    time.sleep(_SWIPE_SLEEP)