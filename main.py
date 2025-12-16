import sys
from pathlib import Path
from typing import Optional
from utils.logger import logger
from utils.adb import adb_connect, adb_is_device_ready
from tasks.handle_trading_posts import handle_trading_posts


class ark_curser:
    """Main application class for ark_curser automation."""
    
    def __init__(self):
        self.device_connected = False
    
    def verify_device_connection(self) -> bool:
        """
        Verify ADB connection to device with detailed error reporting.
        
        Returns:
            bool: True if device is connected and ready, False otherwise
        """
        logger.info("Connecting to device...")
        
        try:
            output = adb_connect()
            if output:
                logger.debug(f"ADB connect output: {output}")
            
            self.device_connected = adb_is_device_ready()
            
            if not self.device_connected:
                self._log_connection_errors()
                return False
            
            logger.info("Device connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"ADB connection error: {e}")
            return False
    
    @staticmethod
    def _log_connection_errors() -> None:
        """Log common connection troubleshooting steps."""
        logger.error("No device detected by ADB! Please check:")
        logger.error("  1. Device is powered on and unlocked")
        logger.error("  2. ADB debugging is enabled in Developer Options")
        logger.error("  3. Device IP/port is correct in config/settings.yaml")
        logger.error("  4. Device and computer are on same network")
        logger.error("  5. Firewall isn't blocking ADB connections")
    
    def run(self) -> int:
        """Main execution loop for the bot.
        
        Returns:
            int: Exit code (0 for success, non-zero for errors)
        """
        try:
            # Step 1: Verify device connection
            if not self.verify_device_connection():
                return 1
            
            # Step 2: Execute main automation task
            logger.info("Starting trading post automation...")
            handle_trading_posts()
            
            logger.info("Automation completed successfully")
            return 0
            
        except KeyboardInterrupt:
            logger.info("User interrupted execution (Ctrl+C)")
            return 0
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return 1


def main() -> None:
    """Main entry point for ark_curser."""
    bot = ark_curser()
    exit_code = bot.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()