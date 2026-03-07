import httpx
from bs4 import BeautifulSoup
import asyncio

async def _get_cover_for_url(url: str):
    def do_scrape():
        try:
            print(f"Scraping: {url}")
            res = httpx.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10,
                follow_redirects=True,
                # verify=False # Let's see if this is needed
            )
            print(f"Done: {url} - {res.status_code}")
            soup = BeautifulSoup(res.text, "html.parser")
            og = soup.find("meta", property="og:image")
            if og:
                return og.get("content")
            return None
        except Exception as e:
            print(f"Error {url}: {e}")
            return None
    return await asyncio.to_thread(do_scrape)

async def test_parallel():
    urls = [
        "https://www.royalroad.com/fiction/21220/mother-of-learning",
        "https://novelfire.net/book/mother-of-learning",
        "https://www.royalroad.com/fiction/38085/just-deserts-revised-edition-mha-oc",
        "https://www.royalroad.com/fiction/14167/metaworld-chronicles"
    ]
    tasks = [_get_cover_for_url(u) for u in urls]
    results = await asyncio.gather(*tasks)
    for u, r in zip(urls, results):
        print(f"URL: {u} -> Cover: {r}")

if __name__ == "__main__":
    asyncio.run(test_parallel())
