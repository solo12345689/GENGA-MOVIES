import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/anime/home") as response:
        status = response.getcode()
        body = response.read().decode('utf-8')
        print(f"Status: {status}")
        print(f"Response: {body[:200]}...")
except Exception as e:
    print(f"Error: {e}")
