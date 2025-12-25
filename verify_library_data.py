from moviebox_api import Session, Homepage
import asyncio
import json

async def verify():
    print("Initializing Session...")
    session = Session()
    homepage = Homepage(session=session)
    
    print("Fetching raw content from library...")
    try:
        content = await homepage.get_content()
        
        # Handle if it's nested in 'data'
        data = content.get('data', content)
        
        print(f"Top Level Keys: {list(content.keys())}")
        if 'data' in content:
            print(f"Data Keys: {list(data.keys())}")
            
        if 'operatingList' in data:
            print(f"Found operatingList! Count: {len(data['operatingList'])}")
            for item in data['operatingList']:
                print(f" - Type: {item.get('type')}, Title: {item.get('title')}")
        else:
            print("operatingList NOT found in library response.")
            
    except Exception as e:
        print(f"Library fetch failed: {e}")
    
if __name__ == "__main__":
    asyncio.run(verify())
