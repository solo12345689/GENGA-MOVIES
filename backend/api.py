import enum
import moviebox_api.v1.constants as const

class PatchedSubjectType(enum.IntEnum):
    ALL = 0
    MOVIES = 1
    TV_SERIES = 2
    SHORT_VIDEO_3 = 3
    SHORT_VIDEO_4 = 4
    EDUCATION = 5
    MUSIC = 6
    ANIME = 7
    SPORTS_8 = 8
    UNKNOWN = 9

const.SubjectType = PatchedSubjectType

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Response, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
from moviebox_api.v1 import Session, Search, MovieAuto, TVSeriesDetails, Homepage
SubjectType = PatchedSubjectType
from moviebox_api.v3.core import Search as SearchV3, ItemDetails as ItemDetailsV3, MovieBoxHttpClient, Homepage as HomepageV3
from moviebox_api.v1.download import (
    MediaFileDownloader, 
    DownloadableMovieFilesDetail, 
    DownloadableTVSeriesFilesDetail,
    resolve_media_file_to_be_downloaded
)
from moviebox_api.v1.extractor._core import ItemJsonDetailsModel
from moviebox_api.v1.extractor.models.json import SubjectModel, SubjectTrailerModel
from moviebox_api.v1.models import SearchResultsItem
from cinecli_service import CineCLIService
from mal_service import MALService
from manga_service import MangaService
from music_service import MusicService
from tv_service import TVService
from radio_service import RadioService
from anilist_service import AnilistService
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

def ensure_v1_item(item):
    """
    Converts any item (V3 ResultsSubjectModel or dict) into a V1 SearchResultsItem 
    compatible with V1 download classes.
    """
    if isinstance(item, SearchResultsItem):
        return item
        
    # Extract properties
    subject_id = None
    detail_path = ""
    title = "Video"
    
    if isinstance(item, dict):
        subject_id = item.get('subject_id') or item.get('subjectId') or item.get('id')
        detail_path = item.get('detail_url') or item.get('detailPath') or ""
        title = item.get('title') or "Video"
    else:
        subject_id = getattr(item, 'subject_id', getattr(item, 'subjectId', getattr(item, 'id', None)))
        detail_path = getattr(item, 'detail_url', getattr(item, 'detailPath', ''))
        title = getattr(item, 'title', 'Video')
        
    # Convert to string and sanitize
    detail_path = str(detail_path) if detail_path else ""
    if detail_path and '/' in detail_path:
        detail_path = detail_path.split('/')[-1]
        
    return SearchResultsItem.construct(
        subjectId=str(subject_id) if subject_id else "",
        detailPath=detail_path,
        title=title
    )

async def resolve_moviebox_media_file(target_item: Any, season: Optional[int] = None, episode: Optional[int] = None, quality: str = "BEST") -> Any:
    """
    Resolves the best quality media file using V3 APIs directly, bypassing buggy V1 classes.
    """
    from moviebox_api.v3.models.downloadables import RootDownloadableFilesDetailModel
    from moviebox_api.v3.constants import CustomResolutionType
    
    # 1. Resolve subject_id
    subject_id = None
    if isinstance(target_item, dict):
        subject_id = target_item.get('subject_id') or target_item.get('subjectId') or target_item.get('id')
    else:
        subject_id = getattr(target_item, 'subject_id', getattr(target_item, 'subjectId', getattr(target_item, 'id', None)))
        
    if not subject_id:
        raise ValueError("Could not resolve subject_id for resource lookup")
        
    # Map quality to enum value
    res_type = CustomResolutionType.BEST
    if quality == "WORST":
        res_type = CustomResolutionType.WORST
    elif quality == "720P":
        res_type = CustomResolutionType._720P
    elif quality == "480P":
        res_type = CustomResolutionType._480P
    elif quality == "360P":
        res_type = CustomResolutionType._360P
        
    res_val = CustomResolutionType.convert_to_default_resolution(res_type).value
    
    params = {
        "subjectId": str(subject_id),
        "resolution": str(res_val),
        "page": "1",
        "perPage": "20"
    }
    if season is not None:
        params["se"] = str(season)
    if episode is not None:
        params["ep"] = str(episode)
        
    async with MovieBoxHttpClient() as client:
        res = await client.get_from_api("/wefeed-mobile-bff/subject-api/resource", params=params)
        
    model = RootDownloadableFilesDetailModel.model_validate(res)
    if not model.list:
        raise ValueError("No downloadable files returned in list")
        
    # Filter files
    files = model.list
    if season is not None and episode is not None:
        files = [f for f in files if f.season == int(season) and f.episode == int(episode)]
        if not files:
            raise ValueError(f"No downloadable files found for Season {season} Episode {episode}")
            
    # Sort files to find the desired one
    if quality == "BEST":
        files.sort(key=lambda x: x.resolution, reverse=True)
        return files[0]
    elif quality == "WORST":
        files.sort(key=lambda x: x.resolution)
        return files[0]
    else:
        # Try to find exact resolution match
        target_res = int(quality.replace("P", ""))
        exact_matches = [f for f in files if f.resolution == target_res]
        if exact_matches:
            return exact_matches[0]
        # Fallback to best available
        files.sort(key=lambda x: x.resolution, reverse=True)
        return files[0]

