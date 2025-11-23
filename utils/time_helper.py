import datetime
import time

def get_ist_time_and_remaining(epoch_time):
    """
    Convert epoch time to IST and calculate time remaining until that time.
    Returns formatted IST time and human-readable time remaining.
    """
    
    current_time = time.time()
    time_difference = epoch_time - current_time
    
    # Convert to IST
    ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    ist_time = datetime.datetime.fromtimestamp(epoch_time, ist_timezone)
    formatted_time = ist_time.strftime("%I:%M %p")
    
    # Calculate time remaining
    remaining_seconds = abs(int(time_difference))
    hours, remainder = divmod(remaining_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if time_difference >= 0:
        time_remaining_str = f"{hours:02}h {minutes:02}m {seconds:02}s"
    else:
        time_remaining_str = f"OVERDUE by {hours:02}h {minutes:02}m {seconds:02}s"
    
    return formatted_time, time_remaining_str