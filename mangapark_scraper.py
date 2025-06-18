import aiohttp
import asyncio
from urllib.parse import urlencode
from bs4.element import Tag
from bs4 import BeautifulSoup

MANGAPARK_BASE_URL = "https://mangapark.io"

def is_correct_manga_tag(tag: Tag) -> bool: 
    return tag.name == "a" and "title" in tag["href"]

def parse_manga_links(html: str) -> list[tuple[str, str]]:
    soup_instance = BeautifulSoup(html, "html.parser")

    return [(tag["href"], tag.contents) for tag in soup_instance.find_all(is_correct_manga_tag)]

def get_search_url(search_query: str) -> str:
    search = urlencode({"word": search_query})
    return f"{MANGAPARK_BASE_URL}/search?{search}"

async def get_html_raw(url_path) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url_path) as response:
            assert response.status == 200, "Response status not 200."

            output = await response.text()
            return output

async def main():
    input_search = "kaguya sama: love is war"

    # get the possible mangas from the search
    search_url = get_search_url(input_search)
    html_data = await get_html_raw(search_url)
    manga_links = parse_manga_links(html_data)

    # for the purpose of this we discard everything else
    # but the first manga link
    top_manga_link = manga_links[0][0]
    print(f"Top manga link: {top_manga_link}")

    # finally, parse out the links from the manga page itself
    # to get chapters
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{top_manga_link}")
    manga_links = parse_manga_links(html_data)

    # parse out the bottom two links
    manga_links = manga_links[:-2]
    f = lambda x: len(x[1]) == 1 and "Start Reading" not in x[1][0]
    manga_links = list(filter(f, manga_links))
    manga_links = list(reversed(manga_links))

    print("\n".join(map(str, manga_links)))

if __name__ == "__main__":
    asyncio.run(main())