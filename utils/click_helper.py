"""
Helper functions for common click patterns with adaptive wait optimization.
"""

from typing import Optional, Dict, List, Union, Tuple, Callable
import time
from utils.adb import adb_tap, get_cached_screenshot
from utils.vision import find_template_in_image
from utils.adaptive_waits import wait_optimizer
from utils.logger import logger

def adaptive_wait(wait_type: str, min_wait: float = 0.05) -> float:
    return wait_optimizer.wait(wait_type, min_wait)

def _execute_action(
    action_name: str,
    action_fn: Callable[[], bool],
    max_retries: int = None,
    description: str = "action"
) -> Tuple[bool, int]:
    """Generic retry engine."""
    if max_retries is None:
        max_retries = wait_optimizer.max_retries
        
    for retry_count in range(max_retries + 1):
        wait_time = wait_optimizer.get_wait_time(action_name)
        time.sleep(wait_time)
        
        success = action_fn()
        
        should_retry, next_wait = wait_optimizer.record_wait_result(
            action_name, wait_time, success, retry_count
        )
        
        if success:
            return True, retry_count
            
        if not should_retry or retry_count >= max_retries:
            logger.debug(f"Failed {description} after {retry_count + 1} attempts")
            break
            
        extra_wait = next_wait - wait_time
        if extra_wait > 0:
            time.sleep(extra_wait)
            
    return False, max_retries

def click_template(
    template_name: Union[str, List[Dict]], 
    threshold: float = 0.8,
    max_retries: int = None,
    wait_after: bool = True,
    description: str = "template click"
) -> Tuple[bool, int]:
    """Find template and click it with smart retry system."""
    
    # 1. Pre-calculated matches
    if isinstance(template_name, list):
        if not template_name: return False, 0
        x, y = template_name[0]["x"], template_name[0]["y"]
        if adb_tap(x, y):
            wait_optimizer.record_wait_result("template_click", 0.05, True, 0)
            if wait_after: adaptive_wait("post_click_wait")
            return True, 0
        return False, 0

    # 2. Action Definition
    def attempt_click():
        screenshot = get_cached_screenshot(force_fresh=True)
        if screenshot is None: return False
        matches = find_template_in_image(screenshot, template_name, threshold)
        if matches:
            coord = matches[0]
            logger.debug(f"Clicking '{template_name}' at ({coord['x']}, {coord['y']})")
            return adb_tap(coord["x"], coord["y"])
        return False

    # 3. Execution
    success, retries = _execute_action("template_click", attempt_click, max_retries, description)
    
    if success and wait_after:
        adaptive_wait("post_click_wait")
        
    return success, retries

def click_region(
    region: tuple, 
    max_retries: int = None,
    sleep_after: float = None
) -> Tuple[bool, int]:
    """Click at the center of a region with retry."""
    if len(region) != 4:
        logger.error(f"Invalid region format: {region}")
        return False, 0
        
    x1, y1, x2, y2 = region
    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
    
    def attempt_click():
        return adb_tap(center_x, center_y)

    success, retries = _execute_action("region_click", attempt_click, max_retries, "region click")
    
    if success:
        if sleep_after is not None:
            time.sleep(sleep_after)
        else:
            adaptive_wait("post_region_click")
            
    return success, retries

def wait_and_click(
    template_name: str,
    timeout: float = 10.0,
    interval: float = None,
    threshold: float = 0.8
) -> bool:
    """Wait for template to appear and click it."""
    if interval is None:
        interval = wait_optimizer.get_wait_time("template_check_interval")
        
    start = time.time()
    while time.time() - start < timeout:
        success, _ = click_template(
            template_name, threshold, max_retries=0, wait_after=True, description=f"wait:{template_name}"
        )
        if success:
            return True
        time.sleep(interval)
        
    logger.warning(f"Timeout waiting for {template_name}")
    return False