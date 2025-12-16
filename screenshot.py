"""
Quick Screenshot
"""
import sys
import cv2
import yaml
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.adb import adb_screenshot

def main():
    # Load settings
    with open(project_root / "config" / "settings.yaml", 'r') as f:
        settings = yaml.safe_load(f)
    
    # Get path and create directory
    path = Path(settings['screenshot_path'])
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Capture and save
    img = adb_screenshot()
    if img is not None:
        cv2.imwrite(str(path), img)
        print(f"Screenshot saved: {path}")
    else:
        print("Failed to capture screenshot")

if __name__ == "__main__":
    main()