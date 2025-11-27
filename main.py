import sys
from pathlib import Path
from utils.logger import logger
from utils.adb import adb_connect, adb_is_device_ready
from tasks.handle_trading_posts import handle_trading_posts


def verify_device_connection() -> bool:
    """
    Verify ADB connection to device.
    
    Returns:
        bool: True if device is connected and ready, False otherwise
    """
    logger.info("Connecting to device...")
    output = adb_connect()
    logger.debug(f"ADB connect output: {output}")
    
    if not adb_is_device_ready():
        logger.error("No device detected by ADB! Please check:")
        logger.error("  1. Device is powered on")
        logger.error("  2. ADB is enabled on device")
        logger.error("  3. Device IP is correct in config/settings.yaml")
        return False
    
    logger.info("Device connected successfully")
    return True


def main():
    """Main entry point for cursingbot"""
    try:
        # Verify device connection
        if not verify_device_connection():
            sys.exit(1)
        
        # Start trading post automation
        logger.info("Starting trading post automation...")
        handle_trading_posts()
        
    except KeyboardInterrupt:
        logger.info("User interrupted execution (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()