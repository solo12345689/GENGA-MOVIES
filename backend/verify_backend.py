import httpx
import asyncio
import sys

BASE_URL = "http://localhost:8000"

async def test_endpoints():
    print("Testing Backend Endpoints...")
    async with httpx.AsyncClient() as client:
        # 1. Health
        try:
            r = await client.get(f"{BASE_URL}/api/health")
            print(f"Health: {r.status_code} {r.json()}")
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return

        # 2. System Status
        try:
            r = await client.get(f"{BASE_URL}/api/system/status")
            print(f"System Status: {r.status_code} {r.json()}")
        except Exception as e:
            print(f"System Status Failed: {e}")

        # 3. CineCLI Search (Mock Query)
        try:
            r = await client.get(f"{BASE_URL}/api/cinecli/search?query=avatar")
            if r.status_code == 200:
                results = r.json().get('results', [])
                print(f"CineCLI Search: Found {len(results)} items")
            else:
                print(f"CineCLI Search Failed: {r.status_code}")
        except Exception as e:
            print(f"CineCLI Search Error: {e}")

        # 4. Proxy Stream (Mock with Google)
        try:
            # We just check if it proxies, not if it streams video
            r = await client.get(f"{BASE_URL}/api/proxy/stream?url=https://www.google.com", follow_redirects=True)
            print(f"Proxy Stream Request: {r.status_code}")
            # If 200, it means it successfully fetched and proxied Google HTML (as a stream)
        except Exception as e:
            print(f"Proxy Stream Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_endpoints())
    except KeyboardInterrupt:
        pass
