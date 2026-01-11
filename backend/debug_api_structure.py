import httpx
import asyncio
import json
import sys

async def test_anime():
    base = "https://aniwatch-api-3e2f.onrender.com/api/v2/hianime"
    anime_id = "naruto-677"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    with open("debug_log.txt", "w") as f:
        f.write("Log started\n")
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            # Test Details
            f.write(f"Testing Details: {base}/anime/{anime_id}\n")
            try:
                res = await client.get(f"{base}/anime/{anime_id}")
                f.write(f"Details Status: {res.status_code}\n")
                details = res.json()
                f.write(f"Details Keys: {list(details.keys())}\n")
                if "data" in details and "anime" in details["data"]:
                    f.write("Successfully found anime data\n")
            except Exception as e:
                f.write(f"Details Error: {e}\n")
            
            # Test Episodes
            f.write(f"\nTesting Episodes: {base}/anime/{anime_id}/episodes\n")
            try:
                res = await client.get(f"{base}/anime/{anime_id}/episodes")
                f.write(f"Episodes Status: {res.status_code}\n")
                episodes_response = res.json()
                f.write(f"Episodes Response Keys: {list(episodes_response.keys())}\n")
                f.write(f"Full response: {json.dumps(episodes_response)[:1000]}\n")
            except Exception as e:
                f.write(f"Episodes Error: {e}\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_anime())
    except Exception as e:
        with open("debug_log.txt", "a") as f:
            f.write(f"Main Error: {e}\n")
