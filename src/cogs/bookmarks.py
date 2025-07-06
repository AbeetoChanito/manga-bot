import discord
import utils.scraper as scraper  # type: ignore
import utils.bot_util as bot_util  # type: ignore
from utils.backend import Backend  # type: ignore
from .manga_selector import MangaSelectorView  # type: ignore


class Bookmarks(discord.ext.commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.command(name="bookmarks", description="Read the manga you've bookmarked.")
    async def bookmarks(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        new_view = await MangaSelectorView.new_manga_selector_view_from_bookmarks(
            ctx.author.id
        )
        if new_view is None:
            await ctx.respond(embed="You have no bookmarks.")
            return
        embed = await new_view.selector.generate_embed()
        await ctx.respond(embed=embed, view=new_view, file=new_view.selector.file)


def setup(bot: discord.Bot):
    bot.add_cog(Bookmarks(bot))
