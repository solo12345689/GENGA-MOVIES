
import httpx
import asyncio
import json
import os

async def check_sources():
    anime_id = "naruto-679"
    # Alternative API
    base_url = "https://hianime-api.vercel.app/api/v1"
    
    log_path = r"c:\Users\akshi\.gemini\antigravity\scratch\moviebox_web_app\backend\check_log_v2.txt"
    output = []
    
    output.append(f"Testing API: {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            url_ep = f"{base_url}/anime/{anime_id}/episodes"
            output.append(f"Fetching episodes: {url_ep}")
            res = await client.get(url_ep)
            data = res.json()
            
            if data.get("status") == 200:
                episodes = data["data"].get("episodes", [])
                if episodes:
                    ep_id = episodes[0]["episodeId"]
                    output.append(f"Found Episode ID: {ep_id}")
                    
                    # Try different servers
                    servers = ["vidcloud", "megacloud", "vidstreaming"]
                    for s in servers:
                        url_src = f"{base_url}/episode/sources?animeEpisodeID={ep_id}&server={s}&category=sub"
                        output.append(f"Fetching sources ({s}): {url_src}")
                        res_src = await client.get(url_src)
                        data_src = res_src.json()
                        output.append(f"Result for {s}: {data_src.get('status')} - {data_src.get('message', 'OK')}")
                        if data_src.get("status") == 200:
                            output.append(json.dumps(data_src, indent=2))
                            break
                else:
                    output.append("No episodes found")
            else:
                output.append(f"API Error: {data}")
    except Exception as e:
        output.append(f"Exception: {str(e)}")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print(f"DONE. Written to {log_path}")

if __name__ == "__main__":
    asyncio.run(check_sources())
