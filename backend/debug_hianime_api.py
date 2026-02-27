
import httpx
import asyncio
import json
import sys

async def check():
    url = "https://aniwatch-api-dotd.onrender.com/api/v2/hianime/anime/one-piece-100/episodes"
    print(f"Checking URL: {url}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(url)
            print(f"Status Code: {res.status_code}")
            print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check())
