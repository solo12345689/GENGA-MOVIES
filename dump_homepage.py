
import asyncio
import json
from moviebox_api import Homepage, Session

async def dump_homepage():
    session = Session()
    try:
        homepage = Homepage(session=session)
        raw_response = await homepage.get_content()
        
        raw_data = raw_response.get('data', raw_response)
        
        summary = {}
        if 'operatingList' in raw_data:
            for group in raw_data['operatingList'][:4]:
                title = group.get('title', 'Unknown')
                summary[title] = []
                
                items_source = []
                if 'subjects' in group and group['subjects']:
                    items_source = group['subjects']
                elif 'banner' in group and group.get('banner') and 'items' in group['banner']:
                    items_source = group['banner']['items']
                
                for item in items_source[:2]:
                    # Check for slug-like attributes
                    summary[title].append({
                        "title": item.get('title'),
                        "id": item.get('id'),
                        "subjectId": item.get('subjectId'),
                        "subjectType": item.get('subjectType'),
                        "detailPath": item.get('detailPath'),
                        # Find other potential path fields
                        "other_fields": {k: v for k, v in item.items() if any(x in k.lower() for x in ['path', 'slug', 'url', 'link'])}
                    })
        
        print(json.dumps(summary, indent=2))
            
    finally:
        pass

if __name__ == "__main__":
    asyncio.run(dump_homepage())
