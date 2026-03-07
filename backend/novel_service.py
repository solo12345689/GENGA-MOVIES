import httpx
import asyncio
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

LIGHTNOVEL_API = "https://lightnovel-crawler-z48o.onrender.com"


class NovelService:
    def __init__(self, base_url: str = LIGHTNOVEL_API):
        self.base_url = base_url
        self.timeout = httpx.Timeout(12.0, connect=5.0)

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"[NovelService] Requesting: {url} with params {params}")
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    print(f"[NovelService] Error {resp.status_code}: {resp.text[:200]}")
                    return None
                return resp.json()
            except Exception as e:
                print(f"[NovelService] Exception for {endpoint}: {str(e)}")
                return None


    # ── DuckDuckGo Search ─────────────────────────────────────────────────────

    async def _ddg_search(self, search_query: str, limit: int = 20) -> List[Dict]:
        """
        Search novels via DuckDuckGo HTML scraping.
        Uses a whitelist of known novel sites and filters out non-novel pages.
        """
        NOVEL_DOMAINS = {
            'novelfire.net', 'novelbin.com', 'readnovelfull.com', 'wuxiaworld.com',
            'royalroad.com', 'scribblehub.com', 'novelfull.com', 'webnovel.com',
            'lightnovelworld.co', 'lightnovelworld.com', 'mtlnovel.com',
            'boxnovel.com', 'novelhall.com', 'volarenovels.com',
            'creativenovels.com', 'readernovel.net', 'readlightnovel.me',
            'bestlightnovel.com', 'moonquill.com',
        }

        # URL path prefixes that indicate non-novel pages (author pages, categories, etc.)
        BAD_PATH_PATTERNS = ('/a/', '/tag/', '/genre/', '/author/', '/category/',
                             '/catalog', '/search', '/page/', '/list')

        def do_search():
            try:
                # Refined query to prioritize direct matches
                query_payload = f'"{search_query}" novel read online'
                res = httpx.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query_payload},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"},
                    timeout=15,
                    follow_redirects=True,
                )
                soup = BeautifulSoup(res.text, "html.parser")
                items = []
                seen_urls = set()
                query_words = [w.lower() for w in search_query.split() if len(w) > 2]

                for a in soup.find_all("a", class_="result__a", href=True):
                    href = a["href"]
                    title = a.text.strip()
                    
                    if not href.startswith("http") or "duckduckgo.com" in href:
                        continue
                        
                    # Title Validation: Ensure at least one significant word from query is in title
                    title_lower = title.lower()
                    if query_words and not any(w in title_lower for w in query_words):
                        continue

                    domain = href.split("/")[2] if "://" in href else ""
                    base_domain = ".".join(domain.split(".")[-2:])
                    if base_domain not in NOVEL_DOMAINS and domain not in NOVEL_DOMAINS:
                        continue

                    # Filter out author pages, category pages, catalog pages etc.
                    path = href.split(domain, 1)[-1] if domain in href else ""
                    if any(path.startswith(p) for p in BAD_PATH_PATTERNS):
                        continue

                    # Skip URLs that are clearly not novel detail pages
                    if href.count('/') < 4:
                        continue

                    if href not in seen_urls:
                        seen_urls.add(href)
                        items.append({
                            "id": href,
                            "title": title,
                            "url": href,
                            "source": "novel",
                            "type": "novel",
                            "domain": domain,
                            "poster_url": None,
                            "author": None,
                            "chapters": 0,
                            "volumes": 0,
                        })
                print(f"[DDG] Found {len(items)} relevant novel-page results for '{search_query}'")
                return items[:limit]
            except Exception as e:
                print(f"[DDG] Search failed: {e}")
                return []

        return await asyncio.to_thread(do_search)

    async def _get_cover_for_url(self, url: str) -> Optional[str]:
        """
        Get cover image for a novel URL.
        Uses site-specific tricks before falling back to og:image scraping.
        """
        import re

        # WebNovel: derive cover from book ID in URL
        # e.g. webnovel.com/book/title_12507348206677105 → book ID = 12507348206677105
        wn_match = re.search(r'webnovel\.com/book/[^_]+_(\d+)', url)
        if wn_match:
            book_id = wn_match.group(1)
            return f"https://img.webnovel.com/bookcover/{book_id}/300/300.jpg"

        # Royal Road: cover is in og:image (SSR-friendly)
        # NovelFire: og:image works
        # NovelBin: og:image works on novel pages (not author pages)
        # Default: scrape og:image from the page
        def do_scrape():
            try:
                res = httpx.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=10,
                    follow_redirects=True,
                )
                soup = BeautifulSoup(res.text, "html.parser")
                og = soup.find("meta", property="og:image")
                if og and og.get("content"):
                    return og["content"]
                tw = soup.find("meta", attrs={"name": "twitter:image"})
                if tw and tw.get("content"):
                    return tw["content"]
                # Try common novel site cover selectors
                img = (soup.select_one(".book-img img") or
                       soup.select_one(".novel-cover img") or
                       soup.select_one(".cover img") or
                       soup.select_one("img.lazy[data-src]"))
                if img:
                    return img.get("data-src") or img.get("src")
                return None
            except Exception:
                return None
        return await asyncio.to_thread(do_scrape)

    async def _is_relevant(self, title: str, query: str) -> bool:
        """
        Check if a title is relevant to the search query.
        """
        if not title or not query:
            return False
            
        title_lower = title.lower()
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        
        # If no significant query words, assume relevance
        if not query_words:
            return True
            
        # Ensure at least one significant word matches
        return any(w in title_lower for w in query_words)

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_novels(self, query: str, limit: int = 20):
        """
        Search novels. Uses DuckDuckGo as a fallback if the crawler returns
        no results or only irrelevant "junk" results.
        """
        search_query = (query or "").strip()

        # Skip empty or homepage queries
        if not search_query or search_query.lower() in ("trending", "popular", "home"):
            return []

        # 1. Try LNCrawl API first
        data = await self._get("/api/novel/search", {"q": search_query, "limit": limit})
        lncrawl_results = []
        if data and isinstance(data, dict):
            raw_results = data.get("results", [])
            seen_urls = set()
            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                
                title = item.get("title", "Unknown")
                url = item.get("url")
                
                # Check Relevance (Phase 1)
                if not await self._is_relevant(title, search_query):
                    # print(f"[NovelService] Filtering out irrelevant crawler result: {title}")
                    continue

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    lncrawl_results.append({
                        "id": item.get("id"),
                        "title": title,
                        "poster_url": item.get("cover"),
                        "url": url,
                        "source": "novel",
                        "type": "novel",
                        "author": item.get("authors"),
                        "chapters": item.get("chapters", 0),
                        "volumes": item.get("volumes", 0),
                        "domain": item.get("domain"),
                    })

        # 2. If LNCrawl returned nothing or only junk, use DuckDuckGo
        if not lncrawl_results:
            print(f"[NovelService] No relevant crawler results for '{search_query}'. Falling back to DuckDuckGo...")
            lncrawl_results = await self._ddg_search(search_query, limit)

        # 3. Enrich top results with posters if missing
        if lncrawl_results:
            results_to_enrich = []
            for i, r in enumerate(lncrawl_results[:12]):
                if not r.get("poster_url"):
                    results_to_enrich.append((i, r["url"]))
            
            if results_to_enrich:
                print(f"[NovelService] Enriching {len(results_to_enrich)} results with covers...")
                cover_tasks = [self._get_cover_for_url(url) for _, url in results_to_enrich]
                covers = await asyncio.gather(*cover_tasks, return_exceptions=True)
                
                for (idx, _), cover in zip(results_to_enrich, covers):
                    if isinstance(cover, str) and cover:
                        lncrawl_results[idx]["poster_url"] = cover

        return lncrawl_results

    async def _scrape_info_direct(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Directly scrape novel metadata from RoyalRoad, NovelFire, etc. as a fallback.
        """
        print(f"[NovelService] Direct info scraping from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
        }
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                soup = BeautifulSoup(resp.text, "html.parser")
                title = "Unknown Novel"
                synopsis = ""
                poster_url = None
                chapters = []

                if "royalroad.com" in url:
                    title = soup.find("h1").text.strip() if soup.find("h1") else title
                    desc_div = soup.find("div", class_="description")
                    synopsis = desc_div.text.strip() if desc_div else ""
                    img = soup.find("img", class_="thumbnail")
                    poster_url = img["src"] if img and img.has_attr("src") else None
                    
                    for row in soup.find_all("tr", class_="chapter-row"):
                        a = row.find("a", href=True)
                        if a:
                            chapters.append({
                                "id": a["href"],
                                "title": a.text.strip(),
                                "url": "https://www.royalroad.com" + a["href"] if a["href"].startswith("/") else a["href"]
                            })

                elif "novelfire.net" in url:
                    title_tag = soup.find("h1", class_="novel-title")
                    title = title_tag.text.strip() if title_tag else title
                    
                    desc_div = soup.find("div", class_="content", attrs={"expand-wrapper": ""}) or soup.find("div", class_="content")
                    synopsis = desc_div.text.strip() if desc_div else ""
                    
                    img = soup.select_one(".glass-background img") or soup.select_one("header.novel-header img")
                    poster_url = img["src"] if img and img.has_attr("src") else None
                    
                    # Try /chapters subpage for full list
                    ch_url = url.rstrip("/") + "/chapters"
                    print(f"[NovelService] Fetching NovelFire chapters from: {ch_url}")
                    ch_resp = await client.get(ch_url)
                    if ch_resp.status_code == 200:
                        ch_soup = BeautifulSoup(ch_resp.text, "html.parser")
                        for a in ch_soup.select("article#chapter-list-page a[href]"):
                            strong_tag = a.find("strong")
                            num_tag = a.find("span")
                            chapters.append({
                                "id": a["href"],
                                "title": strong_tag.text.strip() if strong_tag else a.text.strip(),
                                "number": num_tag.text.strip() if num_tag else None,
                                "url": "https://novelfire.net" + a["href"] if a["href"].startswith("/") else a["href"]
                            })

                if chapters:
                    return {
                        "id": url,
                        "title": title,
                        "synopsis": synopsis,
                        "poster_url": poster_url,
                        "volumes": {"Chapters": chapters},
                        "type": "novel",
                        "source": "novel",
                        "hasFullDetails": True,
                    }
            except Exception as e:
                print(f"[NovelService] Direct info scrape exception: {str(e)}")
        return None

    async def get_novel_info(self, novel_id: Optional[str] = None, url: Optional[str] = None):
        """
        Fetch novel details + chapters.
        1. Try Crawler ID
        2. Try Crawler URL
        3. Try Direct Scrape Fallback
        """
        params = {}
        target_url = url
        if novel_id:
            params["id"] = novel_id
            if novel_id.startswith("http"):
                target_url = novel_id
        elif url:
            params["id"] = url
            params["url"] = url
            target_url = url

        if not params:
            return None

        # Phase 1 & 2: Crawler
        data = await self._get("/api/novel/info", params)
        if data and data.get("title") and (data.get("chapters") or data.get("volumes")):
            # Group chapters by volume for the UI
            api_volumes = data.get("volumes", [])
            api_chapters = data.get("chapters", [])
            
            # Sort chapters by serial number to ensure correct order
            api_chapters.sort(key=lambda x: x.get("serial") or 0)
            
            volumes = {}
            if api_volumes:
                for vol in api_volumes:
                    v_id = vol.get("id")
                    vol_title = vol.get("title") or f"Volume {vol.get('serial', 1)}"
                    volumes[vol_title] = [
                        {
                            "id": ch.get("id"),
                            "title": ch.get("title"),
                            "number": ch.get("serial"),
                            "url": ch.get("url"),
                        }
                        for ch in api_chapters if ch.get("volume_id") == v_id
                    ]
            else:
                volumes["Chapters"] = [
                    {
                        "id": ch.get("id"),
                        "title": ch.get("title"),
                        "number": ch.get("serial"),
                        "url": ch.get("url"),
                    }
                    for ch in api_chapters
                ]

            final_data = {
                "id": data.get("id"),
                "title": data.get("title"),
                "synopsis": data.get("synopsis"),
                "poster_url": data.get("cover") or data.get("poster_url"),
                "authors": data.get("authors"),
                "tags": data.get("tags", []),
                "language": data.get("language"),
                "volumes": volumes,
                "type": "novel",
                "source": "novel",
                "hasFullDetails": True,
            }

            # Enrich poster if missing from crawler data
            if not final_data["poster_url"] and target_url:
                print(f"[NovelService] Detail poster missing. Fetching: {target_url}")
                final_data["poster_url"] = await self._get_cover_for_url(target_url)

            return final_data

        # Phase 3: Direct Scrape Fallback
        if target_url:
            print(f"[NovelService] Crawler info fetch failed (or incomplete). Attempting direct scrape: {target_url}")
            return await self._scrape_info_direct(target_url)

        return None


    async def _scrape_direct(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Directly scrape a novel site if the crawler fails. 
        Supports RoyalRoad, NovelFire, and generic patterns.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
        }
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15) as client:
            try:
                print(f"[NovelService] Direct scraping: {url}")
                resp = await client.get(url)
                if resp.status_code != 200:
                    print(f"[NovelService] Direct scrape failed with status {resp.status_code}")
                    return None
                
                soup = BeautifulSoup(resp.text, "html.parser")
                body = ""
                
                # Site-specific selectors
                if "royalroad.com" in url:
                    content = soup.find("div", class_="chapter-content")
                    if content:
                        body = str(content)
                elif "novelfire.net" in url:
                    content = soup.find("div", id="content") or soup.find("div", id="chr-content") or soup.find("div", class_="chapter-content")
                    if content:
                        body = str(content)
                else:
                    # Common novel site containers
                    for selector in ["div#content", "div.chapter-c", "div#chapter-content", "div.reader-content", "div#chr-content"]:
                        tag, identifier = selector.split(".") if "." in selector else selector.split("#")
                        content = soup.find(tag, class_=identifier) if "." in selector else soup.find(tag, id=identifier)
                        if content:
                            body = str(content)
                            break
                
                if body:
                    print(f"[NovelService] Successfully scraped {len(body)} characters directly.")
                    return {
                        "body": body,
                        "url": url,
                        "format": "html"
                    }
            except Exception as e:
                print(f"[NovelService] Direct scrape exception for {url}: {str(e)}")
            
        return None

    async def get_chapter_content(self, chapter_id: Optional[str] = None, url: Optional[str] = None, format: str = "html"):
        """
        Fetch chapter content. 
        Attempts to fetch by chapter_id first (native crawler ID).
        Falls back to fetching by URL-as-ID if ID fails.
        Finally falls back to DIRECT SCRAPING if both fail.
        """
        # Phase 1: Native ID
        if chapter_id:
            data = await self._get("/api/novel/chapter", {"id": chapter_id, "format": format})
            if data and "body" in data:
                return data

        # Phase 2: URL Fallback (Crawler)
        if url:
            print(f"[NovelService] Native ID fetch failed. Falling back to Crawler URL-as-ID: {url}")
            data = await self._get("/api/novel/chapter", {"id": url, "url": url, "format": format})
            if data and "body" in data:
                return data

            # Phase 3: Direct Scrape (Robust Fallback)
            print(f"[NovelService] Crawler URL fetch failed. Attempting direct scrape: {url}")
            return await self._scrape_direct(url)

        return None


