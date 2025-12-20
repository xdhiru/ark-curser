"""
Helper functions for common click patterns with adaptive wait optimization.
"""

from typing import Optional, Dict, List, Union, Tuple, Callable
import time
from utils.adb import adb_tap, get_cached_screenshot
from utils.vision import find_template_in_image
from utils.adaptive_waits import wait_optimizer
from utils.logger import logger

def static_wait(wait_type: str, min_wait: float = 0.05) -> float:
    """Standard blind sleep using optimized timing (Open-loop)."""
    return wait_optimizer.static_wait(wait_type, min_wait)

def adaptive_wait(
    wait_type: str, 
    validator_func: Callable[[], bool], 
    timeout: float = 20.0,
    poll_frequency: float = 0.5
) -> bool:
    """Waits dynamically using a validator function (Closed-loop)."""
    initial_wait = wait_optimizer.get_wait_time(wait_type)
    time.sleep(initial_wait)

    if validator_func():
        wait_optimizer.record_wait_result(wait_type, initial_wait, True, retry_count=0)
        return True

    elapsed = initial_wait
    retries = 0
    start_time = time.time()
    remaining_timeout = max(timeout - initial_wait, 2.0)

    while time.time() - start_time < remaining_timeout:
        retries += 1
        time.sleep(poll_frequency)
        elapsed += poll_frequency
        
        if validator_func():
            wait_optimizer.record_wait_result(wait_type, elapsed, True, retry_count=retries)
            return True

    logger.warning(f"Validation for '{wait_type}' failed after {elapsed:.1f}s")
    wait_optimizer.record_wait_result(wait_type, elapsed, False, retry_count=retries)
    return False

def _execute_action(
    action_name: str,
    action_fn: Callable[[], bool],
    max_retries: int = None,
    description: str = "action",
    learn: bool = True
) -> Tuple[bool, int]:
    """Generic retry engine."""
    if max_retries is None:
        max_retries = wait_optimizer.max_retries
        
    for retry_count in range(max_retries + 1):
        wait_time = wait_optimizer.get_wait_time(action_name)
        time.sleep(wait_time)
        
        success = action_fn()
        
        if learn:
            should_retry, next_wait = wait_optimizer.record_wait_result(
                action_name, wait_time, success, retry_count
            )
        else:
            should_retry = not success
            next_wait = wait_time
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
    description: str = None,
    timing_key: str = "template_click",
    learn: bool = True
) -> Tuple[bool, int]:
    """Find template and click it with smart retry system."""

    if description is None:
        t_name = template_name if isinstance(template_name, str) else "cached-coordinates"
        description = f"template['{t_name}']"
    
    # 1. Pre-calculated matches
    if isinstance(template_name, list):
        if not template_name: return False, 0
        x, y = template_name[0]["x"], template_name[0]["y"]
        if adb_tap(x, y):
            wait_optimizer.record_wait_result(timing_key, 0.05, True, 0)
            if wait_after: static_wait("post_click_wait")
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
    success, retries = _execute_action(timing_key, attempt_click, max_retries, description, learn=learn)
    
    if success and wait_after:
        static_wait("post_click_wait")
        
    return success, retries

def click_region(
    region: tuple, 
    max_retries: int = None,
    sleep_after: float = None,
    timing_key: str = "region_click",
    description: str = None
) -> Tuple[bool, int]:
    """Click at the center of a region with retry."""
    if len(region) != 4:
        logger.error(f"Invalid region format: {region}")
        return False, 0
        
    x1, y1, x2, y2 = region
    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
    
    def attempt_click():
        return adb_tap(center_x, center_y)

    desc = description if description else f"region {region}"
    success, retries = _execute_action(timing_key, attempt_click, max_retries, desc)
    
    if success:
        if sleep_after is not None:
            time.sleep(sleep_after)
        else:
            static_wait("post_region_click")
            
    return success, retries