"""Discord event handlers."""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EMCBot.Events')


def setup_events(bot: commands.Bot):
    """Set up bot event handlers.
    
    Args:
        bot: Bot instance
    """
    
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        
        else:
            logger.error(f"Command error: {error}", exc_info=error)
            await ctx.send("❌ An error occurred while executing the command.")
    
    @bot.event
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):
        """Handle application command errors."""
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s",
                ephemeral=True
            )
        
        elif isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
        
        elif isinstance(error, discord.app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
        
        else:
            logger.error(f"App command error: {error}", exc_info=error)
            
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while executing the command.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while executing the command.",
                    ephemeral=True
                )
    
    @bot.event
    async def on_error(event: str, *args, **kwargs):
        """Handle general errors."""
        logger.error(f"Error in event {event}", exc_info=True)
    
    @bot.event
    async def on_guild_join(guild: discord.Guild):
        """Called when bot joins a guild."""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    @bot.event
    async def on_guild_remove(guild: discord.Guild):
        """Called when bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    @bot.event
    async def on_member_remove(member: discord.Member):
        """Called when a member leaves the guild."""
        logger.info(f"Member left: {member.display_name} (ID: {member.id})")
        # Note: Don't delete from database - they might rejoin
