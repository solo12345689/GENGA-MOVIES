from moviebox_api import Session, Homepage
import asyncio
import json

async def inspect():
    try:
        session = Session()
        homepage = Homepage(session=session)
        print("Fetching raw content...")
        # Use get_content() instead of get_content_model()
        content = await homepage.get_content()
        print("Content type:", type(content))
        
        if isinstance(content, dict):
            print("Keys:", content.keys())
            if 'data' in content:
                data = content['data']
                print("Data keys:", data.keys())
                if 'homeList' in data:
                    print(f"homeList length: {len(data['homeList'])}")
                    if data['homeList']:
                        print("First group:", data['homeList'][0].keys())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(inspect())
