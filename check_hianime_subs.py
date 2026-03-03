import httpx
import json
import asyncio

async def check_subs():
    api_base = "https://aniwatch-api-dotd.onrender.com/api/v2/hianime"
    # Example: One Piece Episode 1
    ep_id = "one-piece-100?ep=2142" 
    url = f"{api_base}/anime/sources?episodeId={ep_id}&category=sub"
    
    print(f"Fetching: {url}")
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        if res.status_code == 200:
            data = res.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {res.status_code}")

if __name__ == "__main__":
    asyncio.run(check_subs())
