import httpx
from bs4 import BeautifulSoup
import urllib.parse
import re

class AniCliService:
    BASE_URL = "https://www.gogoanime.co.ba"
    # gogoanime.co.ba is the working domain (confirmed from user screenshot)
    
    @staticmethod
    async def search(query: str):
        """
        Searches for anime using GogoAnime.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{AniCliService.BASE_URL}/search.html?keyword={urllib.parse.quote(query)}"
                resp = await client.get(url, timeout=10.0)
                if resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                results = []
                
                # Parse search results
                items = soup.select('ul.items li')
                for item in items:
                    img = item.select_one('img')
                    link = item.select_one('p.name a')
                    release = item.select_one('p.released')
                    
                    if img and link:
                        results.append({
                            "id": link['href'].replace('/category/', ''),
                            "title": link['title'],
                            "poster": img['src'],
                            "year": release.text.strip().replace('Released: ', '') if release else "N/A",
                            "source": "anicli"
                        })
                return results
            except Exception as e:
                print(f"[AniCli] Search error: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    @staticmethod
    async def get_homepage():
        """
        Fetches recent/popular anime from GogoAnime homepage.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{AniCliService.BASE_URL}/"
                resp = await client.get(url, timeout=10.0)
                if resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                results = []
                
                # Parse homepage items (recent releases)
                items = soup.select('ul.items li')
                for item in items[:20]:
                    img = item.select_one('img')
                    link = item.select_one('p.name a')
                    release = item.select_one('p.released')
                    
                    if img and link:
                        results.append({
                            "id": link['href'].replace('/category/', ''),
                            "title": link['title'],
                            "poster": img['src'],
                            "year": release.text.strip().replace('Released: ', '') if release else "N/A",
                            "source": "anicli"
                        })
                return results
            except Exception as e:
                print(f"[AniCli] Homepage error: {e}")
                import traceback
                traceback.print_exc()
                return []

    @staticmethod
    async def get_details(anime_id: str):
        """
        Fetches details and episode list.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{AniCliService.GOGO_BASE}/category/{anime_id}"
                resp = await client.get(url, timeout=10.0)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Get ID for episode list AJAX
                movie_id_input = soup.select_one('#movie_id')
                if not movie_id_input:
                    return None
                    
                movie_id = movie_id_input['value']
                alias = soup.select_one('#alias_anime')['value']
                
                # Fetch Episodes
                ep_url = f"https://ajax.gogocdn.net/ajax/load-list-episode?ep_start=0&ep_end=9999&id={movie_id}&default_ep=0&alias={alias}"
                ep_resp = await client.get(ep_url, timeout=10.0)
                ep_soup = BeautifulSoup(ep_resp.text, 'html.parser')
                
                episodes = []
                for li in ep_soup.select('li'):
                    a = li.select_one('a')
                    if a:
                        ep_num = a.select_one('.name').text.replace('EP ', '')
                        episodes.append({
                            "number": ep_num,
                            "id": a['href'].strip(), # /naruto-episode-1
                            "title": f"Episode {ep_num}"
                        })
                
                # Reverse to show Ep 1 first (Gogo lists descending)
                episodes.reverse()
                
                return {
                    "id": anime_id,
                    "title": soup.select_one('.anime_info_body_bg h1').text.strip(),
                    "poster": soup.select_one('.anime_info_body_bg img')['src'],
                    "description": soup.select_one('.description').text.strip() if soup.select_one('.description') else "",
                    "episodes": episodes,
                    "source": "anicli"
                }

            except Exception as e:
                 print(f"[AniCli] Details error: {e}")
                 return None
                 
    @staticmethod
    async def get_stream_url(episode_path: str):
        """
        Extracts stream link for an episode.
        """
        async with httpx.AsyncClient() as client:
             try:
                url = f"{AniCliService.GOGO_BASE}{episode_path}"
                resp = await client.get(url, timeout=10.0)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find iframe
                iframe = soup.select_one('iframe')
                if iframe:
                    return iframe['src'] # The embed URL
                return None
             except Exception as e:
                 return None
