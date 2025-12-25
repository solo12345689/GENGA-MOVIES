import urllib.request
import json
import sys

def test_url(url):
    print(f"Testing {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            if response.getcode() == 200:
                raw_data = response.read().decode()
                print(f"Raw Response: {raw_data}")
                data = json.loads(raw_data)
                print(f"Parsed Groups count: {len(data.get('groups', []))}")
                return True
            else:
                print(f"Failed with status {response.getcode()}")
    except Exception as e:
        print(f"Failed: {e}")
    return False

if __name__ == "__main__":
    # Try localhost
    if not test_url("http://localhost:8000/api/homepage"):
        # Try IP
        test_url("http://192.168.29.247:8000/api/homepage")
    
    sys.stdout.flush()
