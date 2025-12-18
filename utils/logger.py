"""
Centralized logging configuration with configurable startup rotation.
"""

import logging
import sys
import os
import glob
from pathlib import Path
from utils.config_loader import get_config_value

# Ensure logs directory exists
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(exist_ok=True)

MAIN_LOG_FILE = LOGS_DIR / "ark_curser.log"

# Load Configuration (Defaults: True, 10)
AUTO_DELETE = get_config_value("logging.auto_delete", True)
BACKUP_COUNT = get_config_value("logging.backup_count", 10)

def rotate_logs_on_startup(log_file: Path, backups: int, auto_delete: bool):
    """
    Shifts old logs to numbered backups so the current run always 
    starts with a fresh file.
    
    Args:
        log_file: Path to the main log file.
        backups: Number of files to keep (if auto_delete is True).
        auto_delete: If True, deletes files exceeding 'backups' count.
                     If False, keeps shifting files indefinitely.
    """
    if not log_file.exists():
        return

    # 1. Detect highest existing index to handle generic shifting
    # Finds ark_curser.log.1, .2, .15, etc.
    existing_indexes = []
    prefix = log_file.name + "."
    for p in log_file.parent.glob(f"{prefix}*"):
        try:
            # Extract suffix (e.g., '1' from 'ark_curser.log.1')
            idx = int(p.name.split('.')[-1])
            existing_indexes.append(idx)
        except ValueError:
            pass # Ignore files with non-integer suffixes
    
    max_index = max(existing_indexes) if existing_indexes else 0

    # 2. Determine the range to shift
    if auto_delete:
        # Enforce the Limit:
        # Delete any file that is >= the backup count limit.
        # (Using >= because we need space for the new .1, so .10 must go if limit is 10)
        
        # Cleanup loop (Handles case where user reduced config from 100 -> 10)
        for i in existing_indexes:
            if i >= backups:
                try:
                    os.remove(log_file.with_name(f"{prefix}{i}"))
                except OSError:
                    pass
        
        # We only need to shift up to (backups - 1)
        shift_start = backups - 1
    else:
        # Infinite Growth:
        # Just start shifting from the highest number found
        shift_start = max_index

    # 3. Shift existing logs up by one
    # Loop downwards: .4 -> .5, then .3 -> .4, etc.
    for i in range(shift_start, 0, -1):
        src = log_file.with_name(f"{prefix}{i}")
        dest = log_file.with_name(f"{prefix}{i+1}")
        if src.exists():
            try:
                os.rename(src, dest)
            except OSError:
                pass

    # 4. Rename current main log to .1
    first_backup = log_file.with_name(f"{prefix}1")
    try:
        os.rename(log_file, first_backup)
    except OSError:
        pass

# Initialize Logger
logger = logging.getLogger("ark_curser")
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.handlers:
    # 1. Perform Rotation BEFORE adding handlers
    rotate_logs_on_startup(MAIN_LOG_FILE, BACKUP_COUNT, AUTO_DELETE)

    # 2. Console Handler (INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # 3. File Handler (DEBUG) - This will now create a FRESH file
    file_handler = logging.FileHandler(MAIN_LOG_FILE, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)