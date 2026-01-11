import httpx
import asyncio

async def test():
    base = "https://aniwatch-api-3e2f.onrender.com/api/v2/hianime"
    async with httpx.AsyncClient(follow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'}) as client:
        for path in ["/home", "/search?q=naruto"]:
            url = base + path
            try:
                print(f"Testing {url}...")
                res = await client.get(url, timeout=10.0)
                print(f"Status: {res.status_code}")
                # Print to file to bypass the "no output" issue
                with open("api_test_results.txt", "a") as f:
                    f.write(f"URL: {url}\nStatus: {res.status_code}\nBody: {res.text[:200]}\n\n")
            except Exception as e:
                with open("api_test_results.txt", "a") as f:
                    f.write(f"URL: {url}\nError: {e}\n\n")

if __name__ == "__main__":
    asyncio.run(test())
