import datetime
import time
from typing import Tuple

# IST timezone (UTC+5:30) - define once
_IST_TIMEZONE = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def get_ist_time_and_remaining(epoch_time: float) -> Tuple[str, str]:
    """
    Convert epoch time to IST and calculate time remaining.
    
    Args:
        epoch_time: Unix timestamp to convert
    
    Returns:
        Tuple of (formatted_ist_time, time_remaining_str)
        Example: ("02:30 PM", "01h 23m 45s")
    """
    current_time = time.time()
    time_difference = epoch_time - current_time
    
    # Convert to IST
    ist_time = datetime.datetime.fromtimestamp(epoch_time, _IST_TIMEZONE)
    formatted_time = ist_time.strftime("%I:%M %p")
    
    # Calculate time remaining
    remaining_seconds = abs(int(time_difference))
    hours, remainder = divmod(remaining_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if time_difference >= 0:
        time_remaining_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
    else:
        time_remaining_str = f"OVERDUE by {hours:02d}h {minutes:02d}m {seconds:02d}s"
    
    return formatted_time, time_remaining_str
