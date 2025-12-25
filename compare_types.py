import asyncio
from moviebox_api import Session, Search, Homepage, SubjectType
import json

async def main():
    session = Session()
    
    # 1. Search
    print("Searching...")
    search = Search(session=session, query="Naruto")
    search_results = await search.get_content_model()
    if search_results.items:
        search_item = search_results.items[0]
        print(f"Search item type: {type(search_item)}")
        print(f"Search item: {search_item}")
    
    # 2. Homepage
    print("\nFetching Homepage...")
    homepage = Homepage(session=session)
    homepage_raw = await homepage.get_content()
    
    # Let's find an item in homepage_raw
    data = homepage_raw.get('data', homepage_raw)
    op_list = data.get('operatingList', [])
    if op_list:
        subjects = op_list[0].get('subjects', [])
        if subjects:
            home_item = subjects[0]
            print(f"Homepage item type: {type(home_item)}")
            print(f"Homepage item keys: {list(home_item.keys())}")

if __name__ == "__main__":
    asyncio.run(main())
