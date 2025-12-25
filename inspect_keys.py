import urllib.request
import json
import ssl

def inspect():
    url = "https://h5.aoneroom.com/wefeed-h5-bff/web/home"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    with open('item_keys.txt', 'w', encoding='utf-8') as f:
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                if response.getcode() == 200:
                    data = json.loads(response.read().decode())
                    if 'data' in data:
                        raw_data = data['data']
                        
                        # Inspect Top Picks
                        if 'topPickList' in raw_data and raw_data['topPickList']:
                            first = raw_data['topPickList'][0]
                            f.write(f"TopPick First Item Type: {type(first)}\n")
                            if isinstance(first, dict):
                                f.write(f"TopPick Keys: {list(first.keys())}\n")
                                f.write(f"TopPick Sample: {json.dumps(first, indent=2)}\n")
                        else:
                             f.write("topPickList missing or empty\n")

                        # Inspect Home List
                        if 'homeList' in raw_data and raw_data['homeList']:
                            first_group = raw_data['homeList'][0]
                            f.write(f"\nHomeList First Group Keys: {list(first_group.keys())}\n")
                            
                            # Try to find items list
                            items_key = None
                            if 'list' in first_group: items_key = 'list'
                            elif 'items' in first_group: items_key = 'items'
                            elif 'contents' in first_group: items_key = 'contents'
                            
                            if items_key and first_group[items_key]:
                                first_item = first_group[items_key][0]
                                f.write(f"HomeList Item Keys ({items_key}): {list(first_item.keys())}\n")
                                f.write(f"HomeList Sample: {json.dumps(first_item, indent=2)}\n")
                            else:
                                 f.write("HomeList group has no items found\n")
                    else:
                        f.write("'data' key missing in response\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    inspect()
