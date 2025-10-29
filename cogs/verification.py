"""Verification command cog."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime

from utils import (
    create_verification_embed,
    determine_roles,
    format_nickname,
    validate_minecraft_username,
    is_main_nation
)
from utils.roles import assign_roles
from utils.nicknames import set_nickname

logger = logging.getLogger('EMCBot.Verification')


class VerificationDecisionView(discord.ui.View):
    """View for verification decision panel."""
    
    def __init__(self, cog, interaction, user, discord_data, minecraft_data, apply_nickname):
        super().__init__(timeout=300)
        self.cog = cog
        self.original_interaction = interaction
        self.user = user
        self.discord_data = discord_data
        self.minecraft_data = minecraft_data
        self.apply_nickname = apply_nickname
        self.choice = None
        
    @discord.ui.button(label="Approve with Discord Account", style=discord.ButtonStyle.green)
    async def approve_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve using Discord account link."""
        await interaction.response.defer()
        self.choice = "discord"
        self.stop()
        
    @discord.ui.button(label="Approve with Minecraft Account", style=discord.ButtonStyle.green)
    async def approve_minecraft(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve using Minecraft username link."""
        await interaction.response.defer()
        self.choice = "minecraft"
        self.stop()
        
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reject verification."""
        await interaction.response.defer()
        self.choice = "reject"
        self.stop()


class VerificationCog(commands.Cog):
    """Verification commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    def is_admin_check():
        """Check if user is admin."""
        async def predicate(interaction: discord.Interaction) -> bool:
            return interaction.client.is_admin(interaction.user.id)
        return app_commands.check(predicate)
    
    @app_commands.command(name="verify", description="Manually verify a user")
    @is_admin_check()
    @app_commands.describe(
        user="The Discord user to verify",
        minecraft_username="The Minecraft username",
        nickname="Whether to apply nickname (default: True)"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minecraft_username: str,
        nickname: bool = True
    ):
        """Manually verify a user."""
        await interaction.response.defer(thinking=True)
        
        try:
            # Validate inputs
            if not validate_minecraft_username(minecraft_username):
                await interaction.followup.send("❌ Invalid Minecraft username format.")
                return
            
            # Check blacklist
            if self.bot.is_blacklisted_discord(str(user.id)):
                await interaction.followup.send("❌ This Discord user is blacklisted.")
                return
            
            # Query EMC API for both accounts
            discord_data = await self.bot.api.get_player_by_discord(str(user.id))
            minecraft_data = await self.bot.api.get_player_by_username(minecraft_username)
            
            if not minecraft_data:
                await interaction.followup.send(f"❌ Minecraft user '{minecraft_username}' not found on EarthMC.")
                return
            
            # Check if Minecraft account is blacklisted
            mc_uuid = minecraft_data.get('uuid')
            if self.bot.is_blacklisted_minecraft(mc_uuid):
                await interaction.followup.send("❌ This Minecraft account is blacklisted.")
                return
            
            # Determine verification scenario
            scenario = self._determine_scenario(discord_data, minecraft_data, user.id)
            
            if scenario == "both_linked":
                # Auto-approve if both linked correctly
                await self._complete_verification(
                    interaction, user, minecraft_data, nickname
                )
            
            elif scenario == "neither_linked":
                # Show decision panel
                await self._show_decision_panel(
                    interaction, user, discord_data, minecraft_data, nickname
                )
            
            elif scenario == "discord_linked_different":
                # Discord linked but to different MC account
                await self._show_decision_panel(
                    interaction, user, discord_data, minecraft_data, nickname
                )
            
            elif scenario == "minecraft_linked_different":
                # MC account linked but to different Discord
                await self._show_decision_panel(
                    interaction, user, discord_data, minecraft_data, nickname
                )
                
        except Exception as e:
            logger.error(f"Error in verify command: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred during verification.")
    
    def _determine_scenario(self, discord_data, minecraft_data, user_id):
        """Determine verification scenario."""
        discord_linked = discord_data is not None
        minecraft_linked = minecraft_data and minecraft_data.get('discord')
        
        if discord_linked and minecraft_linked:
            # Check if they link to each other
            discord_mc_uuid = discord_data.get('uuid')
            mc_discord_id = minecraft_data.get('discord')
            
            if discord_mc_uuid == minecraft_data.get('uuid') and mc_discord_id == str(user_id):
                return "both_linked"
            else:
                return "both_linked_different"
        elif not discord_linked and not minecraft_linked:
            return "neither_linked"
        elif discord_linked:
            return "discord_linked_different"
        else:
            return "minecraft_linked_different"
    
    async def _show_decision_panel(self, interaction, user, discord_data, minecraft_data, apply_nickname):
        """Show decision panel for admin to choose."""
        # Create embed showing both options
        embed = discord.Embed(
            title="🔍 Verification Decision Required",
            description=f"Choose which account to use for {user.mention}",
            color=discord.Color.orange()
        )
        
        # Discord account info
        if discord_data:
            embed.add_field(
                name="Discord Linked Account",
                value=f"**IGN:** {discord_data.get('name')}\n**UUID:** {discord_data.get('uuid')}\n**Town:** {discord_data.get('town', {}).get('name', 'None')}\n**Nation:** {discord_data.get('nation', {}).get('name', 'None')}",
                inline=True
            )
        else:
            embed.add_field(
                name="Discord Linked Account",
                value="Not linked to any account",
                inline=True
            )
        
        # Minecraft account info
        if minecraft_data:
            embed.add_field(
                name="Minecraft Username Account",
                value=f"**IGN:** {minecraft_data.get('name')}\n**UUID:** {minecraft_data.get('uuid')}\n**Town:** {minecraft_data.get('town', {}).get('name', 'None')}\n**Nation:** {minecraft_data.get('nation', {}).get('name', 'None')}",
                inline=True
            )
        
        # Create view with buttons
        view = VerificationDecisionView(self, interaction, user, discord_data, minecraft_data, apply_nickname)
        
        await interaction.followup.send(embed=embed, view=view)
        
        # Wait for decision
        await view.wait()
        
        if view.choice == "discord" and discord_data:
            await self._complete_verification(interaction, user, discord_data, apply_nickname)
        elif view.choice == "minecraft" and minecraft_data:
            await self._complete_verification(interaction, user, minecraft_data, apply_nickname)
        elif view.choice == "reject":
            await interaction.followup.send("❌ Verification rejected.")
    
    async def _complete_verification(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        player_data: dict,
        apply_nickname: bool
    ):
        """Complete the verification process."""
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
            
            # Check if linked on EMC
            emc_verified = player_data.get('discord') == str(user.id)
            
            # Determine roles
            role_ids = determine_roles(nation_name, town_uuid, self.bot.config)
            
            # Get county if in main nation
            county_uuid = None
            if is_main_nation(nation_name, self.bot.config) and town_uuid:
                county_data = await self.bot.db.get_county_for_town(town_uuid)
                if county_data:
                    county_uuid = county_data.get('county_uuid')
            
            # Assign roles
            success = await assign_roles(user, role_ids, interaction.guild)
            if not success:
                await interaction.followup.send("⚠️ Could not assign roles (insufficient permissions or higher role).")
            
            # Apply nickname
            if apply_nickname:
                nickname_text = format_nickname(
                    minecraft_ign,
                    town_name,
                    nation_name,
                    is_main_nation(nation_name, self.bot.config)
                )
                await set_nickname(user, nickname_text)
            
            # Save to database
            user_data = {
                'discord_id': str(user.id),
                'minecraft_uuid': minecraft_uuid,
                'minecraft_ign': minecraft_ign,
                'town_uuid': town_uuid,
                'town_name': town_name,
                'nation_uuid': nation_uuid,
                'nation_name': nation_name,
                'county_uuid': county_uuid,
                'emc_verified': emc_verified,
                'verified_by': str(interaction.user.id)
            }
            
            # Check if user already exists
            existing = await self.bot.db.get_user_by_discord(str(user.id))
            if existing:
                await self.bot.db.update_user(str(user.id), user_data)
            else:
                await self.bot.db.add_user(user_data)
            
            # Log to audit
            await self.bot.db.add_audit_log({
                'action_type': 'verify',
                'actor_id': str(interaction.user.id),
                'target_discord_id': str(user.id),
                'target_minecraft_uuid': minecraft_uuid,
                'details': {
                    'minecraft_ign': minecraft_ign,
                    'town': town_name,
                    'nation': nation_name,
                    'emc_verified': emc_verified
                },
                'success': True
            })
            
            # Create verification embed
            embed = create_verification_embed(user_data, user, self.bot.config)
            
            # Send to logging channel and create thread
            logging_channel = await self.bot.get_logging_channel()
            if logging_channel:
                message = await logging_channel.send(embed=embed)
                thread = await message.create_thread(
                    name=f"Verification: {minecraft_ign}",
                    auto_archive_duration=1440
                )
                await thread.send(f"Verified by {interaction.user.mention}")
            
            # Confirm to admin
            await interaction.followup.send(f"✅ Successfully verified {user.mention} as **{minecraft_ign}**!")
            
        except Exception as e:
            logger.error(f"Error completing verification: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while completing verification.")


async def setup(bot):
    """Set up the cog."""
    await bot.add_cog(VerificationCog(bot))
