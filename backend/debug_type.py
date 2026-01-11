
import asyncio
from api import determine_item_type, search
import json

async def debug_type():
    print("Searching for Naruto...")
    results = await search("Naruto", content_type="all")
    for item in results['results']:
        print(f"Title: {item['title']}, Type: {item['type']}")

if __name__ == "__main__":
    asyncio.run(debug_type())
