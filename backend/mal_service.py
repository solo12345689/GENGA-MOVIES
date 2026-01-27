import httpx
from typing import Optional

class MALService:
    """
    Service to fetch MyAnimeList IDs for anime titles.
    Uses Jikan API (unofficial MAL API) to search for anime.
    """
    
    BASE_URL = "https://api.jikan.moe/v4"
    
    @staticmethod
    async def search_mal_id(title: str) -> Optional[int]:
        """
        Search for an anime on MAL and return its MAL ID.
        
        Args:
            title: Anime title to search for
            
        Returns:
            MAL ID if found, None otherwise
        """
        try:
            # Clean title - remove language tags like [Hindi], [Dub], etc.
            clean_title = title
            for tag in ['[Hindi]', '[Urdu]', '[Tamil]', '[Telugu]', '[Dub]', '[Sub]']:
                clean_title = clean_title.replace(tag, '').strip()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search for anime
                url = f"{MALService.BASE_URL}/anime"
                params = {
                    "q": clean_title,
                    "limit": 5,
                    "type": "tv"  # Focus on TV series
                }
                
                resp = await client.get(url, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('data') and len(data['data']) > 0:
                        # Return the first (most relevant) result's MAL ID
                        return data['data'][0]['mal_id']
                
                return None
                
        except Exception as e:
            print(f"[MAL Service] Error searching for '{title}': {e}")
            return None
    
    @staticmethod
    async def get_anime_info(mal_id: int) -> Optional[dict]:
        """
        Get anime information from MAL.
        
        Args:
            mal_id: MyAnimeList ID
            
        Returns:
            Anime info dict or None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{MALService.BASE_URL}/anime/{mal_id}"
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('data')
                
                return None
                
        except Exception as e:
            print(f"[MAL Service] Error fetching info for MAL ID {mal_id}: {e}")
            return None
