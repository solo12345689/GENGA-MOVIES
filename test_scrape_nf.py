import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_scrape():
    url = "https://novelfire.net/book/mother-of-learning/chapter-112"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                content = soup.find("div", id="content") or soup.find("div", id="chr-content")
                if content:
                    print("Successfully found chapter content!")
                    print(f"Content length: {len(str(content))}")
                    # Check first few words
                    text = content.get_text(strip=True)
                    print(f"Start of text: {text[:100]}...")
                else:
                    print("Could not find content selector")
            else:
                print(f"Failed to fetch: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrape())
