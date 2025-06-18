import aiohttp
import asyncio
from urllib.parse import urlencode
from bs4.element import Tag
from bs4 import BeautifulSoup

MANGAPARK_BASE_URL = "https://mangapark.com"

def is_correct_manga_tag(tag: Tag) -> bool: 
    return tag.name == "a" and "title" in tag["href"] and tag.get_text() != ""

def parse_manga_links(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    return [(tag["href"], tag.get_text()) for tag in soup.find_all(is_correct_manga_tag)] # type: ignore

def get_search_url(search_query: str) -> str:
    search = urlencode({"word": search_query})
    return f"{MANGAPARK_BASE_URL}/search?{search}"

async def get_html_raw(url_path) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url_path) as response:
            assert response.status == 200, "Response status not 200."

            output = await response.text()
            return output
        

async def search_manga_links(input_search: str) -> list[tuple[str, str]]:
    search_url = get_search_url(input_search)
    html_data = await get_html_raw(search_url)
    manga_links = parse_manga_links(html_data)
    manga_links = [manga_link for i, manga_link in enumerate(manga_links) if i % 2 == 0]
    return manga_links

async def get_manga_chapters(manga_link: str) -> list[tuple[str, str]]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{manga_link}")
    manga_links = parse_manga_links(html_data)

    manga_links = list(reversed(manga_links))
    DISCARD_PHRASES = ["Newly Added", "Most Likes", "Start Reading"]
    manga_links = list(filter(lambda f: all([p not in f[1] for p in DISCARD_PHRASES]) and f[0] != manga_link, manga_links))
    
    return manga_links

async def main():
    input_search = input("Enter manga name: ")

    manga_links = await search_manga_links(input_search)

    for i, (link, name) in enumerate(manga_links):
        print(f"{i}: {name} ({link})")

    manga_index = int(input("Enter index: "))

    manga_link = manga_links[manga_index][0]
    print(f"Manga link: {manga_link}")

    manga_chapter_links = await get_manga_chapters(manga_link)

    for i, (link, name) in enumerate(manga_chapter_links):
        print(f"{i}: {name} ({link})")

if __name__ == "__main__":
    asyncio.run(main())