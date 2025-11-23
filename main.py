import os, time
import subprocess
import yaml
from pathlib import Path
from utils.adb import *
from utils.vision import find_template
from tasks.navigation import *
from tasks.handle_trading_posts import *

from utils.ocr import * #temp for test


def main():
    print("Connecting to device...")
    # Try connecting using the IP from settings.yaml
    output = adb_connect()
    print("ADB connect output:", output)
    # Check if device is available
    if not adb_is_device_ready():
        print("⚠ No device detected by ADB!")
        return

    # reach_home_screen()
    handle_trading_posts()


if __name__ == "__main__":
    main()
    