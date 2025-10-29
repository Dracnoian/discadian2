"""Embed generation utilities."""

import discord
from datetime import datetime
from typing import Optional, Dict, Any
from .helpers import format_timestamp, get_avatar_url


def create_verification_embed(
    user_data: Dict[str, Any],
    member: discord.Member,
    config: Dict[str, Any]
) -> discord.Embed:
    """Create verification information embed.
    
    Args:
        user_data: User data from database or API
        member: Discord member object
        config: Bot configuration
        
    Returns:
        Discord embed object
    """
    # Determine color based on verification status
    emc_verified = user_data.get('emc_verified', False)
    color = discord.Color.green() if emc_verified else discord.Color.red()
    
    # Create embed
    embed = discord.Embed(
        title="User Information [ Minecraft & Discord ]",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    # Get nation info for author
    nation_name = user_data.get('nation_name', 'Unknown')
    nation_flag = None
    
    # Try to find nation flag from config
    for nation in config.get('main_nations', []):
        if nation['name'] == nation_name:
            nation_flag = nation.get('flag_url')
            break
    
    if nation_flag:
        embed.set_author(
            name=f"Republic of {nation_name}",
            icon_url=nation_flag
        )
    else:
        embed.set_author(name=f"Nation: {nation_name}")
    
    # Set thumbnail to Minecraft avatar
    minecraft_uuid = user_data.get('minecraft_uuid', '')
    if minecraft_uuid:
        embed.set_thumbnail(url=get_avatar_url(minecraft_uuid))
    
    # Add fields
    embed.add_field(
        name="IGN",
        value=user_data.get('minecraft_ign', 'Unknown'),
        inline=False
    )
    
    embed.add_field(
        name="Discord",
        value=f"{member.mention} ({member.display_name})",
        inline=False
    )
    
    embed.add_field(
        name="Discord ID",
        value=str(member.id),
        inline=False
    )
    
    embed.add_field(
        name="Discord Created",
        value=format_timestamp(member.created_at),
        inline=False
    )
    
    # Town info
    town_name = user_data.get('town_name')
    if town_name:
        embed.add_field(name="Town", value=town_name, inline=False)
    else:
        embed.add_field(name="Town", value="No town", inline=False)
    
    # Nation info
    if nation_name:
        embed.add_field(name="Nation", value=nation_name, inline=False)
    else:
        embed.add_field(name="Nation", value="No nation", inline=False)
    
    # Verification timestamps
    if user_data.get('verified_at'):
        embed.add_field(
            name="Verified At",
            value=format_timestamp(user_data['verified_at']),
            inline=False
        )
    
    if member.joined_at:
        embed.add_field(
            name="Joined Discord",
            value=format_timestamp(member.joined_at),
            inline=False
        )
    
    # Footer
    embed.set_footer(text=datetime.now().strftime('%m/%d/%Y %I:%M %p'))
    
    return embed


def create_notification_embed(
    notification_type: str,
    town_data: Dict[str, Any],
    changes: Dict[str, Any],
    config: Dict[str, Any]
) -> Optional[discord.Embed]:
    """Create notification embed for town changes.
    
    Args:
        notification_type: Type of notification (government, status, milestone)
        town_data: Current town data
        changes: Dictionary of changes detected
        config: Bot configuration
        
    Returns:
        Discord embed object or None if no notification needed
    """
    if not changes:
        return None
    
    town_name = town_data.get('town_name', 'Unknown Town')
    nation_name = town_data.get('nation_name', 'Unknown Nation')
    
    # Set color based on type
    color_map = {
        'government': discord.Color.blue(),
        'status': discord.Color.orange(),
        'milestone': discord.Color.gold()
    }
    color = color_map.get(notification_type, discord.Color.blurple())
    
    embed = discord.Embed(
        title=f"🏛️ {town_name} Update",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    embed.set_author(name=nation_name)
    
    # Add change descriptions based on type
    if notification_type == 'government':
        if 'mayor' in changes:
            old, new = changes['mayor']
            embed.add_field(
                name="Mayor Change",
                value=f"**Old:** {old or 'None'}\n**New:** {new or 'None'}",
                inline=False
            )
        
        if 'board_added' in changes:
            for member in changes['board_added']:
                embed.add_field(
                    name="Board Member Added",
                    value=member,
                    inline=True
                )
        
        if 'board_removed' in changes:
            for member in changes['board_removed']:
                embed.add_field(
                    name="Board Member Removed",
                    value=member,
                    inline=True
                )
        
        if 'residents_added' in changes:
            count = len(changes['residents_added'])
            embed.add_field(
                name=f"Residents Joined ({count})",
                value=", ".join(changes['residents_added'][:10]),
                inline=False
            )
        
        if 'residents_removed' in changes:
            count = len(changes['residents_removed'])
            embed.add_field(
                name=f"Residents Left ({count})",
                value=", ".join(changes['residents_removed'][:10]),
                inline=False
            )
    
    elif notification_type == 'status':
        status_labels = {
            'is_public': 'Public Status',
            'is_open': 'Open Status',
            'is_overclaimed': 'Overclaimed Status',
            'is_for_sale': 'For Sale Status',
            'has_overclaim_shield': 'Overclaim Shield'
        }
        
        for key, (old, new) in changes.items():
            label = status_labels.get(key, key)
            embed.add_field(
                name=label,
                value=f"{old} → {new}",
                inline=True
            )
    
    elif notification_type == 'milestone':
        if 'population' in changes:
            value = changes['population']
            embed.add_field(
                name="🎉 Population Milestone",
                value=f"Reached **{value}** residents!",
                inline=False
            )
        
        if 'balance' in changes:
            value = changes['balance']
            embed.add_field(
                name="💰 Balance Milestone",
                value=f"Reached **{value:,.2f}** gold!",
                inline=False
            )
    
    embed.set_footer(text=f"Updated at {datetime.now().strftime('%I:%M %p')}")
    
    return embed


def create_purge_confirmation_embed(
    identifier: str,
    user_data: Optional[Dict] = None
) -> discord.Embed:
    """Create confirmation embed for purge command.
    
    Args:
        identifier: Discord ID or Minecraft UUID
        user_data: User data if found in database
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="⚠️ Confirm Purge",
        description=f"Are you sure you want to purge this user?",
        color=discord.Color.red()
    )
    
    if user_data:
        embed.add_field(
            name="Discord ID",
            value=user_data.get('discord_id', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="Minecraft IGN",
            value=user_data.get('minecraft_ign', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="Town",
            value=user_data.get('town_name', 'None'),
            inline=True
        )
        embed.add_field(
            name="Nation",
            value=user_data.get('nation_name', 'None'),
            inline=True
        )
    else:
        embed.add_field(
            name="Identifier",
            value=identifier,
            inline=False
        )
        embed.add_field(
            name="Status",
            value="User not found in database",
            inline=False
        )
    
    return embed


def create_scan_status_embed(
    scan_type: str,
    users_scanned: int,
    changes_detected: int,
    duration: float
) -> discord.Embed:
    """Create embed showing scan results.
    
    Args:
        scan_type: Type of scan (user or nation)
        users_scanned: Number of users/towns scanned
        changes_detected: Number of changes found
        duration: Scan duration in seconds
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"📊 {scan_type.title()} Scan Complete",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name="Items Scanned",
        value=str(users_scanned),
        inline=True
    )
    embed.add_field(
        name="Changes Detected",
        value=str(changes_detected),
        inline=True
    )
    embed.add_field(
        name="Duration",
        value=f"{duration:.2f}s",
        inline=True
    )
    
    return embed
