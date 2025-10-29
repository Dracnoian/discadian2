"""Auto-verification cog."""

import discord
from discord.ext import commands
import logging

from utils import (
    create_verification_embed,
    determine_roles,
    format_nickname,
    is_main_nation
)
from utils.roles import assign_roles
from utils.nicknames import set_nickname

logger = logging.getLogger('EMCBot.AutoVerify')


class AutoVerifyCog(commands.Cog):
    """Automatic verification on member join."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle member join event."""
        # Only process if in the configured guild
        if member.guild.id != int(self.bot.config['bot']['guild_id']):
            return
        
        logger.info(f"Member joined: {member.display_name} (ID: {member.id})")
        
        try:
            # Check blacklist
            if self.bot.is_blacklisted_discord(str(member.id)):
                logger.warning(f"Blacklisted user attempted to join: {member.id}")
                return
            
            # Check if already verified in database (rejoin case)
            existing_user = await self.bot.db.get_user_by_discord(str(member.id))
            
            if existing_user:
                # User rejoined - reverify with current EMC status
                logger.info(f"Rejoining user detected: {member.display_name}")
                await self._reverify_user(member, existing_user)
                return
            
            # Query EMC API for Discord-linked account
            player_data = await self.bot.api.get_player_by_discord(str(member.id))
            
            if not player_data:
                # No linked account - do nothing
                logger.info(f"No EMC account linked for {member.display_name}")
                return
            
            # Check if Minecraft account is blacklisted
            mc_uuid = player_data.get('uuid')
            if self.bot.is_blacklisted_minecraft(mc_uuid):
                logger.warning(f"User has blacklisted Minecraft account: {member.id}")
                return
            
            # Auto-verify the user
            await self._auto_verify(member, player_data)
            
        except Exception as e:
            logger.error(f"Error in on_member_join: {e}", exc_info=True)
    
    async def _auto_verify(self, member: discord.Member, player_data: dict):
        """Automatically verify a new member."""
        try:
            # Extract data
            minecraft_uuid = player_data.get('uuid')
            minecraft_ign = player_data.get('name')
            town = player_data.get('town', {})
            nation = player_data.get('nation', {})
            
            town_uuid = town.get('uuid')
            town_name = town.get('name')
            nation_uuid = nation.get('uuid')
            nation_name = nation.get('name')
            
            # EMC verified (Discord is linked)
            emc_verified = True
            
            # Determine roles
            role_ids = determine_roles(nation_name, town_uuid, self.bot.config)
            
            # Get county if in main nation
            county_uuid = None
            if is_main_nation(nation_name, self.bot.config) and town_uuid:
                county_data = await self.bot.db.get_county_for_town(town_uuid)
                if county_data:
                    county_uuid = county_data.get('county_uuid')
            
            # Assign roles
            await assign_roles(member, role_ids, member.guild)
            
            # Apply nickname
            nickname_text = format_nickname(
                minecraft_ign,
                town_name,
                nation_name,
                is_main_nation(nation_name, self.bot.config)
            )
            await set_nickname(member, nickname_text)
            
            # Save to database
            user_data = {
                'discord_id': str(member.id),
                'minecraft_uuid': minecraft_uuid,
                'minecraft_ign': minecraft_ign,
                'town_uuid': town_uuid,
                'town_name': town_name,
                'nation_uuid': nation_uuid,
                'nation_name': nation_name,
                'county_uuid': county_uuid,
                'emc_verified': emc_verified,
                'verified_by': None  # Auto-verified
            }
            
            await self.bot.db.add_user(user_data)
            
            # Log to audit
            await self.bot.db.add_audit_log({
                'action_type': 'auto_verify',
                'actor_id': None,
                'target_discord_id': str(member.id),
                'target_minecraft_uuid': minecraft_uuid,
                'details': {
                    'minecraft_ign': minecraft_ign,
                    'town': town_name,
                    'nation': nation_name,
                    'trigger': 'member_join'
                },
                'success': True
            })
            
            # Create verification embed
            embed = create_verification_embed(user_data, member, self.bot.config)
            
            # Send to logging channel and create thread
            logging_channel = await self.bot.get_logging_channel()
            if logging_channel:
                message = await logging_channel.send(embed=embed)
                thread = await message.create_thread(
                    name=f"Auto-Verification: {minecraft_ign}",
                    auto_archive_duration=1440
                )
                await thread.send(f"Automatically verified on join")
            
            logger.info(f"Auto-verified {member.display_name} as {minecraft_ign}")
            
        except Exception as e:
            logger.error(f"Error in auto-verify: {e}", exc_info=True)
    
    async def _reverify_user(self, member: discord.Member, existing_user: dict):
        """Re-verify a returning member with current EMC status."""
        try:
            # Query current EMC data
            minecraft_uuid = existing_user['minecraft_uuid']
            player_data = await self.bot.api.get_player_by_uuid(minecraft_uuid)
            
            if not player_data:
                logger.warning(f"Could not find EMC data for returning user {member.display_name}")
                return
            
            # Update with current data
            town = player_data.get('town', {})
            nation = player_data.get('nation', {})
            
            town_uuid = town.get('uuid')
            town_name = town.get('name')
            nation_uuid = nation.get('uuid')
            nation_name = nation.get('name')
            
            # Determine roles
            role_ids = determine_roles(nation_name, town_uuid, self.bot.config)
            
            # Get county if in main nation
            county_uuid = None
            if is_main_nation(nation_name, self.bot.config) and town_uuid:
                county_data = await self.bot.db.get_county_for_town(town_uuid)
                if county_data:
                    county_uuid = county_data.get('county_uuid')
            
            # Assign roles
            await assign_roles(member, role_ids, member.guild)
            
            # Apply nickname
            minecraft_ign = player_data.get('name')
            nickname_text = format_nickname(
                minecraft_ign,
                town_name,
                nation_name,
                is_main_nation(nation_name, self.bot.config)
            )
            await set_nickname(member, nickname_text)
            
            # Update database
            updates = {
                'town_uuid': town_uuid,
                'town_name': town_name,
                'nation_uuid': nation_uuid,
                'nation_name': nation_name,
                'county_uuid': county_uuid
            }
            await self.bot.db.update_user(str(member.id), updates)
            
            # Log to audit
            await self.bot.db.add_audit_log({
                'action_type': 'rejoin_reverify',
                'actor_id': None,
                'target_discord_id': str(member.id),
                'target_minecraft_uuid': minecraft_uuid,
                'details': {
                    'minecraft_ign': minecraft_ign,
                    'town': town_name,
                    'nation': nation_name
                },
                'success': True
            })
            
            logger.info(f"Re-verified returning user {member.display_name}")
            
        except Exception as e:
            logger.error(f"Error in reverify: {e}", exc_info=True)


async def setup(bot):
    """Set up the cog."""
    await bot.add_cog(AutoVerifyCog(bot))
