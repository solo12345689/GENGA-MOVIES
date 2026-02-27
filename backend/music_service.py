import httpx
from typing import List, Optional, Dict, Any
from urllib.parse import quote

class MusicService:
    def __init__(self):
        self.base_url = "https://gaanapy-a8jf.onrender.com"
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"[MusicService] Requesting: {url} with params {params}")
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    print(f"[MusicService] Error {resp.status_code}: {resp.text[:200]}")
                    return None
                return resp.json()
            except Exception as e:
                print(f"[MusicService] Exception for {endpoint}: {e}")
                return None

    async def search_songs(self, query: str, limit: int = 20):
        # http://127.0.0.1:8000/songs/search?query=<query>&limit=<limit>
        return await self._get("/songs/search", {"query": query, "limit": limit})

    async def get_song_info(self, seokey: str):
        # http://127.0.0.1:8000/songs/info?seokey=SEOKEY
        return await self._get("/songs/info", {"seokey": seokey})

    async def search_albums(self, query: str, limit: int = 10):
        # http://127.0.0.1:8000/albums/search?query=<query>&limit=<limit>
        return await self._get("/albums/search", {"query": query, "limit": limit})

    async def get_album_info(self, seokey: str):
        # http://127.0.0.1:8000/albums/info?seokey=ALBUM_SEOKEY
        return await self._get("/albums/info", {"seokey": seokey})

    async def get_trending(self, language: str = "English"):
        # http://127.0.0.1:8000/trending?language=LANGUAGE
        return await self._get("/trending", {"language": language})

    async def get_new_releases(self, language: str = "English"):
        # http://127.0.0.1:8000/newreleases?language=LANGUAGE
        return await self._get("/newreleases", {"language": language})

    async def get_charts(self):
        # http://127.0.0.1:8000/charts
        return await self._get("/charts")

    async def get_playlist_info(self, seokey: str):
        # http://127.0.0.1:8000/playlists/info?seokey=SEOKEY
        return await self._get("/playlists/info", {"seokey": seokey})
