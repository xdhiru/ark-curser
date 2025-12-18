"""
Main entry point for ark_curser automation.
"""

import sys
import atexit
from utils.logger import logger
from utils.adb import adb_connect, adb_is_device_ready
from utils.adaptive_waits import wait_optimizer
from tasks.handle_trading_posts import handle_trading_posts
from utils.config_loader import get_config_value

class ArkCurserBot:
    """Main application class."""
    
    def __init__(self):
        self.logger = logger
        self.device_connected = False
        atexit.register(self.shutdown)
        
    def shutdown(self):
        if wait_optimizer.enabled:
            self.logger.info("Saving adaptive wait times...")
            wait_optimizer.save_waits()
            wait_optimizer.print_report()

    def verify_device_connection(self) -> bool:
        self.logger.info("Connecting to device...")
        target_ip = get_config_value("device_ip", "127.0.0.1:5555")
        
        try:
            output = adb_connect(target_ip)
            if output:
                self.logger.debug(f"ADB connect output: {output}")
            
            self.device_connected = adb_is_device_ready()
            
            if not self.device_connected:
                self._log_troubleshooting()
                return False
            
            self.logger.info(f"Device connected successfully ({target_ip})")
            return True
            
        except Exception as e:
            self.logger.error(f"ADB connection error: {e}")
            return False
    
    def _log_troubleshooting(self):
        self.logger.error("No device detected! Please check:")
        self.logger.error("  1. Device/Emulator is powered on")
        self.logger.error("  2. ADB debugging is enabled")
        self.logger.error("  3. Check 'device_ip' in settings.yaml")
    
    def run(self) -> int:
        try:
            if not self.verify_device_connection():
                return 1
            
            self.logger.info("Starting automation...")
            handle_trading_posts()
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("User interrupted execution.")
            return 0
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            return 1

def main():
    bot = ArkCurserBot()
    sys.exit(bot.run())

if __name__ == "__main__":
    main()