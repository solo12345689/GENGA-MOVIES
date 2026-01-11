
import httpx
import sys
import os

log_path = r"c:\Users\akshi\.gemini\antigravity\scratch\moviebox_web_app\backend\fogtwist_headers_log.txt"
url = "https://fogtwist21.xyz/_v7/bcc52d54faa312a4db378d17489cb8a004d0e466d2734810803aa4ceb961f23f284642f711fba4bbca93d3ce1f4a812a7d7f9cd4c48150fef35b7c3f31be6b6fded8afc1bab364cdd53e67ee2a279e91515dd28bd0f91d4ffd14b5e2dfd5b6283d011385480e67b720707cf4dc4daa744f35ffd57103b2cb10437298d113311f/master.m3u8"

tests = [
    ("HiAnime", {"Referer": "https://hianime.to/", "Origin": "https://hianime.to"}),
    ("Showbox App", {"Referer": "https://v.showbox.cc/", "Origin": "https://v.showbox.cc"}),
    ("H5 Mirror", {"Referer": "https://fmoviesunblocked.net/", "Origin": "h5.aoneroom.com"}),
    ("MovieBox Pro", {"Referer": "https://www.moviebox.pro/", "Origin": "https://www.moviebox.pro"}),
    ("VideoNext", {"Referer": "https://videonext.net/", "Origin": "https://videonext.net"}),
    ("Megacloud", {"Referer": "https://megacloud.to/", "Origin": "https://megacloud.to"}),
    ("Vidcloud", {"Referer": "https://vidcloud9.me/", "Origin": "https://vidcloud9.me"}),
    ("No Referer", {}),
]

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

try:
    with open(log_path, "w") as f:
        f.write(f"Testing URL: {url}\n\n")
        with httpx.Client(follow_redirects=True, timeout=10.0, verify=False) as client:
            for name, headers in tests:
                h = headers.copy()
                h["User-Agent"] = ua
                try:
                    r = client.get(url, headers=h)
                    f.write(f"[{name}] Status: {r.status_code}\n")
                    if r.status_code == 200:
                        f.write(f"  Content Preview: {r.text[:50]}\n")
                    elif r.status_code == 403:
                        f.write(f"  Forbidden. Server: {r.headers.get('Server')}\n")
                except Exception as e:
                    f.write(f"[{name}] Error: {e}\n")
except Exception as sys_e:
    print(f"System Error: {sys_e}")
