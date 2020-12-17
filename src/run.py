import os

from discord.ext import commands
from loguru import logger

from music import MusicPlayer

logger.info("Starting bot")

bot = commands.Bot(
    command_prefix="!", case_insensitive=True, description="Music bot by Nikitos"
)
bot.add_cog(MusicPlayer(bot))
bot.run(os.environ["DISCORD_BOT_TOKEN"])
