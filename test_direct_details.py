from moviebox_api import Session, Movie, Series
import asyncio
import json

async def test_direct_details():
    session = Session()
    # From search results/previous logs: Solo Leveling: ReAwakening [CAM] ID is 4757760137329361264
    # Actually that was Avatar. Solo Leveling ID is likely different.
    # Let's search once to get a real ID.
    from moviebox_api import Search
    s = Search(session=session, query="Solo Leveling")
    results = await s.get_content_model()
    if not results.items:
        print("No results")
        return
    
    item = results.items[0]
    item_id = str(item.id)
    print(f"Item: {item.title}, ID: {item_id}")
    
    # Try creating Movie or Series directly
    print("Testing Movie(id=...) direct details...")
    try:
        movie = Movie(session=session, id=item_id)
        # Note: Movie class might not exist or might work differently
        details = await movie.get_content_model()
        print(f"Success! Title: {details.title}")
    except Exception as e:
        print(f"Movie(id=...) failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_details())
