import httpx
import asyncio
import json

async def test_local():
    base = "http://localhost:8000"
    print(f"Testing {base}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test Anime Home
        try:
            url = f"{base}/api/anime/home"
            print(f"\nRequesting {url}...")
            r = await client.get(url)
            print(f"Anime Home: Status {r.status_code}")
            try:
                data = r.json()
                print("Anime Home: Received JSON")
                # print(json.dumps(data, indent=2)[:500] + "...")
            except:
                print(f"Anime Home: Non-JSON response - {r.text[:500]}")
        except Exception as e:
            print(f"Anime Home: ERROR - {e}")

        # Test Manga Search
        try:
            url = f"{base}/api/manga/search?query=naruto"
            print(f"\nRequesting {url}...")
            r = await client.get(url)
            print(f"Manga Search: Status {r.status_code}")
            try:
                data = r.json()
                results = data.get('results', [])
                print(f"Manga Search: SUCCESS - Found {len(results)} items")
                if results:
                     print(f"First result: {results[0]['title']}")
            except:
                print(f"Manga Search: Non-JSON response - {r.text[:500]}")
        except Exception as e:
            print(f"Manga Search: ERROR - {e}")

if __name__ == "__main__":
    asyncio.run(test_local())
