
import asyncio
from api import determine_item_type, search
import sys

async def main():
    try:
        results = await search("Naruto", content_type="all")
        if results and results.get('results'):
            for item in results['results']:
                print(f"TITLE: {item['title']} | TYPE: {item['type']}")
        else:
            print("No results found")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
