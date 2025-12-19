"""
Standalone Screenshot Tool.
"""
import yaml
import subprocess
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent
    config_path = project_root / "config" / "settings.yaml"
    
    with open(config_path, 'r') as f:
        settings = yaml.safe_load(f)
    output_path = project_root / settings.get("screenshot_path", "Screenshots/screen.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    device_address=settings.get("device_ip", "127.0.0.1:5555")
    with open(output_path, "wb") as f:
        subprocess.run(["adb", "connect", device_address ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["adb", "-s", device_address, "exec-out", "screencap", "-p"], stdout=f, check=True)

if __name__ == "__main__":
    main()