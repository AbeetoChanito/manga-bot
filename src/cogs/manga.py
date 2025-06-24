import discord
from discord.ext import commands
import utils.scraper as scraper  # type: ignore
from datetime import timedelta
from aiohttp_client_cache import CachedSession, MongoDBBackend
from io import BytesIO


async def url_to_image_file(url: str) -> discord.File:
    cache = MongoDBBackend(expire_after=timedelta(days=1))
    async with CachedSession(cache=cache) as session:
        async with session.get(url) as response:
            assert response.status == 200, "Response status not 200."

            data = await response.read()
            buffer = BytesIO(data)
            buffer.seek(0)

            file_ext = url.split(".")[-1].split("?")[0]
            assert file_ext in [
                "png",
                "jpg",
                "jpeg",
                "gif",
            ], "Invalid image file extension."

            filename = f"image.{file_ext}"

            file = discord.File(buffer, filename=filename)

            return file


class MangaReaderView(discord.ui.View):
    @staticmethod
    async def new_manga_reader_view(
        chapters: list[scraper.Chapter], current_chapter: int
    ) -> "MangaReaderView":
        view = MangaReaderView(chapters, current_chapter)
        await view.get_chapter_data()
        return view

    def __init__(self, chapters: list[scraper.Chapter], current_chapter: int):
        super().__init__(timeout=1000)
        self.chapters = chapters
        self.current_chapter = current_chapter
        self.name: str = ""
        self.pages: list[str] = []
        self.current_page = 0
        self.file: discord.File = None  # type: ignore

    async def get_chapter_data(self):
        chapter = self.chapters[self.current_chapter]
        self.name = chapter.name
        self.pages = await scraper.get_manga_chapter_images(chapter.link)
        self.current_page = 0

    async def generate_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.name, color=discord.Colour.dark_grey())
        self.file = await url_to_image_file(self.pages[self.current_page])
        embed.set_image(url=f"attachment://{self.file.filename}")
        embed.set_footer(text=f"Page #{self.current_page + 1}")

        return embed

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_page = (self.current_page - 1) % len(self.pages)
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_page = (self.current_page + 1) % len(self.pages)
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Next Chapter")
    async def cycle_next_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_chapter = (self.current_chapter + 1) % len(self.chapters)
        await self.get_chapter_data()
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Previous Chapter")
    async def cycle_prev_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_chapter = (self.current_chapter - 1) % len(self.chapters)
        await self.get_chapter_data()
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)


class MangaChapterSelector(discord.ui.Select):
    def _init__(self):
        super().__init__(row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        index = int(self.values[0])  # type: ignore
        new_view = await MangaReaderView.new_manga_reader_view(self.view.chapters, index)  # type: ignore
        embed = await new_view.generate_embed()
        await interaction.edit_original_response(
            embed=embed, file=new_view.file, view=new_view
        )


class MangaChapterSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_chapter_selector_view(
        manga_link: str,
    ) -> "MangaChapterSelectorView":
        return MangaChapterSelectorView(
            await scraper.get_manga_chapters(manga_link), manga_link
        )

    def __init__(self, chapters: list[scraper.Chapter], manga_link: str):
        super().__init__(timeout=120)
        self.chapters = chapters
        self.manga_link = manga_link
        self.current_chunk = 0

        self.chunks = [
            [(i + j, chapters[i + j]) for j in range(min(25, len(chapters) - i))]
            for i in range(0, len(chapters), 25)
        ]

        self.selector: discord.ui.Select = MangaChapterSelector()
        self.initialize_selector()
        self.add_item(self.selector)

    def initialize_selector(self):
        selector_options = [
            discord.SelectOption(label=chapter.name, value=str(i))
            for i, chapter in self.chunks[self.current_chunk]
        ]
        self.selector.options = selector_options

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        self.current_chunk = (self.current_chunk - 1) % len(self.chunks)
        self.initialize_selector()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        self.current_chunk = (self.current_chunk + 1) % len(self.chunks)
        self.initialize_selector()
        await interaction.response.edit_message(view=self)


class MangaSelector(discord.ui.Select):
    @staticmethod
    async def new_manga_selector(to_search: str) -> "MangaSelector":
        return MangaSelector(
            (await scraper.search_manga_links(to_search))[:10], to_search
        )

    def __init__(self, search_results: list[scraper.Manga], to_search: str):
        self.to_search = to_search
        self.search_results = search_results
        self.selected_index: int = 0

        options = [
            discord.SelectOption(label=manga.name, value=str(i), default=i == 0)
            for i, manga in enumerate(search_results)
        ]

        self.file: discord.File = None  # type: ignore

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
        self.file = await url_to_image_file(
            f"{scraper.MANGAPARK_BASE_URL}{manga.cover}"
        )
        embed.set_image(url=f"attachment://{self.file.filename}")
        return embed

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected_index = int(self.values[0])  # type: ignore
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
        self.selector: MangaSelector = None  # type: ignore

    async def set_search(self, to_search: str):
        self.selector = await MangaSelector.new_manga_selector(to_search)
        self.add_item(self.selector)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Confirm", row=1)
    async def callback(self, button: discord.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        link = self.selector.search_results[self.selector.selected_index].link
        new_view = await MangaChapterSelectorView.new_manga_chapter_selector_view(link)
        await interaction.edit_original_response(
            embed=None, view=new_view, attachments=[]
        )


class Manga(commands.Cog):
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
