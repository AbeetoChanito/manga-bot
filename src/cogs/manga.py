import discord
import utils.bot_util as bot_util  # type: ignore
from utils.backend import Backend  # type: ignore
from .manga_selector import MangaSelectorView  # type: ignore


class Manga(discord.ext.commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.command(name="read", description="Search and read for manga.")
    async def read(
        self,
        ctx: discord.ApplicationContext,
        to_search=discord.Option(str, description="The manga you want to search for."),
    ):
        await ctx.defer()
        new_view = await MangaSelectorView.new_manga_selector_view(to_search)
        embed = await new_view.selector.generate_embed()
        await ctx.respond(embed=embed, view=new_view, file=new_view.selector.file)


def setup(bot: discord.Bot):
    bot.add_cog(Manga(bot))
