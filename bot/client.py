"""Main Discord bot client."""

import discord
from discord.ext import commands
import logging
import yaml
import os
from typing import Dict, Any
from pathlib import Path

from database import DatabaseManager, init_database
from api import EarthMCAPI, BatchQueryHandler, APICache

logger = logging.getLogger('EMCBot')


class EMCBot(commands.Bot):
    """EarthMC Verification Bot."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the bot.
        
        Args:
            config_path: Path to configuration file
        """
        # Store config path and directory
        self.config_path = os.path.abspath(config_path)
        self.bot_dir = os.path.dirname(self.config_path)
        
        # Load configuration
        self.config = self._load_config(self.config_path)
        
        # Set up intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        # Initialize bot
        super().__init__(
            command_prefix="!",  # Not used with slash commands
            intents=intents,
            help_command=None
        )
        
        # Initialize components
        self.db: DatabaseManager = None
        self.api: EarthMCAPI = None
        self.batch_handler: BatchQueryHandler = None
        self.api_cache: APICache = None
        
        # Guild reference
        self.guild: discord.Guild = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    async def setup_hook(self):
        """Called when bot is starting up."""
        logger.info("Setting up bot...")
        
        # Initialize database (use absolute path)
        db_path = os.path.join(self.bot_dir, "database.db")
        await init_database(db_path)
        self.db = DatabaseManager(db_path)
        logger.info(f"Database initialized at: {db_path}")
        
        # Initialize API client
        api_config = self.config.get('api', {})
        self.api = EarthMCAPI(
            base_url=api_config.get('base_url'),
            rate_limit=api_config.get('rate_limit', 180)
        )
        self.batch_handler = BatchQueryHandler(self.api)
        self.api_cache = APICache(ttl_seconds=300)
        logger.info("API client initialized")
        
        # Load cogs
        await self._load_cogs()
        
        # Sync commands with Discord
        guild_id = self.config['bot']['guild_id']
        guild = discord.Object(id=int(guild_id))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info(f"Commands synced to guild {guild_id}")
    
    async def _load_cogs(self):
        """Load all cogs."""
        cogs = [
            'cogs.verification',
            'cogs.admin',
            'cogs.auto_verify',
            'cogs.scanner'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        
        # Get guild reference
        guild_id = int(self.config['bot']['guild_id'])
        self.guild = self.get_guild(guild_id)
        
        if not self.guild:
            logger.error(f"Could not find guild with ID {guild_id}")
            return
        
        logger.info(f"Connected to guild: {self.guild.name}")
        logger.info("Bot is ready!")
    
    async def close(self):
        """Clean up when bot is shutting down."""
        logger.info("Shutting down bot...")
        
        # Close API session
        if self.api:
            await self.api.close()
        
        await super().close()
        logger.info("Bot shut down complete")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user is admin, False otherwise
        """
        # Check if user ID is in admin list
        admin_user_ids = self.config.get('admins', {}).get('user_ids', [])
        if str(user_id) in admin_user_ids:
            return True
        
        # Check if user has admin role
        if not self.guild:
            return False
        
        member = self.guild.get_member(user_id)
        if not member:
            return False
        
        admin_role_ids = self.config.get('admins', {}).get('role_ids', [])
        for role in member.roles:
            if str(role.id) in admin_role_ids:
                return True
        
        return False
    
    def is_blacklisted_discord(self, discord_id: str) -> bool:
        """Check if Discord ID is blacklisted.
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            True if blacklisted, False otherwise
        """
        blacklist = self.config.get('blacklist', {}).get('discord_ids', [])
        return discord_id in blacklist
    
    def is_blacklisted_minecraft(self, minecraft_uuid: str) -> bool:
        """Check if Minecraft UUID is blacklisted.
        
        Args:
            minecraft_uuid: Minecraft UUID
            
        Returns:
            True if blacklisted, False otherwise
        """
        blacklist = self.config.get('blacklist', {}).get('minecraft_uuids', [])
        return minecraft_uuid in blacklist
    
    async def get_logging_channel(self) -> discord.TextChannel:
        """Get the logging channel.
        
        Returns:
            Logging channel or None
        """
        channel_id = self.config.get('channels', {}).get('logging')
        if not channel_id:
            return None
        
        return self.guild.get_channel(int(channel_id))
    
    async def get_notification_channel(self, channel_type: str) -> discord.TextChannel:
        """Get a notification channel.
        
        Args:
            channel_type: Type of notification channel (government, status, milestones)
            
        Returns:
            Notification channel or None
        """
        channels_config = self.config.get('channels', {}).get('notifications', {})
        channel_id = channels_config.get(channel_type)
        
        if not channel_id:
            return None
        
        return self.guild.get_channel(int(channel_id))