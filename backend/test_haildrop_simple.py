
import httpx
import asyncio

async def test():
    url = "https://haildrop77.pro/_v7/174d034d32597a2d0a75f498a6d370bd4d2097f6f23ca98cf719ca5d495c21052a4b0257d42e775b47fbe2cef221fa914e742e801349de33491e61d524c74aea91beece345cd5eaee642e0aab195984dfc0e447dc731e712e9ed1371a10f5f3098a27fb45af5b6c2987e6810aefed6a3d787d6e3be87925dba33160ad7272194/master.m3u8"
    
    # Try just NO Referer first, then basic MB referer
    headers_list = [
        {"name": "No Referer", "headers": {}},
        {"name": "MovieBox", "headers": {"Referer": "https://www.moviebox.pro/", "Origin": "https://www.moviebox.pro"}},
        {"name": "Showbox", "headers": {"Referer": "https://v.showbox.cc/", "Origin": "https://v.showbox.cc"}},
    ]
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    async with httpx.AsyncClient(timeout=10) as client:
        for item in headers_list:
            headers = item["headers"]
            headers["User-Agent"] = ua
            try:
                print(f"--- TEST: {item['name']} ---")
                res = await client.head(url, headers=headers)
                print(f"HEAD: {res.status_code}")
                if res.status_code != 200:
                    res = await client.get(url, headers=headers)
                    print(f"GET: {res.status_code}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
