import json

with open('full_homepage.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
if 'data' in data and 'operatingList' in data['data']:
    for idx, item in enumerate(data['data']['operatingList']):
        print(f"Item {idx}: Type={item.get('type')}, Title={item.get('title')}, Keys={list(item.keys())}")
        if 'subjects' in item and item['subjects']:
             print(f"  - Subjects count: {len(item['subjects'])}")
        if 'banner' in item and item['banner']:
             print(f"  - Banner items count: {len(item['banner'].get('items', []))}")
