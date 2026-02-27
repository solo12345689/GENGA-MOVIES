import httpx
import asyncio
import json

BASE_URL = "https://api-consumet-org-mswp.onrender.com"

async def test_manga_api():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Search Manga
        query = "one piece"
        provider = "anilist-manga"
        print(f"Testing search for: {query} using {provider}")
        search_url = f"{BASE_URL}/meta/{provider}/{query}"
        resp = await client.get(search_url)
        print(f"Search Status: {resp.status_code}")
        if resp.status_code == 200:
            search_results = resp.json()
            results = search_results.get('results', search_results)
            if isinstance(results, list):
                print(f"Found {len(results)} results")
                if results:
                    manga = results[0]
                    manga_id = manga.get('id')
                    print(f"Selected Manga: {manga.get('title')} (ID: {manga_id})")
                    
                    # 2. Get Info
                    print(f"\nTesting info for ID: {manga_id} using {provider}")
                    info_url = f"{BASE_URL}/meta/{provider}/info/{manga_id}"
                    info_resp = await client.get(info_url)
                    print(f"Info Status: {info_resp.status_code}")
                    if info_resp.status_code == 200:
                        info = info_resp.json()
                        print(f"Title: {info.get('title')}")
                        chapters = info.get('chapters', [])
                        print(f"Found {len(chapters)} chapters")
                        
                        if chapters:
                            chapter_id = chapters[0]['id']
                            print(f"\nTesting read for Chapter ID: {chapter_id} using {provider}")
                            read_url = f"{BASE_URL}/meta/{provider}/read?chapterId={chapter_id}"
                            read_resp = await client.get(read_url)
                            print(f"Read Status: {read_resp.status_code}")
                            if read_resp.status_code == 200:
                                pages = read_resp.json()
                                print(f"Found {len(pages)} pages")



if __name__ == "__main__":
    asyncio.run(test_manga_api())
