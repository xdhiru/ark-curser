"""
Utility functions for the cursingbot project.
"""

from .logger import logger
from .config_loader import load_config, get_config_value
from .adb import (
    adb_run, adb_connect, adb_is_device_ready, adb_tap, adb_swipe,
    swipe_left, swipe_right, slow_swipe_left, slow_swipe_right, slow_swipe_up,
    get_cached_screenshot, adb_screenshot, clear_screenshot_cache
)
from .vision import find_template, find_template_in_image
from .ocr import (
    read_timer_from_region, read_text_from_region, find_text_coordinates,
    read_timer_from_image, read_text_from_image
)
from .time_helper import get_ist_time_and_remaining
from .click_helper import click_template, wait_and_click, click_region

__all__ = [
    # Core
    'logger',
    'load_config',
    'get_config_value',
    
    # ADB
    'adb_run', 'adb_connect', 'adb_is_device_ready', 'adb_tap', 'adb_swipe',
    'swipe_left', 'swipe_right', 'slow_swipe_left', 'slow_swipe_right', 'slow_swipe_up',
    'get_cached_screenshot', 'adb_screenshot', 'clear_screenshot_cache',
    
    # Vision
    'find_template', 'find_template_in_image',
    
    # OCR
    'read_timer_from_region', 'read_text_from_region', 'find_text_coordinates',
    'read_timer_from_image', 'read_text_from_image',
    
    # Time
    'get_ist_time_and_remaining',
    
    # Click Helpers
    'click_template', 'wait_and_click', 'click_region',
]