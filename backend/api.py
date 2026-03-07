from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Response, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
from moviebox_api import Session, Search, SubjectType, MovieAuto, TVSeriesDetails, Homepage
from moviebox_api.download import (
    MediaFileDownloader, 
    DownloadableMovieFilesDetail, 
    DownloadableTVSeriesFilesDetail,
    resolve_media_file_to_be_downloaded
)
from moviebox_api.extractor._core import ItemJsonDetailsModel
from moviebox_api.extractor.models.json import SubjectModel, SubjectTrailerModel
from moviebox_api.models import SearchResultsItem
from cinecli_service import CineCLIService
from mal_service import MALService
from manga_service import MangaService
from music_service import MusicService
from novel_service import NovelService
from tv_service import TVService
from typing import Optional, Union, get_args, get_origin
import pydantic
import asyncio
import sys
import uuid
import json
import subprocess
import shutil
import httpx
import traceback
from urllib.parse import quote

# --- Monkeypatch for Pydantic Validation Error ---
def unwrap_annotation(annotation):
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        for arg in args:
            if isinstance(arg, type) and arg is not type(None):
                return arg
    return annotation

def patch_moviebox_models():
    try:
        # Patch SubjectModel directly since we imported it
        if hasattr(SubjectModel, 'model_fields') and 'trailer' in SubjectModel.model_fields:
            # Replace FieldInfo object to allow None
            from pydantic.fields import FieldInfo
            SubjectModel.model_fields['trailer'] = FieldInfo(annotation=Optional[Union[dict, SubjectTrailerModel]], default=None)
            
            if hasattr(SubjectModel, 'model_rebuild'):
                SubjectModel.model_rebuild(force=True)
            
            # Rebuild parents
            # We need to find ResDataModel to rebuild it
            if 'resData' in ItemJsonDetailsModel.model_fields:
                ResDataModel = unwrap_annotation(ItemJsonDetailsModel.model_fields['resData'].annotation)
                if hasattr(ResDataModel, 'model_rebuild'):
                    ResDataModel.model_rebuild(force=True)
            
            if hasattr(ItemJsonDetailsModel, 'model_rebuild'):
                ItemJsonDetailsModel.model_rebuild(force=True)
                
            print("Successfully patched SubjectModel.trailer and rebuilt models")
    except Exception as e:
        print(f"Failed to patch models: {e}")
        import traceback
        traceback.print_exc()

# Apply patch immediately
patch_moviebox_models()

router = APIRouter()

ANIME_API_BASE = "https://aniwatch-api-dotd.onrender.com/api/v2/hianime"

manga_service = MangaService()
music_service = MusicService()
novel_service = NovelService()
tv_service = TVService()

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://fmoviesunblocked.net/',
    'Origin': 'https://h5.aoneroom.com'
}

# Global session - initialized with custom headers to ensure consistency across library and player
session = Session(headers=DEFAULT_HEADERS)
_global_http_async_client = None

def get_http_client() -> httpx.AsyncClient:
    global _global_http_async_client
    if _global_http_async_client is None:
        _global_http_async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=500, max_keepalive_connections=50),
            headers=DEFAULT_HEADERS
        )
    return _global_http_async_client

# Simple in-memory cache: {uuid: item_object}
search_cache = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        except Exception:
            pass

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

def extract_numeric_id(ep_id: str) -> str:
    """
    Extracts the numeric episode ID from various HiAnime episode string formats.
    Megaplay REQUIRES the correct numeric episode ID to avoid 410 errors.
    """
    if not ep_id: return ""
    ep_id = str(ep_id).strip()
    
    if "ep=" in ep_id:
        return ep_id.split("ep=")[-1].split("&")[0]
    
    # Fallback: only if the string is purely numeric
    if ep_id.isdigit():
        return ep_id
        
    return ""  # Return empty if we cannot safely determine the numeric episode ID

def extract_seasons_from_title(title: str) -> List[dict]:
    """
    Extracts season information from titles like "Naruto [Hindi] S1-S2" or "Loki S2".
    Returns a list of season dictionaries.
    """
    import re
    seasons = []
    # Match S1, S2, S1-S2, Season 1, etc.
    # Pattern for ranges like S1-S2 or S01-S02
    range_match = re.search(r'[sS](?P<start>\d+)-(?:[sS])?(?P<end>\d+)', title)
    if range_match:
        try:
            start = int(range_match.group('start'))
            end = int(range_match.group('end'))
            # Safety check to avoid crazy ranges
            if 0 < start <= end < 100:
                for s in range(start, end + 1):
                    seasons.append({"season_number": s, "max_episodes": 0})
                return seasons
        except: pass

    # Pattern for single season like S2 or Season 2
    single_match = re.search(r'(?:[sS]eason\s+|[sS])(?P<num>\d+)', title)
    if single_match:
        try:
            s = int(single_match.group('num'))
            if 0 < s < 100:
                seasons.append({"season_number": s, "max_episodes": 0})
                return seasons
        except: pass
        
    return seasons

def srt_to_vtt(srt_content: str) -> str:
    """
    Robust SRT to WebVTT conversion.
    Handles potentially malformed SRT and ensures the WEBVTT header is present.
    """
    import re
    if not srt_content: return "WEBVTT\n\n"
    
    # If already VTT, just return
    if srt_content.lstrip().startswith("WEBVTT"):
        return srt_content

    # Replace comma in timestamps with dot
    # Matches: 00:00:00,000 --> 00:00:00,000
    vtt = re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', srt_content)
    
    # Ensure it starts with WEBVTT
    if not vtt.lstrip().startswith('WEBVTT'):
        vtt = "WEBVTT\n\n" + vtt.lstrip()
        
    return vtt

def get_source_headers(url: str, source: str = None) -> list[dict]:
    """
    Returns a LIST of dictionary headers to try.
    Provides fallbacks for 403 Forbidden scenarios by cycling through possible Referers.
    """
    base_headers = DEFAULT_HEADERS.copy()
    
    # 2. Exhaustive Referer Cycling
    url_lower = url.lower()
    is_moviebox_cdn = any(d in url_lower for d in ["haildrop", "moviebox", "fogtwist", "sunburst", "stormshade", "hakunaymatata", "bcdn"]) or "/_v7/" in url_lower or "/_v10/" in url_lower
    
    configs_refs = []
    
    # If it's MovieBox, prioritize using the exact headers currently in the session
    # as these are what were used to generate any signed URLs.
    if source == 'moviebox' or is_moviebox_cdn:
        session_headers = {}
        if hasattr(session, '_headers'):
            session_headers = session._headers
        elif hasattr(session, '_client') and hasattr(session._client, 'headers'):
            session_headers = dict(session._client.headers)
            
        if session_headers:
            # Create a priority config from session
            session_cfg = {k: v for k, v in session_headers.items() if k in ['Referer', 'Origin', 'User-Agent', 'Cookie']}
            if session_cfg:
                configs_refs.append(session_cfg)

    # 2. Add heuristics if session headers didn't cover it or for variety
    if source == 'hianime':
        configs_refs.append({'Referer': 'https://hianime.to/', 'Origin': 'https://hianime.to'})

    if "megaplay.buzz" in url_lower:
        configs_refs.append({'Referer': 'https://megaplay.buzz/', 'Origin': 'https://megaplay.buzz'})
        
    if "hianime" in url_lower or "aniwatch" in url_lower or "megacloud" in url_lower or "vidcloud" in url_lower or "rabbitstream" in url_lower:
        configs_refs.append({'Referer': 'https://hianime.to/', 'Origin': 'https://hianime.to'})
    
    # Standard MovieBox Fallbacks
    if is_moviebox_cdn or source == 'moviebox':
        configs_refs.append({'Referer': 'https://fmoviesunblocked.net/', 'Origin': 'https://h5.aoneroom.com'})
        configs_refs.append({'Referer': 'https://www.moviebox.net/', 'Origin': 'https://www.moviebox.net'})
        configs_refs.append({'Referer': 'https://www.moviebox.pro/', 'Origin': 'https://www.moviebox.pro'})
        configs_refs.append({'Referer': 'https://showbox.media/', 'Origin': 'https://showbox.media'})
        
        # Domain-as-referer strategy
        from urllib.parse import urlparse
        domain_parts = urlparse(url).netloc.split(".")
        if len(domain_parts) >= 2:
            domain = ".".join(domain_parts[-2:])
            configs_refs.append({'Referer': f'https://{domain}/', 'Origin': f'https://{domain}'})
            configs_refs.append({'Referer': f'https://www.{domain}/', 'Origin': f'https://www.{domain}'})
        
        # No-referer strategy
        configs_refs.append({}) 

        # Additional strategies for stubborn CDNs (Sunburst, Fogtwist, Stormshade, Lightning, active-storage)
        if any(k in url_lower for k in ["sunburst", "fogtwist", "stormshade", "lightning", "active-storage", "rainveil"]):
            configs_refs.append({'Referer': 'https://megacloud.blog/', 'Origin': 'https://megacloud.blog'})
            configs_refs.append({'Referer': 'https://megacloud.tv/', 'Origin': 'https://megacloud.tv'})
            configs_refs.append({'Referer': 'https://vidcloud.tv/', 'Origin': 'https://vidcloud.tv'})
            configs_refs.append({'Referer': 'https://megaup.net/', 'Origin': 'https://megaup.net'})
        
    # Priority B: Universal Candidates (deduplicated)
    candidates = [
        {'Referer': 'https://megaplay.buzz/', 'Origin': 'https://megaplay.buzz'},
        {'Referer': 'https://hianime.to/', 'Origin': 'https://hianime.to'},
        {'Referer': 'https://vidcloud9.me/', 'Origin': 'https://vidcloud9.me'},
        {'Referer': 'https://megacloud.to/', 'Origin': 'https://megacloud.to'},
        {'Referer': 'https://v.showbox.cc/', 'Origin': 'https://v.showbox.cc'},
        {'Referer': 'https://fmoviesunblocked.net/', 'Origin': 'h5.aoneroom.com'},
        {'Referer': 'https://www.moviebox.pro/', 'Origin': 'https://www.moviebox.pro'},
        {'Referer': 'https://videonext.net/', 'Origin': 'https://videonext.net'},
        {} # None
    ]
    
    # Ensure source-specific referers are at the VERY START
    final_refs = []
    # 1. Add source-specific ones first
    for ref in configs_refs:
        if ref not in final_refs:
            final_refs.append(ref)
            
    # 2. Add generic ones if not already there
    for cand in candidates:
        if cand not in final_refs:
            final_refs.append(cand)

    # Merge with base_headers to create final configurations
    final_configs = []
    for ref_dict in final_refs:
        cfg = base_headers.copy()
        cfg.pop('Referer', None)
        cfg.pop('Origin', None)
        cfg.update(ref_dict)
        final_configs.append(cfg)
        
    return final_configs

