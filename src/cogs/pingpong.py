import discord
from discord.ext import commands

class PingPong(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(name="ping", description="Ping!")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond("Pong!")

def setup(bot: discord.Bot):
    bot.add_cog(PingPong(bot))