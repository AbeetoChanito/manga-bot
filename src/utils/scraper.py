import asyncio
from urllib.parse import urlencode
from bs4.element import Tag
from bs4 import BeautifulSoup
from datetime import timedelta
from aiohttp_client_cache import CachedSession, SQLiteBackend

MANGAPARK_BASE_URL = "https://mangapark.com"


def parse_chapter_links(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    soup = soup.find(lambda x: x.get("data-name", None) == "chapter-list")  # type: ignore

    return [(tag["href"], tag.get_text()) for tag in soup.find_all(lambda x: x.name == "a")]  # type: ignore


def parse_page_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    return [tag.find(lambda x: x.name == "img")["src"] for tag in soup.find_all(lambda x: x.get("data-name", None) == "image-item")]  # type: ignore


def parse_cover_images(html: str) -> list[tuple[str, str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    return [(tag.parent["href"], tag["title"], tag["src"]) for tag in soup.find_all(lambda x: x.name == "img" and "thumb" in x["src"])]  # type: ignore


def get_search_url(search_query: str) -> str:
    search = urlencode({"word": search_query})
    return f"{MANGAPARK_BASE_URL}/search?{search}"


async def get_html_raw(url: str) -> str:
    # NOTE: the cookies are crucial for retrieving the image files
    cache = SQLiteBackend(expire_after=timedelta(days=1))
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


async def search_manga_links(input_search: str) -> list[tuple[str, str, str]]:
    search_url = get_search_url(input_search)
    html_data = await get_html_raw(search_url)
    manga_covers = parse_cover_images(html_data)
    return manga_covers


async def get_manga_chapters(manga_link: str) -> list[tuple[str, str]]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{manga_link}")
    manga_links = parse_chapter_links(html_data)

    manga_links = list(reversed(manga_links))

    return manga_links


async def get_manga_chapter_images(chapter_link: str) -> list[str]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{chapter_link}")
    images = parse_page_images(html_data)

    return images


# proof of concept cli to show the scraper works
async def main():
    input_search = input("Enter manga name: ")

    manga_links = await search_manga_links(input_search)

    for i, (link, name, cover) in enumerate(manga_links):
        print(f"{i}: {name} ({link}) (cover: {cover})")

    manga_index = int(input("Enter index: "))

    manga_link = manga_links[manga_index][0]
    print(f"Manga link: {manga_link}")

    manga_chapter_links = await get_manga_chapters(manga_link)

    for i, (link, name) in enumerate(manga_chapter_links):
        print(f"{i}: {name} ({link})")

    chapter_index = int(input("Enter index: "))
    chapter_link = manga_chapter_links[chapter_index][0]
    print(f"Chapter link: {chapter_link}")

    images = await get_manga_chapter_images(chapter_link)
    for i, link in enumerate(images):
        print(f"{i}: {link}")


if __name__ == "__main__":
    asyncio.run(main())
