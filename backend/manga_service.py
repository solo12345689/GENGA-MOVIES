import httpx
import asyncio
import io
import zipfile
from typing import List, Optional, Any

class MangaService:
    BASE_URL = "https://api-consumet-org-mswp.onrender.com"
    PROVIDER = "mangapill"

    @staticmethod
    async def search(query: str) -> List[dict]:
        """
        Searches for manga using Consumet API.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{MangaService.BASE_URL}/manga/{MangaService.PROVIDER}/{query}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    print(f"[MangaService] Search error {resp.status_code} for {url}: {resp.text[:200]}")
                    return []
                
                try:
                    data = resp.json()
                    results = data.get('results', data)
                    if not isinstance(results, list):
                        return []
                    
                    return [{
                        "id": item.get('id'),
                        "title": item.get('title'),
                        "poster_url": item.get('image') or item.get('poster') or item.get('cover'),
                        "type": "manga",
                        "source": "manga"
                    } for item in results]
                except Exception as json_err:
                    print(f"[MangaService] JSON error for {url}: {json_err} | Body: {resp.text[:500]}")
                    return []
            except Exception as e:
                print(f"[MangaService] Search error: {e}")
                return []

    @staticmethod
    async def get_info(manga_id: str) -> Optional[dict]:
        """
        Fetches manga details and chapter list.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{MangaService.BASE_URL}/manga/{MangaService.PROVIDER}/info?id={manga_id}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                info = resp.json()
                # Group chapters by volume if possible
                chapters = info.get('chapters', [])
                volumes = {}
                for ch in chapters:
                    vol = ch.get('volume', 'No Volume')
                    if vol not in volumes:
                        volumes[vol] = []
                    volumes[vol].append({
                        "id": ch.get('id'),
                        "title": ch.get('title'),
                        "number": ch.get('chapterNumber'),
                        "releaseDate": ch.get('releaseDate')
                    })
                
                return {
                    "id": info.get('id'),
                    "title": info.get('title'),
                    "description": info.get('description'),
                    "poster_url": info.get('image') or info.get('poster') or info.get('cover'),
                    "status": info.get('status'),
                    "genres": info.get('genres', []),
                    "volumes": volumes,
                    "type": "manga"
                }
            except Exception as e:
                print(f"[MangaService] Info error: {e}")
                return None

    @staticmethod
    async def get_pages(chapter_id: str) -> List[dict]:
        """
        Fetches image URLs for a specific chapter.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{MangaService.BASE_URL}/manga/{MangaService.PROVIDER}/read?chapterId={chapter_id}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                
                pages = resp.json()
                if not isinstance(pages, list):
                    return []
                
                # Normalize pages
                return [{
                    "page": i + 1,
                    "img": p.get('img') if isinstance(p, dict) else p,
                    "headerForImage": {"Referer": "https://mangapill.com/"}
                } for i, p in enumerate(pages)]
            except Exception as e:
                print(f"[MangaService] Pages error: {e}")
                return []

    @staticmethod
    async def generate_pdf(chapter_id: str) -> Optional[io.BytesIO]:
        """
        Generates a PDF file containing all pages of a chapter.
        """
        import img2pdf
        pages = await MangaService.get_pages(chapter_id)
        if not pages:
            return None
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = []
            for p in pages:
                tasks.append(client.get(p['img'], headers=p['headerForImage']))
            
            responses = await asyncio.gather(*tasks)
            image_data = [resp.content for resp in responses if resp.status_code == 200]
            
            if not image_data:
                return None
            
            pdf_bytes = img2pdf.convert(image_data)
            return io.BytesIO(pdf_bytes)

    @staticmethod
    async def save_chapter_locally(chapter_id: str, manga_title: str, chapter_title: str) -> dict:
        """
        Downloads all pages of a chapter directly to a local folder.
        """
        from pathlib import Path
        import os
        
        pages = await MangaService.get_pages(chapter_id)
        if not pages:
            return {"status": "error", "message": "No pages found"}
        
        # Sanitize titles for filesystem
        safe_manga = "".join(c for c in manga_title if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_chapter = "".join(c for c in chapter_title if c.isalnum() or c in (' ', '_', '-')).strip()
        
        # Root directory for manga (project root)
        manga_root = Path(__file__).parent.parent / "manga"
        chapter_dir = manga_root / safe_manga / safe_chapter
        os.makedirs(chapter_dir, exist_ok=True)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = []
            for p in pages:
                tasks.append(client.get(p['img'], headers=p['headerForImage']))
            
            responses = await asyncio.gather(*tasks)
            saved_count = 0
            for i, resp in enumerate(responses):
                if resp.status_code == 200:
                    url = pages[i]['img']
                    ext = url.split('.')[-1].split('?')[0] if '.' in url else 'jpg'
                    if len(ext) > 4: ext = 'jpg'
                    filepath = chapter_dir / f"page_{i+1:03d}.{ext}"
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                    saved_count += 1
        
        return {
            "status": "success", 
            "message": f"Saved {saved_count} pages to {chapter_dir}",
            "path": str(chapter_dir)
        }

    @staticmethod
    async def create_chapter_zip(chapter_id: str, title: str) -> Optional[io.BytesIO]:
        """
        Creates a ZIP file containing all pages of a chapter.
        """
        pages = await MangaService.get_pages(chapter_id)
        if not pages:
            return None
        
        zip_buffer = io.BytesIO()
        async with httpx.AsyncClient(timeout=60.0) as client:
            # zipfile.ZipFile doesn't support async, but we can write to buffer
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                tasks = []
                for p in pages:
                    tasks.append(client.get(p['img'], headers=p['headerForImage']))
                
                responses = await asyncio.gather(*tasks)
                for i, resp in enumerate(responses):
                    if resp.status_code == 200:
                        # Try to get extension from URL
                        url = pages[i]['img']
                        ext = url.split('.')[-1].split('?')[0] if '.' in url else 'jpg'
                        if len(ext) > 4: ext = 'jpg' # Sanity check
                        zip_file.writestr(f"page_{i+1:03d}.{ext}", resp.content)
        
        zip_buffer.seek(0)
        return zip_buffer

