
import asyncio
from backend.api import stream, search, details
from backend.api import session

async def debug_moviebox_flow():
    print("--- 1. Searching for 'Avatar' ---")
    sr = await search(query="Avatar", content_type="movie")
    if not sr.get('results'):
        print("FAIL: No results found")
        return
    
    item = sr['results'][0]
    print(f"Found: {item.title} ({item.id})")
    
    print("\n--- 2. Fetching Details ---")
    det = await details(item.id)
    print(f"Details: {det.get('title')}")
    
    print("\n--- 3. Resolving Stream URL ---")
    try:
        # Simulate what the frontend asks for
        # /api/stream?mode=url&query=Title&id=ID&content_type=movie
        res = await stream(query=item.title, id=item.id, content_type=item.type, mode="url")
        print("Stream Result:", res)
        
        if res.get('url'):
            print(f"\n[SUCCESS] Got URL: {res['url']}")
            # Check if it's proxied
            if "/api/proxy/stream" in res['url']:
                print("   -> Is Proxy URL (Good)")
        else:
             print("[FAIL] No URL returned")
             
    except Exception as e:
        print(f"[ERROR] Stream resolution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(debug_moviebox_flow())
