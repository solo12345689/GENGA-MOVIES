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
    if response.status_code == 200:
        data = response.json().get('data', {})
        
        # Check homeList item structure
        if 'homeList' in data and data['homeList']:
            group = data['homeList'][0]
            print(f"Group keys: {list(group.keys())}")
            items_key = 'list' if 'list' in group else 'items' if 'items' in group else 'contents'
            print(f"Items key: {items_key}")
            
            if items_key in group and group[items_key]:
                item = group[items_key][0]
                print(f"Item keys: {list(item.keys())}")
                print(f"Sample Item: {json.dumps(item, indent=2)}")
                
except Exception as e:
    print(f"Error: {e}")
"""
    try:
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding='utf-8')
        with open('raw_item_structure.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout + "\n" + result.stderr)
            
    except Exception as e:
        print(f"Subprocess failed: {e}")

if __name__ == "__main__":
    run_test()
