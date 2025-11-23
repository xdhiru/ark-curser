from utils.adb import adb_connect, adb_is_device_ready, adb_screenshot, adb_tap, swipe_left, swipe_right
from utils.vision import find_template
from utils.ocr import find_text_coordinates
from utils.logger import logger
import time

def click_template(template_name, threshold=0.8):
    # Find the template
    matches = find_template(template_name, threshold)

    # If found → Click
    
    if matches:
        x, y = matches[0]["x"], matches[0]["y"]
        logger.info(f"Found template '{template_name}' at ({x}, {y}), tapping")
        adb_tap(x, y)
        return True
        # else:
        #     logger.debug(f"Found multiple instances of '{template_name}'")
        #     handle_multiple_matches(template_name, matches)
    else:
        logger.warning(f"Template '{template_name}' not found")
        return False

def find_and_click_text(input_text):
    adb_tap(find_text_coordinates(input_text))

def is_home_screen():
    return bool(find_template("settings-icon"))
    
def reach_home_screen():
    while not is_home_screen():
        # wait_for_template("back-icon")
        click_template("back-icon")
        time.sleep(1)
    return True

def return_back_to_base_left_side():
    while not check_if_reached_base():
        # wait_for_template("back-icon")
        click_template("back-icon")
        time.sleep(1)
    reach_base_left_side()
    return True


def reach_base():
    time.sleep(1)
    if check_if_reached_base():
        return True
    reach_home_screen()
    click_template("base-icon")
    time.sleep(5)
    return True
    
def check_if_reached_base():
    if find_template("reached-base"):
        return True
    return False

def reach_base_left_side():
    reach_base()
    swipe_right()
    time.sleep(1)
    return True

def find_trading_posts():
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