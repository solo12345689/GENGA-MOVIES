
import asyncio
from moviebox_api import Search, SubjectType, Session

async def check():
    # api.py uses global session = Session()
    session = Session()
    try:
        # Search for a movie
        print("Searching for Movie (Inception)...")
        s_movie = Search(session=session, query='Inception', subject_type=SubjectType.MOVIES)
        res_movie = await s_movie.get_content_model()
        if res_movie.items:
            item = res_movie.items[0]
            # Try to see what's in the item
            print(f"Movie: {item.title}")
            print(f"  detailPath: '{getattr(item, 'detailPath', 'N/A')}'")
            print(f"  subjectType: {item.subjectType}")
            # Try to see if it's a TV series
            print(f"  Attributes: {[a for a in dir(item) if not a.startswith('_')]}")

        # Search for a series
        print("\nSearching for Series (Classroom of the Elite)...")
        s_series = Search(session=session, query='Classroom of the Elite', subject_type=SubjectType.TV_SERIES)
        res_series = await s_series.get_content_model()
        if res_series.items:
            item = res_series.items[0]
            print(f"Series: {item.title}")
            print(f"  detailPath: '{getattr(item, 'detailPath', 'N/A')}'")
            print(f"  subjectType: {item.subjectType}")
            
    finally:
        # Session might have an internal client to close
        if hasattr(session, 'close'):
            await session.close()
        elif hasattr(session, '_client') and hasattr(session._client, 'aclose'):
            await session._client.aclose()

if __name__ == "__main__":
    asyncio.run(check())
