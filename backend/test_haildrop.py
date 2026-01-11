
import httpx
import asyncio

async def test_headers():
    url = "https://haildrop77.pro/_v7/bcc52d54faa312a4db378d17489cb8a004d0e466d2734810803aa4ceb961f23f284642f711fba4bbca93d3ce1f4a812a7d7f9cd4c48150fef35b7c3f31be6b6fded8afc1bab364cdd53e67ee2a279e91515dd28bd0f91d4ffd14b5e2dfd5b6283d011385480e67b720707cf4dc4daa744f35ffd57103b2cb10437298d113311f/master.m3u8"
    
    headers_list = [
        {"name": "No Referer", "headers": {}},
        {"name": "HiAnime Referer", "headers": {"Referer": "https://hianime.to/", "Origin": "https://hianime.to"}},
        {"name": "MovieBox Referer", "headers": {"Referer": "https://www.moviebox.pro/", "Origin": "https://www.moviebox.pro"}},
        {"name": "MovieBox App Referer", "headers": {"Referer": "https://v.showbox.cc/", "Origin": "https://v.showbox.cc"}},
    ]
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    log_output = []
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for item in headers_list:
            headers = item["headers"].copy()
            headers["User-Agent"] = ua
            try:
                log_output.append(f"Testing {item['name']}...")
                res = await client.get(url, headers=headers)
                log_output.append(f"Result: {res.status_code}")
                if res.status_code == 200:
                    log_output.append("SUCCESS!")
                    # break # Check all
            except Exception as e:
                log_output.append(f"Error: {e}")

    with open("haildrop_test_log.txt", "w") as f:
        f.write("\n".join(log_output))

if __name__ == "__main__":
    asyncio.run(test_headers())