router = APIRouter()


manga_service = MangaService()
music_service = MusicService()
tv_service = TVService()
radio_service = RadioService()

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
            verify=False,
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
    url = str(url)
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
    if source == 'anilist':
        configs_refs.append({'Referer': 'https://megaplay.buzz/', 'Origin': 'https://megaplay.buzz'})

    if "megaplay.buzz" in url_lower:
        configs_refs.append({'Referer': 'https://megaplay.buzz/', 'Origin': 'https://megaplay.buzz'})
        
    if "anilist" in url_lower or "megacloud" in url_lower or "vidcloud" in url_lower or "rabbitstream" in url_lower:
        configs_refs.append({'Referer': 'https://megaplay.buzz/', 'Origin': 'https://megaplay.buzz'})
    
    # VLC/MPV mimicking and domain referer cycling for TV streams
    if source == 'tv':
        try:
            domain_host = url.split("://")[-1].split("/")[0]
        except Exception:
            domain_host = ""
        
        configs_refs.append({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': f'https://{domain_host}/' if domain_host else 'https://famelack.com/',
            'Origin': f'https://{domain_host}' if domain_host else 'https://famelack.com',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        configs_refs.append({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://famelack.com/',
            'Origin': 'https://famelack.com',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        configs_refs.append({
            'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        configs_refs.append({
            'User-Agent': 'mpv 0.35.1',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })

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
    
    # 1. Check explicit subjectType / subject_type from library model
    subject_type_val = getattr(item, 'subject_type', getattr(item, 'subjectType', None))
    if subject_type_val is not None:
        # Check both enum class instances and raw integer comparisons
        if subject_type_val == SubjectType.TV_SERIES or str(subject_type_val) == '2' or (hasattr(subject_type_val, 'value') and subject_type_val.value == 2):
            item_type = "series"
        elif subject_type_val == SubjectType.MOVIES or str(subject_type_val) == '1' or (hasattr(subject_type_val, 'value') and subject_type_val.value == 1):
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
            
        async with MovieBoxHttpClient() as client:
            search_instance = SearchV3(client_session=client, query=query, page=page, subject_type=subject_type)
            results_model = await search_instance.get_content_model()
            
            items = []
            if hasattr(results_model, 'items'):
                for item in results_model.items:
                    sub_id = str(getattr(item, 'subject_id', getattr(item, 'subjectId', getattr(item, 'id', ''))))
                    item_id = f"moviebox_{sub_id}" if sub_id else str(uuid.uuid4())
                    
                    # Use async helper to determine type and poster
                    item_type = await determine_item_type(item, content_type)
                    poster_url = await extract_item_poster(item)
                    
                    # Cache the results
                    search_cache[item_id] = {
                        "item": item,
                        "search_instance": None,  # No longer need to cache the search instance since details uses ItemDetailsV3
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


# --- TV Endpoints ---
@router.get("/tv/countries")
async def get_tv_countries():
    countries = await tv_service.get_countries()
    return {"results": countries}

@router.get("/tv/country/{code}")
async def get_tv_channels_by_country(code: str):
    channels = await tv_service.get_channels_by_country(code)
    return {"results": channels}

@router.get("/tv/parse-playlist")
async def parse_tv_playlist(url: str):
    channels = await tv_service.parse_m3u_playlist(url)
    return {"results": channels}

@router.get("/tv/resolve-youtube/{yt_id}")
async def resolve_youtube_hls(yt_id: str):
    """
    Uses local yt-dlp to resolve a direct YouTube HLS (.m3u8) URL.
    This replaces unstable third-party proxies like ythls.armelin.one.
    """
    try:
        # Command: yt-dlp -g -f best http://youtube.com/watch?v=VIDEO_ID
        url = f"https://www.youtube.com/watch?v={yt_id}" if len(yt_id) == 11 else f"https://www.youtube.com/channel/{yt_id}/live"
        
        # Use --no-warnings to keep stdout clean
        process = await asyncio.create_subprocess_exec(
            "yt-dlp", "-g", "-f", "best", "--no-warnings", "--no-check-certificate", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            lines = stdout.decode().strip().splitlines()
            # The URL is usually the last line of stdout
            stream_url = lines[-1].strip() if lines else ""
            if stream_url.startswith("http"):
                return {"url": stream_url, "type": "hls"}
            else:
                return {"error": f"Invalid URL format: {stream_url}"}
        else:
            error = stderr.decode().strip()
            print(f"[YT-DLP ERROR] {error}")
            return {"error": error}
    except FileNotFoundError:
        print("[YT-DLP] yt-dlp not found in system PATH")
        return {"error": "yt-dlp not installed or not in PATH. Please install it on the backend server."}
    except Exception as e:
        print(f"[YT-DLP FATAL] {e}")
        return {"error": str(e)}

@router.get("/tv/category/{category}")
async def get_tv_channels_by_category(category: str):
    channels = await tv_service.get_channels_by_category(category)
    return {"results": channels}

# --- Radio Endpoints ---
@router.get("/radio/countries")
async def get_radio_countries():
    countries = await radio_service.get_countries()
    return {"results": countries}

@router.get("/radio/country/{code}")
async def get_radio_channels_by_country(code: str):
    channels = await radio_service.get_channels_by_country(code)
    return {"results": channels}

async def warmup_session() -> None:
    """
    Warms up the session by performing a lightweight dummy search.
    This helps reduce latency for the first user search.
    """
    print("Warming up session...")
    try:
        async with MovieBoxHttpClient() as client:
            search_instance = SearchV3(client_session=client, query="test")
            await search_instance.get_content_model()
        
        # Anilist warmup
        asyncio.create_task(AnilistService.warmup())
        
        print("Session warmed up successfully.")
    except Exception as e:
        print(f"Warmup failed: {e}")

@router.get("/homepage")
async def get_homepage_content() -> dict:
    """
    Fetches trending and featured content for the homepage using the MovieBox V3 API.
    """
    try:
        print("Fetching homepage via moviebox_api V3...")
        async with MovieBoxHttpClient() as client:
            homepage = HomepageV3(client)
            raw_response = await homepage.get_content()
        
        results = []
        items = raw_response.get('items', [])
        
        for group in items:
            group_title = group.get('title')
            if not group_title:
                continue
                
            # Process standard subjects and banners
            items_source = []
            
            # 1. Subjects
            if group.get('subjects'):
                items_source.extend(group['subjects'])
                
            # 2. Banners
            if group.get('banner') and isinstance(group['banner'], dict) and group['banner'].get('banners'):
                for banner in group['banner']['banners']:
                    if banner.get('subject'):
                        # Use the nested subject but fallback/override poster from banner
                        sub = banner['subject'].copy()
                        if 'image' in banner and banner['image']:
                            sub['cover'] = banner['image']
                        items_source.append(sub)
                    else:
                        items_source.append(banner)
            
            if not items_source:
                continue
                
            if group_title == "Banner":
                group_title = "Featured"
                
            group_results = []
            for item in items_source:
                try:
                    # Extract basic info
                    sid = item.get('subjectId') or item.get('subject_id') or item.get('id')
                    if not sid or str(sid) == "0":
                        continue
                        
                    # Extract poster
                    poster_url = ""
                    cover = item.get('cover') or item.get('image')
                    if isinstance(cover, dict):
                        poster_url = cover.get('url', '')
                        
                    # Extract Title
                    title = item.get('title') or item.get('content') or ''
                    if not title:
                        continue
                        
                    # Extract Year
                    date_str = item.get('releaseDate') or item.get('release_date') or ''
                    year = str(date_str)[:4] if date_str else "N/A"
                    
                    # Extract Rating
                    rating = str(item.get('imdbRatingValue') or item.get('imdbRate') or 'N/A')
                    
                    # Use subjectType (default to 1)
                    subject_type_raw = item.get('subjectType') or item.get('subject_type', 1)
                    subject_type_val = int(subject_type_raw.value) if hasattr(subject_type_raw, 'value') else int(subject_type_raw)
                    
                    # Determine type
                    if subject_type_val in [3, 7]:
                        it_type = "anime"
                    elif subject_type_val == 2:
                        it_type = "series"
                    else:
                        it_type = "movie"
                        
                    # Cache in memory
                    search_cache[str(sid)] = {
                        "item": {
                            "id": str(sid),
                            "title": title,
                            "poster_url": poster_url,
                            "year": year,
                            "rating": rating,
                            "type": it_type,
                            "subjectType": subject_type_val,
                            "detailPath": item.get('detailPath'),
                            "source": "moviebox"
                        },
                        "search_instance": None,
                        "type": it_type,
                        "is_homepage": True,
                        "needs_search": True
                    }
                    
                    group_results.append({
                        "id": str(sid),
                        "title": title,
                        "year": year,
                        "type": it_type,
                        "poster_url": poster_url,
                        "rating": rating,
                        "source": "moviebox"
                    })
                except Exception as item_err:
                    print(f"Skipping malformed homepage item: {item_err}")
                    continue
                    
            if group_results:
                # Clean up any trailing / leading question marks in titles (V3 sometimes includes "?Cinema" etc)
                clean_title = group_title.strip("? \t\r\n")
                results.append({
                    "title": clean_title,
                    "items": group_results
                })
                
        print(f"Homepage fetch success (V3). Returning {len(results)} groups.")
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
        async with MovieBoxHttpClient() as client:
            search_instance = SearchV3(client_session=client, query=query)
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
        if item_id.startswith("moviebox_") or (item_id.isdigit() and len(item_id) >= 18):
            sub_id = item_id.replace("moviebox_", "")
            search_cache[item_id] = {
                "item": {
                    "id": item_id,
                    "subject_id": sub_id,
                    "type": "movie"
                },
                "type": "movie"
            }
        else:
            raise HTTPException(status_code=404, detail="Item not found in cache. Please search again.")
    
    cached = search_cache[item_id]
    item = cached["item"]
    item_type = cached.get("type", "movie")
    
    try:
        subject_id = None
        if isinstance(item, dict):
            subject_id = item.get('subject_id') or item.get('subjectId') or item.get('id')
        else:
            subject_id = getattr(item, 'subject_id', getattr(item, 'subjectId', getattr(item, 'id', None)))
            
        if not subject_id:
            raise ValueError("Could not resolve subject_id for item details")

        async with MovieBoxHttpClient() as client:
            details_provider = ItemDetailsV3(client_session=client, include_seasons=True)
            
            tasks = [details_provider.get_content_model(subject_id=str(subject_id))]
            
            # Only add MAL search if it's an anime
            mal_task_idx = -1
            if item_type == "anime":
                title = getattr(item, 'title', '')
                if not title and isinstance(item, dict):
                    title = item.get('title', '')
                tasks.append(MALService.search_mal_id(title))
                mal_task_idx = 1
                
            results_parallel = await asyncio.gather(*tasks, return_exceptions=True)
            
            details_model = results_parallel[0]
            if isinstance(details_model, Exception):
                print(f"[RETRY] First details fetch failed: {details_model}. Retrying...")
                details_model = await details_provider.get_content_model(subject_id=str(subject_id))
                
            mal_id = None
            if mal_task_idx != -1:
                mal_res = results_parallel[mal_task_idx]
                if not isinstance(mal_res, Exception):
                    mal_id = mal_res
            

        
        # Extract IMDB rating if available
        imdb_rating = None
        imdb_rating_value = None
        
        # Try to get rating value from details_model first
        rating_attr = None
        if hasattr(details_model, 'imdb_rating_value'):
            rating_attr = 'imdb_rating_value'
        elif hasattr(details_model, 'imdbRatingValue'):
            rating_attr = 'imdbRatingValue'
            
        if rating_attr:
            value = getattr(details_model, rating_attr)
            if value:
                imdb_rating_value = float(value)
                imdb_rating = f"{value}/10"
                print(f"[DEBUG] Found rating in details_model.{rating_attr}: {imdb_rating}")
        
        # Fallback: Try to get from resData
        if not imdb_rating_value and hasattr(details_model, 'resData'):
            resData = details_model.resData
            res_rating_attr = None
            if hasattr(resData, 'imdb_rating_value'):
                res_rating_attr = 'imdb_rating_value'
            elif hasattr(resData, 'imdbRatingValue'):
                res_rating_attr = 'imdbRatingValue'
                
            if res_rating_attr:
                value = getattr(resData, res_rating_attr)
                if value:
                    imdb_rating_value = float(value)
                    imdb_rating = f"{value}/10"
                    print(f"[DEBUG] Found rating in resData.{res_rating_attr}: {imdb_rating}")
        
        # Fallback: Try to get from the original search item
        if not imdb_rating_value:
            item_rating_attr = None
            if hasattr(item, 'imdb_rating_value'):
                item_rating_attr = 'imdb_rating_value'
            elif hasattr(item, 'imdbRatingValue'):
                item_rating_attr = 'imdbRatingValue'
            elif isinstance(item, dict):
                if 'imdb_rating_value' in item:
                    item_rating_attr = 'imdb_rating_value'
                elif 'imdbRatingValue' in item:
                    item_rating_attr = 'imdbRatingValue'
                    
            if item_rating_attr:
                value = item.get(item_rating_attr) if isinstance(item, dict) else getattr(item, item_rating_attr)
                if value:
                    imdb_rating_value = float(value)
                    imdb_rating = f"{value}/10"
                    print(f"[DEBUG] Found rating in item.{item_rating_attr}: {imdb_rating}")
        
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
            elif hasattr(details_model, 'seasons') and details_model.seasons:
                if hasattr(details_model.seasons, 'seasons'):
                    seasons_list = details_model.seasons.seasons
                else:
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
                        m_ep = season.get('max_ep', season.get('maxEp', season.get('max_episodes', season.get('episode_count', season.get('episodeCount', 0)))))
                    else:
                        s_num = getattr(season, 'se', getattr(season, 'number', getattr(season, 'season_number', 0)))
                        m_ep = getattr(season, 'max_ep', getattr(season, 'maxEp', getattr(season, 'max_episodes', getattr(season, 'episode_count', getattr(season, 'episodeCount', 0)))))
                    
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
            async with MovieBoxHttpClient() as client:
                search_instance = SearchV3(client_session=client, query=query, subject_type=subject_type)
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
        
        media_file = await resolve_moviebox_media_file(item, season=season, episode=episode, quality="BEST")
        
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
        
        if id and id not in search_cache:
            if id.startswith("moviebox_") or (id.isdigit() and len(id) >= 18):
                sub_id = id.replace("moviebox_", "")
                search_cache[id] = {
                    "item": {
                        "id": id,
                        "subject_id": sub_id,
                        "title": query or "Video"
                    },
                    "type": content_type,
                    "needs_search": True
                }

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
                async with MovieBoxHttpClient() as client:
                    search_instance = SearchV3(client_session=client, query=target_item['title'], subject_type=subject_type)
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
                search_cache[id]["search_instance"] = None
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
                    async with MovieBoxHttpClient() as client:
                        search_instance = SearchV3(client_session=client, query=query, subject_type=subject_type)
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

            
        # 4. Resolve Media File with V3 APIs directly
        media_file = None
        for res_attempt in range(max_retries + 1):
            try:
                media_file = await resolve_moviebox_media_file(target_item, season=season, episode=episode, quality="BEST")
                if media_file and media_file.url:
                    break
            except Exception as res_err:
                if res_attempt < max_retries:
                    print(f"[STREAM] Metadata fetch attempt {res_attempt + 1} failed: {res_err}. Retrying...")
                    await asyncio.sleep(1)
                    continue
                raise HTTPException(status_code=404, detail="Playable stream URL not found")
             
        if not media_file or not media_file.url:
            raise HTTPException(status_code=404, detail="Playable stream URL not found")

        # Return URL if mode is 'url'
        if mode == "url":
            # Return a proxy URL that routes through our backend
            # This bypasses 403 Forbidden errors from streaming providers
            proxy_url = f"/api/proxy-stream?url={quote(str(media_file.url))}"
            
            # Extract subtitles using V3 details
            subtitles = []
            try:
                subject_id = None
                if isinstance(target_item, dict):
                    subject_id = target_item.get('subject_id') or target_item.get('subjectId') or target_item.get('id')
                else:
                    subject_id = getattr(target_item, 'subject_id', getattr(target_item, 'subjectId', getattr(target_item, 'id', None)))
                if subject_id:
                    async with MovieBoxHttpClient() as client:
                        details_provider = ItemDetailsV3(client_session=client, include_seasons=True)
                        details_model = await details_provider.get_content_model(subject_id=str(subject_id))
                        if hasattr(details_model, 'subtitles') and details_model.subtitles:
                            # Note: V3 returns subtitles list. If details model has subtitles, let's map them
                            # (usually V3 returns direct URLs in details model subtitles or play_info)
                            pass
                
                # Fallback to media_file's ext_captions if present
                if hasattr(media_file, 'ext_captions') and media_file.ext_captions:
                    for caption in media_file.ext_captions:
                        url = caption.get('url') if isinstance(caption, dict) else getattr(caption, 'url', None)
                        lan = caption.get('lan') if isinstance(caption, dict) else getattr(caption, 'lan', None)
                        lan_name = caption.get('lanName') if isinstance(caption, dict) else getattr(caption, 'lanName', None)
                        if url:
                            proxied_sub_url = f"/api/proxy-stream?url={quote(str(url))}&source=moviebox"
                            subtitles.append({
                                "lang": lan_name or lan or "Unknown",
                                "language": lan or "en",
                                "url": proxied_sub_url
                            })
            except Exception as sub_err:
                print(f"[SUBTITLE ERROR] Failed to fetch subtitles: {sub_err}")
            
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
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Streaming error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/moviebox/download")
async def moviebox_download(
    request: Request,
    query: str, 
    id: Optional[str] = None, 
    content_type: str = "all", 
    season: Optional[int] = None, 
    episode: Optional[int] = None,
    check_only: bool = False
):
    """
    Direct video download for MovieBox items. 
    Resolves the best stream and proxies it as an attachment.
    """
    try:
        # 1. Resolve item (Reusing logic similar to /stream)
        target_item = None
        search_instance = None
        
        if id and id not in search_cache:
            if id.startswith("moviebox_") or (id.isdigit() and len(id) >= 18):
                sub_id = id.replace("moviebox_", "")
                search_cache[id] = {
                    "item": {
                        "id": id,
                        "subject_id": sub_id,
                        "title": query or "Video"
                    },
                    "type": content_type,
                    "search_instance": None,
                    "needs_search": True
                }

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
                async with MovieBoxHttpClient() as client:
                    search_instance = SearchV3(client_session=client, query=target_item['title'], subject_type=subject_type)
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
                    search_cache[id]["search_instance"] = None
                    search_cache[id]["needs_search"] = False
        else:
            subject_type = SubjectType.ALL
            if content_type.lower() in ["movie", "anime_movie"]:
                subject_type = SubjectType.MOVIES
            elif content_type.lower() in ["series", "anime"]:
                subject_type = SubjectType.TV_SERIES
            async with MovieBoxHttpClient() as client:
                search_instance = SearchV3(client_session=client, query=query, subject_type=subject_type)
                results = await search_instance.get_content_model()
            if not results.items:
                raise HTTPException(status_code=404, detail="Content not found")
            target_item = results.items[0]

        # 2. Resolve Media File (Best Quality)
        media_file = None
        quality_options = ["BEST", "720P", "480P", "360P"]
        
        for quality in quality_options:
            try:
                media_file = await resolve_moviebox_media_file(target_item, season=season, episode=episode, quality=quality)
                if media_file and media_file.url:
                    break
            except Exception as e:
                print(f"[DOWNLOAD RESOLUTION ERROR] Quality {quality} resolution attempt failed: {e}")
                continue
                
        if not media_file or not media_file.url:
            raise HTTPException(status_code=404, detail="Downloadable stream URL not found")

        if check_only:
            return {"status": "available"}

        # 3. Proxy the download directly using the same connection-pooling range-supporting logic as proxy-stream
        import re
        from starlette.background import BackgroundTask
        
        filename = f"{getattr(target_item, 'title', 'video')}.mp4"
        if season is not None and episode is not None:
            filename = f"{getattr(target_item, 'title', 'video')} S{season}E{episode}.mp4"
        filename = re.sub(r'[/\\?%*:|"<>]', '-', filename)

        # Cycle through headers until success
        candidates = get_source_headers(str(media_file.url), "moviebox")
        client_range = request.headers.get('range')
        client = get_http_client()

        last_error = None
        for headers in candidates:
            if client_range:
                headers['Range'] = client_range

            try:
                req = client.build_request("GET", str(media_file.url), headers=headers)
                resp = await client.send(req, stream=True, follow_redirects=True)
                
                if resp.status_code >= 400:
                    print(f"[DOWNLOAD PROXY ERROR] {resp.status_code} for {str(media_file.url)[:50]}")
                    await resp.aclose()
                    last_error = f"Source returned {resp.status_code}"
                    continue
                
                # Success!
                excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive", "content-disposition"]
                res_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
                res_headers.update({
                    "Access-Control-Allow-Origin": "*",
                    "Connection": "keep-alive",
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/octet-stream",
                    "X-Proxy-Status": "Direct-Download"
                })
                if "Content-Length" in resp.headers:
                    res_headers["Content-Length"] = resp.headers["Content-Length"]

                async def cleanup():
                    await resp.aclose()

                return StreamingResponse(
                    resp.aiter_raw(),
                    status_code=resp.status_code,
                    headers=res_headers,
                    background=BackgroundTask(cleanup)
                )

            except Exception as e:
                print(f"[DOWNLOAD PROXY ATTEMPT FAILED] {e} for {str(media_file.url)[:50]}")
                last_error = str(e)
                continue

        raise HTTPException(status_code=502, detail=f"Proxy failed: {last_error}")


    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- Anilist & MegaPlay Section ---

@router.get("/anime/home")
async def get_anime_home():
    try:
        trending = await AnilistService.get_trending(per_page=20)
        
        return [
            {"title": "Trending Now", "items": trending}
        ]
    except Exception as e:
        print(f"Anilist Home error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/top-100")
async def get_anime_top_100(page: int = 1):
    try:
        return await AnilistService.get_top_100(page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/search")
async def search_anime(query: str, page: int = 1):
    try:
        return await AnilistService.search(query, page=page)
    except Exception as e:
        print(f"Anilist Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anime/details/{anime_id}")
async def get_anime_details(anime_id: str):
    try:
        info = await AnilistService.get_info(anime_id)
        if not info:
            raise HTTPException(status_code=404, detail="Anime not found")
        return info
    except Exception as e:
        print(f"Anilist Details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/anime/episodes/{anime_id}")
async def get_anime_episodes(anime_id: str):
    try:
        info = await AnilistService.get_info(anime_id)
        if not info: 
            return {"status": 404, "data": {"episodes": []}}
        
        # Calculate how many episodes have actually released
        # Default to 0, then try to find the best estimate
        count = 0
        
        ep_count = info.get('episodes_count') or 0
        next_ep = info.get('next_episode')
        streaming_count = info.get('streaming_episodes_count', 0)
        schedule_count = info.get('aired_episodes_from_schedule', 0)
        status = info.get('status')
        
        count = 0
        
        # 1. Start with the most reliable historical data
        count = max(schedule_count, streaming_count)
        
        # 2. If it's FINISHED, use total episodes
        if status == 'FINISHED' and ep_count > 0:
            count = max(count, ep_count)
            
        # 3. If it's RELEASING, use next_ep - 1
        if status == 'RELEASING' and next_ep and next_ep > 1:
            count = max(count, next_ep - 1)
            
        # 4. Final safety fallbacks
        if not count or count < 1:
            if status == 'FINISHED' and ep_count > 0:
                count = ep_count
            elif status == 'RELEASING':
                count = ep_count if (ep_count and ep_count > 0) else 1
            else:
                count = ep_count if (ep_count and ep_count > 0) else 1

        # Final absolute floor
        if not count or count < 1:
            count = 1

        print(f"[Anilist Episodes] ID: {anime_id} | Status: {status} | Final Count: {count} (Sched: {schedule_count}, Stream: {streaming_count}, Next: {next_ep}, Total: {ep_count})")
        if count <= 1:
            print(f"[Anilist Episodes] LOW COUNT DEBUG - Full Info: {info}")
        
        episodes = []
        for i in range(1, int(count) + 1):
            episodes.append({
                "number": i,
                "episodeId": str(i),
                "title": f"Episode {i}"
            })
        return {"status": 200, "data": {"episodes": episodes}}
    except Exception as e:
        print(f"[API ERROR] get_anime_episodes failed for {anime_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": 200, "data": {"episodes": [], "error": str(e)}}

# Removed anime/servers as MegaPlay uses direct embed




    


@router.get("/anime/sources")
async def get_anime_sources(episode_id: str, anime_id: str = None, category: str = "sub"):
    """
    Returns the MegaPlay embed URL for the given Anilist ID and episode number.
    """
    if not anime_id:
        # If frontend didn't pass anime_id explicitly, we assume episode_id might contain it or be the ep number
        # But for Anilist switch, we expect both.
        raise HTTPException(status_code=400, detail="Anilist ID required")
    
    # Endpoint: https://megaplay.buzz/stream/ani/{anilist-id}/{ep-num}/{language}
    url = f"https://megaplay.buzz/stream/ani/{anime_id}/{episode_id}/{category}"
    return {
        "status": 200,
        "data": {
            "sources": [{"url": url, "type": "embed"}]
        }
    }

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




@router.get("/iframe-proxy")
async def iframe_proxy(url: str):
    """
    Returns a clean HTML wrapper for the video player.
    Preserves original scripts and provides ad-blocking + event monitoring.
    """
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Anime Player</title>
<style>
  html, body {{ margin:0; height:100%; background:#000; overflow:hidden; }}
  #player {{ position:fixed; inset:0; width:100%; height:100%; border:0; }}
</style>
</head>
<body>
<iframe
  id="player"
  src="{url}"
  allow="autoplay; fullscreen; picture-in-picture"
  allowfullscreen>
</iframe>

<script>
// 1. AD-BLOCKER (Safe Mode) - Prevents basic redirects
(function() {{
    var ALLOWED = ['megaplay.buzz', 'megacloud.tv', 'megacloud.blog', 'anilist.co', 'localhost', '127.0.0.1'];
    function isAllowed(uStr) {{ try {{ var u = new URL(uStr, window.location.href); return ALLOWED.some(d => u.hostname.includes(d)); }} catch(e) {{ return false; }} }}
    
    var _open = window.open;
    window.open = function(u) {{ if (u && isAllowed(u)) return _open.apply(window, arguments); return null; }};
    
    document.addEventListener('click', function(e) {{
        var t = e.target; while (t && t.tagName !== 'A') t = t.parentElement;
        if (t && t.href && !isAllowed(t.href)) {{ e.preventDefault(); e.stopPropagation(); return false; }}
    }}, true);
}})();

// 2. EVENT LISTENER - Monitor player state
window.addEventListener("message", function (event) {{
  if (event.origin !== "https://megaplay.buzz") return;
  let data = event.data;
  if (typeof data === "string") {{ try {{ data = JSON.parse(data); }} catch {{ return; }} }}
  if (data.event === "complete") {{ console.log("[MegaPlay] Episode finished"); }}
  if (data.event === "error") {{ console.log("[MegaPlay] Playback error"); }}
}});
</script>
</body>
</html>'''
    
    return Response(
        content=html_content, 
        media_type="text/html",
        headers={
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Frame-Options": "ALLOWALL",
            "Content-Security-Policy": "frame-ancestors *"
        }
    )
    
@router.options("/proxy-stream")
async def proxy_stream_options():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }
    )

@router.get("/proxy-stream")
async def proxy_stream(request: Request, url: str, source: str = None, download: bool = False, filename: str = "video.mp4"):
    """
    Proxies a stream URL through the backend in a single pass.
    Bypasses 403s and supports range requests via browser headers.
    """
    # Cycle through headers until success
    candidates = get_source_headers(url, source)
    
    # Forward Range from browser
    client_range = request.headers.get('range')
    
    # Use the global persistent client to benefit from connection pooling and reuse TLS handshakes
    client = get_http_client()
    
    try:
        last_error = None
        for headers in candidates:
            req_headers = headers.copy()
            is_m3u8 = url.split("?")[0].lower().endswith(".m3u8")
            if client_range and not is_m3u8:
                req_headers['Range'] = client_range

            try:
                if is_m3u8:
                    # For playlists, we download and REWRITE absolute URLs to proxy through US
                    resp = await client.get(url, headers=req_headers, follow_redirects=True, timeout=15.0)
                    if resp.status_code not in [200, 206]:
                        last_error = f"Source returned {resp.status_code}"
                        continue
                    
                    content = resp.text
                    base_url = str(resp.url).rsplit('/', 1)[0]
                    lines = content.splitlines()
                    new_lines = []
                    
                    # Use the endpoint that this function is mounted on
                    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
                    if "onrender.com" in str(request.url.netloc):
                        scheme = "https"
                    proxy_base = f"{scheme}://{request.url.netloc}/api/proxy-stream"
                    
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
                    
                    # No need to close the global client

                    
                    return Response(
                        content=rewritten_content,
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Methods": "GET, OPTIONS",
                            "Cross-Origin-Resource-Policy": "cross-origin",
                            "X-Proxy-Status": "Rewritten-M3U8"
                        }
                    )

                # Not M3U8 -> Standard Proxy
                is_srt = ".srt" in url.lower()
                if is_srt:
                    # Use regular GET for subtitles (worked in standalone test)
                    resp = await client.get(url, headers=req_headers, follow_redirects=True, timeout=15.0)
                else:
                    req = client.build_request("GET", url, headers=req_headers)
                    resp = await client.send(req, stream=True, follow_redirects=True)
                
                # Check if Content-Type indicates M3U8 even if extension didn't (Second Chance)
                ct = resp.headers.get("Content-Type", "").lower()
                is_ts_file = url.split("?")[0].lower().endswith(".ts")
                if not is_ts_file and ("mpegurl" in ct or "m3u8" in ct):
                    # It IS M3U8, but we started streaming it.
                    # We need to read it and rewrite.
                    content = await resp.read() # Read all
                    await resp.aclose() # Close stream
                    
                    text = content.decode('utf-8', errors='ignore')
                    base_url = str(resp.url).rsplit('/', 1)[0]
                    lines = text.splitlines()
                    new_lines = []
                    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
                    if "onrender.com" in str(request.url.netloc):
                        scheme = "https"
                    proxy_base = f"{scheme}://{request.url.netloc}/api/proxy-stream"
                    
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
                    # No need to close the global client

                    
                    return Response(
                        content=rewritten_content,
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Methods": "GET, OPTIONS",
                            "Cross-Origin-Resource-Policy": "cross-origin",
                            "X-Proxy-Status": "Rewritten-M3U8-CT"
                        }
                    )
                
                if resp.status_code >= 400:
                    print(f"[PROXY ERROR] {resp.status_code} for {url[:50]}")
                    await resp.aclose()
                    last_error = f"Source returned {resp.status_code}"
                    continue
                
                # Success!
                excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive", "content-disposition", "cross-origin-resource-policy"]
                res_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
                res_headers.update({
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Cross-Origin-Resource-Policy": "cross-origin",
                    "Connection": "keep-alive",
                    "X-Proxy-Status": "One-Shot"
                })
                if download:
                    res_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
                    res_headers["Content-Type"] = "application/octet-stream"
                elif url.split("?")[0].lower().endswith(".ts"):
                    res_headers["Content-Type"] = "video/mp2t"
                    
                if "Content-Length" in resp.headers:
                    res_headers["Content-Length"] = resp.headers["Content-Length"]

                from starlette.background import BackgroundTask
                
                async def cleanup():
                    await resp.aclose()
                    # Global client is NOT closed here


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
        # No need to close the global client

        return Response(
            content=json.dumps({"detail": f"Proxy failed: {last_error}"}),
            status_code=502,
            media_type="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )

    except Exception as e:
        print(f"[PROXY FATAL] {e}")
        import traceback
        traceback.print_exc()
        return Response(
            content=json.dumps({"detail": str(e)}),
            status_code=500,
            media_type="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )

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

@router.get("/manga/mangapill/popular")
async def manga_popular(page: int = 1):
    return {"results": await MangaService.get_popular(page)}

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

TRANSPARENT_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

@router.get("/manga/image-proxy")
async def manga_image_proxy(url: str, referer: str = "https://mangapill.com/"):
    """
    Proxies images with a customizable referer to bypass hotlinking protections.
    Adds CORS and CORP headers to ensure browsers allow embedding.
    """
    if not url or url == "null":
        return Response(content=TRANSPARENT_SVG, media_type="image/svg+xml")
        
    headers = {
        "Referer": referer,
        "User-Agent": DEFAULT_HEADERS["User-Agent"]
    }
    client = get_http_client()
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True, timeout=10.0)
        if resp.status_code != 200:
            return Response(
                content=TRANSPARENT_SVG,
                media_type="image/svg+xml",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                    "Cross-Origin-Resource-Policy": "cross-origin"
                }
            )
        
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
        return Response(
            content=TRANSPARENT_SVG,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )

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