manager = ConnectionManager()

class SearchResultItem(BaseModel):
    id: str
    title: str
    year: Optional[str] = None
    poster_url: Optional[str] = None
    type: str

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Handles WebSocket connections for real-time download progress updates.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def determine_item_type(item: Any, content_type_filter: str = "all") -> str:
    """
    Determines the content type (movie, series, anime) of a search item.

    Args:
        item (Any): The search result item from moviebox_api.
        content_type_filter (str): The filter applied in the search (all, movie, series, anime).

    Returns:
        str: The normalized item type.
    """
    item_type = "movie"  # Default
    
    # 1. Check explicit subjectType from library model
    if hasattr(item, 'subjectType'):
        if item.subjectType == SubjectType.TV_SERIES:
            item_type = "series"
        elif item.subjectType == SubjectType.MOVIES:
            item_type = "movie"
    
    # 2. Refine based on frontend content_type filter
    filter_lower = content_type_filter.lower()
    if filter_lower == "anime":
        item_type = "anime"
    elif filter_lower == "series":
        item_type = "series"
    elif filter_lower == "movie":
        item_type = "movie"
    
    # 3. Fallback to attributes if still default or ambiguous
    if item_type == "movie" and getattr(item, 'is_tv_series', False):
        item_type = "series"
    
    # 4. Check category and genre for Anime/Series specific detection
    category = str(getattr(item, 'category', '')).lower()
    genres = [str(g).lower() for g in getattr(item, 'genre', [])] if hasattr(item, 'genre') else []
    title = str(getattr(item, 'title', '')).lower()
    
    # Check if it's anime based on title patterns (same logic as homepage)
    has_lang_tag = any(k in title for k in ['[hindi]', '[urdu]', '[tamil]', '[telugu]'])
    is_animation = 'anime' in category or 'anime' in title

    # Only label as anime if specifically filtered as anime or if it's a known anime source
    # For MovieBox, we prefer 'series' or 'movie' to use its native details logic
    if filter_lower == "anime":
        # Force anime type if filter is explicitly anime
        if (item_type == "series" or 
            'series' in category or 'tv' in category or 
            getattr(item, 'is_tv_series', False)):
            item_type = "anime"
        else:
            item_type = "anime_movie"
            
    # Intelligent Detection
    elif is_animation:
        # If it's explicitly animation, classify correctly
        if (item_type == "series" or 
            'series' in category or 'tv' in category or 
            getattr(item, 'is_tv_series', False)):
            item_type = "anime"
        else:
            # It's an animated movie, but call it 'movie' for UI consistency unless it's clearly anime
            item_type = "movie" if 'anime' not in category and 'anime' not in title else "anime_movie"
            
    elif has_lang_tag:
        # If it has [Hindi] etc tag:
        # - SERIES -> Likely Anime (e.g. Naruto [Hindi])
        # - MOVIE -> Likely Bollywood/Regional (e.g. Tashkent Files [Hindi]) -> Keep as MOVIE
        if (item_type == "series" or 
            'series' in category or 'tv' in category or 
            getattr(item, 'is_tv_series', False)):
            item_type = "anime"
        else:
            # It's a movie with [Hindi] tag - keep as 'movie' unless we know it's animation
            if is_animation:
                item_type = "anime_movie"
            else:
                item_type = "movie"
                
    elif 'series' in category or 'tv' in category:
        item_type = "series"
        
    return item_type

async def extract_item_poster(item: Any) -> Optional[str]:
    """
    Safely extracts a poster URL from a search result item, checking various field names.

    Args:
        item (Any): The search result item from moviebox_api.

    Returns:
        Optional[str]: The extracted URL or None.
    """
    poster_url = None
    
    # 1. Try 'cover' field (standard library model)
    if hasattr(item, 'cover') and item.cover:
        cover = item.cover
        if hasattr(cover, 'url'):
            poster_url = str(cover.url)
        elif isinstance(cover, str):
            poster_url = cover
            
    # 2. Fallback to other possible common field names
    if not poster_url:
        for field in ['boxCover', 'cover_url', 'poster_url', 'image_url', 'poster', 'image']:
            if hasattr(item, field):
                val = getattr(item, field)
                if val:
                    poster_url = str(val.url) if hasattr(val, 'url') else str(val)
                    break
                    
    return poster_url

@router.get("/search", response_model=dict)
async def search(query: str, page: int = 1, content_type: str = "all") -> dict:
    """
    Searches for content using moviebox-api.
    """
    try:
        subject_type = SubjectType.ALL
        if content_type.lower() == "movie":
            subject_type = SubjectType.MOVIES
        elif content_type.lower() == "series":
            subject_type = SubjectType.TV_SERIES
        elif content_type.lower() == "anime":
            # moviebox_api doesn't have ANIME type, so use TV_SERIES
            subject_type = SubjectType.TV_SERIES
            
        search_instance = Search(session=session, query=query, page=page, subject_type=subject_type)
        results_model = await search_instance.get_content_model()
        
        items = []
        if hasattr(results_model, 'items'):
            for item in results_model.items:
                item_id = str(uuid.uuid4())
                
                # Use async helper to determine type and poster
                item_type = await determine_item_type(item, content_type)
                poster_url = await extract_item_poster(item)
                
                # Cache the results
                search_cache[item_id] = {
                    "item": item,
                    "search_instance": search_instance,
                    "type": item_type
                }
                
                # Improved Year Extraction
                year = getattr(item, 'year', None)
                if not year:
                    year = getattr(item, 'release_date', None)
                if not year:
                    year = getattr(item, 'released', None)
                if not year:
                    year = getattr(item, 'premiered', None)
                
                # Format year if it's a full date string
                if year and isinstance(year, str) and len(year) >= 4:
                    year = year[:4]

                items.append({
                    "id": item_id,
                    "title": getattr(item, 'title', 'Unknown'),
                    "year": year,
                    "poster_url": poster_url,
                    "type": item_type
                })
        
        return {"results": items}
    except UnicodeDecodeError as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ENCODING ERROR IN SEARCH] {e}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Encoding error: {str(e)}")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[SEARCH ERROR] {e}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/novel/search")
async def search_novels(query: str = "", limit: int = 20):
    results = await novel_service.search_novels(query, limit)
    # novel_service.search_novels now returns a plain list
    return {"results": results if isinstance(results, list) else []}


@router.get("/novel/info")
async def get_novel_info(id: Optional[str] = None, url: Optional[str] = None):
    info = await novel_service.get_novel_info(novel_id=id, url=url)
    if not info:
        raise HTTPException(status_code=404, detail="Novel not found")
    return info

@router.get("/novel/chapter")
@router.get("/api/novel/chapter")
async def get_novel_chapter(id: str = None, url: str = None, format: str = "html"):
    content = await novel_service.get_chapter_content(id, url, format)

    if not content:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return content

# --- TV Endpoints ---
@router.get("/tv/countries")
async def get_tv_countries():
    countries = await tv_service.get_countries()
    return {"results": countries}

@router.get("/tv/country/{code}")
async def get_tv_channels_by_country(code: str):
    channels = await tv_service.get_channels_by_country(code)
    return {"results": channels}

@router.get("/tv/category/{category}")
async def get_tv_channels_by_category(category: str):
    channels = await tv_service.get_channels_by_category(category)
    return {"results": channels}

async def warmup_session() -> None:
    """
    Warms up the session by performing a lightweight dummy search.
    This helps reduce latency for the first user search.
    """
    print("Warming up session...")
    try:
        search_instance = Search(session=session, query="test")
        await search_instance.get_content_model()
        print("Session warmed up successfully.")
    except Exception as e:
        print(f"Warmup failed: {e}")

@router.get("/homepage")
async def get_homepage_content() -> dict:
    """
    Fetches trending and featured content for the homepage using the global session.
    """
    try:
        print("Fetching homepage via moviebox_api using global session...")
        # Use GLOBAL session
        homepage = Homepage(session=session)
        
        # Get raw content
        raw_response = await homepage.get_content()
        
        # Data is usually in 'data' key or root
        raw_data = raw_response.get('data', raw_response)
        
        results = []
        
        # Process operatingList (Main source for movies/banners)
        if 'operatingList' in raw_data and raw_data['operatingList']:
            for group in raw_data['operatingList']:
                group_title = group.get('title')
                if not group_title: continue
                
                items_source = []
                if 'subjects' in group and group['subjects']:
                    items_source = group['subjects']
                elif 'banner' in group and group.get('banner') and 'items' in group['banner']:
                    items_source = group['banner']['items']
                    if group_title == "Banner": group_title = "Featured"
                
                if not items_source: continue
                
                group_results = []
                for item in items_source:
                    try:
                        # Extract basic info
                        sid = item.get('subjectId') or item.get('id')
                        # For banners, id is often "0" but subjectId is valid
                        if sid == "0" and 'subjectId' in item:
                            sid = item['subjectId']
                            
                        # Extract poster
                        poster_url = ""
                        if 'cover' in item and isinstance(item['cover'], dict):
                            poster_url = item['cover'].get('url', '')
                        elif 'image' in item and isinstance(item['image'], dict):
                            poster_url = item['image'].get('url', '')
                            
                        # Extract Title
                        title = item.get('title', '')
                        
                        # Extract Year
                        date_str = item.get('releaseDate', '')
                        year = date_str[:4] if date_str else "N/A"
                        
                        # Extract Rating
                        rating = str(item.get('imdbRatingValue', 'N/A'))
                        
                        if sid and title and sid != "0":
                            # Store in search_cache for details fetching
                            # Homepage items don't have all fields required by SearchResultsItem
                            # So we cache them as dictionaries and handle them specially
                            
                            # Use the actual subjectType from API
                            # 1=MOVIES, 2=TV_SERIES, 3=ANIME (likely), 6=MUSIC
                            subject_type = item.get('subjectType', 1)  # Default to movie if missing
                            
                            # Determine content type
                            # STRICTER ANIME CHECK: Only if explicitly type 3 or has "anime" in text
                            # "Hindi" and "Urdu" checks were causing false positives for Indian movies.
                            normalized_title = title.lower()
                            is_anime = (subject_type == 3 or 
                                       'anime' in normalized_title or
                                       'myanimelist' in normalized_title)
                            
                            if is_anime:
                                it_type = "anime"
                            elif subject_type == 2:
                                it_type = "series"
                            else:
                                it_type = "movie"

                            
                            # Cache as a simple dictionary - we'll do a fresh search if details are needed
                            search_cache[str(sid)] = {
                                "item": {
                                    "id": str(sid),
                                    "title": title,
                                    "poster_url": poster_url,
                                    "year": year,
                                    "rating": rating,
                                    "type": it_type,
                                    "subjectType": subject_type,
                                    "detailPath": item.get('detailPath')
                                },
                                "search_instance": None,  # Will create on-demand
                                "type": it_type,
                                "is_homepage": True,
                                "needs_search": True  # Flag to trigger fresh search in details endpoint
                            }
                            
                            group_results.append({
                                "id": str(sid),
                                "title": title,
                                "year": year,
                                "type": it_type,
                                "poster_url": poster_url,
                                "rating": rating
                            })
                    except Exception as item_err:
                        print(f"Skipping malformed homepage item: {item_err}")
                        continue
                        
                if group_results:
                    results.append({
                        "title": group_title,
                        "items": group_results
                    })
                    
        print(f"Homepage fetch success. Returning {len(results)} groups.")
        return {"groups": results}

    except Exception as e:
        print(f"Error in /api/homepage: {e}")
        import traceback
        traceback.print_exc()
        return {"groups": [], "error": str(e)}

