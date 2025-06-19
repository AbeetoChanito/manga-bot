import discord
from discord.ext import commands
import utils.scraper as scraper # type: ignore

class PaginatedView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=120)
        self.pages = pages
        self.index = 0
    
    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.index = (self.index - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.index = (self.index + 1) % len(self.pages)
        await self.update(interaction)


class Manga(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.command(name="read", description="Search and read for manga.")
    async def read(
        self, 
        ctx: discord.ApplicationContext, 
        to_search = discord.Option(str, description="The manga you want to search for."),
    ):
        search_results = await scraper.search_manga_links(to_search)
        pages: list[discord.Embed] = []

        for i, (link, name, cover_link) in enumerate(search_results):
            embed = discord.Embed(title=f"Search Results for *{to_search}*: page #{i + 1}", color=discord.Colour.dark_grey())
            embed.add_field(value=f"[{name}]({scraper.MANGAPARK_BASE_URL}{link})", name="", inline=False)
            embed.set_image(url=f"{scraper.MANGAPARK_BASE_URL}{cover_link}")

            pages.append(embed)

        view = PaginatedView(pages)
        await ctx.respond(embed=pages[0], view=view)

def setup(bot: discord.Bot) -> None:
    bot.add_cog(Manga(bot))