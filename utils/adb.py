import subprocess
import yaml
import time
from pathlib import Path

# Load settings.yaml
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"


with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

ADB_PATH = cfg.get("adb_path")
SCREENSHOT_PATH = cfg.get("screenshot_path")
DEVICE_ID = cfg.get("device_ip")


def adb_run(cmd):
    """Run a system command and return output."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.stdout.strip()


def adb_connect(device_ip=None):
    """
    Connect to BlueStacks or Android device.
    If device_ip not provided, use from YAML.
    """
    if device_ip is None:
        device_ip = cfg.get("device_ip")

    if device_ip:
        return adb_run([ADB_PATH, "connect", device_ip])
    else:
        return adb_run([ADB_PATH, "devices"])


def adb_is_device_ready():
    """Check if ADB detects a connected device."""
    output = adb_run([ADB_PATH, "devices"])
    return "device" in output.split("\n")[-1]

def adb_tap(x, y=None):
    """
    Tap on screen.
    Works with:
    - adb_tap(100, 200)  # Direct coordinates
    - adb_tap([(100, 200)])  # Single coordinate in list
    - adb_tap([(100, 200), (300, 400)])  # Multiple coordinates => (halts)
    """
    if x is None:
        print("Error: No coordinates provided (x is None)")
        return False
    
    if y is not None:
        x_coord, y_coord = x, y
    else:
        # Otherwise, x should be a list with at least one coordinate tuple
        if not x or not isinstance(x, list) or not isinstance(x[0], tuple):
            print("Error: When using single parameter, must provide list of coordinate tuples")
            return False
        
        # Check if multiple coordinates exist
        if len(x) > 1:
            print(f"Error: adb_tap found {len(x)} coordinates. Halting.")
            print(f"Coordinates: {x}")
            return False
        
        x_coord, y_coord = x[0]  # Use first coordinate
    
    print(f"adb tapping: {x_coord}, {y_coord}")
    return adb_run([ADB_PATH, "-s", DEVICE_ID, "shell", "input", "tap", str(x_coord), str(y_coord)])

def adb_swipe(x1, y1, x2, y2, duration_ms=300):
    """Swipe gesture."""
    return adb_run([
        ADB_PATH, "-s", DEVICE_ID, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2),
        str(duration_ms)
    ])

def swipe_left():
    adb_swipe(1500, 535, 840, 535)
    print("swiped left, sleeping 1sec")
    time.sleep(1)

def swipe_right():
    adb_swipe(840, 535, 1500, 535)
    print("swiped right, sleeping 1sec")
    time.sleep(1)

def slow_swipe_left():
    adb_swipe(1500, 550, 1000, 550, 700)
    time.sleep(0.5)

def slow_swipe_right():
    adb_swipe(1000, 550, 1500, 550, 700)
    time.sleep(0.5)

def adb_screenshot(save_path=None):
    """Take screenshot and save it."""
    if save_path is None:
        save_path = SCREENSHOT_PATH

    tmp = "/sdcard/screen_tmp.png"
    adb_run([ADB_PATH, "-s", DEVICE_ID, "shell", "screencap", "-p", tmp])
    adb_run([ADB_PATH, "-s", DEVICE_ID, "pull", tmp, save_path])

    return Path(save_path)
