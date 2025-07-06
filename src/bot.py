import discord
from os import getenv
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")

assert BOT_TOKEN is not None, "Bot token not found in environment variables."

bot = discord.Bot()


@bot.event
async def on_ready():
    print(f"Bot is online: {bot.user}")
    await bot.sync_commands()


bot.load_extension("cogs.pingpong")
bot.load_extension("cogs.manga")
bot.load_extension("cogs.bookmarks")
bot.run(BOT_TOKEN)
