import urllib.request
import json
url = "https://raw.githubusercontent.com/famelack/famelack-channels/main/channels/raw/countries_metadata.json"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = response.read().decode('utf-8')
    items = json.loads(data)
    if isinstance(items, dict):
      print(json.dumps(list(items.items())[:2], indent=2))
    elif isinstance(items, list):
      print(json.dumps(items[:2], indent=2))
    else: print(type(items))
except Exception as e:
    print(e)
