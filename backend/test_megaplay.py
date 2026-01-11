import httpx

url = "https://megaplay.buzz/stream/s-2/47085/sub"
headers = {
    "Referer": "https://megaplay.buzz/",
    "Origin": "https://megaplay.buzz",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    r = httpx.get(url, headers=headers, verify=False, follow_redirects=True, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Content length: {len(r.text)}")
    if "sorry" in r.text.lower() or "410" in r.text:
        print(">>> BLOCKED - Contains 'sorry' or '410'")
    else:
        print(">>> SUCCESS - Page loaded!")
    print("\nFirst 1000 chars:")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {e}")
