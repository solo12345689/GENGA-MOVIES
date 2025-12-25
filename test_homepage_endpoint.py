import requests
import json

try:
    print("Testing /api/homepage endpoint...")
    # Try localhost first
    response = requests.get("http://localhost:8000/api/homepage")
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        if "groups" in data:
            print(f"Found {len(data['groups'])} groups.")
            for group in data['groups']:
                print(f"- {group['title']} ({len(group['items'])} items)")
        else:
            print("Response structure unexpected:", data.keys())
    else:
        print(f"Failed with status {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Connection failed: {e}")
    # Try with the IP seen in screenshot if localhost fails
    try:
        print("\nTrying IP 192.168.29.247...")
        response = requests.get("http://192.168.29.247:8000/api/homepage")
        if response.status_code == 200:
            print("Success on IP!")
            data = response.json()
            print(f"Found {len(data['groups'])} groups.")
        else:
            print(f"Failed on IP with status {response.status_code}")
    except Exception as e2:
        print(f"Connection to IP failed: {e2}")
