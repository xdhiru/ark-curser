"""
Navigation utilities with adaptive wait optimization.
"""

from utils.adb import adb_tap, swipe_left, swipe_right, get_cached_screenshot
from utils.vision import find_template, find_template_in_image
from utils.ocr import find_text_coordinates
from utils.click_helper import click_template, adaptive_wait
from utils.adaptive_waits import wait_optimizer
from utils.logger import logger
from typing import Optional, List, Dict, Callable, Union, Tuple
import time

def find_and_click_text_with_retry(
    text: str, 
    confidence_threshold: float = 0.6,
    max_retries: int = None
) -> Tuple[bool, int]:
    """Find text on screen using OCR and click it with retry."""
    if max_retries is None:
        max_retries = wait_optimizer.max_retries
    
    # We implement a manual loop here because 'text finding' isn't in click_helper
    for retry_count in range(max_retries + 1):
        wait_time = wait_optimizer.get_wait_time("text_find")
        time.sleep(wait_time)
        
        coords = find_text_coordinates(text, confidence_threshold)
        
        success = False
        if coords:
            success = adb_tap(coords[0][0], coords[0][1])
            
        should_retry, next_wait = wait_optimizer.record_wait_result(
            "text_find", wait_time, success, retry_count
        )
        
        if success:
            adaptive_wait("post_click_wait")
            return True, retry_count
        
        if not should_retry or retry_count >= max_retries:
            break
            
        extra_wait = next_wait - wait_time
        if extra_wait > 0:
            time.sleep(extra_wait)
    
    return False, max_retries

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
            return True
        
        # Click back (use generic template click)
        success, _ = click_template(
            "back-icon", 
            wait_after=False,
            description="reach_home:back"
        )
        
        if success:
            adaptive_wait("screen_transition")
    
    logger.warning(f"Failed to reach home screen after {max_attempts} attempts")
    return False

def reach_base(max_back_attempts: int = 15) -> bool:
    """Navigate to base view."""
    logger.debug("Navigating to base")
    
    for _ in range(max_back_attempts):
        if is_base():
            return True
        
        if is_home_screen():
            logger.debug("Reached home screen, navigating to base")
            success, _ = click_template(
                "base-icon", 
                description="reach_base:base_icon"
            )
            
            if success:
                adaptive_wait("base_transition", min_wait=3.0)
                return True
        
        # Click back
        success, _ = click_template(
            "back-icon", 
            wait_after=False,
            description="reach_base:back"
        )
        
        if success:
            adaptive_wait("screen_transition")
    
    logger.warning("Failed to navigate to base")
    return False

def reach_base_left_side() -> bool:
    """Navigate to base and position on left side."""
    if not reach_base():
        return False
    
    # Check for zoomed out view
    screenshot = get_cached_screenshot()
    if screenshot is not None:
        zoomed_out = find_template_in_image(screenshot, "trading-post-zoomed-out-base")
        if zoomed_out:
            logger.debug("Base appears zoomed out, repositioning")
            click_template([zoomed_out[0]]) # Click the match found
            if not reach_base():
                return False
    
    swipe_right()
    adaptive_wait("swipe_completion")
    swipe_right()
    adaptive_wait("base_left_side_position")
    return True

def find_trading_posts() -> List[Dict]:
    """Find all trading posts on non-zoomed-out base (left side)."""
    logger.debug("Searching for trading posts")
    
    # Force fresh screenshot
    screenshot = get_cached_screenshot(force_fresh=True)
    if screenshot is None:
        return []
    
    adaptive_wait("pre_template_search")
    matches = find_template_in_image(screenshot, "trading-post")
    logger.debug(f"Found {len(matches)} trading post(s)")
    return matches

def find_factories() -> List[Dict]:
    """Find all factories on base (left side)."""
    logger.debug("Searching for factories")
    
    screenshot = get_cached_screenshot(force_fresh=True)
    if screenshot is None:
        return []
    
    adaptive_wait("pre_template_search")
    matches = find_template_in_image(screenshot, "factory")
    return matches

def enter_base_overview() -> bool:
    """Enter base overview screen."""
    if not reach_base(): return False
    
    if click_template("base-overview-icon", threshold=0.8):
        adaptive_wait("base_overview_load")
        return True
    return False

def wait_for_template(
    template_name: str,
    timeout: int = 40,
    threshold: float = 0.8,
    check_interval: float = None
) -> Optional[Dict]:
    """Wait for a template to appear on screen."""
    logger.debug(f"Waiting for '{template_name}' (timeout: {timeout}s)")
    
    if check_interval is None:
        check_interval = wait_optimizer.get_wait_time("template_check_interval")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        screenshot = get_cached_screenshot(force_fresh=True)
        if screenshot is None:
            time.sleep(check_interval)
            continue

        matches = find_template_in_image(screenshot, template_name, threshold)
        if matches:
            adaptive_wait("post_template_find")
            return matches[0]
        
        # Record failure to adaptive wait (allows system to learn if check interval is too fast)
        wait_optimizer.record_wait_result(
            "template_check_interval", check_interval, False, 0
        )
        
        time.sleep(check_interval)
    
    logger.warning(f"Template '{template_name}' not found after {timeout}s")
    return None

def retry_operation(
    func: Callable[[], bool],
    max_attempts: int = 3,
    delay_type: str = "retry_delay",
    desc: str = "operation"
) -> bool:
    """Retry a function until it succeeds."""
    for attempt in range(1, max_attempts + 1):
        if func():
            return True
        if attempt < max_attempts:
            adaptive_wait(delay_type)
    return False

def ensure_at_location(
    check_func: Callable[[], bool],
    navigate_func: Callable[[], bool],
    location: str = "target location"
) -> bool:
    """Ensure we're at a specific location."""
    if check_func():
        return True
    
    logger.info(f"Navigating to {location}...")
    success = navigate_func()
    if success:
        adaptive_wait("post_navigation")
    return success

# Backward compatibility alias
reach_home_screen_with_retry = lambda x=15: (reach_home_screen(x), 0)
reach_base_with_retry = lambda x=15: (reach_base(x), 0)