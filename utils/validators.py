"""Input validation utilities."""

import re
import logging

logger = logging.getLogger('EMCBot.Validators')


def validate_discord_id(discord_id: str) -> bool:
    """Validate Discord ID format.
    
    Args:
        discord_id: Discord user ID string
        
    Returns:
        True if valid, False otherwise
    """
    if not discord_id:
        return False
    
    # Discord IDs are numeric and at least 17 characters
    if not discord_id.isdigit():
        return False
    
    if len(discord_id) < 17 or len(discord_id) > 20:
        return False
    
    return True


def validate_minecraft_username(username: str) -> bool:
    """Validate Minecraft username format.
    
    Args:
        username: Minecraft username
        
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False
    
    # Minecraft usernames are 3-16 characters, alphanumeric and underscores
    if len(username) < 3 or len(username) > 16:
        return False
    
    # Check if alphanumeric and underscores only
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False
    
    return True


def validate_minecraft_uuid(uuid: str) -> bool:
    """Validate Minecraft UUID format.
    
    Args:
        uuid: Minecraft UUID string
        
    Returns:
        True if valid, False otherwise
    """
    if not uuid:
        return False
    
    # Minecraft UUIDs are 32 hex characters (without dashes) or 36 with dashes
    # Remove dashes for validation
    uuid_clean = uuid.replace('-', '')
    
    if len(uuid_clean) != 32:
        return False
    
    # Check if hex
    try:
        int(uuid_clean, 16)
        return True
    except ValueError:
        return False


def sanitize_nickname(nickname: str) -> str:
    """Sanitize nickname for Discord.
    
    Args:
        nickname: Nickname string
        
    Returns:
        Sanitized nickname
    """
    # Remove problematic characters
    sanitized = ''.join(
        c for c in nickname
        if c.isprintable() and c not in '@#:```'
    )
    
    # Limit to Discord's 32 character limit
    return sanitized[:32]


def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize general text input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove non-printable characters
    sanitized = ''.join(c for c in text if c.isprintable())
    
    # Trim to max length
    return sanitized[:max_length]


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url:
        return False
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    return bool(url_pattern.match(url))
