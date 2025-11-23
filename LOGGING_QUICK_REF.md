# Logging Quick Reference

## How to Use Logging in Your Code

### Basic Import
```python
from utils.logger import logger
```

### Log Levels (in order of severity)

```python
# DEBUG - Detailed diagnostic info for developers
logger.debug("Template 'ok' found at (540, 960)")

# INFO - General informational messages
logger.info("Device connected successfully")

# WARNING - Warning messages for unexpected situations
logger.warning("Template 'cancel' not found, retrying")

# ERROR - Error messages for serious problems
logger.error("Failed to read screenshot: File not found")

# CRITICAL - Critical errors (rarely used)
logger.critical("Device disconnected unexpectedly")
```

### Logging with Variables
```python
tp_id = 3
x, y = 540, 960
logger.debug(f"TP {tp_id}: Tapping at ({x}, {y})")
```

### Logging Exceptions
```python
try:
    # some code
except Exception as e:
    logger.error(f"Error in curse task: {e}", exc_info=True)
```

## Output Examples

### Console Output (INFO and above)
```
2025-11-24 14:30:15 - cursingbot - INFO - Connecting to device...
2025-11-24 14:30:15 - cursingbot - WARNING - Template 'base-icon' not found
2025-11-24 14:30:16 - cursingbot - ERROR - Failed to read template file: Templates/invalid.png
```

### Log File (`logs/cursingbot.log`) - All levels
```
2025-11-24 14:30:15 - cursingbot - DEBUG - [adb.py:85] - Tapping at coordinates: 540, 960
2025-11-24 14:30:15 - cursingbot - DEBUG - [vision.py:42] - Template 'base-icon' found 1 unique matches
2025-11-24 14:30:16 - cursingbot - INFO - Device connected successfully
2025-11-24 14:30:16 - cursingbot - WARNING - Template 'cancel' not found
2025-11-24 14:30:17 - cursingbot - ERROR - [ocr.py:95] - Invalid timer format
```

## File Locations
- **Logs saved to**: `logs/cursingbot.log`
- **Logger config**: `utils/logger.py`
- **New to remove**: Any remaining `print()` statements

## Tips
1. Use **DEBUG** for developer details (coordinates, raw OCR text)
2. Use **INFO** for workflow milestones (connected, task started)
3. Use **WARNING** for recoverable errors (retry scenarios)
4. Use **ERROR** for critical failures (need to stop/investigate)
5. Always include context (TP ID, coordinates, etc.) in messages
