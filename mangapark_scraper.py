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

def is_image(tag: Tag) -> bool:
    return tag.name == "img" and tag.get("class", None) == ["w-full", "h-full"]

def parse_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    return [tag["src"] for tag in soup.find_all(is_image)] # type: ignore

def get_search_url(search_query: str) -> str:
    search = urlencode({"word": search_query})
    return f"{MANGAPARK_BASE_URL}/search?{search}"

async def get_html_raw(url_path) -> str:
    # NOTE: the cookies are crucial for retrieving the image files
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
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
    }
    COOKIES = {
        "theme": "mdark",
        "tfv": "1750232773570",
        "Hm_lvt_a7025e25c8500c732b8f48cc46e21467": "1750273651,1750275977,1750299608,1750311668",
        "Hm_lpvt_a7025e25c8500c732b8f48cc46e21467": "1750311668",
        "HMACCOUNT": "A6016F638E220909",
        "wd": "553x1087"
    }
    async with aiohttp.ClientSession(headers=HEADERS, cookies=COOKIES) as session:
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

async def get_manga_chapter_images(chapter_link: str) -> list[str]:
    html_data = await get_html_raw(f"{MANGAPARK_BASE_URL}{chapter_link}")
    images = parse_images(html_data)

    return images
    
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

    chapter_index = int(input("Enter index: "))
    chapter_link = manga_chapter_links[chapter_index][0]
    print(f"Chapter link: {chapter_link}")

    images = await get_manga_chapter_images(chapter_link)
    for i, link in enumerate(images):
        print(f"{i}: {link}")

if __name__ == "__main__":
    asyncio.run(main())