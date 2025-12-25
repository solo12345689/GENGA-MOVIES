import asyncio
from moviebox_api import Session, Search

async def deep_debug():
    session = Session()
    query = "Solo Leveling"
    print(f"Searching for '{query}'...")
    search_instance = Search(session=session, query=query)
    results = await search_instance.get_content_model()
    
    if not results or not results.items:
        print("No results found.")
        return
    
    item = results.items[0]
    print(f"Item Title: {item.title}")
    
    # Dump item attributes
    print("\n[ITEM ATTRIBUTES]")
    for attr in dir(item):
        if not attr.startswith('_'):
            try:
                val = getattr(item, attr)
                print(f" - {attr}: {val}")
            except: pass
            
    # Get details
    print("\nFetching details...")
    provider = search_instance.get_item_details(item)
    details = await provider.get_content_model()
    
    # Dump details attributes
    print("\n[DETAILS ATTRIBUTES]")
    for attr in dir(details):
        if not attr.startswith('_'):
            try:
                val = getattr(details, attr)
                # If it's a model, show its dict
                if hasattr(val, 'dict'):
                    print(f" - {attr}: {val.dict()}")
                else:
                    print(f" - {attr}: {val}")
            except: pass

if __name__ == "__main__":
    asyncio.run(deep_debug())
