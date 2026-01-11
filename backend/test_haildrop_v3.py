
import httpx
import asyncio
import json

async def test_headers():
    # Using the exact URL from the user's latest log
    url = "https://haildrop77.pro/_v7/174d034d32597a2d0a75f498a6d370bd4d2097f6f23ca98cf719ca5d495c21052a4b0257d42e775b47fbe2cef221fa914e742e801349de33491e61d524c74aea91beece345cd5eaee642e0aab195984dfc0e447dc731e712e9ed1371a10f5f3098a27fb45af5b6c2987e6810aefed6a3d787d6e3be87925dba33160ad7272194/master.m3u8"
    
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "MovieBox/2.1.2 (iPhone; iOS 15.0; Scale/3.00)"
    ]
    
    referers = [
        None,
        "https://hianime.to/",
        "https://www.moviebox.pro/",
        "https://v.showbox.cc/",
        "https://videonext.net/" # Another common one
    ]
    
    log_output = []
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for ua in uas:
            for ref in referers:
                headers = {"User-Agent": ua}
                if ref:
                    headers["Referer"] = ref
                    headers["Origin"] = ref.rstrip("/")
                
                try:
                    log_output.append(f"Testing UA: {ua[:40]}... | REF: {ref}")
                    res = await client.head(url, headers=headers)
                    log_output.append(f"Result (HEAD): {res.status_code}")
                    if res.status_code == 200:
                        log_output.append("!!! SUCCESS !!!")
                    
                    # Try GET if HEAD fails but stay brief
                    if res.status_code != 200:
                         res_get = await client.get(url, headers=headers)
                         log_output.append(f"Result (GET): {res_get.status_code}")
                         if res_get.status_code == 200:
                             log_output.append("!!! SUCCESS !!!")
                except Exception as e:
                    log_output.append(f"Error: {e}")
                log_output.append("-" * 20)

    with open("haildrop_debug_v3.txt", "w") as f:
        f.write("\n".join(log_output))

if __name__ == "__main__":
    asyncio.run(test_headers())
