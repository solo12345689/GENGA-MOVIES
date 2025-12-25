from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Response
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

# Global session
session = Session()

# Persistent HTTP client for better performance and to avoid connection closure issues
# We use a larger timeout and connection pool for streaming.
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(60.0, connect=10.0),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)

# Simple in-memory cache: {uuid: item_object}
search_cache = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

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
    
    if 'anime' in category or 'anime' in genres:
        item_type = "anime_movie" if item_type == "movie" else "anime"
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
                
                items.append({
                    "id": item_id,
                    "title": getattr(item, 'title', 'Unknown'),
                    "year": getattr(item, 'year', None),
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
    Fetches trending and featured content for the homepage.
    """
    """
    Fetch trending/homepage content using the moviebox-api library.
    """
    try:
        print("Fetching homepage via moviebox_api...")
        # Use library's Session and Homepage
        session = Session()
        homepage = Homepage(session=session)
        
        # Get raw content (since HomepageContentModel is currently buggy with 'groups')
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
                            # Create a dummy search instance for this group's context
                            item_search = Search(session=session, query=title)
                            
                            cache_item = {
                                "id": str(sid),
                                "title": title,
                                "year": year,
                                "type": "movie",
                                "poster_url": poster_url,
                                "rating": rating
                            }
                            
                            # Cache the raw data and the search instance
                            # Wrap the raw item dict in a SearchResultsItem model for library compatibility
                            try:
                                # Ensure we have the required fields for the model mapping
                                model_data = item.copy()
                                # SearchResultsItem expects 'id' as 'id' or 'subjectId'
                                if 'subjectId' in model_data and 'id' not in model_data:
                                    model_data['id'] = model_data['subjectId']
                                
                                model_item = SearchResultsItem.model_validate(model_data)
                            except Exception as model_err:
                                print(f"[WARNING] Failed to validate homepage item model: {model_err}. Using as-is.")
                                model_item = item

                            search_cache[str(sid)] = {
                                "item": model_item,
                                "search_instance": item_search,
                                "type": "movie",
                                "is_homepage": True
                            }
                            
                            group_results.append(cache_item)
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
        # Use the search instance to get details for this item
        details_provider = search_instance.get_item_details(item)
        details_model = await details_provider.get_content_model()
        
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
            "title": getattr(details_model, 'title', getattr(item, 'title', 'Unknown')),
            "year": getattr(details_model, 'year', getattr(item, 'year', None)),
            "plot": getattr(details_model, 'plot', getattr(details_model, 'description', None)),
            "rating": imdb_rating,
            "rating_value": imdb_rating_value,
            "poster_url": poster_url,
            "trailer": getattr(details_model, 'trailer', None),
            "type": item_type
        }
        
        # Extract seasons for TV series and anime
        if item_type in ["series", "anime"]:
            seasons_data = []
            try:
                # Try multiple paths to find season data
                seasons_list = None
                
                # Path 1: details_model.resData.resource.seasons
                if hasattr(details_model, 'resData'):
                    if hasattr(details_model.resData, 'resource') and hasattr(details_model.resData.resource, 'seasons'):
                        seasons_list = details_model.resData.resource.seasons
                    elif hasattr(details_model.resData, 'seasons'):
                        seasons_list = details_model.resData.seasons
                
                # Path 2: details_model.resource.seasons (fallback)
                elif hasattr(details_model, 'resource') and hasattr(details_model.resource, 'seasons'):
                    seasons_list = details_model.resource.seasons
                
                # Path 3: details_model.seasons
                elif hasattr(details_model, 'seasons'):
                    seasons_list = details_model.seasons
                
                # Path 4: Try to get from dict representation
                elif hasattr(details_model, 'dict'):
                    try:
                        model_dict = details_model.dict()
                        if 'resData' in model_dict:
                            if 'resource' in model_dict['resData'] and 'seasons' in model_dict['resData']['resource']:
                                seasons_list = model_dict['resData']['resource']['seasons']
                            elif 'seasons' in model_dict['resData']:
                                seasons_list = model_dict['resData']['seasons']
                        elif 'resource' in model_dict and 'seasons' in model_dict['resource']:
                            seasons_list = model_dict['resource']['seasons']
                    except:
                        pass
                
                # Extract season data
                if seasons_list:
                    for season in seasons_list:
                        # Handle both object and dict formats
                        if isinstance(season, dict):
                            season_num = season.get('se', season.get('season_number', 0))
                            max_ep = season.get('maxEp', season.get('max_episodes', season.get('episode_count', 0)))
                        else:
                            season_num = getattr(season, 'se', getattr(season, 'season_number', 0))
                            max_ep = getattr(season, 'maxEp', getattr(season, 'max_episodes', getattr(season, 'episode_count', 0)))
                        
                        if season_num and max_ep:
                            seasons_data.append({
                                "season_number": season_num,
                                "max_episodes": max_ep,
                            })
            except Exception as e:
                # Log error but don't fail the entire request
                print(f"Error extracting seasons: {e}")
            
            response["seasons"] = seasons_data
            
        return response
    except Exception as e:
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
            print(f"[STREAM] Using cached item: {getattr(target_item, 'title', 'Unknown')}")
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
            from urllib.parse import quote
            proxy_url = f"/api/proxy-stream?url={quote(str(media_file.url))}"
            return {"status": "success", "url": proxy_url, "title": target_item.title, "direct_url": str(media_file.url)}

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
        cmd = [mpv_path, str(media_file.url), f"--title={target_item.title}"]
        
        # Case-insensitive header map
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Add User-Agent
        if "user-agent" in headers_lower:
            cmd.append(f"--user-agent={headers_lower['user-agent']}")
            
        # Add Referer
        if "referer" in headers_lower:
            cmd.append(f"--referrer={headers_lower['referer']}")
            
        # Add other headers via http-header-fields
        other_headers = []
        allowed_headers = ["origin", "cookie", "authorization"]
        
        for k, v in headers.items():
            if k.lower() in allowed_headers:
                other_headers.append(f"{k}: {v}")
        
        if other_headers:
            cmd.append(f"--http-header-fields={','.join(other_headers)}")
        
        # Log the command
        print(f"[DEBUG] Launching MPV with command: {cmd}")
        with open("stream_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Launching command: {cmd}\n")
            f.write(f"URL: {media_file.url}\n")
            f.write(f"Headers: {headers}\n")
 
        # Run non-blocking using subprocess.Popen (more reliable on Windows for GUI apps)
        try:
            cmd = [str(arg) for arg in cmd]
            
            # Popen is non-blocking - it starts the process and returns immediately
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            print(f"[SUCCESS] Launched MPV (PID: {process.pid}) for: {target_item.title}")
        except Exception as launch_err:
            error_msg = f"{type(launch_err).__name__}: {str(launch_err)}"
            print(f"[CRITICAL] Failed to launch MPV: {error_msg}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to launch MPV: {error_msg}")
        
        return {"status": "streaming", "message": f"Streaming {target_item.title}..."}

    except HTTPException:
        raise
    except Exception as e:
        error_details = traceback.format_exc()
        with open("stream_error.log", "a") as f:
            f.write(f"Stream error: {e}\n")
            f.write(f"Traceback:\n{error_details}\n")
        print(f"Stream error: {e}")
        
        # If mode is 'url', return a JSON error response instead of raising
        if mode == "url":
            return {"status": "error", "message": str(e), "details": error_details}
        
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy-stream")
async def proxy_stream(url: str) -> StreamingResponse:
    """
    Proxy endpoint that streams video content with proper headers to bypass 403 Forbidden errors.
    This version uses a persistent global client and properly manages the response lifecycle.
    """
    try:
        # Extract headers from session
        headers = {}
        if hasattr(session, '_headers'):
            headers.update(session._headers)
        if hasattr(session, '_client') and hasattr(session._client, 'headers'):
            headers.update(session._client.headers)
        
        # Ensure we have a User-Agent
        if 'User-Agent' not in headers and 'user-agent' not in headers:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Stream the content from the source using the global client
        # We manually enter the stream to peek at the headers
        request = http_client.build_request("GET", url, headers=headers)
        response = await http_client.send(request, stream=True)
        
        if response.status_code >= 400:
            await response.aclose()
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Provider returned error: {response.status_code}"
            )
            
        content_type = response.headers.get('content-type', 'video/mp4')
        content_length = response.headers.get('content-length')
        
        async def generate():
            try:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 64): # Use larger chunks for video
                    yield chunk
            except Exception as stream_err:
                print(f"[STREAM ERROR] Exception during proxy streaming: {stream_err}")
                traceback.print_exc()
            finally:
                await response.aclose()
        
        response_headers = {
            'Accept-Ranges': 'bytes',
            'Content-Type': content_type,
        }
        if content_length:
            response_headers['Content-Length'] = content_length
            
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers=response_headers
        )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Proxy stream setup error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

