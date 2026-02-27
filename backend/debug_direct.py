import httpx
import asyncio

async def test():
    url = "https://aniwatch-api-dotd.onrender.com/api/v2/hianime/search?q=naruto"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            print(f"Testing direct call to {url}...")
            res = await client.get(url, timeout=30.0)
            print(f"Status: {res.status_code}")
            print(f"Headers: {dict(res.headers)}")
            print(f"Response: {res.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
