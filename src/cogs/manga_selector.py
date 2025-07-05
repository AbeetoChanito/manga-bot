import discord
import utils.scraper as scraper  # type: ignore
import utils.bot_util as bot_util  # type: ignore
from utils.backend import Backend  # type: ignore
from .manga_chapter_selector import MangaChapterSelectorView  # type: ignore


class MangaSelector(discord.ui.Select):
    @staticmethod
    async def new_manga_selector(to_search: str) -> "MangaSelector":
        top_searches = (await scraper.search_manga_links(to_search))[:10]
        return MangaSelector(top_searches, to_search)

    def __init__(self, search_results: list[scraper.Manga], to_search: str):
        self.to_search = to_search
        self.search_results = search_results
        self.selected_index: int = 0

        options = [
            discord.SelectOption(label=manga.name, value=str(i), default=i == 0)
            for i, manga in enumerate(search_results)
        ]

        super().__init__(options=options, row=0)

    async def generate_embed(self) -> discord.Embed:
        manga = self.search_results[self.selected_index]
        embed = discord.Embed(
            title=f"Search Results for *{self.to_search}*",
            color=discord.Colour.dark_grey(),
        )
        embed.add_field(
            name="",
            value=f"[{manga.name}]({scraper.MANGAPARK_BASE_URL}{manga.link})",
            inline=False,
        )
        self.file = await bot_util.url_to_image_file(
            f"{scraper.MANGAPARK_BASE_URL}{manga.cover}"
        )
        embed.set_image(url=f"attachment://{self.file.filename}")
        return embed

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        assert type(self.values[0]) is str
        self.selected_index = int(self.values[0])
        embed = await self.generate_embed()
        for option in self.options:
            if option.default:
                option.default = False
                break
        self.options[self.selected_index].default = True
        await interaction.edit_original_response(
            embed=embed, view=self.view, file=self.file
        )


class MangaSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_selector_view(to_search: str) -> "MangaSelectorView":
        view = MangaSelectorView(to_search)
        await view.set_search(to_search)
        return view

    def __init__(self, to_search: str):
        super().__init__(timeout=120)
        self.to_search = to_search

    async def set_search(self, to_search: str):
        self.selector = await MangaSelector.new_manga_selector(to_search)
        self.add_item(self.selector)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Confirm", row=1)
    async def callback(self, button: discord.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        link = self.selector.search_results[self.selector.selected_index].link
        assert interaction.user is not None
        user_id = interaction.user.id
        new_view = await MangaChapterSelectorView.new_manga_chapter_selector_view(
            link, user_id
        )
        await interaction.edit_original_response(
            embed=None, view=new_view, attachments=[]
        )
