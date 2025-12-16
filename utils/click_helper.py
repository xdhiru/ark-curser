"""
Helper functions for common click patterns with screenshot caching.
"""

from typing import Optional, Dict, List, Union
import time
from .adb import adb_tap, get_cached_screenshot  # CHANGED: relative import
from .vision import find_template_in_image  # CHANGED: relative import
from .logger import logger  # CHANGED: relative import


def click_template(
    template_name: Union[str, List[Dict]], 
    threshold: float = 0.8,
    max_attempts: int = 1
) -> bool:
    """
    Find template and click it with screenshot caching.
    
    Args:
        template_name: Template name or pre-found matches
        threshold: Confidence threshold
        max_attempts: How many times to try
    
    Returns:
        bool: True if clicked successfully
    """
    for attempt in range(max_attempts):
        # If already have matches, just click
        if isinstance(template_name, list):
            if not template_name:
                return False
            x, y = template_name[0]["x"], template_name[0]["y"]
            logger.debug(f"Clicking template at ({x}, {y})")
            return adb_tap(x, y)
        
        # Get screenshot
        screenshot = get_cached_screenshot()
        if screenshot is None:
            if attempt < max_attempts - 1:
                time.sleep(0.5)
                continue
            return False
        
        # Find template
        matches = find_template_in_image(screenshot, template_name, threshold)
        
        if matches:
            coord = matches[0]
            logger.debug(f"Clicking '{template_name}' at ({coord['x']}, {coord['y']})")
            return adb_tap(coord["x"], coord["y"])
        
        if attempt < max_attempts - 1:
            time.sleep(0.5)
    
    logger.debug(f"Template '{template_name}' not found (threshold: {threshold})")
    return False


def wait_and_click(
    template_name: str,
    timeout: float = 10.0,
    interval: float = 0.5,
    threshold: float = 0.8
) -> bool:
    """
    Wait for template to appear and click it.
    
    Args:
        template_name: Template to wait for
        timeout: Maximum time to wait (seconds)
        interval: Time between checks (seconds)
        threshold: Confidence threshold
    
    Returns:
        bool: True if clicked successfully, False on timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if click_template(template_name, threshold):
            return True
        time.sleep(interval)
    
    logger.warning(f"Timeout waiting for template '{template_name}'")
    return False


def click_region(region: tuple, sleep_after: float = 0.5) -> bool:
    """
    Click at the center of a region.
    
    Args:
        region: (x1, y1, x2, y2) coordinates
        sleep_after: Seconds to sleep after clicking
    
    Returns:
        bool: Always returns True
    """
    if len(region) != 4:
        logger.error(f"Invalid region format: {region}")
        return False
    
    x1, y1, x2, y2 = region
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    
    logger.debug(f"Clicking region center at ({center_x}, {center_y})")
    adb_tap(center_x, center_y)
    time.sleep(sleep_after)
    return True