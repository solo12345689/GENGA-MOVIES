
import httpx
import asyncio
import json

async def test_prod():
    base_url = "https://aniwatch-api-3e2f.onrender.com/api/v2/hianime"
    anime_id = "one-piece-100"
    
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Fetch episodes
        url_ep = f"{base_url}/anime/episodes/{anime_id}"
        print(f"Fetching: {url_ep}")
        res = await client.get(url_ep)
        data = res.json()
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200 and data.get("success"):
            episodes = data["data"].get("episodes", [])
            print(f"Found {len(episodes)} episodes")
            if episodes:
                for i in range(min(3, len(episodes))):
                    ep = episodes[i]
                    print(f"Ep {ep['number']}: {ep['episodeId']}")
        else:
            print("Failed to fetch episodes")
            print(data)

if __name__ == "__main__":
    asyncio.run(test_prod())
