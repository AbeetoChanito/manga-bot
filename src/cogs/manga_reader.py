import discord
import utils.scraper as scraper  # type: ignore
import utils.bot_util as bot_util  # type: ignore
from utils.backend import Backend  # type: ignore


class BookmarkJumperButton(discord.ui.Button["MangaReaderView"]):
    def __init__(self, target_chapter: int):
        super().__init__(label="Jump To Bookmark", row=1)
        self.target_chapter = target_chapter

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await self.view.update_chapter(interaction, self.target_chapter)


class MangaReaderView(discord.ui.View):
    @staticmethod
    async def new_manga_reader_view(
        manga_link: str,
        current_chapter: int,
        user_id: int,
        chapters: list[scraper.Chapter] = [],
    ) -> "MangaReaderView":
        view = MangaReaderView(manga_link, current_chapter, chapters)
        await view.handle_bookmark_jumper(user_id)
        await view.get_chapter_data()
        return view

    def __init__(
        self, manga_link: str, current_chapter: int, chapters: list[scraper.Chapter]
    ):
        super().__init__(timeout=1000)
        self.manga_link = manga_link
        self.chapters = chapters
        self.current_chapter = current_chapter
        self.name: str = ""
        self.pages: list[str] = []
        self.current_page = 0
        self.button: BookmarkJumperButton | None = None

    async def handle_bookmark_jumper(self, user_id: int):
        chapter: int | None = await bot_util.find_bookmark(self.manga_link, user_id)
        if chapter is None:
            return
        if self.button is None:
            self.button = BookmarkJumperButton(chapter)
            self.add_item(self.button)
        else:
            self.button.target_chapter = chapter

    async def get_chapter_data(self):
        if len(self.chapters) == 0:
            self.chapters = await scraper.get_manga_chapters(self.manga_link)
        chapter = self.chapters[self.current_chapter]
        self.name = chapter.name
        self.pages = await scraper.get_manga_chapter_images(chapter.link)
        self.current_page = 0

    async def generate_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.name, color=discord.Colour.dark_grey())
        self.file = await bot_util.url_to_image_file(self.pages[self.current_page])
        embed.set_image(url=f"attachment://{self.file.filename}")
        embed.set_footer(text=f"Page #{self.current_page + 1}")

        return embed

    async def update_page(self, interaction: discord.Interaction, page_number: int):
        await interaction.response.defer()
        self.current_page = page_number
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)

    async def update_chapter(
        self, interaction: discord.Interaction, chapter_number: int
    ):
        await interaction.response.defer()
        self.current_chapter = chapter_number
        await self.get_chapter_data()
        embed = await self.generate_embed()
        await interaction.edit_original_response(embed=embed, file=self.file, view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.update_page(interaction, (self.current_page - 1) % len(self.pages))

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.update_page(interaction, (self.current_page + 1) % len(self.pages))

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Previous Chapter", row=0)
    async def cycle_prev_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.update_chapter(
            interaction, (self.current_chapter - 1) % len(self.chapters)
        )

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Next Chapter", row=0)
    async def cycle_next_chapter(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.update_chapter(
            interaction, (self.current_chapter + 1) % len(self.chapters)
        )

    @discord.ui.button(style=discord.ButtonStyle.gray, label="Bookmark", row=1)
    async def bookmark(self, button: discord.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        backend = await Backend.get_instance()
        assert interaction.user is not None
        user_id = interaction.user.id
        await backend.add_new_bookmark(user_id, self.manga_link, self.current_chapter)

        await self.handle_bookmark_jumper(user_id)
