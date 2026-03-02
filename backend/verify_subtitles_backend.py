import asyncio
from moviebox_api import Session, Search, SubjectType
from moviebox_api.download import (
    DownloadableMovieFilesDetail, 
    DownloadableTVSeriesFilesDetail,
    resolve_media_file_to_be_downloaded
)

async def test_extraction():
    session = Session()
    try:
        # Search for a popular movie to ensure results
        query = "Inception"
        search = Search(session=session, query=query, subject_type=SubjectType.MOVIES)
        results = await search.get_content_model()
        
        if not results.items:
            print("No items found")
            return

        target_item = results.items[0]
        print(f"Testing with: {target_item.title} (ID: {target_item.subjectId})")

        files_provider = DownloadableMovieFilesDetail(session=session, item=target_item)
        files_metadata = await files_provider.get_content_model()
        
        print(f"Downloads found: {len(files_metadata.downloads)}")
        print(f"Captions found: {len(files_metadata.captions)}")
        
        for caption in files_metadata.captions:
            print(f"  - Lang: {caption.lanName} ({caption.lan}) | URL: {str(caption.url)[:50]}...")

    finally:
        # session.close() is not needed if it's not async or not available
        pass

if __name__ == "__main__":
    asyncio.run(test_extraction())
