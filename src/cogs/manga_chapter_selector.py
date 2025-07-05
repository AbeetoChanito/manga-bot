import discord
import utils.scraper as scraper  # type: ignore
import utils.bot_util as bot_util  # type: ignore
from utils.backend import Backend  # type: ignore
from .manga_reader import MangaReaderView  # type: ignore


class MangaChapterSelectorConfirmButton(discord.ui.Button["MangaChapterSelectorView"]):
    def __init__(self):
        super().__init__(label="Confirm", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.defer()
        try:
            assert type(self.view.selector.values[0]) is str
            index = int(self.view.selector.values[0])
        except TypeError:
            index = self.view.bookmark_default
        assert interaction.user is not None
        user_id = interaction.user.id
        new_view = await MangaReaderView.new_manga_reader_view(
            self.view.manga_link, index, user_id, self.view.chapters
        )
        embed = await new_view.generate_embed()
        await interaction.edit_original_response(
            embed=embed, file=new_view.file, view=new_view
        )


class MangaChapterSelector(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select a chapter", row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class MangaChapterSelectorView(discord.ui.View):
    @staticmethod
    async def new_manga_chapter_selector_view(
        manga_link: str, user_id: int
    ) -> "MangaChapterSelectorView":
        manga_chapters = await scraper.get_manga_chapters(manga_link)
        view = MangaChapterSelectorView(manga_chapters, manga_link)
        await view.handle_bookmark_jumper(user_id)
        return view

    def __init__(self, chapters: list[scraper.Chapter], manga_link: str):
        super().__init__(timeout=120)
        self.chapters = chapters
        self.manga_link = manga_link
        self.current_chunk = 0

        self.chunks = [
            [(i + j, chapters[i + j]) for j in range(min(25, len(chapters) - i))]
            for i in range(0, len(chapters), 25)
        ]

        self.selector = MangaChapterSelector()
        self.initialize_selector()
        self.add_item(self.selector)

        self.confirm = MangaChapterSelectorConfirmButton()
        self.add_item(self.confirm)

    def initialize_selector(self):
        selector_options = [
            discord.SelectOption(label=chapter.name, value=str(i))
            for i, chapter in self.chunks[self.current_chunk]
        ]
        self.selector.options = selector_options

    async def send_updated_selector(self, interaction: discord.Interaction, chunk: int):
        self.current_chunk = chunk
        self.initialize_selector()
        await interaction.response.edit_message(view=self)

    async def handle_bookmark_jumper(self, user_id: int):
        backend = await Backend.get_instance()
        self.bookmark_default = await backend.find_bookmark(user_id, self.manga_link)
        if self.bookmark_default is None:
            return

        self.current_chunk = self.bookmark_default // 25
        self.initialize_selector()
        self.selector.options[
            self.bookmark_default - self.current_chunk * 25
        ].default = True

    @discord.ui.button(style=discord.ButtonStyle.gray, label="⬅️", row=0)
    async def cycle_left(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.send_updated_selector(
            interaction, (self.current_chunk - 1) % len(self.chunks)
        )

    @discord.ui.button(style=discord.ButtonStyle.gray, label="➡️", row=0)
    async def cycle_right(
        self, button: discord.Button, interaction: discord.Interaction
    ):
        await self.send_updated_selector(
            interaction, (self.current_chunk + 1) % len(self.chunks)
        )
