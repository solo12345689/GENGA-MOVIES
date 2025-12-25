from moviebox_api import Session, Homepage
import asyncio
import json

async def inspect():
    try:
        print("Initializing session...")
        session = Session()
        
        print("Checking Homepage class...")
        homepage = Homepage(session=session)
        print("Homepage instance created.")
        
        print("Fetching homepage content...")
        content = await homepage.get_content_model()
        print("Content fetched successfully.")
        
        if content and content.groups:
            print(f"Found {len(content.groups)} groups.")
            for group in content.groups:
                print(f"Group: {group.title}")
                if group.items:
                    print(f"  First item: {group.items[0].title}")
        else:
            print("No groups found.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(inspect())
