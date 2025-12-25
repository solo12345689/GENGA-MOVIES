import requests
import json

def test_homepage():
    url = "http://localhost:8000/api/homepage"
    print(f"Testing {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            groups = data.get("groups", [])
            print(f"Received {len(groups)} groups.")
            for group in groups:
                print(f"Section: {group.get('title')}")
                items = group.get('items', [])
                print(f"Items: {len(items)}")
                if items:
                    item = items[0]
                    print(f"  - First Item: {item.get('title')}")
                    print(f"  - Poster: {item.get('poster')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_homepage()
