"""
Navigation utilities for screen navigation and location verification.
"""

from utils.adb import adb_tap, swipe_left, swipe_right, get_cached_screenshot
from utils.vision import find_template, find_template_in_image
from utils.ocr import find_text_coordinates
from utils.click_helper import click_template as click_helper_template
from utils.logger import logger
from typing import Optional, List, Dict, Callable, Union
import time


def click_template(
    template_name: Union[str, List[Dict]], 
    threshold: float = 0.8,
    use_cached_screenshot: bool = True
) -> bool:
    """
    Find and click a template on screen.
    
    Args:
        template_name: Template name or pre-found matches
        threshold: Minimum confidence threshold
        use_cached_screenshot: Use cached screenshot if available
    """
    # Use the optimized click helper
    return click_helper_template(template_name, threshold, max_attempts=1 if use_cached_screenshot else 3)


def find_and_click_text(
    text: str, 
    confidence_threshold: float = 0.6,
    use_cached_screenshot: bool = True
) -> bool:
    """Find text on screen using OCR and click it."""
    coords = find_text_coordinates(text, confidence_threshold)
    
    if coords:
        return adb_tap(coords[0])  # Click first occurrence
    return False


def is_home_screen() -> bool:
    """Check if currently on home screen."""
    screenshot = get_cached_screenshot()
    if screenshot is None:
        return False
    return bool(find_template_in_image(screenshot, "settings-icon"))


def is_base() -> bool:
    """Check if currently at base view."""
    screenshot = get_cached_screenshot()
    if screenshot is None:
        return False
    return bool(find_template_in_image(screenshot, "base-overview-icon"))


def is_inside_tp() -> bool:
    """Check if currently at trading post view."""
    screenshot = get_cached_screenshot()
    if screenshot is None:
        return False
    return bool(find_template_in_image(screenshot, "check-if-inside-tp"))


def reach_home_screen(max_attempts: int = 15) -> bool:
    """Navigate back to home screen."""
    logger.debug("Navigating to home screen")
    for _ in range(max_attempts):
        if is_home_screen():
            logger.debug("Arrived at home screen")
            return True
        click_template("back-icon", use_cached_screenshot=False)
        time.sleep(1)
    logger.warning(f"Failed to reach home screen after {max_attempts} attempts")
    return False


def reach_base(max_back_attempts: int = 15) -> bool:
    """Navigate to base view."""
    logger.debug("Navigating to base")
    
    # Press back until at base or home screen
    for _ in range(max_back_attempts):
        if is_base():
            logger.debug("Arrived at base")
            return True
        if is_home_screen():
            logger.debug("Reached home screen, navigating to base")
            click_template("base-icon", use_cached_screenshot=False)
            time.sleep(5)
            return True       
        click_template("back-icon", use_cached_screenshot=False)
        time.sleep(1)    
    logger.warning("Failed to navigate to base")
    return False


def reach_base_left_side() -> bool:
    """Navigate to base and position on left side."""
    if not reach_base():
        return False
    
    # Check for zoomed out view
    screenshot = get_cached_screenshot()
    if screenshot is not None:
        zoomed_out_tp_match = find_template_in_image(screenshot, "trading-post-zoomed-out-base")
        if zoomed_out_tp_match:
            logger.debug("Base appears zoomed out, repositioning")
            click_template(zoomed_out_tp_match)
            if not reach_base():
                return False
    
    swipe_right()
    swipe_right()
    time.sleep(0.5)
    logger.debug("Positioned at base left side")
    return True


def find_trading_posts() -> List[Dict]:
    """Find all trading posts on non-zoomed-out base (left side)."""
    logger.debug("Searching for trading posts")
    
    # Get fresh screenshot for accurate detection
    screenshot = get_cached_screenshot()
    if screenshot is None:
        logger.error("Failed to get screenshot for trading post detection")
        return []
    
    matches = find_template_in_image(screenshot, "trading-post")
    logger.debug(f"Found {len(matches)} trading post(s)")
    return matches


def find_factories() -> List[Dict]:
    """Find all factories on base (left side)."""
    logger.debug("Searching for factories")
    
    screenshot = get_cached_screenshot()
    if screenshot is None:
        logger.error("Failed to get screenshot for factory detection")
        return []
    
    matches = find_template_in_image(screenshot, "factory")
    logger.debug(f"Found {len(matches)} factory(ies)")
    return matches


def enter_base_overview() -> bool:
    """Enter base overview screen."""
    logger.info("Entering base overview")
    
    if not reach_base():
        logger.warning("Could not reach base")
        return False
    
    if not click_template("base-overview-icon", use_cached_screenshot=False):
        logger.warning("Could not click base overview icon")
        return False
    
    time.sleep(0.25)
    logger.debug("Successfully entered base overview")
    return True


def wait_for_template(
    template_name: str,
    timeout: int = 40,
    threshold: float = 0.8,
    check_interval: float = 1.0,
    use_cached_screenshot: bool = True
) -> Optional[Dict]:
    """Wait for a template to appear on screen."""
    logger.debug(f"Waiting for '{template_name}' (timeout: {timeout}s)")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if use_cached_screenshot:
            screenshot = get_cached_screenshot()
            if screenshot is None:
                time.sleep(check_interval)
                continue
            matches = find_template_in_image(screenshot, template_name, threshold)
        else:
            matches = find_template(template_name, threshold)
        
        if matches:
            elapsed = time.time() - start_time
            logger.debug(f"Template found after {elapsed:.1f}s")
            time.sleep(1)  # Brief pause for stability
            return matches[0]
        time.sleep(check_interval)
    
    logger.warning(f"Template '{template_name}' not found after {timeout}s")
    return None


def retry_operation(
    func: Callable[[], bool],
    max_attempts: int = 3,
    delay: float = 1.0,
    desc: str = "operation"
) -> bool:
    """Retry a function until it succeeds or max attempts reached."""
    for attempt in range(1, max_attempts + 1):
        logger.debug(f"Attempting {desc} (try {attempt}/{max_attempts})")
        
        if func():
            logger.debug(f"{desc} succeeded on attempt {attempt}")
            return True
        
        if attempt < max_attempts:
            time.sleep(delay)
    
    logger.warning(f"{desc} failed after {max_attempts} attempts")
    return False


def ensure_at_location(
    check_func: Callable[[], bool],
    navigate_func: Callable[[], bool],
    location: str = "target location"
) -> bool:
    """Ensure we're at a specific location, navigating if necessary."""
    if check_func():
        logger.debug(f"Already at {location}")
        return True
    
    logger.info(f"Not at {location}, navigating...")
    return navigate_func()