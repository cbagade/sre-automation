"""Utility functions for date and timeslot handling."""

from datetime import datetime, timezone
from typing import Tuple


def get_current_timeslot() -> str:
    """Get the current timeslot based on UTC time.
    
    Returns:
        str: Timeslot in format '00_hr-06_hr', '06_hr-12_hr', '12_hr-18_hr', or '18_hr-00_hr'
    """
    current_hour = datetime.now(timezone.utc).hour
    
    if 0 <= current_hour < 6:
        return "00_hr-06_hr"
    elif 6 <= current_hour < 12:
        return "06_hr-12_hr"
    elif 12 <= current_hour < 18:
        return "12_hr-18_hr"
    else:
        return "18_hr-00_hr"


def get_timeslot_order() -> list:
    """Get the ordered list of timeslots in a day.
    
    Returns:
        list: List of timeslots in chronological order
    """
    return ["00_hr-06_hr", "06_hr-12_hr", "12_hr-18_hr", "18_hr-00_hr"]


def is_later_timeslot(timeslot1: str, timeslot2: str) -> bool:
    """Check if timeslot1 is later than timeslot2.
    
    Args:
        timeslot1: First timeslot
        timeslot2: Second timeslot
        
    Returns:
        bool: True if timeslot1 is later than timeslot2
    """
    timeslot_order = get_timeslot_order()
    try:
        idx1 = timeslot_order.index(timeslot1)
        idx2 = timeslot_order.index(timeslot2)
        return idx1 > idx2
    except ValueError:
        return False


def format_date_for_git(date_obj: datetime) -> str:
    """Format date object for git path.
    
    Args:
        date_obj: Date object
        
    Returns:
        str: Date in format 'YYYY-MM-DD'
    """
    return date_obj.strftime("%Y-%m-%d")


def parse_date_from_string(date_str: str) -> datetime:
    """Parse date string to datetime object.
    
    Args:
        date_str: Date string in format 'YYYY-MM-DD'
        
    Returns:
        datetime: Parsed datetime object
    """
    return datetime.strptime(date_str, "%Y-%m-%d")

# Made with Bob
