import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_cover():
    url = "https://www.royalroad.com/fiction/21220/mother-of-learning"
    print(f"Testing cover scrape for: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
            res = await client.get(url)
            print(f"Status: {res.status_code}")
            soup = BeautifulSoup(res.text, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                print(f"Found OG: {og['content']}")
            
            img = (soup.select_one(".book-img img") or
                   soup.select_one(".novel-cover img") or
                   soup.select_one(".cover img") or
                   soup.select_one("img.lazy[data-src]"))
            if img:
                print(f"Found IMG tag: {img.get('data-src') or img.get('src')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cover())
