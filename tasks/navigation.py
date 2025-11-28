from utils.adb import adb_tap, swipe_left, swipe_right
from utils.vision import find_template
from utils.ocr import find_text_coordinates
from utils.logger import logger
from typing import Optional, List, Dict, Callable
import time


def click_template(template_name, threshold: float = 0.8) -> bool:
    """
    Find and click a template on screen.
    
    Args:
        template_name: Template name (str) or list of coordinate dicts
        threshold: Confidence threshold for template matching
    
    Returns:
        bool: True if clicked successfully, False otherwise
    """
    # Handle both string template names and pre-found coordinate lists
    if isinstance(template_name, str):
        matches = find_template(template_name, threshold)
    elif isinstance(template_name, list):
        matches = template_name
    else:
        raise ValueError(
            "template_name must be either a string (template name) or "
            "list of coordinate dicts"
        )
    
    if not matches:
        logger.warning(f"Template '{template_name}' not found")
        return False
    
    # Click the first (best) match
    x, y = matches[0]["x"], matches[0]["y"]
    logger.debug(f"Clicking '{template_name}' at ({x}, {y})")
    adb_tap(x, y)
    return True


def find_and_click_text(input_text: str) -> bool:
    """
    Find text on screen using OCR and click it.
    
    Args:
        input_text: Text to search for
    
    Returns:
        bool: True if found and clicked, False otherwise
    """
    coords = find_text_coordinates(input_text)
    if coords:
        return adb_tap(coords)
    return False


def is_home_screen() -> bool:
    """Check if currently on home screen"""
    return bool(find_template("settings-icon"))


def check_if_reached_base() -> bool:
    """Check if currently at base view"""
    return bool(find_template("reached-base"))


def navigate_back_until(check_func: Callable[[], bool], timeout: int = 80) -> bool:
    """
    Navigate back until check_func returns True.
    
    Args:
        check_func: Function that returns True when target screen is reached
        timeout: Maximum time to attempt navigation (seconds)
    
    Returns:
        bool: True if target reached, False if timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if check_func():
            logger.debug(f"Target screen reached after {time.time() - start_time:.1f}s")
            return True
        
        click_template("back-icon")
        time.sleep(1)
    
    logger.warning(f"navigate_back_until timeout after {timeout}s")
    return False


def reach_home_screen() -> bool:
    """
    Navigate back to home screen.
    
    Returns:
        bool: True if home screen reached, False otherwise
    """
    logger.info("Navigating to home screen")
    return navigate_back_until(is_home_screen)


def reach_base() -> bool:
    """
    Navigate to base view.
    
    Returns:
        bool: True if base reached, False otherwise
    """
    logger.info("Navigating to base")
    
    # Check if already at base
    if check_if_reached_base():
        logger.debug("Already at base")
        return True
    
    # Navigate home first if not there
    if not is_home_screen():
        reach_home_screen()
    
    # Click base icon and wait
    click_template("base-icon")
    time.sleep(5)
    
    return check_if_reached_base()


def reach_base_left_side() -> bool:
    """
    Navigate to base and position on left side.
    
    Returns:
        bool: True if positioned successfully
    """
    if not check_if_reached_base():
        reach_base()
    
    logger.info("Positioning on base left side")
    swipe_right()
    return True


def return_back_to_base_left_side() -> bool:
    """
    Navigate back to base and position on left side.
    
    Returns:
        bool: True if positioned successfully
    """
    logger.info("Navigating back to base (left side)")
    navigate_back_until(check_if_reached_base)
    reach_base_left_side()
    return True


def find_trading_posts() -> List[Dict]:
    """
    Find all trading posts on base (left side).
    Handles both zoomed-in and zoomed-out base views.
    
    Returns:
        List of trading post coordinate dictionaries
    """
    logger.info("Searching for trading posts")
    reach_base_left_side()
    
    # Try to find trading posts
    tp_matches = find_template("trading-post")
    
    # If not found, base might be zoomed out - reposition
    if not tp_matches:
        logger.info("Base appears zoomed out, repositioning")
        click_template("trading-post-zoomed-out-base")
        return_back_to_base_left_side()
        tp_matches = find_template("trading-post")
    
    if tp_matches:
        logger.info(f"Found {len(tp_matches)} trading post(s)")
    else:
        logger.warning("No trading posts found")
    
    return tp_matches or []


def wait_for_template(
    template_name: str, 
    timeout: int = 40, 
    threshold: float = 0.8,
    check_interval: float = 1.0
) -> Optional[Dict]:
    """
    Wait for a template to appear on screen.
    
    Args:
        template_name: Template name to search for
        timeout: Maximum wait time (seconds)
        threshold: Confidence threshold for matching
        check_interval: Time between checks (seconds)
    
    Returns:
        First match dict if found, None if timeout
    """
    logger.debug(f"Waiting for template '{template_name}' (timeout: {timeout}s)")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        matches = find_template(template_name, threshold)
        
        if matches:
            elapsed = time.time() - start_time
            logger.debug(f"Template '{template_name}' found after {elapsed:.1f}s")
            time.sleep(1)  # Brief pause for stability
            return matches[0]
        
        time.sleep(check_interval)
    
    logger.warning(f"Template '{template_name}' not found after {timeout}s timeout")
    return None


# ============================================================================
# Additional helper functions for common navigation patterns
# ============================================================================

def retry_until_success(
    func: Callable[[], bool],
    max_attempts: int = 3,
    delay: float = 1.0,
    description: str = "operation"
) -> bool:
    """
    Retry a function until it succeeds or max attempts reached.
    
    Args:
        func: Function that returns True on success
        max_attempts: Maximum number of attempts
        delay: Delay between attempts (seconds)
        description: Description for logging
    
    Returns:
        bool: True if successful within max attempts, False otherwise
    """
    for attempt in range(1, max_attempts + 1):
        logger.debug(f"Attempting {description} (try {attempt}/{max_attempts})")
        
        if func():
            logger.debug(f"{description} succeeded on attempt {attempt}")
            return True
        
        if attempt < max_attempts:
            time.sleep(delay)
    
    logger.warning(f"{description} failed after {max_attempts} attempts")
    return False


def ensure_at_location(
    check_func: Callable[[], bool],
    navigate_func: Callable[[], bool],
    location_name: str = "target location"
) -> bool:
    """
    Ensure we're at a specific location, navigating if necessary.
    
    Args:
        check_func: Function to check if at location
        navigate_func: Function to navigate to location
        location_name: Location name for logging
    
    Returns:
        bool: True if at location, False otherwise
    """
    if check_func():
        logger.debug(f"Already at {location_name}")
        return True
    
    logger.info(f"Not at {location_name}, navigating...")
    return navigate_func()