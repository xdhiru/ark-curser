"""
Centralized logging configuration for the cursingbot project.
All modules should import and use the logger from this module.
"""

import logging
import sys
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Create logger
logger = logging.getLogger("cursingbot")
logger.setLevel(logging.DEBUG)

# Prevent adding duplicate handlers
if not logger.handlers:
    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (DEBUG level - captures everything)
    file_handler = logging.FileHandler(LOGS_DIR / "cursingbot.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

# Disable propagation to avoid duplicate logs
logger.propagate = False
