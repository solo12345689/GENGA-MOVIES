import asyncio
import json
from moviebox_api import Session, Search, Homepage

async def debug_details():
    session = Session()
    query = "Solo Leveling"
    print(f"Searching for '{query}'...")
    search_instance = Search(session=session, query=query)
    results = await search_instance.get_content_model()
    
    if not results or not results.items:
        print("No results found.")
        return
    
    # Take the first item (Solo Leveling: ReAwakening likely)
    item = results.items[0]
    print(f"Target Item: {item.title}")
    
    # Get details
    print("Fetching details...")
    details_provider = search_instance.get_item_details(item)
    details_model = await details_provider.get_content_model()
    
    # Inspect attributes of details_model
    print("\nDetails Model Attributes:")
    attrs = dir(details_model)
    important_fields = ['cover', 'image', 'poster', 'portrait', 'landscape', 'stills', 'resData', 'resource']
    for field in important_fields:
        if field in attrs:
            val = getattr(details_model, field)
            print(f" - {field}: {type(val)} {val if not hasattr(val, 'url') else val.url}")
            
    # Check resData/resource nesting
    if hasattr(details_model, 'resData'):
        resData = details_model.resData
        if hasattr(resData, 'resource'):
            resource = resData.resource
            if hasattr(resource, 'cover'):
                print(f" - resData.resource.cover: {resource.cover.url if hasattr(resource.cover, 'url') else resource.cover}")

if __name__ == "__main__":
    asyncio.run(debug_details())
