import httpx
import asyncio
import json

async def debug_gaana():
    base_url = "https://gaanapy-a8jf.onrender.com"
    timeout = httpx.Timeout(30.0)
    
    endpoints = [
        "/trending?language=English",
        "/newreleases?language=English",
        "/charts"
    ]
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for ep in endpoints:
            print(f"\n--- Checking {ep} ---")
            try:
                resp = await client.get(f"{base_url}{ep}")
                print(f"Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    # Print first 2 items of the response to see structure
                    print(json.dumps(data[:2] if isinstance(data, list) else data, indent=2))
                else:
                    print(f"Error: {resp.text[:500]}")
            except Exception as e:
                print(f"Exception for {ep}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_gaana())
