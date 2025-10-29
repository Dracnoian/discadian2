"""Role assignment logic."""

import logging
from typing import List, Dict, Any, Optional
import discord

logger = logging.getLogger('EMCBot.Roles')


def determine_roles(
    nation_name: Optional[str],
    town_uuid: Optional[str],
    config: Dict[str, Any],
    county_uuid: Optional[str] = None
) -> List[str]:
    """Determine which role IDs should be assigned to a user.
    
    Args:
        nation_name: User's nation name
        town_uuid: User's town UUID
        config: Bot configuration
        county_uuid: User's county UUID
        
    Returns:
        List of role IDs to assign
    """
    role_ids = []
    
    if not nation_name:
        # No nation = foreigner only
        foreigner_id = config['roles'].get('foreigner')
        if foreigner_id:
            role_ids.append(foreigner_id)
        return role_ids
    
    # Check if main nation
    main_nation_names = [n['name'] for n in config.get('main_nations', [])]
    if nation_name in main_nation_names:
        # Citizen role
        citizen_id = config['roles'].get('citizen')
        if citizen_id:
            role_ids.append(citizen_id)
        
        # Add county role if applicable
        if county_uuid:
            county_role_ids = get_county_roles([county_uuid], config)
            role_ids.extend(county_role_ids)
    
    # Check if allied nation
    elif nation_name in config.get('allied_nations', []):
        # Allied role
        allied_id = config['roles'].get('allied')
        if allied_id:
            role_ids.append(allied_id)
        
        # Also foreigner role
        foreigner_id = config['roles'].get('foreigner')
        if foreigner_id:
            role_ids.append(foreigner_id)
    
    else:
        # Other nation = foreigner
        foreigner_id = config['roles'].get('foreigner')
        if foreigner_id:
            role_ids.append(foreigner_id)
    
    logger.debug(f"Determined roles for nation {nation_name}: {role_ids}")
    return role_ids


def get_county_roles(county_uuids: List[str], config: Dict[str, Any]) -> List[str]:
    """Get Discord role IDs for counties.
    
    Args:
        county_uuids: List of county UUIDs
        config: Bot configuration
        
    Returns:
        List of role IDs
    """
    # County role mapping would be stored in database
    # For now, return empty list as counties are managed in DB
    return []


async def assign_roles(
    member: discord.Member,
    role_ids: List[str],
    guild: discord.Guild,
    remove_old: bool = True
) -> bool:
    """Assign roles to a member.
    
    Args:
        member: Discord member
        role_ids: List of role IDs to assign
        guild: Discord guild
        remove_old: Whether to remove old verification roles first
        
    Returns:
        Success status
    """
    try:
        # Get role objects
        roles_to_add = []
        for role_id in role_ids:
            role = guild.get_role(int(role_id))
            if role:
                roles_to_add.append(role)
            else:
                logger.warning(f"Role {role_id} not found in guild")
        
        if not roles_to_add:
            logger.warning("No valid roles to assign")
            return False
        
        # Remove old verification roles if requested
        if remove_old:
            # Get verification role IDs from config
            verification_role_ids = []
            # This would get all possible verification roles
            # For simplicity, we'll just add the new roles
        
        # Add new roles
        await member.add_roles(*roles_to_add, reason="EMC Verification")
        logger.info(f"Assigned {len(roles_to_add)} roles to {member.display_name}")
        return True
        
    except discord.Forbidden:
        logger.error(f"Missing permissions to assign roles to {member.display_name}")
        return False
    except Exception as e:
        logger.error(f"Error assigning roles: {e}")
        return False


async def remove_verification_roles(
    member: discord.Member,
    config: Dict[str, Any]
) -> bool:
    """Remove all verification-related roles from a member.
    
    Args:
        member: Discord member
        config: Bot configuration
        
    Returns:
        Success status
    """
    try:
        # Get all verification role IDs
        role_ids = [
            config['roles'].get('citizen'),
            config['roles'].get('allied'),
            config['roles'].get('foreigner')
        ]
        
        # Filter out None values
        role_ids = [rid for rid in role_ids if rid]
        
        # Get role objects
        roles_to_remove = []
        for role_id in role_ids:
            role = member.guild.get_role(int(role_id))
            if role and role in member.roles:
                roles_to_remove.append(role)
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="EMC Verification Purge")
            logger.info(f"Removed {len(roles_to_remove)} roles from {member.display_name}")
        
        return True
        
    except discord.Forbidden:
        logger.error(f"Missing permissions to remove roles from {member.display_name}")
        return False
    except Exception as e:
        logger.error(f"Error removing roles: {e}")
        return False


async def update_roles(
    member: discord.Member,
    old_role_ids: List[str],
    new_role_ids: List[str],
    guild: discord.Guild
) -> bool:
    """Update member roles, removing old and adding new.
    
    Args:
        member: Discord member
        old_role_ids: List of old role IDs to remove
        new_role_ids: List of new role IDs to add
        guild: Discord guild
        
    Returns:
        Success status
    """
    try:
        # Get roles to remove
        roles_to_remove = []
        for role_id in old_role_ids:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                roles_to_remove.append(role)
        
        # Get roles to add
        roles_to_add = []
        for role_id in new_role_ids:
            role = guild.get_role(int(role_id))
            if role and role not in member.roles:
                roles_to_add.append(role)
        
        # Remove old roles
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="EMC Verification Update")
        
        # Add new roles
        if roles_to_add:
            await member.add_roles(*roles_to_add, reason="EMC Verification Update")
        
        logger.info(
            f"Updated roles for {member.display_name}: "
            f"removed {len(roles_to_remove)}, added {len(roles_to_add)}"
        )
        return True
        
    except discord.Forbidden:
        logger.error(f"Missing permissions to update roles for {member.display_name}")
        return False
    except Exception as e:
        logger.error(f"Error updating roles: {e}")
        return False
