import httpx
import asyncio
import traceback
import random
from typing import List, Optional, Any
from urllib.parse import quote

# Constants
# Updated Mirror List based on 2025 status
YTS_MIRRORS = [
    "https://yts.mx/api/v2",
    "https://yts.lt/api/v2",
    "https://yts.am/api/v2",
    "https://yts.ag/api/v2",
    "https://yts.rs/api/v2",
    "https://yts.pm/api/v2",
    "https://yts.do/api/v2",
    "https://yts.run/api/v2",
    "https://yts-proxy.com/api/v2",
    "https://yifymovies.pro/api/v2",
    "https://yts.torrentbay.st/api/v2"
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class CineCLIService:
    """
    Abstractions for CineCLI functionality (YTS Search & Magnet Resolution).
    Re-implemented with httpx for better performance than subprocess calls.
    Robustness added with Mirror Fallback and increased Timeouts.
    """
    
    @staticmethod
    async def _fetch_with_fallback(endpoint: str, params: dict) -> Optional[dict]:
        """
        Tries to fetch from multiple YTS mirrors until one succeeds.
        """
        # Randomize mirrors to avoid hammering the same dead one first every time
        mirrors = list(YTS_MIRRORS)
        random.shuffle(mirrors)
        
        # Disable SSL verification to avoid handshake errors on mirrors
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=45.0, verify=False) as client:
            for base_url in mirrors:
                url = f"{base_url}{endpoint}"
                try:
                    # print(f"[CineCLI] Trying: {url}")
                    resp = await client.get(url, params=params)
                    
                    if resp.status_code == 200:
                        try:
                            # Some proxies return HTML on 404/500, check content type or parse
                            data = resp.json()
                            if data.get('status') == 'ok':
                                return data
                            else:
                                pass # print(f"[CineCLI] API status not ok: {data.get('status_message')}")
                        except Exception:
                            pass # print(f"[CineCLI] Failed to parse JSON from {base_url}")
                    else:    
                        pass # print(f"[CineCLI] Failed {url}: Status {resp.status_code}")
                        
                except httpx.ConnectTimeout:
                    pass # print(f"[CineCLI] Timeout connecting to {base_url}")
                except Exception as e:
                    pass # print(f"[CineCLI] Error connecting to {base_url}: {e}")
                
        print("[CineCLI] All mirrors failed.")
        return None

    @staticmethod
    async def search(query: str, limit: int = 20) -> List[dict]:
        """
        Search movies on YTS.
        """
        try:
            data = await CineCLIService._fetch_with_fallback(
                "/list_movies.json", 
                params={
                    "query_term": query,
                    "limit": limit,
                    "sort_by": "seeds", # Smart default: best health
                    "quality": "1080p"  # Preference
                }
            )
            
            if not data or not data.get('data', {}).get('movies'):
                return []
                
            movies = data['data']['movies']
            results = []
            for m in movies:
                results.append({
                    "id": str(m['id']),
                    "title": m['title_long'],
                    "year": m['year'],
                    "rating": m['rating'],
                    "poster_url": m['medium_cover_image'],
                    "torrents": m.get('torrents', []),
                    "type": "cinecli",  # Marker
                    "source": "cinecli"
                })
            return results
        except Exception as e:
            print(f"[CineCLI] Search failed: {e}")
            traceback.print_exc()
            return []

    @staticmethod
    async def get_details(movie_id: str) -> dict:
        """
        Get full details including magnet links.
        """
        try:
            data = await CineCLIService._fetch_with_fallback(
                "/movie_details.json",
                params={
                    "movie_id": movie_id,
                    "with_images": "true",
                    "with_cast": "true"
                }
            )
            
            if not data:
                return {}
                
            movie = data['data']['movie']
            
            # Construct magnet links
            torrents = []
            for t in movie.get('torrents', []):
                hash_val = t['hash']
                title_encoded = quote(movie['title'])
                magnet = f"magnet:?xt=urn:btih:{hash_val}&dn={title_encoded}&tr=udp://open.demonii.com:1337/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.coppersurfer.tk:6969"
                
                torrents.append({
                    "quality": t['quality'],
                    "type": t['type'],
                    "size": t['size'],
                    "seeds": t['seeds'],
                    "peers": t['peers'],
                    "hash": hash_val,
                    "url": t['url'],
                    "magnet": magnet
                })
            
            return {
                "id": str(movie['id']),
                "title": movie['title_long'],
                "year": movie['year'],
                "rating": movie['rating'],
                "runtime": movie['runtime'],
                "genres": movie.get('genres', []),
                "description": movie['description_full'],
                "poster_url": movie['large_cover_image'],
                "background_image": movie['background_image'],
                "torrents": torrents,
                "type": "cinecli"
            }

        except Exception as e:
            print(f"[CineCLI] Details failed: {e}")
            traceback.print_exc()
            return {}