@router.get("/debug/search")
async def debug_search(query: str) -> dict:
    """
    Debug endpoint to inspect the raw structure of a search result item.
    """
    try:
        search_instance = Search(session=session, query=query)
        results_model = await search_instance.get_content_model()
        
        if hasattr(results_model, 'items') and results_model.items:
            item = results_model.items[0]
            item_dict = {attr: str(getattr(item, attr)) for attr in dir(item) 
                         if not attr.startswith('_') and not callable(getattr(item, attr))}
            return {"first_item_attributes": item_dict}
        return {"error": "No results"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/details/{item_id}")
async def details(item_id: str) -> dict:
    """
    Retrieves detailed information (plot, rating, seasons) for a specific item.
    """
    if item_id not in search_cache:
        raise HTTPException(status_code=404, detail="Item not found in cache. Please search again.")
    
    cached = search_cache[item_id]
    item = cached["item"]
    search_instance = cached["search_instance"]
    item_type = cached.get("type", "movie")
    
    try:
        # If this is a homepage item, we can often bypass the fresh search
        if cached.get("needs_search", False):
            print(f"[FAST-PATH] Bypassing search for homepage item: {getattr(item, 'title', 'Unknown')}")
            
            # Construct a mock search item that moviebox_api can accept
            class MockSearchItem(SearchResultsItem):
                def __init__(self, fields_dict, sid, stype):
                    # Use object.__setattr__ to bypass Pydantic's validation 
                    # while still being an instance of SearchResultsItem
                    object.__setattr__(self, 'id', sid)
                    object.__setattr__(self, 'subjectId', sid)
                    object.__setattr__(self, 'subjectType', stype)
                    
                    # detailPath is required for calculating page_url in moviebox_api.models
                    detail_path = "movie" if stype == 1 else "tv"
                    object.__setattr__(self, 'detailPath', detail_path)
                    
                    # Copy all other fields from original item
                    for k, v in fields_dict.items():
                        if not hasattr(self, k):
                            object.__setattr__(self, k, v)
            
            # Use original subjectType if available, fallback to normalized logic
            raw_stype = getattr(item, 'subjectType', None)
            if raw_stype == 1: subject_type = SubjectType.MOVIES
            elif raw_stype == 2: subject_type = SubjectType.TV_SERIES
            elif raw_stype == 3: subject_type = SubjectType.ALL # Anime
            else:
                # Fallback based on item_type
                if item_type == "anime": subject_type = SubjectType.ALL
                elif item_type == "series": subject_type = SubjectType.TV_SERIES
                else: subject_type = SubjectType.MOVIES
            
            # Use this mock item
            item_fields = cached.get("item", {})
            mock_detail_path = item_fields.get("detailPath")
            item = MockSearchItem(item_fields, item_fields['id'], raw_stype or (1 if subject_type == SubjectType.MOVIES else 2))
            # If we have a cached detailPath, set it explicitly to override the default "movie"/"tv" logic
            if mock_detail_path:
                object.__setattr__(item, 'detailPath', mock_detail_path)
            
            # We still need a search instance to call get_item_details
            # An empty query search instance is fine for details fetching
            from moviebox_api import Search
            search_instance = Search(session=session, query='', subject_type=subject_type)
            
            # Update cache so we don't do this again if refreshed
            search_cache[item_id]["item"] = item
            search_cache[item_id]["search_instance"] = search_instance
            search_cache[item_id]["needs_search"] = False
            print(f"[FAST-PATH] Mock item constructed successfully for {item_id}")

        
        # Use the search instance to get details for this item
        details_provider = search_instance.get_item_details(item)
        
        # PARALLELIZE: Fetch details and MAL ID at the same time
        tasks = [details_provider.get_content_model()]
        
        # Only add MAL search if it's an anime
        mal_task_idx = -1
        if item_type == "anime":
            title = getattr(item, 'title', '')
            tasks.append(MALService.search_mal_id(title))
            mal_task_idx = 1
            
        results_parallel = await asyncio.gather(*tasks, return_exceptions=True)
        
        details_model = results_parallel[0]
        if isinstance(details_model, Exception):
            print(f"[RETRY] First details fetch failed: {details_model}. Retrying...")
            details_model = await details_provider.get_content_model()
            
        mal_id = None
        if mal_task_idx != -1:
            mal_res = results_parallel[mal_task_idx]
            if not isinstance(mal_res, Exception):
                mal_id = mal_res
        
        # Extract IMDB rating if available
        imdb_rating = None
        imdb_rating_value = None
        
        # Try to get rating value from details_model first
        if hasattr(details_model, 'imdbRatingValue'):
            value = getattr(details_model, 'imdbRatingValue')
            if value:
                imdb_rating_value = float(value)
                imdb_rating = f"{value}/10"
                print(f"[DEBUG] Found rating in details_model.imdbRatingValue: {imdb_rating}")
        
        # Fallback: Try to get from resData
        if not imdb_rating_value and hasattr(details_model, 'resData'):
            resData = details_model.resData
            if hasattr(resData, 'imdbRatingValue'):
                value = getattr(resData, 'imdbRatingValue')
                if value:
                    imdb_rating_value = float(value)
                    imdb_rating = f"{value}/10"
                    print(f"[DEBUG] Found rating in resData.imdbRatingValue: {imdb_rating}")
        
        # Fallback: Try to get from the original search item
        if not imdb_rating_value and hasattr(item, 'imdbRatingValue'):
            value = getattr(item, 'imdbRatingValue')
            if value:
                imdb_rating_value = float(value)
                imdb_rating = f"{value}/10"
                print(f"[DEBUG] Found rating in item.imdbRatingValue: {imdb_rating}")
        
        print(f"[DEBUG] Final rating: {imdb_rating}, rating_value: {imdb_rating_value}")
        
        # Extract poster_url with extreme robustness
        poster_url = None
        
        # 1. Try common fields in details_model
        for field in ['cover', 'image', 'boxCover', 'poster', 'portrait']:
            if hasattr(details_model, field):
                val = getattr(details_model, field)
                if val and hasattr(val, 'url'):
                    poster_url = str(val.url)
                    break
                elif isinstance(val, str) and val.startswith('http'):
                    poster_url = val
                    break
        
        # 2. Try nested resData.resource.cover
        if not poster_url and hasattr(details_model, 'resData'):
            resData = details_model.resData
            if hasattr(resData, 'resource'):
                res = resData.resource
                if hasattr(res, 'cover') and res.cover and hasattr(res.cover, 'url'):
                    poster_url = str(res.cover.url)
                elif hasattr(res, 'image') and res.image and hasattr(res.image, 'url'):
                    poster_url = str(res.image.url)
        
        # 3. Fallback to cached item info (if available)
        if not poster_url:
            # Check cached library object or raw dict
            cached_item = cached.get("item")
            if cached_item:
                if isinstance(cached_item, dict):
                    poster_url = cached_item.get('poster_url') or cached_item.get('poster')
                    if not poster_url and 'cover' in cached_item and isinstance(cached_item['cover'], dict):
                        poster_url = cached_item['cover'].get('url')
                else:
                    # Library object
                    if hasattr(cached_item, 'cover') and cached_item.cover and hasattr(cached_item.cover, 'url'):
                        poster_url = str(cached_item.cover.url)
            
        # Final fallback to existing poster_url in cache (if any)
        if not poster_url:
            poster_url = getattr(item, 'poster_url', getattr(item, 'poster', None))
            
        response = {
            "id": item_id,
            "title": getattr(details_model, 'title', getattr(item, 'title', 'Unknown')),
            "year": getattr(details_model, 'year', getattr(item, 'year', None)),
            "plot": getattr(details_model, 'plot', getattr(details_model, 'description', None)),
            "rating": imdb_rating,
            "rating_value": imdb_rating_value,
            "poster_url": poster_url,
            "trailer": getattr(details_model, 'trailer', None),
            "category": getattr(details_model, 'category', getattr(item, 'category', None)),
            "type": item_type
        }
        
        # Extract seasons for MovieBox items (robust detection)
        seasons_data = []
        try:
            seasons_list = None
            # Path 1: details_model.resData.resource.seasons
            if hasattr(details_model, 'resData'):
                if hasattr(details_model.resData, 'resource') and hasattr(details_model.resData.resource, 'seasons'):
                    seasons_list = details_model.resData.resource.seasons
                elif hasattr(details_model.resData, 'seasons'):
                    seasons_list = details_model.resData.seasons
            # Path 2: details_model.resource.seasons
            elif hasattr(details_model, 'resource') and hasattr(details_model.resource, 'seasons'):
                seasons_list = details_model.resource.seasons
            # Path 3: details_model.seasons
            elif hasattr(details_model, 'seasons'):
                seasons_list = details_model.seasons
            # Path 4: details_model.item.seasons
            elif hasattr(details_model, 'item') and hasattr(details_model.item, 'seasons'):
                seasons_list = details_model.item.seasons
            # Path 5: data.seasons
            elif hasattr(details_model, 'data'):
                data_obj = details_model.data
                if hasattr(data_obj, 'seasons'):
                    seasons_list = data_obj.seasons

            if seasons_list:
                for season in seasons_list:
                    if isinstance(season, dict):
                        s_num = season.get('se', season.get('number', season.get('season_number', 0)))
                        m_ep = season.get('maxEp', season.get('max_episodes', season.get('episode_count', season.get('episodeCount', 0))))
                    else:
                        s_num = getattr(season, 'se', getattr(season, 'number', getattr(season, 'season_number', 0)))
                        m_ep = getattr(season, 'maxEp', getattr(season, 'max_episodes', getattr(season, 'episode_count', getattr(season, 'episodeCount', 0))))
                    
                    if s_num is not None:
                        seasons_data.append({
                            "season_number": int(s_num),
                            "max_episodes": int(m_ep) if m_ep else 0,
                        })

            if seasons_data:
                # Filter out dummy Season 0 if it's the only one and has 0 or 1 episode (likely a MovieBox movie container)
                is_standalone_movie = len(seasons_data) == 1 and seasons_data[0]["season_number"] == 0 and seasons_data[0]["max_episodes"] <= 1
                
                if not is_standalone_movie:
                    response["seasons"] = seasons_data
                    # If we found real seasons, it MUST be a series or anime
                    if item_type == "movie":
                        response["type"] = "series"
                        item_type = "series"
                    print(f"[INFO] Returning {len(seasons_data)} seasons for {item_type}: {response.get('title', 'Unknown')}")
                else:
                    print(f"[INFO] Ignoring standalone dummy season for movie: {response.get('title', 'Unknown')}")
            
            # FALLBACK: If API returned no seasons but title has season info (e.g. "S1-S2")
            if not seasons_data:
                title_for_extract = getattr(details_model, 'title', getattr(item, 'title', ''))
                seasons_data = extract_seasons_from_title(title_for_extract)
                if seasons_data:
                    response["seasons"] = seasons_data
                    if item_type == "movie":
                        response["type"] = "series"
                        item_type = "series"
                    print(f"[INFO] Extracted {len(seasons_data)} seasons from title: {title_for_extract}")

            # FINAL FALLBACK: If it's a series type but still no seasons, assume Season 1
            if not seasons_data and (item_type == "series" or item_type == "anime"):
                seasons_data = [{"season_number": 1, "max_episodes": 0}]
                response["seasons"] = seasons_data
                print(f"[INFO] Fallback to Season 1 for series/anime: {response.get('title', 'Unknown')}")
        except Exception as e:
            print(f"Error extracting seasons: {e}")
            traceback.print_exc()
        
        # Add pre-fetched MAL ID if available
        if item_type == "anime" and mal_id:
            response["mal_id"] = mal_id
            print(f"[INFO] Using pre-fetched MAL ID {mal_id}")
        elif item_type == "anime":
            # Fallback (shouldn't happen often with parallel catch)
            try:
                title = response.get('title', '')
                mal_id = await MALService.search_mal_id(title)
                if mal_id:
                    response["mal_id"] = mal_id
            except: pass
            
        return response
    except Exception as e:
        print(f"Details extraction failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def download_task(
    item_id: Optional[str] = None, 
    query: Optional[str] = None, 
    season: Optional[int] = None, 
    episode: Optional[int] = None
) -> None:
    """
    Background task to handle media file downloads with real-time progress reporting.
    """
    try:
        # 1. Resolve item
        item = None
        search_instance = None
        
        if item_id and item_id in search_cache:
            # Use cached item
            cached = search_cache[item_id]
            item = cached["item"]
            search_instance = cached["search_instance"]
            print(f"[DOWNLOAD] Using cached item: {getattr(item, 'title', 'Unknown')}")
        elif query:
            # Fallback: Search for the item
            await manager.broadcast({"status": "searching", "message": f"Searching for {query}..."})
            
            subject_type = SubjectType.TV_SERIES if season is not None else SubjectType.ALL
            search_instance = Search(session=session, query=query, subject_type=subject_type)
            results = await search_instance.get_content_model()
            
            if not results.items:
                await manager.broadcast({"status": "error", "message": "No results found"})
                return
            
            item = results.items[0]
            print(f"[DOWNLOAD] Using search result: {getattr(item, 'title', 'Unknown')}")
        else:
            await manager.broadcast({"status": "error", "message": "No item ID or query provided"})
            return
        
        # 2. Get Files
        await manager.broadcast({"status": "resolving", "message": "Resolving files..."})
        
        media_file = None
        if season is not None and episode is not None:
             # TV Series
             files_provider = DownloadableTVSeriesFilesDetail(session=session, item=item)
             files_metadata = await files_provider.get_content_model(season=season, episode=episode)
             media_file = resolve_media_file_to_be_downloaded("BEST", files_metadata)
        else:
             # Movie
             files_provider = DownloadableMovieFilesDetail(session=session, item=item)
             files_metadata = await files_provider.get_content_model()
             media_file = resolve_media_file_to_be_downloaded("BEST", files_metadata)
        
        # 4. Download
        downloader = MediaFileDownloader()
        
        def progress_hook(progress: Any) -> None:
            """
            Hook called by the downloader to report progress to clients via WebSockets.
            """
            try:
                data = progress if isinstance(progress, dict) else str(progress)
                # Safely schedule the broadcast in the running event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(manager.broadcast({"status": "downloading", "progress": data}))
            except Exception as e:
                print(f"Progress reporting error: {e}")

        await manager.broadcast({"status": "started", "message": f"Starting download: {getattr(item, 'title', 'Unknown')}"})
        
        if season is not None and episode is not None:
            await downloader.run(
                media_file=media_file, 
                filename=item, 
                progress_hook=progress_hook,
                season=season,
                episode=episode
            )
        else:
            await downloader.run(media_file=media_file, filename=item, progress_hook=progress_hook)
            
        await manager.broadcast({"status": "completed", "message": "Download complete!"})

    except Exception as e:
        print(f"Download task failed: {e}")
        await manager.broadcast({"status": "error", "message": f"Download failed: {str(e)}"})

@router.post("/download")
async def download(
    id: Optional[str] = None, 
    query: Optional[str] = None, 
    season: Optional[int] = None, 
    episode: Optional[int] = None
) -> dict:
    """
    Endpoint to initiate a content download. Runs as a background task.
    """
    asyncio.create_task(download_task(id, query, season, episode))
    return {"status": "started", "message": "Download task initiated"}

@router.post("/stream")
async def stream(
    query: str, 
    id: Optional[str] = None, 
    content_type: str = "all", 
    season: Optional[int] = None, 
    episode: Optional[int] = None, 
    mode: str = "play"
) -> dict:
    """
    Endpoint to stream content either by launching MPV locally or returning a proxy URL.
    """
    try:
        # 1. Try to use cached item first (avoids re-search and ID mismatch)
        target_item = None
        search_instance = None
        max_retries = 2
        
        if id and id in search_cache:
            # Use cached item directly
            cached = search_cache[id]
            target_item = cached["item"]
            search_instance = cached["search_instance"]
            print(f"[STREAM] Using cached item: {getattr(target_item, 'title', target_item.get('title', 'Unknown') if isinstance(target_item, dict) else 'Unknown')}")
            
            # If this is a homepage item, we need to do a fresh search first
            if cached.get("needs_search", False):

                # Use appropriate SubjectType based on content type
                if cached.get("type") == "anime":
                    subject_type = SubjectType.ALL  # Use ALL for anime
                elif cached.get("type") == "series":
                    subject_type = SubjectType.TV_SERIES
                else:
                    subject_type = SubjectType.MOVIES
                search_instance = Search(session=session, query=target_item['title'], subject_type=subject_type)
                results = await search_instance.get_content_model()
                
                if not results.items:
                    raise HTTPException(status_code=404, detail="Content not found via search")
                
                # Find the matching item by ID (don't just take first result)
                original_id = target_item['id']
                matched_item = None
                for search_item in results.items:
                    if str(getattr(search_item, 'id', '')) == str(original_id) or str(getattr(search_item, 'subjectId', '')) == str(original_id):
                        matched_item = search_item

                        break
                
                # If no ID match, fall back to first result (but log warning)
                if not matched_item:
                    matched_item = results.items[0]
                
                target_item = matched_item
                
                # Update cache with proper SearchResultsItem
                search_cache[id]["item"] = target_item
                search_cache[id]["search_instance"] = search_instance
                search_cache[id]["needs_search"] = False

        else:
            # 2. Fallback: Search for the item with retries for network resilience
            subject_type = SubjectType.ALL
            if content_type.lower() == "movie" or content_type.lower() == "anime_movie":
                subject_type = SubjectType.MOVIES
            elif content_type.lower() in ["series", "anime"]:
                subject_type = SubjectType.TV_SERIES

            for attempt in range(max_retries + 1):
                try:
                    search_instance = Search(session=session, query=query, subject_type=subject_type)
                    results = await search_instance.get_content_model()
                    
                    if not results.items:
                        if attempt < max_retries:
                            print(f"[STREAM] Search attempt {attempt + 1} yielded no results. Retrying...")
                            await asyncio.sleep(1)
                            continue
                        raise HTTPException(status_code=404, detail="Content not found")
                        
                    target_item = results.items[0]
                    print(f"[STREAM] Using search result: {getattr(target_item, 'title', 'Unknown')}")
                    break
                except Exception as e:
                    if attempt < max_retries:
                        print(f"[STREAM] Search attempt {attempt + 1} failed: {e}. Retrying...")
                        await asyncio.sleep(1)
                        continue
                    raise e

            
        # 4. Resolve Media File with encoding error handling
        media_file = None
        quality_options = ["BEST", "WORST", "720P", "480P", "360P"]
        
        for quality in quality_options:
            try:
                # Add retries for media file resolving as well
                for res_attempt in range(max_retries + 1):
                    try:
                        if season is not None and episode is not None:
                            # TV Series / Anime
                            files_provider = DownloadableTVSeriesFilesDetail(session=session, item=target_item)
                            files_metadata = await files_provider.get_content_model(season=season, episode=episode)
                            media_file = resolve_media_file_to_be_downloaded(quality, files_metadata)
                        else:
                            # Movie
                            files_provider = DownloadableMovieFilesDetail(session=session, item=target_item)
                            files_metadata = await files_provider.get_content_model()
                            media_file = resolve_media_file_to_be_downloaded(quality, files_metadata)
                        
                        if media_file and media_file.url:
                            print(f"[SUCCESS] Resolved media file with quality: {quality}")
                            break
                    except Exception as res_err:
                        if res_attempt < max_retries:
                            print(f"[STREAM] Resolution attempt {res_attempt + 1} for {quality} failed: {res_err}. Retrying...")
                            await asyncio.sleep(1)
                            continue
                        raise res_err
                
                if media_file and media_file.url:
                    break

                    
            except UnicodeDecodeError as e:
                print(f"[ENCODING ERROR] Quality {quality} failed with encoding error: {e}")
                # Try next quality option
                continue
            except Exception as e:
                print(f"[ERROR] Quality {quality} failed: {e}")
                # Try next quality option
                continue
             
        if not media_file or not media_file.url:
            raise HTTPException(status_code=404, detail="Playable stream URL not found")

        # Return URL if mode is 'url'
        if mode == "url":
            # Return a proxy URL that routes through our backend
            # This bypasses 403 Forbidden errors from streaming providers
            proxy_url = f"/api/proxy-stream?url={quote(str(media_file.url))}"
            
            # Extract subtitles
            subtitles = []
            if 'files_metadata' in locals() and hasattr(files_metadata, 'captions'):
                for caption in files_metadata.captions:
                    # Proxy the subtitle URL to avoid CORS/Forbidden issues
                    proxied_sub_url = f"/api/proxy-stream?url={quote(str(caption.url))}&source=moviebox"
                    subtitles.append({
                        "lang": caption.lanName,
                        "language": caption.lan,
                        "url": proxied_sub_url
                    })
            
            return {
                "status": "success", 
                "url": proxy_url, 
                "title": target_item.title, 
                "type": content_type if content_type != "all" else ("series" if getattr(target_item, 'subject_type', 1) == 2 else "movie"),
                "direct_url": str(media_file.url),
                "subtitles": subtitles
            }

        # 5. Launch MPV
        mpv_path = shutil.which("mpv")
        if not mpv_path:
            raise HTTPException(status_code=500, detail="mpv player not found. Please install mpv to stream.")
            
        # Extract headers from session
        headers = {}
        if hasattr(session, '_headers'):
            headers.update(session._headers)
        if hasattr(session, '_client') and hasattr(session._client, 'headers'):
            headers.update(session._client.headers)
            
        # Construct mpv command
        cmd = [mpv_path, str(media_file.url), f"--title={target_item.title}", "--no-ytdl"]
        
        # Get hardened headers for this specific URL
        mpv_headers = get_source_headers(str(media_file.url))[0]
        
        # Add User-Agent explicitly
        if 'User-Agent' in mpv_headers:
            cmd.append(f"--user-agent={mpv_headers['User-Agent']}")
            
        # Add Referer explicitly
        if 'Referer' in mpv_headers:
            cmd.append(f"--referrer={mpv_headers['Referer']}")

        # Build other header fields
        header_fields = []
        for key, value in mpv_headers.items():
            if key not in ['User-Agent', 'Referer', 'Cookie', 'cookie']:
                header_fields.append(f"{key}: {value}")
                
        # Handle Cookies
        cookie_str = mpv_headers.get('Cookie') or mpv_headers.get('cookie')
        if not cookie_str:
            if hasattr(session, 'cookies') and session.cookies:
                 cookie_str = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
            elif hasattr(session, '_client') and hasattr(session._client, 'cookies') and session._client.cookies:
                 cookie_str = "; ".join([f"{k}={v}" for k, v in session._client.cookies.items()])

        if cookie_str:
            header_fields.append(f"Cookie: {cookie_str}")

        # Pass all collected headers to mpv
        for field in header_fields:
            cmd.append(f"--http-header-fields={field}")

        # Auto-confirm selection if moviebox CLI prompts (though we are calling mpv directly now)
        # But wait, this code launches MPV directly. Good.

        print(f"Launching mpv: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        
        return {"status": "success", "message": "Streaming started locally"}
    except Exception as e:
        print(f"Streaming error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/moviebox/download")
async def moviebox_download(
    query: str, 
    id: Optional[str] = None, 
    content_type: str = "all", 
    season: Optional[int] = None, 
    episode: Optional[int] = None
):
    """
    Direct video download for MovieBox items. 
    Resolves the best stream and proxies it as an attachment.
    """
    try:
        # 1. Resolve item (Reusing logic similar to /stream)
        target_item = None
        search_instance = None
        
        if id and id in search_cache:
            cached = search_cache[id]
            target_item = cached["item"]
            search_instance = cached["search_instance"]
            
            if cached.get("needs_search", False):
                if cached.get("type") == "anime":
                    subject_type = SubjectType.ALL
                elif cached.get("type") == "series":
                    subject_type = SubjectType.TV_SERIES
                else:
                    subject_type = SubjectType.MOVIES
                search_instance = Search(session=session, query=target_item['title'], subject_type=subject_type)
                results = await search_instance.get_content_model()
                if results.items:
                    original_id = target_item['id']
                    matched_item = None
                    for search_item in results.items:
                        if str(getattr(search_item, 'id', '')) == str(original_id) or str(getattr(search_item, 'subjectId', '')) == str(original_id):
                            matched_item = search_item
                            break
                    target_item = matched_item or results.items[0]
                    search_cache[id]["item"] = target_item
                    search_cache[id]["search_instance"] = search_instance
                    search_cache[id]["needs_search"] = False
        else:
            subject_type = SubjectType.ALL
            if content_type.lower() in ["movie", "anime_movie"]:
                subject_type = SubjectType.MOVIES
            elif content_type.lower() in ["series", "anime"]:
                subject_type = SubjectType.TV_SERIES
            search_instance = Search(session=session, query=query, subject_type=subject_type)
            results = await search_instance.get_content_model()
            if not results.items:
                raise HTTPException(status_code=404, detail="Content not found")
            target_item = results.items[0]

        # 2. Resolve Media File (Best Quality)
        media_file = None
        quality_options = ["BEST", "720P", "480P", "360P"]
        
        for quality in quality_options:
            try:
                if season is not None and episode is not None:
                    files_provider = DownloadableTVSeriesFilesDetail(session=session, item=target_item)
                    files_metadata = await files_provider.get_content_model(season=season, episode=episode)
                else:
                    files_provider = DownloadableMovieFilesDetail(session=session, item=target_item)
                    files_metadata = await files_provider.get_content_model()
                
                media_file = resolve_media_file_to_be_downloaded(quality, files_metadata)
                if media_file and media_file.url:
                    break
            except:
                continue
                
        if not media_file or not media_file.url:
            raise HTTPException(status_code=404, detail="Downloadable stream URL not found")

        # 3. Proxy the download
        filename = f"{getattr(target_item, 'title', 'video')}.mp4"
        if season is not None and episode is not None:
            filename = f"{getattr(target_item, 'title', 'video')} S{season}E{episode}.mp4"
        
        # Sanitize filename
        filename = filename.replace("/", "_").replace("\\", "_")
        
        # We reuse get_source_headers to get correct credentials for the CDN
        candidates = get_source_headers(str(media_file.url), "moviebox")
        headers = candidates[0]
        
        # We MUST NOT use 'async with' because StreamingResponse needs the client open!
        client = httpx.AsyncClient(verify=False, follow_redirects=True, timeout=60.0)
        req = client.build_request("GET", str(media_file.url), headers=headers)
        resp = await client.send(req, stream=True, follow_redirects=True)
        
        if resp.status_code >= 400:
            await resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=resp.status_code, detail=f"CDN returned {resp.status_code}")

        res_headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": resp.headers.get("Content-Type", "video/mp4"),
            "Access-Control-Allow-Origin": "*"
        }
        if "Content-Length" in resp.headers:
            res_headers["Content-Length"] = resp.headers["Content-Length"]

        from starlette.background import BackgroundTask
        async def cleanup():
            await resp.aclose()
            await client.aclose()

        return StreamingResponse(
            resp.aiter_raw(),
            status_code=resp.status_code,
            headers=res_headers,
            background=BackgroundTask(cleanup)
        )

    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy-stream")
