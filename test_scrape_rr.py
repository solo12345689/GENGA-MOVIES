import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_scrape():
    url = "https://www.royalroad.com/fiction/21220/mother-of-learning/chapter/301778/1-good-morning-brother"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # RoyalRoad content is usually in .chapter-content
                content = soup.find("div", class_="chapter-content")
                if content:
                    print("Successfully found chapter content!")
                    print(f"Content length: {len(str(content))}")
                else:
                    print("Could not find .chapter-content")
            else:
                print(f"Failed to fetch: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrape())
