import subprocess
import sys

def run_test():
    code = """
import requests
import json
url = "https://h5.aoneroom.com/wefeed-h5-bff/web/home"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Valid JSON. Keys: {list(data.keys())}")
        if 'data' in data:
             print(f"Data keys: {list(data['data'].keys())}")
             if 'list' in data['data']:
                 print(f"List length: {len(data['data']['list'])}")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
"""
    try:
        # Run the code string in a separate process
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding='utf-8')
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        with open('final_debug_output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout + "\n" + result.stderr)
            
    except Exception as e:
        print(f"Subprocess failed: {e}")

if __name__ == "__main__":
    run_test()
