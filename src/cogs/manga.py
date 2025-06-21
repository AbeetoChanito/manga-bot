import discord
from discord.ext import commands
import utils.scraper as scraper  # type: ignore
import aiohttp
from io import BytesIO


async def url_to_image_file(url: str) -> discord.File:
    async with aiohttp.ClientSession() as session:
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
        chapters: list[tuple[str, str]], current_chapter: int
    ) -> "MangaReaderView":
        view = MangaReaderView(chapters, current_chapter)
        await view.get_chapter_data()
        return view

    def __init__(self, chapters: list[tuple[str, str]], current_chapter: int):
        super().__init__(timeout=1000)
        self.chapters = chapters
        self.current_chapter = current_chapter
        self.name: str = ""
        self.pages: list[str] = []
        self.current_page = 0
        self.file: discord.File | None = None

    async def get_chapter_data(self):
        link, self.name = self.chapters[self.current_chapter]
        self.pages = await scraper.get_manga_chapter_images(link)
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
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)  # type: ignore

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_page = (self.current_page + 1) % len(self.pages)
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)  # type: ignore

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Next Chapter")
    async def cycle_next_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_chapter = (self.current_chapter + 1) % len(self.chapters)
        await self.get_chapter_data()
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)  # type: ignore

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Previous Chapter")
    async def cycle_prev_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await interaction.response.defer()
        self.current_chapter = (self.current_chapter - 1) % len(self.chapters)
        await self.get_chapter_data()
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)  # type: ignore


class MangaChapterSelector(discord.ui.Select):
    def _init__(self):
        super().__init__(row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        index = int(self.values[0])  # type: ignore
        view = await MangaReaderView.new_manga_reader_view(self.view.options, index)  # type: ignore
        embed = await view.generate_embed()
        await interaction.edit_original_response(embed=embed, file=view.file, view=view)  # type: ignore


class MangaChapterSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_chapter_selector_view(
        manga_link: str,
    ) -> "MangaChapterSelectorView":
        return MangaChapterSelectorView(
            await scraper.get_manga_chapters(manga_link), manga_link
        )

    def __init__(self, options: list[tuple[str, str]], manga_link: str):
        super().__init__(timeout=120)
        self.options = options
        self.manga_link = manga_link
        self.current_chunk = 0

        self.chunks = [
            [(i + j, options[i + j]) for j in range(min(25, len(options) - i))]
            for i in range(0, len(options), 25)
        ]

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


class MangaSelectorButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="Confirm")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        link = self.view.selector.search_results[self.view.selector.selected_index][0]  # type: ignore
        new_view = await MangaChapterSelectorView.new_manga_chapter_selector_view(link)
        await interaction.edit_original_response(
            embed=None, view=new_view, attachments=[]
        )


class MangaSelector(discord.ui.Select):
    @staticmethod
    async def new_manga_selector(to_search: str) -> "MangaSelector":
        return MangaSelector(
            (await scraper.search_manga_links(to_search))[:10], to_search
        )

    def __init__(self, search_results: list[tuple[str, str, str]], to_search: str):
        self.to_search = to_search
        self.search_results = search_results
        self.selected_index: int | None = None

        options = [
            discord.SelectOption(label=name, value=str(i))
            for i, (_, name, _) in enumerate(search_results)
        ]

        self.file: discord.File | None = None

        super().__init__(options=options)

    async def generate_embed(self, index: int) -> discord.Embed:
        link, name, cover = self.search_results[index]
        embed = discord.Embed(
            title=f"Search Results for *{self.to_search}*",
            color=discord.Colour.dark_grey(),
        )
        embed.add_field(
            name="", value=f"[{name}]({scraper.MANGAPARK_BASE_URL}{link})", inline=False
        )
        self.file = await url_to_image_file(f"{scraper.MANGAPARK_BASE_URL}{cover}")
        embed.set_image(url=f"attachment://{self.file.filename}")
        return embed

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.selected_index is None:
            self.view.add_item(MangaSelectorButton())  # type: ignore
        self.selected_index = int(self.values[0])  # type: ignore
        embed = await self.generate_embed(self.selected_index)
        for option in self.options:
            if option.default:
                option.default = False
                break
        self.options[self.selected_index].default = True
        await interaction.edit_original_response(embed=embed, view=self.view, file=self.file)  # type: ignore


class MangaSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_selector_view(to_search: str) -> "MangaSelectorView":
        view = MangaSelectorView(to_search)
        view.selector = await MangaSelector.new_manga_selector(to_search)
        view.add_item(view.selector)
        return view

    def __init__(self, to_search: str):
        super().__init__(timeout=120)
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
        to_search=discord.Option(str, description="The manga you want to search for."),
    ):
        await ctx.defer()
        new_view = await MangaSelectorView.new_manga_selector_view(to_search)
        await ctx.respond(view=new_view)


def setup(bot: discord.Bot):
    bot.add_cog(Manga(bot))
