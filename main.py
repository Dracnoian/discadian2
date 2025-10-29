"""Main entry point for EMC Verification Bot."""

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Add script directory to path to ensure imports work
sys.path.insert(0, SCRIPT_DIR)

# Change to script directory so all relative paths work correctly
os.chdir(SCRIPT_DIR)

print("Starting EMC Verification Bot...")
print(f"Python: {sys.version}")
print(f"Script directory: {SCRIPT_DIR}")
print(f"Working directory: {os.getcwd()}")
print()

# Try importing the bot
try:
    from bot import EMCBot
    print("✓ Bot module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import bot module: {e}")
    print()
    print("Please run the diagnostic script to identify the issue:")
    print("  python diagnose.py")
    print()
    print("Common fixes:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Check all __init__.py files exist")
    print("  3. Check for syntax errors: python -m py_compile bot/client.py")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error importing bot: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist (relative to script dir)
    log_dir = os.path.join(SCRIPT_DIR, "logs")
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    log_file = os.path.join(log_dir, 'bot.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set up discord.py logger
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Set up aiohttp logger
    aiohttp_logger = logging.getLogger('aiohttp')
    aiohttp_logger.setLevel(logging.WARNING)
    
    logging.info(f"Logging configured - log file: {log_file}")


async def main():
    """Main function."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger('EMCBot.Main')
    
    logger.info("=" * 50)
    logger.info("EMC Verification Bot Starting")
    logger.info("=" * 50)
    logger.info(f"Script directory: {SCRIPT_DIR}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Check for config file (relative to script directory)
    config_path = os.path.join(SCRIPT_DIR, 'config.yaml')
    if not os.path.exists(config_path):
        logger.error(f"config.yaml not found at: {config_path}")
        print()
        print(f"✗ config.yaml not found at: {config_path}")
        print("Please create config.yaml in the same directory as main.py")
        return
    
    logger.info(f"Loading config from: {config_path}")
    
    # Create and run bot (pass config path)
    bot = EMCBot(config_path=config_path)
    
    try:
        # Get token from config
        token = bot.config['bot']['token']
        
        # Debug: Show token info (masked for security)
        logger.info(f"Token type: {type(token)}")
        logger.info(f"Token length: {len(token) if token else 0}")
        if token:
            # Show first 10 chars for debugging
            logger.info(f"Token starts with: {token[:10]}...")
        
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            logger.error("Please set your bot token in config.yaml!")
            print()
            print("✗ Bot token not set!")
            print("Please edit config.yaml and set your bot token.")
            print(f"Current token value: {token}")
            return
        
        # Run bot
        logger.info("Starting bot...")
        await bot.start(token)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("Bot shut down")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")