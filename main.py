"""
Edue Helper Discord Bot
Main entry point for the educational Discord bot with chat, Q&A, and rate limiting features.
"""

import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EdueBot(commands.Bot):
    """
    Custom Bot class for Edue Helper with initialization and setup hooks.
    """
    
    def __init__(self):
        # Required intents for message content and guild members
        intents = discord.Intents.default()
        intents.message_content = True  # Required for commands to work
        intents.guilds = True
        intents.guild_messages = True
        intents.members = True  # For member-related features
        
        super().__init__(
            command_prefix='!',  # Text command prefix
            intents=intents,
            description="Edue Helper - Your educational Discord assistant",
            help_command=commands.DefaultHelpCommand()
        )
    
    async def setup_hook(self):
        """
        Called when the bot is starting up, before connecting to Discord.
        Used to load extensions and sync commands.
        """
        logger.info("Setting up Edue Helper bot...")
        
        # Load cogs (load rate_limit first as chat depends on it)
        try:
            await self.load_extension('cogs.rate_limit')
            logger.info("Loaded rate_limit cog successfully")
        except Exception as e:
            logger.error(f"Failed to load rate_limit cog: {e}")
        
        try:
            await self.load_extension('cogs.chat')
            logger.info("Loaded chat cog successfully")
        except Exception as e:
            logger.error(f"Failed to load chat cog: {e}")
        
        try:
            await self.load_extension('cogs.qa')
            logger.info("Loaded qa cog successfully")
        except Exception as e:
            logger.error(f"Failed to load qa cog: {e}")
        
        # Sync application commands (slash commands)
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application commands")
        except Exception as e:
            logger.error(f"Failed to sync application commands: {e}")
    
    async def on_ready(self):
        """
        Called when the bot has successfully connected to Discord.
        """
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for educational questions | !help"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """
        Global error handler for text commands.
        """
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided. Please check your input.")
            return
        
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        # Log unexpected errors
        logger.error(f"Unexpected error in command {ctx.command}: {error}")
        await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def main():
    """
    Main function to run the bot.
    """
    # Check for required environment variables
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        return
    
    # Create and run bot
    bot = EdueBot()
    
    try:
        await bot.start(bot_token)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
        await bot.close()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