async def proxy_stream(request: Request, url: str, source: str = None):
    """
    Proxies a stream URL through the backend in a single pass.
    Bypasses 403s and supports range requests via browser headers.
    """
    # Cycle through headers until success
    candidates = get_source_headers(url, source)
    
    # Forward Range from browser
    client_range = request.headers.get('range')
    
    # User Request: Fix Format Error (Client closing too early)
    # We must NOT use 'async with' because StreamingResponse needs the client open!
    client = httpx.AsyncClient(verify=False, follow_redirects=True)
    
    try:
        last_error = None
        for headers in candidates:
            if client_range:
                headers['Range'] = client_range

            try:
                # Check if this is an HLS request
                is_m3u8 = url.split("?")[0].endswith(".m3u8")
                
                if is_m3u8:
                    # For playlists, we download and REWRITE absolute URLs to proxy through US
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                    if resp.status_code != 200:
                        last_error = f"Source returned {resp.status_code}"
                        continue
                    
                    content = resp.text
                    base_url = str(resp.url).rsplit('/', 1)[0]
                    lines = content.splitlines()
                    new_lines = []
                    
                    proxy_base = f"{request.url.scheme}://{request.url.netloc}/api/proxy-stream"
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            new_lines.append(line)
                            continue
                        
                        if line.startswith("#"):
                            if "URI=" in line:
                                import re
                                def wrap_uri(match):
                                    uri = match.group(2)
                                    if not uri.startswith("http"):
                                        uri = f"{base_url}/{uri}"
                                    return f'{match.group(1)}="{proxy_base}?url={quote(uri)}&source={source or ""}"'
                                line = re.sub(r'(URI)=["\']([^"\']+)["\']', wrap_uri, line)
                            new_lines.append(line)
                        else:
                            target_url = line
                            if not target_url.startswith("http"):
                                target_url = f"{base_url}/{target_url}"
                            proxied_url = f"{proxy_base}?url={quote(target_url)}&source={source or ''}"
                            new_lines.append(proxied_url)
                    
                    rewritten_content = "\n".join(new_lines)
                    
                    # Close client since we are done
                    await client.aclose()
                    
                    return Response(
                        content=rewritten_content,
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "X-Proxy-Status": "Rewritten-M3U8"
                        }
                    )

                # Not M3U8 -> Standard Proxy
                is_srt = ".srt" in url.lower()
                if is_srt:
                    # Use regular GET for subtitles (more robust for CloudFront)
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                else:
                    req = client.build_request("GET", url, headers=headers)
                    resp = await client.send(req, stream=True, follow_redirects=True)
                
                if resp.status_code >= 400:
                    await resp.aclose()
                    last_error = f"Source returned {resp.status_code}"
                    continue
                
                # Success!
                
                # Intercept SRT for conversion to VTT (Browsers don't support SRT natively in tracks)
                is_srt = ".srt" in url.lower() or "application/x-subrip" in resp.headers.get("Content-Type", "").lower()
                
                if is_srt:
                    try:
                        print(f"[SUBTITLE] Processing {url[:100]}")
                        content = await resp.aread()
                        try:
                            text = content.decode('utf-8')
                        except:
                            text = content.decode('latin-1', errors='replace')
                        
                        vtt_text = srt_to_vtt(text)
                        await resp.aclose()
                        await client.aclose()
                        
                        print(f"[SUBTITLE] Successfully converted {url[:50]} to VTT")
                        return Response(
                            content=vtt_text,
                            media_type="text/vtt",
                            headers={
                                "Access-Control-Allow-Origin": "*",
                                "X-Proxy-Status": "Converted-SRT-to-VTT"
                            }
                        )
                    except Exception as sub_e:
                        print(f"[SUBTITLE ERROR] Conversion failed: {sub_e}")
                        traceback.print_exc()
                        # Fallback: if conversion fails, return raw if possible or raise
                        raise HTTPException(status_code=500, detail=f"Subtitle conversion error: {str(sub_e)}")
                
                excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive", "content-disposition"]
                res_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
                res_headers.update({
                    "Access-Control-Allow-Origin": "*",
                    "Connection": "keep-alive",
                    "X-Proxy-Status": "One-Shot"
                })
                if "Content-Length" in resp.headers:
                    res_headers["Content-Length"] = resp.headers["Content-Length"]

                from starlette.background import BackgroundTask
                
                async def cleanup():
                    await resp.aclose()
                    await client.aclose()

                return StreamingResponse(
                    resp.aiter_raw(),
                    status_code=resp.status_code,
                    headers=res_headers,
                    background=BackgroundTask(cleanup)
                )

            except Exception as e:
                print(f"[PROXY ATTEMPT FAILED] {e} for {url[:50]}")
                last_error = str(e)
                continue
                
        # If we exit loop without returning
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Proxy failed: {last_error or 'Unknown error'}")

    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes (avoid 500)
        raise
    except Exception as e:
        # Fallback closure for actual crashes
        if 'client' in locals():
            try: await client.aclose()
            except: pass
        print(f"[PROXY FATAL] {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# --- HiAnime Section ---

@router.get("/anime/home")
async def get_anime_home():
    try:
        url = f"{ANIME_API_BASE}/home"
        print(f"[HiAnime] Requesting Home: {url}")
        client = get_http_client()
        response = await client.get(url, timeout=30.0)
        if response.status_code != 200:
            print(f"[HiAnime] Home API error {response.status_code}: {response.text[:200]}")
            raise HTTPException(status_code=response.status_code, detail=f"Upstream error: {response.status_code}")
        
        try:
            data = response.json()
            normalized_groups = []
            if data.get('status') == 200 and data.get('data'):
                d = data['data']
                if d.get('spotlightAnimes'):
                    normalized_groups.append({
                        "title": "Spotlight",
                        "items": [{
                            "id": a.get('id'),
                            "title": a.get('name'),
                            "poster_url": a.get('poster'),
                            "year": a.get('type') or "Anime",
                            "type": "anime",
                            "source": "hianime"
                        } for a in d['spotlightAnimes']]
                    })
                if d.get('trendingAnimes'):
                    normalized_groups.append({
                        "title": "Trending",
                        "items": [{
                            "id": a.get('id'),
                            "title": a.get('name'),
                            "poster_url": a.get('poster'),
                            "year": a.get('type') or "Anime",
                            "type": "anime",
                            "source": "hianime"
                        } for a in d['trendingAnimes']]
                    })
                if d.get('latestEpisodeAnimes'):
                    normalized_groups.append({
                        "title": "Latest Episodes",
                        "items": [{
                            "id": a.get('id'),
                            "title": a.get('name'),
                            "poster_url": a.get('poster'),
                            "year": a.get('type') or "Anime",
                            "type": "anime",
                            "source": "hianime"
                        } for a in d['latestEpisodeAnimes']]
                    })
                if d.get('topUpcomingAnimes'):
                    normalized_groups.append({
                        "title": "Upcoming",
                        "items": [{
                            "id": a.get('id'),
                            "title": a.get('name'),
                            "poster_url": a.get('poster'),
                            "year": a.get('type') or "Anime",
                            "type": "anime",
                            "source": "hianime"
                        } for a in d['topUpcomingAnimes']]
                    })
            return normalized_groups
        except Exception as json_err:
            print(f"[HiAnime] Home JSON Parse error: {json_err} | Body: {response.text[:500]}")
            raise HTTPException(status_code=500, detail="Malformed upstream response")
    except Exception as e:
        print(f"HiAnime Home fatal error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/search")
async def search_anime(query: str, page: int = 1):
    try:
        url = f"{ANIME_API_BASE}/search?q={quote(query)}&page={page}"
        print(f"[HiAnime] Searching: {url}")
        client = get_http_client()
        response = await client.get(url, timeout=30.0)
        if response.status_code != 200:
            print(f"[HiAnime] Search API error {response.status_code}: {response.text[:200]}")
            raise HTTPException(status_code=response.status_code, detail=f"Upstream error: {response.status_code}")
        
        try:
            data = response.json()
            # Normalize to flat list for frontend
            results = []
            if data.get('status') == 200 and data.get('data'):
                animes = data['data'].get('animes', [])
                for a in animes:
                    results.append({
                        "id": a.get('id'),
                        "title": a.get('name'),
                        "poster_url": a.get('poster'),
                        "year": a.get('type') or "Anime",
                        "type": "anime",
                        "source": "hianime"
                    })
            return results
        except Exception as json_err:
            print(f"[HiAnime] Search JSON Parse error: {json_err} | Body: {response.text[:500]}")
            raise HTTPException(status_code=500, detail="Malformed upstream response")
    except Exception as e:
        print(f"HiAnime Search fatal error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/details/{anime_id}")
async def get_anime_details(anime_id: str):
    try:
        about_url = f"{ANIME_API_BASE}/anime/{anime_id}"
        client = get_http_client()
        about_res = await client.get(about_url, timeout=30.0)
        
        if about_res.status_code != 200:
            print(f"[HiAnime] Details API error {about_res.status_code} for {anime_id}")
            return {"error": f"API returned {about_res.status_code}", "status": about_res.status_code, "id": anime_id}

        try:
            about_data = about_res.json()
        except Exception as e:
            print(f"[HiAnime] JSON error for {anime_id}: {e}")
            return {"error": "Invalid JSON from API", "status": 500, "id": anime_id}
        
        if about_data.get("status") == 200 and "data" in about_data:
            anime = about_data["data"]["anime"]
            info = anime.get("info", {})
            more_info = anime.get("moreInfo", {})
            
            return {
                "id": anime_id,
                "title": info.get("name", "Unknown"),
                "plot": info.get("description", ""),
                "poster_url": info.get("poster", ""),
                "rating": more_info.get("status", "N/A"),
                "rating_value": float(anime.get("stats", {}).get("rating", 0)) if anime.get("stats", {}).get("rating") else 0,
                "year": more_info.get("aired", "N/A"),
                "type": "anime",
                "episodes_data": about_data["data"].get("seasons") or []
            }
        
        return {"error": "Failed to fetch anime details", "status": about_data.get("status"), "id": anime_id}
    except Exception as e:
        print(f"HiAnime Details error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/episodes/{anime_id}")
async def get_anime_episodes(anime_id: str):
    try:
        url = f"{ANIME_API_BASE}/anime/{anime_id}/episodes"
        client = get_http_client()
        response = await client.get(url, timeout=30.0)
        return response.json()
    except Exception as e:
        print(f"HiAnime Episodes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/servers")
async def get_anime_servers(episode_id: str):
    try:
        url = f"{ANIME_API_BASE}/episode/servers?animeEpisodeId={quote(episode_id)}"
        client = get_http_client()
        response = await client.get(url, timeout=30.0)
        return response.json()
    except Exception as e:
        print(f"HiAnime Servers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/iframe-proxy")
async def iframe_proxy(url: str):
    """
    Serves a minimal HTML page containing the target iframe.
    Includes AGGRESSIVE ad-blocking to prevent ALL redirects.
    """
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Video Player</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: black; overflow: hidden; }}
        .iframe-container {{ width: 100%; height: 100%; position: relative; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        /* Hide any ad overlays */
        .ad, .ads, .advert, .advertisement, .popup, .overlay, [class*="ad-"], [class*="popup"], 
        [id*="ad-"], [id*="popup"], [class*="sponsor"], [class*="banner"] {{ display: none !important; }}
    </style>
    <script>
        // AGGRESSIVE AD-BLOCKER v2.0
        (function() {{
            'use strict';
            console.log("[AdBlock] STRICT MODE ACTIVE");
            
            var ALLOWED = ['megaplay.buzz', 'megacloud.tv', 'megacloud.blog', 'hianime.to', 'localhost', '127.0.0.1'];
            
            function isAllowed(urlStr) {{
                try {{
                    var u = new URL(urlStr, window.location.href);
                    return ALLOWED.some(function(d) {{ return u.hostname.indexOf(d) !== -1; }});
                }} catch(e) {{ return false; }}
            }}
            
            // 1. BLOCK window.open
            var _open = window.open;
            window.open = function(url) {{
                if (url && isAllowed(url)) return _open.apply(window, arguments);
                console.log("[AdBlock] Blocked window.open:", url);
                return null;
            }};
            
            // 2. BLOCK location changes
            // 2. BLOCK location changes (Safe method)
            // Cannot redefine window.location directly in modern browsers
            window.addEventListener('beforeunload', function(e) {{
                // heuristic: if we didn't initiate a click on an allowed link, it might be a redirect
                // But this is hard to detect perfectly. 
                // For now, relies on click hijacking (below) to stop new tabs.
            }});
            
            // 3. BLOCK top/parent navigation
            try {{
                if (window.top !== window) {{
                    Object.defineProperty(window, 'top', {{ get: function() {{ return window; }} }});
                    Object.defineProperty(window, 'parent', {{ get: function() {{ return window; }} }});
                }}
            }} catch(e) {{}}
            
            // 4. BLOCK ALL click events on suspicious elements
            document.addEventListener('click', function(e) {{
                var t = e.target;
                
                // Block clicks on invisible overlays (ad trick)
                var style = window.getComputedStyle(t);
                if (style.opacity === '0' || style.visibility === 'hidden' || 
                    (style.position === 'fixed' && parseInt(style.zIndex) > 1000)) {{
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log("[AdBlock] Blocked invisible overlay click");
                    return false;
                }}
                
                // Block external links
                while (t && t.tagName !== 'A') {{ t = t.parentElement; }}
                if (t && t.href && !isAllowed(t.href)) {{
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log("[AdBlock] Blocked link:", t.href);
                    return false;
                }}
            }}, true);
            
            // 5. BLOCK mousedown/mouseup (some ads use these)
            ['mousedown', 'mouseup', 'pointerdown', 'pointerup'].forEach(function(evt) {{
                document.addEventListener(evt, function(e) {{
                    var t = e.target;
                    while (t && t.tagName !== 'A') {{ t = t.parentElement; }}
                    if (t && t.href && !isAllowed(t.href)) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        return false;
                    }}
                }}, true);
            }});
            
            // 6. BLOCK form submissions to external sites
            document.addEventListener('submit', function(e) {{
                var form = e.target;
                if (form.action && !isAllowed(form.action)) {{
                    e.preventDefault();
                    console.log("[AdBlock] Blocked form submit:", form.action);
                    return false;
                }}
            }}, true);
            
            // 7. INTERCEPT and BLOCK setTimeout/setInterval redirects
            var _setTimeout = window.setTimeout;
            var _setInterval = window.setInterval;
            window.setTimeout = function(fn, delay) {{
                if (typeof fn === 'string' && (fn.includes('location') || fn.includes('open') || fn.includes('href'))) {{
                    console.log("[AdBlock] Blocked setTimeout redirect");
                    return 0;
                }}
                return _setTimeout.apply(window, arguments);
            }};
            window.setInterval = function(fn, delay) {{
                if (typeof fn === 'string' && (fn.includes('location') || fn.includes('open') || fn.includes('href'))) {{
                    console.log("[AdBlock] Blocked setInterval redirect");
                    return 0;
                }}
                return _setInterval.apply(window, arguments);
            }};
            
            // 8. BLOCK beforeunload (prevents "are you sure" popups)
            window.onbeforeunload = null;
            window.addEventListener('beforeunload', function(e) {{
                delete e.returnValue;
            }});
            
            // 9. Remove ad elements on load
            function removeAds() {{
                var selectors = ['.ad', '.ads', '.advert', '.popup', '.overlay', '[class*="ad-"]', 
                                 '[class*="popup"]', '[id*="ad-"]', '[id*="popup"]', 'iframe[src*="ads"]'];
                selectors.forEach(function(sel) {{
                    document.querySelectorAll(sel).forEach(function(el) {{
                        if (!el.src || !isAllowed(el.src)) {{
                            el.remove();
                        }}
                    }});
                }});
            }}
            document.addEventListener('DOMContentLoaded', removeAds);
            setInterval(removeAds, 2000);
            
            // 10. BLOCK postMessage redirects
            window.addEventListener('message', function(e) {{
                if (e.data && typeof e.data === 'string') {{
                    if (e.data.includes('redirect') || e.data.includes('location') || e.data.includes('http')) {{
                        console.log("[AdBlock] Blocked postMessage:", e.data.substring(0, 100));
                        e.stopImmediatePropagation();
                    }}
                }}
            }}, true);
            
            console.log("[AdBlock] All protections loaded successfully");
        }})();
    </script>
