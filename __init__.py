"""
ark-curser - Arknights Trading Post Automation Bot
"""

__version__ = "1.0.0"
__author__ = "ark_curser"
__description__ = "Automated trading post management for Arknights"

# Export main components for easy import
from utils.logger import logger
from utils.adb import adb_screenshot, get_cached_screenshot
from utils.vision import find_template
from utils.click_helper import click_template

__all__ = [
    'logger',
    'adb_screenshot',
    'get_cached_screenshot',
    'find_template',
    'click_template',
]