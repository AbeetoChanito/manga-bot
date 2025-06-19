import discord
from os import getenv
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Bot is online: ({bot.user})")
    await bot.sync_commands()

bot.load_extension("cogs.pingpong")
bot.load_extension("cogs.manga")
bot.run(BOT_TOKEN)