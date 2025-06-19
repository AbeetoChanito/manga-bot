import discord
from os import getenv
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Bot is online: ({bot.user})")

bot.load_extension("cogs.pingpong")
bot.run(BOT_TOKEN)