</head>
<body>
    <div class="iframe-container">
        <iframe 
            src="{url}"
            frameborder="0"
            scrolling="no"
            allowfullscreen
            allow="autoplay; encrypted-media; fullscreen"
            sandbox="allow-scripts allow-same-origin allow-forms allow-presentation">
        </iframe>
    </div>
</body>
</html>'''
    
    return Response(content=html_content, media_type="text/html")

@router.get("/anime/sources")
async def get_anime_sources(episode_id: str, server: str = "vidcloud", category: str = "sub"):
    """
    Fetches anime stream sources, attempting multiple servers and providers if needed.
    """
    # providers = [
    #     "https://hianime-api.vercel.app/api/v1",
    #     ANIME_API_BASE
    # ]
    provider = ANIME_API_BASE
    
    # User Request: Prioritize hd-2, but keep backups to prevent 404s.
    # We try hd-2 first, then others if it fails.
    servers = ["hd-2", "megacloud", "vidcloud"] 
    
    # If a specific server was requested via `server` param that isn't in our list, 
    # we could add it, but for now strict optimization.

    client = get_http_client()
    for s in servers:
        try:
            url = f"{provider}/episode/sources?animeEpisodeId={quote(episode_id)}&server={s}&category={category}"
            response = await client.get(url, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 200 and data.get("data", {}).get("sources"):
                    print(f"[HiAnime] Success with {s} on {provider}")
                    
                    # If any source is Megaplay, ensure it's marked as 'embed'
                    for src in data["data"]["sources"]:
                        if "megaplay.buzz" in src.get("url", ""):
                            src["type"] = "embed"
                    return data
                else:
                    print(f"[HiAnime] API returned 200 but no sources for {s} on {provider}: {data.get('message')}")
            else:
                print(f"[HiAnime] Provider {provider} returned {response.status_code} for {s}")
        except Exception as e:
            print(f"[HiAnime] Error fetching from {provider} for {s}: {e}")
            continue

    raise HTTPException(status_code=404, detail="No working stream sources found for this episode.")

# --- CineCLI & Proxy Routes ---

@router.get("/cinecli/search")
async def cinecli_search(query: str) -> dict:
    """
    Search for movies via CineCLI (YTS/Torrents).
    """
    print(f"Searching CineCLI for: {query}")
    results = await CineCLIService.search(query)
    return {"results": results}

@router.get("/cinecli/details/{movie_id}")
async def cinecli_details(movie_id: str) -> dict:
    """
    Get details and magnet links for a CineCLI movie.
    """
    details = await CineCLIService.get_details(movie_id)
    if not details:
        raise HTTPException(status_code=404, detail="Movie not found")
    return details

# --- Ani-CLI (Allmanga/Gogo) Routes ---
from anicli_service import AniCliService

@router.get("/anicli/search")
async def anicli_search(query: str) -> dict:
    """
    Search for anime via Ani-CLI (GogoAnime scraper).
    """
    results = await AniCliService.search(query)
    return {"results": results}

@router.get("/anicli/details/{anime_id}")
async def anicli_details(anime_id: str) -> dict:
    """
    Get details and episodes for an Ani-CLI anime.
    """
    details = await AniCliService.get_details(anime_id)
    if not details:
        raise HTTPException(status_code=404, detail="Anime not found")
    return details

@router.get("/anicli/stream")
async def anicli_stream(episode_id: str) -> dict:
    """
    Get stream URL (embed) for an Ani-CLI episode.
    """
    url = await AniCliService.get_stream_url(episode_id)
    if not url:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"url": url}

@router.get("/anicli/home")
async def anicli_home() -> dict:
    """
    Get homepage content for Ani-CLI (recent releases).
    """
    results = await AniCliService.get_homepage()
    return {"results": results}


@router.get("/iframe-proxy")
async def iframe_proxy(url: str, request: Request):
    """
    Proxies an iframe page (like Megaplay) to bypass Referer checks.
    Injects <base> tag to ensure relative links (JS/CSS) work.
    """
    client = get_http_client()
    
    # Get proper headers (referer spoofing)
    headers = {
        'User-Agent': DEFAULT_HEADERS['User-Agent'],
        'Referer': 'https://hianime.to/',
        'Origin': 'https://hianime.to'
    }
    
    # Specific handling for known providers
    if "megaplay.buzz" in url:
        headers['Referer'] = 'https://megaplay.buzz/'
        headers['Origin'] = 'https://megaplay.buzz'
        
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        content = resp.text
        
        # Inject <base> tag right after <head>
        base_to_inject = f'<base href="{url}">'
        if "<head>" in content:
            content = content.replace("<head>", f"<head>{base_to_inject}", 1)
        # Fallback for upper case
        elif "<HEAD>" in content:
            content = content.replace("<HEAD>", f"<HEAD>{base_to_inject}", 1)
        else:
            # If no head, just prepend (browsers are lenient)
            content = base_to_inject + content
            
        return Response(content=content, media_type="text/html")
        
    except Exception as e:
        print(f"Iframe proxy failed: {e}")
        return Response(content=f"Proxy Error: {e}", status_code=500)


@router.get("/proxy-stream")
async def proxy_stream(request: Request, url: str, source: str = None):
    """
    Proxies a stream URL through the backend in a single pass.
    Bypasses 403s and supports range requests via browser headers.
    """
    # Cycle through headers until success
    candidates = get_source_headers(url, source)
    
    # Forward Range from browser
    client_range = request.headers.get('range')
    
    # User Request: Fix Format Error (Client closing too early)
    # We must NOT use 'async with' because StreamingResponse needs the client open!
    client = httpx.AsyncClient(verify=False, follow_redirects=True)
    
    try:
        last_error = None
        for headers in candidates:
            if client_range:
                headers['Range'] = client_range

            try:
                # Check if this is an HLS request
                # Combine robust checks: URL extension OR Content-Type (from previous check, but here we check URL first optimization)
                is_m3u8 = url.split("?")[0].endswith(".m3u8")
                
                if is_m3u8:
                    # For playlists, we download and REWRITE absolute URLs to proxy through US
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                    if resp.status_code != 200:
                        last_error = f"Source returned {resp.status_code}"
                        continue
                    
                    content = resp.text
                    base_url = str(resp.url).rsplit('/', 1)[0]
                    lines = content.splitlines()
                    new_lines = []
                    
                    # Use the endpoint that this function is mounted on
                    proxy_base = f"{request.url.scheme}://{request.url.netloc}/api/proxy-stream"
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            new_lines.append(line)
                            continue
                        
                        if line.startswith("#"):
                            if "URI=" in line:
                                import re
                                def wrap_uri(match):
                                    uri = match.group(2)
                                    if not uri.startswith("http"):
                                        uri = f"{base_url}/{uri}"
                                    return f'{match.group(1)}="{proxy_base}?url={quote(uri)}&source={source or ""}"'
                                line = re.sub(r'(URI)=["\']([^"\']+)["\']', wrap_uri, line)
                            new_lines.append(line)
                        else:
                            target_url = line
                            if not target_url.startswith("http"):
                                target_url = f"{base_url}/{target_url}"
                            proxied_url = f"{proxy_base}?url={quote(target_url)}&source={source or ''}"
                            new_lines.append(proxied_url)
                    
                    rewritten_content = "\n".join(new_lines)
                    
                    # Close client since we are done
                    await client.aclose()
                    
                    return Response(
                        content=rewritten_content,
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "X-Proxy-Status": "Rewritten-M3U8"
                        }
                    )

                # Not M3U8 -> Standard Proxy
                is_srt = ".srt" in url.lower()
                if is_srt:
                    # Use regular GET for subtitles (worked in standalone test)
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                else:
                    req = client.build_request("GET", url, headers=headers)
                    resp = await client.send(req, stream=True, follow_redirects=True)
                
                # Check if Content-Type indicates M3U8 even if extension didn't (Second Chance)
                ct = resp.headers.get("Content-Type", "").lower()
                if "mpegurl" in ct or "m3u8" in ct:
                    # It IS M3U8, but we started streaming it.
                    # We need to read it and rewrite.
                    content = await resp.read() # Read all
                    await resp.aclose() # Close stream
                    
                    text = content.decode('utf-8', errors='ignore')
                    base_url = str(resp.url).rsplit('/', 1)[0]
                    lines = text.splitlines()
                    new_lines = []
                    proxy_base = f"{request.url.scheme}://{request.url.netloc}/api/proxy-stream"
                    
                    import re
                    for line in lines:
                        line = line.strip()
                        if not line:
                            new_lines.append(line)
                            continue
                        if line.startswith("#"):
                            if "URI=" in line:
                                def wrap_uri(match):
                                    uri = match.group(2)
                                    if not uri.startswith("http"):
                                        uri = f"{base_url}/{uri}"
                                    return f'{match.group(1)}="{proxy_base}?url={quote(uri)}&source={source or ""}"'
                                line = re.sub(r'(URI)=["\']([^"\']+)["\']', wrap_uri, line)
                            new_lines.append(line)
                        else:
                            target_url = line
                            if not target_url.startswith("http"):
                                target_url = f"{base_url}/{target_url}"
                            proxied_url = f"{proxy_base}?url={quote(target_url)}&source={source or ''}"
                            new_lines.append(proxied_url)
                            
                    rewritten_content = "\n".join(new_lines)
                    await client.aclose()
                    
                    return Response(
                        content=rewritten_content,
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "X-Proxy-Status": "Rewritten-M3U8-CT"
                        }
                    )
                
                if resp.status_code >= 400:
                    print(f"[PROXY ERROR] {resp.status_code} for {url[:50]}")
                    await resp.aclose()
                    last_error = f"Source returned {resp.status_code}"
                    continue
                
                # Success!
                excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive", "content-disposition"]
                res_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
                res_headers.update({
                    "Access-Control-Allow-Origin": "*",
                    "Connection": "keep-alive",
                    "X-Proxy-Status": "One-Shot"
                })
                if "Content-Length" in resp.headers:
                    res_headers["Content-Length"] = resp.headers["Content-Length"]

                from starlette.background import BackgroundTask
                
                async def cleanup():
                    await resp.aclose()
                    await client.aclose()

                return StreamingResponse(
                    resp.aiter_raw(),
                    status_code=resp.status_code,
                    headers=res_headers,
                    background=BackgroundTask(cleanup)
                )

            except Exception as e:
                print(f"[PROXY ATTEMPT FAILED] {e} for {url[:50]}")
                last_error = str(e)
                continue
                
        # If we exit loop without returning
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Proxy failed: {last_error}")

    except Exception as e:
        # Fallback closure
        if 'client' in locals():
            await client.aclose()
        print(f"[PROXY FATAL] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy/download")
async def proxy_download(url: str, filename: str = "download.mp4"):
    """
    Forces a download of the remote URL.
    """
    client = get_http_client()
    try:
        req = client.build_request("GET", url, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
        r = await client.send(req, stream=True)
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": r.headers.get("Content-Type", "application/octet-stream")
        }
        if "Content-Length" in r.headers:
            headers["Content-Length"] = r.headers["Content-Length"]
            
        return StreamingResponse(
            r.aiter_bytes(),
            headers=headers,
            background=asyncio.create_task(r.aclose())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/skip-times")
async def get_skip_times(mal_id: int, episode_number: float):
    """
    Proxies request to AniSkip API to get intro/outro timestamps.
    """
    url = f"https://api.aniskip.com/v2/skip-times/{mal_id}/{episode_number}?types[]=op&types[]=ed&episodeLength=0"
    client = get_http_client()
    try:
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return {"found": False}
    except Exception as e:
        print(f"AniSkip error: {e}")
        return {"found": False}

# --- Manga Endpoints ---

@router.get("/manga/search")
async def manga_search(query: str):
    return {"results": await MangaService.search(query)}

@router.get("/manga/details/{manga_id:path}")
async def manga_details(manga_id: str):
    info = await MangaService.get_info(manga_id)
    if not info:
        raise HTTPException(status_code=404, detail="Manga not found")
    return info

@router.get("/manga/read/{chapter_id:path}")
async def manga_read(chapter_id: str):
    pages = await MangaService.get_pages(chapter_id)
    return {"pages": pages}

@router.get("/manga/pdf/{chapter_id:path}")
async def manga_pdf(chapter_id: str):
    pdf_buffer = await MangaService.generate_pdf(chapter_id)
    if not pdf_buffer:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=chapter_{chapter_id.replace('/', '_')}.pdf"}
    )

@router.get("/manga/download/{chapter_id:path}")
async def manga_download(chapter_id: str, title: str = "chapter"):
    zip_buffer = await MangaService.create_chapter_zip(chapter_id, title)
    if not zip_buffer:
        raise HTTPException(status_code=500, detail="Failed to create ZIP")
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{title.replace("/", "_")}.zip"'}
    )

@router.get("/manga/save-local/{chapter_id:path}")
async def manga_save_local(chapter_id: str, manga_title: str, chapter_title: str):
    result = await MangaService.save_chapter_locally(chapter_id, manga_title, chapter_title)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.get("/manga/image-proxy")
async def manga_image_proxy(url: str, referer: str = "https://mangapill.com/"):
    """
    Proxies images with a customizable referer to bypass hotlinking protections.
    Adds CORS and CORP headers to ensure browsers allow embedding.
    """
    if not url or url == "null":
        return Response(content="Invalid URL", status_code=400)
        
    headers = {
        "Referer": referer,
        "User-Agent": DEFAULT_HEADERS["User-Agent"]
    }
    client = get_http_client()
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        if resp.status_code != 200:
            print(f"[IMAGE PROXY] Failed to fetch {url[:50]}... Status: {resp.status_code}")
            return Response(content=f"Error {resp.status_code}", status_code=resp.status_code)
        
        return Response(
            content=resp.content,
            media_type=resp.headers.get("Content-Type", "image/jpeg"),
            headers={
                "Cache-Control": "public, max-age=31536000",
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
                "X-Proxy-Status": "Success"
            }
        )
    except Exception as e:
        print(f"[IMAGE PROXY FATAL] {e} for {url[:50]}")
        return Response(content=str(e), status_code=500)

@router.get("/image-proxy")
async def generic_image_proxy(url: str, referer: str = None):
    """
    Alias for manga_image_proxy but defaults to no referer if not provided.
    Useful for News section images or other external resources.
    """
    return await manga_image_proxy(url, referer or "https://www.animenewsnetwork.com/")

@router.get("/system/status")
async def system_status():
    """
    Checks status of external services (YTS, MovieBox).
    """
    # Simple check - could be cached
    status = {"yts": "unknown", "moviebox": "operational", "overall": "operational"}
    try:
        # Ping YTS
        async with httpx.AsyncClient() as client:
            r = await client.get("https://yts.mx/api/v2/list_movies.json?limit=1", timeout=5.0)
            if r.status_code == 200:
                status["yts"] = "operational"
            else:
                status["yts"] = "down"
    except:
        status["yts"] = "down"
        status["overall"] = "degraded"
        
    return status

@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}

# --- Music Endpoints ---

@router.get("/music/home")
async def get_music_home(language: str = "English"):
    try:
        # Aggregate trending and new releases
        trending = await music_service.get_trending(language)
        new_releases = await music_service.get_new_releases(language)
        charts = await music_service.get_charts()
        
        groups = []
        
        if trending:
            groups.append({
                "title": f"Trending ({language})",
                "items": [
                    {
                        "id": item.get("seokey"),
                        "title": item.get("title"),
                        "poster_url": item.get("images", {}).get("urls", {}).get("medium_artwork"),
                        "year": item.get("artists"),
                        "type": "music",
                        "source": "music"
                    } for item in (trending if isinstance(trending, list) else [])
                ]
            })
            
        if new_releases:
            # newreleases returns a dict with "tracks" and "albums"
            songs = new_releases.get("tracks", [])
            if songs:
                groups.append({
                    "title": f"New Releases ({language})",
                    "items": [
                        {
                            "id": item.get("seokey"),
                            "title": item.get("title"),
                            "poster_url": item.get("images", {}).get("urls", {}).get("medium_artwork") or item.get("image"),
                            "year": item.get("artists"),
                            "type": "music",
                            "source": "music"
                        } for item in (songs if isinstance(songs, list) else [])
                    ]
                })

        if charts:
            groups.append({
                "title": "Top Charts",
                "items": [
                    {
                        "id": item.get("seokey"),
                        "title": item.get("title"),
                        "poster_url": (item.get("images", {}).get("urls", {}).get("medium_artwork") if item.get("images") else None) or item.get("image"),
                        "year": "Playlist",
                        "type": "music_playlist",
                        "source": "music"
                    } for item in (charts if isinstance(charts, list) else [])
                ]
            })
            
        return {"groups": groups}
    except Exception as e:
        print(f"[Music] Home error: {e}")
        return {"groups": []}

@router.get("/music/search")
async def search_music(query: str, limit: int = 20):
    try:
        results = await music_service.search_songs(query, limit)
        if not results:
            return {"results": []}
            
        normalized = [
            {
                "id": item.get("seokey"),
                "title": item.get("title"),
                "poster_url": (item.get("images", {}).get("urls", {}).get("medium_artwork") if item.get("images") else None) or item.get("image"),
                "year": item.get("artists"),
                "type": "music",
                "source": "music"
            } for item in (results if isinstance(results, list) else [])
        ]
        return {"results": normalized}
    except Exception as e:
        print(f"[Music] Search error: {e}")
        return {"results": []}

@router.get("/music/info")
async def get_music_info(seokey: str, type: Optional[str] = "music"):
    try:
        if type == "music_playlist":
            data = await music_service.get_playlist_info(seokey)
        else:
            data = await music_service.get_song_info(seokey)
            
        if not data:
            raise HTTPException(status_code=404, detail="Music not found")
            
        # GaanaPy returns a list of tracks for playlists, but a single object/list[0] for songs
        is_playlist = type == "music_playlist"
        
        if is_playlist:
            # For playlists, data is the list of tracks
            raw_tracks = data if isinstance(data, list) else []
            normalized_tracks = [
                {
                    "id": t.get("seokey"),
                    "track_id": t.get("track_id"),
                    "title": t.get("title"),
                    "artists": t.get("artists"),
                    "poster_url": t.get("images", {}).get("urls", {}).get("large_artwork"),
                    "stream_url": t.get("stream_urls", {}).get("urls", {}).get("very_high_quality"),
                    "source": "music",
                    "type": "music"
                } for t in raw_tracks
            ]
            
            return {
                "id": seokey,
                "tracks": normalized_tracks,
                "type": "music_playlist",
                "source": "music",
                "poster_url": normalized_tracks[0].get("poster_url") if normalized_tracks else None
                # We omit 'title' to let the frontend keep the playlist title from the card
            }
        else:
            # For single songs
            item = data[0] if isinstance(data, list) and len(data) > 0 else data
            return {
                "id": item.get("seokey"),
                "track_id": item.get("track_id"),
                "title": item.get("title"),
                "artists": item.get("artists"),
                "album": item.get("album"),
                "duration": item.get("duration"),
                "release_date": item.get("release_date"),
                "genres": item.get("genres"),
                "poster_url": item.get("images", {}).get("urls", {}).get("large_artwork") or item.get("poster_url"),
                "stream_url": item.get("stream_urls", {}).get("urls", {}).get("very_high_quality") or item.get("stream_url"),
                "type": "music",
                "source": "music"
            }
    except Exception as e:
        print(f"[Music] Info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
