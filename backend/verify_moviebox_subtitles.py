import httpx
import asyncio
import json

async def test_subtitles():
    # Example movie: 'Moana 2'
    query = "Moana 2"
    base_url = "http://localhost:8000"
    
    print(f"Testing subtitles for '{query}'...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for item
        search_res = await client.get(f"{base_url}/api/search?query={query}")
        if search_res.status_code != 200: return
        
        results = search_res.json().get("results", [])
        if not results: return
        
        item = results[0]
        item_id = item["id"]
        
        # Call stream endpoint (POST)
        stream_url = f"{base_url}/api/stream?mode=url&query={query}&id={item_id}"
        print(f"Requesting stream: {stream_url}")
        
        res = await client.post(stream_url)
        if res.status_code == 200:
            data = res.json()
            subtitles = data.get("subtitles", [])
            print(f"Found {len(subtitles)} subtitle tracks")
            for sub in subtitles:
                print(f" - {sub['lang']}: {sub['url']}")
            
            if len(subtitles) > 0:
                print("VERIFICATION SUCCESSFUL: Subtitles returned by API")
            else:
                print("WARNING: No subtitles returned for this item")
        else:
            print(f"Error: {res.status_code}")

if __name__ == "__main__":
    asyncio.run(test_subtitles())
