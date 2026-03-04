import httpx
import asyncio
import sys

async def test_download():
    # Use a known movie ID or rely on search
    # Example movie: 'Moana 2' or similar
    query = "Moana 2"
    base_url = "http://localhost:8000"
    
    # First, let's search to get a valid ID in cache
    print(f"Searching for '{query}'...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        search_res = await client.get(f"{base_url}/api/search?query={query}")
        if search_res.status_code != 200:
            print(f"Search failed: {search_res.status_code}")
            return
            
        results = search_res.json().get("results", [])
        if not results:
            print("No results found.")
            return
            
        item = results[0]
        item_id = item["id"]
        print(f"Found item: {item['title']} (ID: {item_id})")
        
        # Now test the download endpoint
        download_url = f"{base_url}/api/moviebox/download?id={item_id}&query={query}"
        print(f"Testing download endpoint: {download_url}")
        
        # We only want to check headers and start of stream
        try:
            async with client.stream("GET", download_url) as resp:
                print(f"Status Code: {resp.status_code}")
                print(f"Headers: {dict(resp.headers)}")
                
                if resp.status_code == 200:
                    content_disposition = resp.headers.get("Content-Disposition", "")
                    if "attachment" in content_disposition:
                        print(f"SUCCESS: Found attachment header: {content_disposition}")
                    else:
                        print("WARNING: 'attachment' not found in Content-Disposition")
                        
                    # Read first few bytes to ensure it's streaming
                    chunk = await resp.aiter_bytes().__anext__()
                    print(f"Successfully received first chunk of size: {len(chunk)} bytes")
                    print("VERIFICATION SUCCESSFUL")
                else:
                    print(f"FAILURE: Received status {resp.status_code}")
                    # Try to read error message if small
                    try:
                        error_body = await resp.aread()
                        print(f"Error Body: {error_body.decode()}")
                    except: pass
                    
        except Exception as e:
            print(f"Error during download test: {e}")

if __name__ == "__main__":
    asyncio.run(test_download())
