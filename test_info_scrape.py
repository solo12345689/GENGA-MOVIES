import httpx
from bs4 import BeautifulSoup
import asyncio
import json

async def test_info_scrape():
    url = "https://novelfire.net/book/mother-of-learning"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15) as client:
        try:
            resp = await client.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                title_tag = soup.find("h1", class_="novel-title")
                title = title_tag.text.strip() if title_tag else "Unknown"
                print(f"Title: {title}")
                
                # Fetch chapters from subpage
                ch_url = url.rstrip("/") + "/chapters"
                print(f"Fetching chapters from: {ch_url}")
                ch_resp = await client.get(ch_url)
                if ch_resp.status_code == 200:
                    ch_soup = BeautifulSoup(ch_resp.text, "html.parser")
                    chapters = []
                    for a in ch_soup.select("article#chapter-list-page a[href]"):
                        strong_tag = a.find("strong")
                        chapters.append({
                            "id": a["href"],
                            "title": strong_tag.text.strip() if strong_tag else a.text.strip(),
                            "url": "https://novelfire.net" + a["href"] if a["href"].startswith("/") else a["href"]
                        })
                    print(f"Chapters found: {len(chapters)}")
                    if chapters:
                        print(f"First chapter: {chapters[0]}")
                else:
                    print(f"Failed to fetch chapters: {ch_resp.status_code}")
            else:
                print(f"Failed to fetch book: {resp.status_code}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_info_scrape())
