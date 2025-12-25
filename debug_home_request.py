import requests

url = "https://h5.aoneroom.com/wefeed-h5-bff/web/home"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    print(f"Testing {url}...")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Success! Keys:", data.keys())
        if 'data' in data:
            print("Data keys:", data['data'].keys())
    else:
        print("Response:", response.text[:500])
except Exception as e:
    print(f"Error: {e}")
