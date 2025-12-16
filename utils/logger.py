"""
Centralized logging configuration for the ark_curser project.
All modules should import and use the logger from this module.
"""

import logging
import sys
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure logger
logger = logging.getLogger("ark_curser")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Prevent duplicate logs

# Only add handlers once
if not logger.handlers:
    # Console handler (INFO level) - for user-facing messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # File handler (DEBUG level) - for detailed debugging
    file_handler = logging.FileHandler(LOGS_DIR / "ark_curser.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)