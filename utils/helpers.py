"""Helper utility functions."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dateutil import parser as dateutil_parser

logger = logging.getLogger('EMCBot.Helpers')


def format_timestamp(dt: datetime) -> str:
    """Format datetime object to readable string.
    
    Args:
        dt: Datetime object
        
    Returns:
        Formatted timestamp string
    """
    if not dt:
        return "Unknown"
    
    return dt.strftime('%m/%d/%Y %I:%M %p')


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return dateutil_parser.parse(timestamp_str)
    except Exception as e:
        logger.error(f"Error parsing timestamp '{timestamp_str}': {e}")
        return None


def get_avatar_url(minecraft_uuid: str, size: int = 128, overlay: bool = True) -> str:
    """Get Minecraft avatar URL from Crafatar.
    
    Args:
        minecraft_uuid: Minecraft UUID
        size: Avatar size (default 128)
        overlay: Include skin overlay (default True)
        
    Returns:
        Avatar URL
    """
    # Remove dashes from UUID if present
    uuid_clean = minecraft_uuid.replace('-', '')
    
    overlay_param = "true" if overlay else "false"
    return f"https://crafatar.com/avatars/{uuid_clean}?size={size}&overlay={overlay_param}"


def detect_milestone(
    old_value: int,
    new_value: int,
    thresholds: List[int]
) -> Optional[int]:
    """Detect if a value crossed a milestone threshold.
    
    Args:
        old_value: Previous value
        new_value: Current value
        thresholds: List of milestone thresholds
        
    Returns:
        The milestone threshold crossed, or None
    """
    for threshold in sorted(thresholds):
        if old_value < threshold <= new_value:
            return threshold
    return None


def compare_lists(old_list: List[str], new_list: List[str]) -> Dict[str, List[str]]:
    """Compare two lists and return additions and removals.
    
    Args:
        old_list: Previous list
        new_list: Current list
        
    Returns:
        Dictionary with 'added' and 'removed' keys
    """
    old_set = set(old_list or [])
    new_set = set(new_list or [])
    
    return {
        'added': list(new_set - old_set),
        'removed': list(old_set - new_set)
    }


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_list(items: List[str], max_items: int = 10, conjunction: str = "and") -> str:
    """Format a list of items into a human-readable string.
    
    Args:
        items: List of items
        max_items: Maximum items to show before truncating
        conjunction: Word to use before last item
        
    Returns:
        Formatted string
    """
    if not items:
        return "none"
    
    if len(items) == 1:
        return items[0]
    
    if len(items) <= max_items:
        if len(items) == 2:
            return f"{items[0]} {conjunction} {items[1]}"
        return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"
    
    shown = items[:max_items]
    remaining = len(items) - max_items
    return f"{', '.join(shown)}, and {remaining} more"


def is_main_nation(nation_name: str, config: Dict[str, Any]) -> bool:
    """Check if a nation is a main nation.
    
    Args:
        nation_name: Nation name to check
        config: Bot configuration
        
    Returns:
        True if main nation, False otherwise
    """
    main_nations = [n['name'] for n in config.get('main_nations', [])]
    return nation_name in main_nations


def is_allied_nation(nation_name: str, config: Dict[str, Any]) -> bool:
    """Check if a nation is an allied nation.
    
    Args:
        nation_name: Nation name to check
        config: Bot configuration
        
    Returns:
        True if allied nation, False otherwise
    """
    return nation_name in config.get('allied_nations', [])


def get_nation_flag_url(nation_name: str, config: Dict[str, Any]) -> Optional[str]:
    """Get flag URL for a nation.
    
    Args:
        nation_name: Nation name
        config: Bot configuration
        
    Returns:
        Flag URL or None
    """
    for nation in config.get('main_nations', []):
        if nation['name'] == nation_name:
            return nation.get('flag_url')
    return None
