from aiohttp_client_cache import CachedSession, MongoDBBackend
from datetime import timedelta
from io import BytesIO
import discord
from utils.backend import Backend # type: ignore

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


async def find_bookmark(link: str, user_id: int) -> int | None:
    backend = await Backend.get_instance()
    bookmarks = await backend.get_bookmarks(user_id)
    for bookmark in bookmarks:
        if bookmark["link"] == link:
            return int(bookmark["chapter"])
    return None