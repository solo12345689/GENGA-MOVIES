import asyncio
import json
from moviebox_api import Session, Homepage

async def inspect_library():
    print("Starting library inspection...")
    try:
        session = Session()
        homepage = Homepage(session=session)
        
        # Get raw content
        print("Fetching raw content via library...")
        content = await homepage.get_content()
        
        with open('lib_homepage_raw.json', 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        
        print(f"Content keys: {list(content.keys())}")
        
        # Check sessions headers
        print(f"Session headers: {session.headers}")

    except Exception as e:
        print(f"Error during inspection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(inspect_library())
