"""Admin commands cog."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Literal, Optional
import yaml

from utils import create_purge_confirmation_embed, create_scan_status_embed
from utils.roles import remove_verification_roles
from utils.nicknames import reset_nickname

logger = logging.getLogger('EMCBot.Admin')


class PurgeConfirmView(discord.ui.View):
    """Confirmation view for purge command."""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.confirmed = False
        
    @discord.ui.button(label="Confirm Purge", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm purge action."""
        await interaction.response.defer()
        self.confirmed = True
        self.stop()
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel purge action."""
        await interaction.response.defer()
        self.confirmed = False
        self.stop()


class AdminCog(commands.Cog):
    """Administrative commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    def is_admin_check():
        """Check if user is admin."""
        async def predicate(interaction: discord.Interaction) -> bool:
            return interaction.client.is_admin(interaction.user.id)
        return app_commands.check(predicate)
    
    # ========== TEXT COMMANDS (for when slash commands aren't working) ==========
    
    @commands.command(name="sync")
    async def sync_commands(self, ctx: commands.Context, scope: str = "guild"):
        """Sync slash commands to Discord (Text command for admins).
        
        Usage:
            !sync - Sync to current guild only (fast, ~10 seconds)
            !sync global - Sync globally to all guilds (slow, ~1 hour)
            !sync clear - Clear guild commands
        
        Args:
            scope: 'guild' (default), 'global', or 'clear'
        """
        # Check if user is admin
        if not self.bot.is_admin(ctx.author.id):
            await ctx.send("❌ You must be an admin to use this command.")
            return
        
        try:
            if scope == "clear":
                # Clear guild commands
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send("✅ Cleared all slash commands from this guild.")
                return
            
            elif scope == "global":
                # Global sync (takes ~1 hour to propagate)
                await ctx.send("🔄 Syncing commands globally... (This takes ~1 hour to propagate)")
                synced = await self.bot.tree.sync()
                await ctx.send(f"✅ Synced {len(synced)} commands globally.\n⏰ Wait up to 1 hour for changes to appear.")
                
                # List synced commands
                if synced:
                    cmd_list = "\n".join([f"  • /{cmd.name}" for cmd in synced])
                    await ctx.send(f"**Synced commands:**\n{cmd_list}")
            
            else:
                # Guild sync (fast, ~10 seconds)
                await ctx.send("🔄 Syncing commands to this guild...")
                
                # Copy global commands to guild and sync
                guild_obj = discord.Object(id=ctx.guild.id)
                self.bot.tree.copy_global_to(guild=guild_obj)
                synced = await self.bot.tree.sync(guild=guild_obj)
                
                await ctx.send(f"✅ Synced {len(synced)} commands to **{ctx.guild.name}**\n⏰ Wait 5-10 minutes and restart Discord (Ctrl+R).")
                
                # List synced commands
                if synced:
                    cmd_list = "\n".join([f"  • /{cmd.name}" for cmd in synced])
                    await ctx.send(f"**Synced commands:**\n{cmd_list}")
                else:
                    await ctx.send("⚠️ No commands were synced. Check that cogs are loaded correctly.")
            
            logger.info(f"Commands synced by {ctx.author} (scope: {scope})")
            
        except Exception as e:
            logger.error(f"Error syncing commands: {e}", exc_info=True)
            await ctx.send(f"❌ Error syncing commands: {e}")
    
    @commands.command(name="listcogs")
    async def list_cogs(self, ctx: commands.Context):
        """List all loaded cogs and their commands (Text command for admins)."""
        # Check if user is admin
        if not self.bot.is_admin(ctx.author.id):
            await ctx.send("❌ You must be an admin to use this command.")
            return
        
        embed = discord.Embed(
            title="📦 Loaded Cogs & Commands",
            color=discord.Color.blue()
        )
        
        # List cogs
        cogs = list(self.bot.cogs.keys())
        embed.add_field(
            name=f"Loaded Cogs ({len(cogs)})",
            value="\n".join([f"  • {cog}" for cog in cogs]) if cogs else "None",
            inline=False
        )
        
        # List slash commands
        slash_commands = self.bot.tree.get_commands()
        if slash_commands:
            cmd_list = "\n".join([f"  • /{cmd.name} - {cmd.description}" for cmd in slash_commands])
            embed.add_field(
                name=f"Slash Commands ({len(slash_commands)})",
                value=cmd_list,
                inline=False
            )
        else:
            embed.add_field(
                name="Slash Commands",
                value="⚠️ No slash commands registered",
                inline=False
            )
        
        # List text commands
        text_commands = [cmd for cmd in self.bot.commands if not cmd.hidden]
        if text_commands:
            cmd_list = "\n".join([f"  • !{cmd.name}" for cmd in text_commands])
            embed.add_field(
                name=f"Text Commands ({len(text_commands)})",
                value=cmd_list,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="reloadcog")
    async def reload_cog(self, ctx: commands.Context, cog_name: str):
        """Reload a specific cog (Text command for admins).
        
        Usage: !reloadcog cogs.admin
        """
        # Check if user is admin
        if not self.bot.is_admin(ctx.author.id):
            await ctx.send("❌ You must be an admin to use this command.")
            return
        
        try:
            await self.bot.reload_extension(cog_name)
            await ctx.send(f"✅ Reloaded cog: {cog_name}")
            logger.info(f"Cog {cog_name} reloaded by {ctx.author}")
        except Exception as e:
            await ctx.send(f"❌ Error reloading cog: {e}")
            logger.error(f"Error reloading cog {cog_name}: {e}", exc_info=True)
    
    # ========== SLASH COMMANDS ==========
    
    @app_commands.command(name="purge", description="Remove a user's verification")
    @is_admin_check()
    @app_commands.describe(
        type="Type of identifier",
        identifier="Discord ID or Minecraft UUID"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        type: Literal["Discord", "Minecraft"],
        identifier: str
    ):
        """Purge a user's verification."""
        await interaction.response.defer(thinking=True)
        
        try:
            # Find user in database
            if type == "Discord":
                user_data = await self.bot.db.get_user_by_discord(identifier)
            else:  # Minecraft
                user_data = await self.bot.db.get_user_by_uuid(identifier)
            
            # Show confirmation
            embed = create_purge_confirmation_embed(identifier, user_data)
            view = PurgeConfirmView()
            
            await interaction.followup.send(embed=embed, view=view)
            await view.wait()
            
            if not view.confirmed:
                await interaction.followup.send("❌ Purge cancelled.")
                return
            
            if not user_data:
                await interaction.followup.send("❌ User not found in database.")
                return
            
            # Get Discord member
            discord_id = user_data['discord_id']
            member = interaction.guild.get_member(int(discord_id))
            
            # Remove roles and nickname
            if member:
                await remove_verification_roles(member, self.bot.config)
                await reset_nickname(member)
            
            # Remove from database
            await self.bot.db.delete_user(discord_id)
            
            # Log to audit
            await self.bot.db.add_audit_log({
                'action_type': 'purge',
                'actor_id': str(interaction.user.id),
                'target_discord_id': discord_id,
                'target_minecraft_uuid': user_data['minecraft_uuid'],
                'details': {
                    'minecraft_ign': user_data['minecraft_ign'],
                    'reason': 'Manual purge'
                },
                'success': True
            })
            
            await interaction.followup.send(f"✅ Successfully purged user **{user_data['minecraft_ign']}**")
            
        except Exception as e:
            logger.error(f"Error in purge command: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred during purge.")
    
    @app_commands.command(name="scan", description="Manually trigger user and nation scans")
    @is_admin_check()
    async def scan(self, interaction: discord.Interaction):
        """Manually trigger scans."""
        await interaction.response.defer(thinking=True)
        
        try:
            # Get scanner cog
            scanner_cog = self.bot.get_cog('ScannerCog')
            if not scanner_cog:
                await interaction.followup.send("❌ Scanner cog not loaded.")
                return
            
            await interaction.followup.send("🔄 Starting scans...")
            
            # Run user scan
            user_result = await scanner_cog.run_user_scan()
            user_embed = create_scan_status_embed(
                "User",
                user_result['scanned'],
                user_result['changes'],
                user_result['duration']
            )
            await interaction.followup.send(embed=user_embed)
            
            # Run nation scan
            nation_result = await scanner_cog.run_nation_scan()
            nation_embed = create_scan_status_embed(
                "Nation",
                nation_result['scanned'],
                nation_result['changes'],
                nation_result['duration']
            )
            await interaction.followup.send(embed=nation_embed)
            
            await interaction.followup.send("✅ Scans complete!")
            
        except Exception as e:
            logger.error(f"Error in scan command: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred during scan.")
    
    @app_commands.command(name="blacklist", description="Manage blacklist")
    @is_admin_check()
    @app_commands.describe(
        action="Action to perform",
        discord_id="Discord user ID (optional)",
        minecraft_uuid="Minecraft UUID (optional)"
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "remove", "list"],
        discord_id: Optional[str] = None,
        minecraft_uuid: Optional[str] = None
    ):
        """Manage blacklist."""
        await interaction.response.defer(thinking=True)
        
        try:
            config_path = "./config.yaml"
            
            if action == "list":
                # Show current blacklist
                discord_blacklist = self.bot.config.get('blacklist', {}).get('discord_ids', [])
                minecraft_blacklist = self.bot.config.get('blacklist', {}).get('minecraft_uuids', [])
                
                embed = discord.Embed(
                    title="🚫 Blacklist",
                    color=discord.Color.red()
                )
                
                embed.add_field(
                    name="Discord IDs",
                    value="\n".join(discord_blacklist) if discord_blacklist else "None",
                    inline=False
                )
                embed.add_field(
                    name="Minecraft UUIDs",
                    value="\n".join(minecraft_blacklist) if minecraft_blacklist else "None",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                return
            
            if not discord_id and not minecraft_uuid:
                await interaction.followup.send("❌ Please provide either a Discord ID or Minecraft UUID.")
                return
            
            # Load config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'blacklist' not in config:
                config['blacklist'] = {'discord_ids': [], 'minecraft_uuids': []}
            
            # Perform action
            if action == "add":
                if discord_id:
                    if discord_id not in config['blacklist']['discord_ids']:
                        config['blacklist']['discord_ids'].append(discord_id)
                        message = f"Added Discord ID `{discord_id}` to blacklist"
                    else:
                        message = f"Discord ID `{discord_id}` already in blacklist"
                
                if minecraft_uuid:
                    if minecraft_uuid not in config['blacklist']['minecraft_uuids']:
                        config['blacklist']['minecraft_uuids'].append(minecraft_uuid)
                        message = f"Added Minecraft UUID `{minecraft_uuid}` to blacklist"
                    else:
                        message = f"Minecraft UUID `{minecraft_uuid}` already in blacklist"
            
            elif action == "remove":
                if discord_id:
                    if discord_id in config['blacklist']['discord_ids']:
                        config['blacklist']['discord_ids'].remove(discord_id)
                        message = f"Removed Discord ID `{discord_id}` from blacklist"
                    else:
                        message = f"Discord ID `{discord_id}` not in blacklist"
                
                if minecraft_uuid:
                    if minecraft_uuid in config['blacklist']['minecraft_uuids']:
                        config['blacklist']['minecraft_uuids'].remove(minecraft_uuid)
                        message = f"Removed Minecraft UUID `{minecraft_uuid}` from blacklist"
                    else:
                        message = f"Minecraft UUID `{minecraft_uuid}` not in blacklist"
            
            # Save config
            with open(config_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            
            # Reload bot config
            self.bot.config = config
            
            await interaction.followup.send(f"✅ {message}")
            
        except Exception as e:
            logger.error(f"Error in blacklist command: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred managing blacklist.")


async def setup(bot):
    """Set up the cog."""
    await bot.add_cog(AdminCog(bot))