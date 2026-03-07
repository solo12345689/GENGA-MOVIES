import httpx
import asyncio
import json

async def verify_fixes():
    API_BASE = "http://localhost:8000" # Based on the user's screenshots/prev logs
    
    print("--- 1. Testing Search Relevance and Posters ---")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{API_BASE}/api/novel/search?query=Solo%20Leveling")
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                print(f"Found {len(results)} results.")
                for i, r in enumerate(results[:5]):
                    print(f"[{i}] {r['title']} - Poster: {'Present' if r.get('poster_url') else 'MISSING'}")
                    if "Spire's Spite" in r['title']:
                        print("!!! ERROR: Irrelevant result found: Spire's Spite")
            else:
                print(f"Search failed: {resp.status_code}")
    except Exception as e:
        print(f"Search exception: {e}")

    print("\n--- 2. Testing Details Sorting & Metadata ---")
    try:
        # Using a Solo Leveling URL from NovelFire as a test ID
        test_id = "https://novelfire.net/book/solo-leveling"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{API_BASE}/api/novel/info?id={test_id}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Novel: {data.get('title')}")
                print(f"Poster: {'Present' if data.get('poster_url') else 'MISSING'}")
                
                volumes = data.get("volumes", {})
                for vol, chapters in volumes.items():
                    print(f"Volume: {vol} ({len(chapters)} chapters)")
                    if chapters:
                        # Check sorting
                        nums = [ch.get("number") for ch in chapters[:10] if ch.get("number")]
                        print(f"First 10 serial numbers: {nums}")
                        if nums != sorted(nums):
                            print("!!! ERROR: Chapters are NOT sorted correctly")
                        else:
                            print("Chapters appear sorted.")
            else:
                print(f"Info failed: {resp.status_code}")
    except Exception as e:
        print(f"Info exception: {e}")

if __name__ == "__main__":
    asyncio.run(verify_fixes())
