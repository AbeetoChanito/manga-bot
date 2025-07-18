import asyncio
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from datetime import timedelta
from aiohttp_client_cache import CachedSession, MongoDBBackend
from dataclasses import dataclass
from typing import Mapping

MANGAPARK_BASE_URL = "https://mangapark.com"


@dataclass
class Chapter:
    link: str
    name: str


@dataclass
class Manga:
    link: str
    name: str
    cover: str


def parse_chapter_links(html: str) -> list[Chapter]:
    soup = BeautifulSoup(html, "html.parser")
    chapter_list = soup.find(lambda x: x.get("data-name", None) == "chapter-list")
    assert chapter_list is not None
    link_items = chapter_list.find_all(lambda x: x.name == "a")  # type: ignore
    assert link_items is not None

    return [Chapter(tag["href"], tag.get_text()) for tag in link_items]


def parse_page_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    image_items = soup.find_all(lambda x: x.get("data-name", None) == "image-item")
    assert image_items is not None

    return [tag.find(lambda x: x.name == "img")["src"] for tag in image_items]  # type: ignore


def parse_cover_images(html: str) -> list[Manga]:
    soup = BeautifulSoup(html, "html.parser")
    cover_items = soup.find_all(lambda x: x.name == "img" and "thumb" in x["src"])
    assert cover_items is not None

    return [Manga(tag.parent.get("href", None), tag["title"], tag["src"]) for tag in cover_items]  # type: ignore


def parse_manga_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    description_tag = soup.find(lambda x: x.name == "div" and x.get("class", None) == ["limit-html-p"])
    assert description_tag is not None

    return description_tag.get_text()


async def get_html_raw(url: str) -> str:
    # NOTE: the cookies are crucial for retrieving the image files
    cache = MongoDBBackend(expire_after=timedelta(days=1))
    HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "dnt": "1",
        "priority": "u=0, i",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    }
    COOKIES = {
        "theme": "mdark",
        "tfv": "1750232773570",
        "Hm_lvt_a7025e25c8500c732b8f48cc46e21467": "1750273651,1750275977,1750299608,1750311668",
        "Hm_lpvt_a7025e25c8500c732b8f48cc46e21467": "1750311668",
        "HMACCOUNT": "A6016F638E220909",
        "wd": "553x1087",
    }
    async with CachedSession(headers=HEADERS, cookies=COOKIES, cache=cache) as session:
        async with session.get(url) as response:
            assert response.status == 200, "Response status not 200."

            output = await response.text()
            return output


async def search_manga_links(input_search: str) -> list[Manga]:
    search = urlencode({"word": input_search})
    search_url = f"{MANGAPARK_BASE_URL}/search?{search}"
    html_data = await get_html_raw(search_url)
    manga_covers = parse_cover_images(html_data)
    return manga_covers


async def get_manga_chapters(manga_link: str) -> list[Chapter]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{manga_link}")
    chapter_links = parse_chapter_links(html_data)
    chapter_links = list(reversed(chapter_links))
    return chapter_links


async def get_manga_chapter_images(chapter_link: str) -> list[str]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{chapter_link}")
    images = parse_page_images(html_data)

    return images


async def get_manga_description(chapter_link: str) -> str:
    # NOTE: we might use this html data later in get_manga_chapters,
    # but all of the requests are cached 
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{chapter_link}")
    description = parse_manga_description(html_data)

    return description


async def convert_manga_links_to_manga_objects(
    manga_links: list[Mapping[str, str]],
) -> list[Manga]:
    manga_objects = []
    for bookmark in manga_links:
        link = bookmark["link"]
        search_url = f"{MANGAPARK_BASE_URL}{link}"
        html_data = await get_html_raw(search_url)
        covers = parse_cover_images(html_data)
        manga_objects.append(Manga(link, covers[0].name, covers[0].cover))
    return manga_objects


# proof of concept cli to show the scraper works
async def main():
    input_search = input("Enter manga name: ")

    manga_links = await search_manga_links(input_search)

    for i, manga in enumerate(manga_links):
        print(f"{i}: {manga.name} ({manga.link}) (cover: {manga.cover})")

    manga_index = int(input("Enter index: "))

    manga_link = manga_links[manga_index].link
    print(f"Manga link: {manga_link}")

    manga_chapter_links = await get_manga_chapters(manga_link)

    for i, chapter in enumerate(manga_chapter_links):
        print(f"{i}: {chapter.name} ({chapter.link})")

    chapter_index = int(input("Enter index: "))
    chapter_link = manga_chapter_links[chapter_index].link
    print(f"Chapter link: {chapter_link}")

    images = await get_manga_chapter_images(chapter_link)
    for i, link in enumerate(images):
        print(f"{i}: {link}")

if __name__ == "__main__":
    asyncio.run(main())
