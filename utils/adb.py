
import subprocess
import yaml
import time
from pathlib import Path
from typing import Optional, List, Tuple, Union
from utils.logger import logger

# Load configuration once at module level
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"

with open(CONFIG_PATH, "r") as f:
    _config = yaml.safe_load(f)

ADB_PATH = _config["adb_path"]
SCREENSHOT_PATH = _config["screenshot_path"]
DEVICE_ID = _config["device_ip"]


def adb_run(cmd: List[str]) -> str:
    """Run an ADB command and return output."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.stdout.strip()


def adb_connect(device_ip: Optional[str] = None) -> str:
    """
    Connect to Android device via ADB.
    If device_ip not provided, uses value from config.
    """
    target_ip = device_ip or DEVICE_ID
    
    if target_ip:
        return adb_run([ADB_PATH, "connect", target_ip])
    else:
        return adb_run([ADB_PATH, "devices"])


def adb_is_device_ready() -> bool:
    """Check if ADB detects a connected device."""
    output = adb_run([ADB_PATH, "devices"])
    return "device" in output.split("\n")[-1]


def adb_tap(x: Union[int, List[Tuple[int, int]]], y: Optional[int] = None) -> bool:
    """
    Tap on screen at specified coordinates.
    
    Args:
        x: Either x-coordinate (int) or list of (x, y) tuples
        y: y-coordinate (int) when x is int, None otherwise
    
    Usage:
        adb_tap(100, 200)           # Direct coordinates
        adb_tap([(100, 200)])       # Single coordinate in list
        adb_tap([(100, 200), ...])  # Multiple coordinates (ERROR)
    
    Returns:
        bool: True if successful, False otherwise
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
        
        # Check for multiple coordinates (potential error)
        if len(x) > 1:
            logger.error(f"adb_tap found {len(x)} coordinates. Halting. Coordinates: {x}")
            return False
        
        x_coord, y_coord = x[0]
    
    logger.debug(f"Tapping at coordinates: ({x_coord}, {y_coord})")
    adb_run([ADB_PATH, "-s", DEVICE_ID, "shell", "input", "tap", str(x_coord), str(y_coord)])
    return True


def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Perform swipe gesture from (x1, y1) to (x2, y2)."""
    return adb_run([
        ADB_PATH, "-s", DEVICE_ID, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration_ms)
    ])


# Swipe presets with consistent sleep timing
_SWIPE_SLEEP = 0.25

def swipe_left():
    """Swipe left on screen"""
    logger.debug("Swiping left")
    adb_swipe(1650, 535, 700, 535)
    time.sleep(_SWIPE_SLEEP)


def swipe_right():
    """Swipe right on screen"""
    logger.debug("Swiping right")
    adb_swipe(700, 535, 1650, 535)
    time.sleep(_SWIPE_SLEEP)


def slow_swipe_left():
    """Slow swipe left on screen"""
    logger.debug("Slow swiping left")
    adb_swipe(1500, 550, 1000, 550, 700)
    time.sleep(_SWIPE_SLEEP)


def slow_swipe_right():
    """Slow swipe right on screen"""
    logger.debug("Slow swiping right")
    adb_swipe(1000, 550, 1500, 550, 700)
    time.sleep(_SWIPE_SLEEP)


def adb_screenshot(save_path: Optional[str] = None) -> Path:
    """
    Take screenshot and save to local filesystem.
    
    Args:
        save_path: Local path to save screenshot. Uses config default if None.
    
    Returns:
        Path object pointing to the saved screenshot
    """
    save_path = save_path or SCREENSHOT_PATH
    tmp_path = "/sdcard/screen_tmp.png"
    
    adb_run([ADB_PATH, "-s", DEVICE_ID, "shell", "screencap", "-p", tmp_path])
    adb_run([ADB_PATH, "-s", DEVICE_ID, "pull", tmp_path, save_path])
    
    return Path(save_path)
