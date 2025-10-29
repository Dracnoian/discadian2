"""Nickname formatting utilities."""

import logging
from typing import Optional
import discord

logger = logging.getLogger('EMCBot.Nicknames')


def format_nickname(
    minecraft_ign: str,
    town_name: Optional[str] = None,
    nation_name: Optional[str] = None,
    is_main_nation: bool = False
) -> str:
    """Format Discord nickname based on Minecraft and town/nation info.
    
    Args:
        minecraft_ign: Minecraft in-game name
        town_name: Town name (optional)
        nation_name: Nation name (optional)
        is_main_nation: Whether user is in main nation
        
    Returns:
        Formatted nickname string
    """
    # Sanitize IGN
    ign = sanitize_nickname_component(minecraft_ign)
    
    # Format: [IGN] | Town/Nation
    if is_main_nation and town_name:
        # Main nation citizen with town
        location = sanitize_nickname_component(town_name)
        nickname = f"[{ign}] | {location}"
    elif nation_name:
        # Has nation but not main nation, or no town
        location = sanitize_nickname_component(nation_name)
        nickname = f"[{ign}] | {location}"
    else:
        # No town or nation
        nickname = f"[{ign}]"
    
    # Discord nickname limit is 32 characters
    if len(nickname) > 32:
        # Truncate location part if needed
        max_location = 32 - len(f"[{ign}] | ")
        if is_main_nation and town_name:
            nickname = f"[{ign}] | {town_name[:max_location]}"
        elif nation_name:
            nickname = f"[{ign}] | {nation_name[:max_location]}"
        else:
            nickname = f"[{ign}]"
    
    return nickname[:32]  # Ensure we don't exceed limit


def sanitize_nickname_component(component: str) -> str:
    """Sanitize a component of the nickname.
    
    Args:
        component: Component string to sanitize
        
    Returns:
        Sanitized string
    """
    # Remove problematic characters
    sanitized = ''.join(
        c for c in component
        if c.isprintable() and c not in '@#:```'
    )
    return sanitized


async def set_nickname(
    member: discord.Member,
    nickname: str
) -> bool:
    """Set a member's nickname.
    
    Args:
        member: Discord member
        nickname: Nickname to set
        
    Returns:
        Success status
    """
    try:
        # Can't change nickname of server owner
        if member.id == member.guild.owner_id:
            logger.warning(f"Cannot change nickname of server owner {member.display_name}")
            return False
        
        # Can't change nickname of users with higher roles than bot
        if member.top_role >= member.guild.me.top_role:
            logger.warning(f"Cannot change nickname of {member.display_name} (higher role)")
            return False
        
        await member.edit(nick=nickname, reason="EMC Verification")
        logger.info(f"Set nickname for {member.display_name} to '{nickname}'")
        return True
        
    except discord.Forbidden:
        logger.error(f"Missing permissions to change nickname of {member.display_name}")
        return False
    except Exception as e:
        logger.error(f"Error setting nickname: {e}")
        return False


async def reset_nickname(member: discord.Member) -> bool:
    """Reset a member's nickname to their Discord username.
    
    Args:
        member: Discord member
        
    Returns:
        Success status
    """
    try:
        # Can't change nickname of server owner
        if member.id == member.guild.owner_id:
            logger.warning(f"Cannot change nickname of server owner {member.display_name}")
            return False
        
        # Can't change nickname of users with higher roles than bot
        if member.top_role >= member.guild.me.top_role:
            logger.warning(f"Cannot reset nickname of {member.display_name} (higher role)")
            return False
        
        await member.edit(nick=None, reason="EMC Verification Purge")
        logger.info(f"Reset nickname for {member.display_name}")
        return True
        
    except discord.Forbidden:
        logger.error(f"Missing permissions to reset nickname of {member.display_name}")
        return False
    except Exception as e:
        logger.error(f"Error resetting nickname: {e}")
        return False
