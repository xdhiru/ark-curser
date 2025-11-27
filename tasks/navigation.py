from utils.adb import adb_connect, adb_is_device_ready, adb_screenshot, adb_tap, swipe_left, swipe_right
from utils.vision import find_template
from utils.ocr import find_text_coordinates
from utils.logger import logger
import time

def click_template(template_name, threshold=0.8):
    # Find the template
    if isinstance(template_name, str):
        matches = find_template(template_name, threshold)
    elif isinstance(template_name, list):
        matches = template_name
    else:
        raise ValueError("in click_template, template_name must be either a string of template name or list of dict of coordinates")
    # If found → Click
    
    if matches:
        x, y = matches[0]["x"], matches[0]["y"]
        logger.debug(f"Clicking '{template_name}' at ({x}, {y})")
        adb_tap(x, y)
        return True
    else:
        logger.warning(f"Template '{template_name}' not found")
        return False

def find_and_click_text(input_text):
    adb_tap(find_text_coordinates(input_text))

def is_home_screen():
    return bool(find_template("settings-icon"))

def navigate_back_until(check_func, timeout=80):
    """Navigate back (click back-icon) until check_func returns True"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_func():
            return True
        click_template("back-icon")
        time.sleep(1)
    logger.warning(f"navigate_back_until timeout after {timeout}s")
    return False
    
def reach_home_screen():
    """Navigate back to home screen"""
    logger.info("Navigating back to home screen")
    return navigate_back_until(is_home_screen)

def reach_base():
    logger.info("Navigating to base")
    time.sleep(1)
    if check_if_reached_base():
        return True
    # Only navigate home if not already there
    if not is_home_screen():
        reach_home_screen()
    click_template("base-icon")
    time.sleep(5)
    return True
    
def check_if_reached_base():
    return bool(find_template("reached-base"))

def reach_base_left_side():
    if not check_if_reached_base():
        reach_base()
    logger.info("Positioning on base left side")
    swipe_right()
    time.sleep(0.5)
    return True

def return_back_to_base_left_side():
    """Navigate back to base, then position on left side"""
    logger.info("Navigating back to base (left side)")
    navigate_back_until(check_if_reached_base)
    reach_base_left_side()
    return True

def find_trading_posts():
    logger.info("Searching for trading posts")
    reach_base_left_side()
    return find_template("trading-post") #return the "matches" list of dictionaries with x,y keys


def wait_for_template(template_name, timeout=40, threshold=0.8):
    """
    Repeatedly captures the screen until the given template is detected.
    Returns the match data or None if timed out.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        matches = find_template(template_name, threshold)
        if matches:
            time.sleep(1)
            return matches[0]   # return first match

        time.sleep(1)  # check twice per second

    return None