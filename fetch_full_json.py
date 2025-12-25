import urllib.request
import json
import ssl

def fetch():
    url = "https://h5.aoneroom.com/wefeed-h5-bff/web/home"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    with open('full_homepage.json', 'w', encoding='utf-8') as f:
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                if response.getcode() == 200:
                    raw = response.read().decode()
                    parsed = json.loads(raw)
                    f.write(json.dumps(parsed, indent=2))
                else:
                    f.write(f"Error: Status {response.getcode()}")
        except Exception as e:
            f.write(f"Error: {e}")

if __name__ == "__main__":
    fetch()
