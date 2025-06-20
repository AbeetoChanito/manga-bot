import discord
from discord.ext import commands
import utils.scraper as scraper # type: ignore

class MangaReaderView(discord.ui.View):
    @staticmethod
    async def new_manga_reader_view(link: str, name: str) -> 'MangaReaderView':
        view = MangaReaderView(await scraper.get_manga_chapter_images(link), name, link)
        return view

    def __init__(self, pages: list[str], name: str, link: str):
        super().__init__()
        self.link = link
        self.name = name
        self.pages = pages

        self.current_page = 0
        
    def generate_page_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"Page #{self.current_page + 1}",
            color=discord.Colour.dark_grey()
        )
        embed.set_image(url=self.pages[self.current_page])
        return embed

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(self, button: discord.Button, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.generate_page_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(self, button: discord.Button, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.generate_page_embed(), view=self)

class MangaChapterSelector(discord.ui.Select):
    def _init__(self):
        super().__init__(row=2)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0]) # type: ignore
        link, name = self.view.options[index] # type: ignore
        view = await MangaReaderView.new_manga_reader_view(link, name)
        await interaction.response.edit_message(view=view, embed=view.generate_page_embed())

class MangaChapterSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_chapter_selector_view(manga_link: str) -> 'MangaChapterSelectorView':
        return MangaChapterSelectorView(await scraper.get_manga_chapters(manga_link), manga_link)

    def __init__(self, options: list[tuple[str, str]], manga_link: str):
        super().__init__()
        self.options = options
        self.manga_link = manga_link
        self.current_chunk = 0

        self.chunks = [[(i + j, options[i + j]) for j in range(min(25, len(options) - i))] for i in range(0, len(options), 25)]

        self.selector: discord.ui.Select = MangaChapterSelector()
        self.initialize_selector()
        self.add_item(self.selector)

    def initialize_selector(self):
        selector_options = [
            discord.SelectOption(label=name, value=str(i))
            for i, (_, name) in self.chunks[self.current_chunk]
        ]
        self.selector.options = selector_options

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(self, button: discord.Button, interaction: discord.Interaction):
        self.current_chunk = (self.current_chunk - 1) % len(self.chunks)
        self.initialize_selector()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(self, button: discord.Button, interaction: discord.Interaction):
        self.current_chunk = (self.current_chunk + 1) % len(self.chunks)
        self.initialize_selector()
        await interaction.response.edit_message(view=self)

class MangaSelectorButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="Confirm")

    async def callback(self, interaction: discord.Interaction):
        link = self.view.selector.search_results[self.view.selector.selected_index][0] # type: ignore
        await interaction.response.edit_message(embed=None, view=await MangaChapterSelectorView.new_manga_chapter_selector_view(link))

class MangaSelector(discord.ui.Select):
    @staticmethod
    async def new_manga_selector(to_search: str) -> 'MangaSelector':
        return MangaSelector((await scraper.search_manga_links(to_search))[:10], to_search)

    def __init__(self, search_results: list[tuple[str, str, str]], to_search: str):
        self.to_search = to_search
        self.search_results = search_results
        self.selected_index: int | None = None

        options = [
            discord.SelectOption(label=name, value=str(i))
            for i, (_, name, _) in enumerate(search_results)
        ]

        super().__init__(options=options)

    def generate_embed(self, index: int) -> discord.Embed:
        link, name, cover = self.search_results[index]
        embed = discord.Embed(
            title=f"Search Results for *{self.to_search}*",
            color=discord.Colour.dark_grey()
        )
        embed.add_field(name="", value=f"[{name}]({scraper.MANGAPARK_BASE_URL}{link})", inline=False)
        embed.set_image(url=f"{scraper.MANGAPARK_BASE_URL}{cover}")
        return embed

    async def callback(self, interaction: discord.Interaction):
        if self.selected_index is None:
            self.view.add_item(MangaSelectorButton()) # type: ignore
        self.selected_index = int(self.values[0]) # type: ignore
        embed = self.generate_embed(self.selected_index)        
        for option in self.options:
            if option.default:
                option.default = False
                break
        self.options[self.selected_index].default = True
        await interaction.response.edit_message(embed=embed, view=self.view)

class MangaSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_selector_view(to_search: str) -> 'MangaSelectorView':
        view = MangaSelectorView(to_search)
        view.selector = await MangaSelector.new_manga_selector(to_search)
        view.add_item(view.selector)
        return view

    def __init__(self, to_search: str):
        super().__init__()
        self.to_search = to_search
        self.selector: MangaSelector | None = None
        self.confirm: MangaSelectorButton | None = None

class Manga(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.command(name="read", description="Search and read for manga.")
    async def read(
        self, 
        ctx: discord.ApplicationContext, 
        to_search = discord.Option(str, description="The manga you want to search for."),
    ):
        await ctx.respond(view=await MangaSelectorView.new_manga_selector_view(to_search))

def setup(bot: discord.Bot) -> None:
    bot.add_cog(Manga(bot))