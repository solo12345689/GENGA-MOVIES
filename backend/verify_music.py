import httpx
import asyncio
import json

async def test_music_api():
    base_url = "http://127.0.0.1:8000/api/music"
    
    print("\n--- Testing Music Home ---")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{base_url}/home?lang=English")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Home success: {len(data.get('groups', []))} groups found")
                for group in data.get('groups', []):
                    print(f" - {group['title']}: {len(group['items'])} items")
            else:
                print(f"Home failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Home error: {e}")

    print("\n--- Testing Music Search ---")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{base_url}/search?query=Tyler Herro")
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                print(f"Search success: {len(results)} results found")
                if results:
                    print(f" - First result: {results[0]['title']} by {results[0]['year']}")
            else:
                print(f"Search failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Search error: {e}")

    print("\n--- Testing Music Info ---")
    try:
        # Using a known seokey from the documentation/example
        seokey = "tyler-herro"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{base_url}/info?seokey={seokey}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Info success: {data['title']}")
                print(f" - Artists: {data['artists']}")
                print(f" - Stream URL: {data['stream_url'][:50]}...")
            else:
                print(f"Info failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Info error: {e}")

if __name__ == "__main__":
    asyncio.run(test_music_api())
