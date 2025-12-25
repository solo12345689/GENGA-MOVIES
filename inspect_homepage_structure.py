from moviebox_api import Session, Homepage
import asyncio
import json

async def inspect():
    try:
        print("Initializing session...")
        session = Session()
        
        print("Checking Homepage class...")
        homepage = Homepage(session=session)
        
        print("Fetching homepage content...")
        content = await homepage.get_content_model()
        print("Content fetched successfully.")
        
        print(f"Content Type: {type(content)}")
        print("Attributes:")
        for attr in dir(content):
            if not attr.startswith('_'):
                try:
                    val = getattr(content, attr)
                    if not callable(val):
                        print(f"  {attr}: {type(val)}")
                except:
                    pass
                    
        # If it's Pydantic
        if hasattr(content, 'model_dump'):
            print("\nModel Dump Keys:", content.model_dump().keys())
        elif hasattr(content, 'dict'):
            print("\nModel Dict Keys:", content.dict().keys())

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(inspect())
