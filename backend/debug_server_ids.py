
import httpx
import asyncio
import re

async def check_servers(episode_id, name):
    url = f"https://hianime.to/ajax/v2/episode/servers?episodeId={episode_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://hianime.to/watch/{name}?ep={episode_id}",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    print(f"\nChecking {name} (Ep ID: {episode_id})...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                # Extract data-id and titles
                # <div class="item server-item" data-id="123456" data-server-id="4">
                matches = re.findall(r'data-id="(\d+)"[^>]*data-server-id="(\d+)"', html)
                for link_id, server_id in matches:
                    print(f"Found Server: ID={link_id}, ServerType={server_id}")
                    # Check if 136197 is here for MHA
            else:
                print("Failed to get servers.")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Boruto Ep 1: 47085
    await check_servers("47085", "boruto-naruto-next-generations-8143")
    
    # MHA Ep 1: 6210
    await check_servers("6210", "my-hero-academia-322")

if __name__ == "__main__":
    asyncio.run(main())
