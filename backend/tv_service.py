import httpx
import re

class TVService:
    def __init__(self):
        self.base_url = "https://raw.githubusercontent.com/famelack/famelack-data/main/tv/raw"
        self.client = httpx.AsyncClient(timeout=20.0)
        self.cache = {}

    async def get_countries(self):
        """Fetches the list of countries with channels."""
        if 'countries' in self.cache:
            return self.cache['countries']

        url = f"{self.base_url}/countries_metadata.json"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Data format: {"AD": {"country": "Andorra", "hasChannels": true, ...}, ...}
            countries = []
            for code, info in data.items():
                if isinstance(info, dict) and info.get('hasChannels'):
                    flag = ''
                    if len(code) == 2 and code.isalpha():
                        flag = ''.join(chr(0x1F1E6 + ord(c) - ord('A')) for c in code.upper())
                    name = info.get('country', code)
                    countries.append({
                        "id": code.lower(),
                        "title": f"{flag} {name}" if flag else name,
                        "name": name,
                        "poster_url": "",
                        "type": "country",
                        "source": "tv"
                    })

            countries.sort(key=lambda x: x["name"])
            self.cache['countries'] = countries
            return countries
        except Exception as e:
            print(f"[TVService] Error fetching countries: {e}")
            import traceback; traceback.print_exc()
            return []

    async def get_channels_by_country(self, country_code: str):
        """Fetches channels for a specific country code."""
        code = country_code.lower()
        cache_key = f"country_{code}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"{self.base_url}/countries/{code}.json"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            channels = response.json()
            result = []
            for c in channels:
                formatted = self._format_channel(c)
                if formatted:
                    result.append(formatted)
            self.cache[cache_key] = result
            return result
        except Exception as e:
            print(f"[TVService] Error fetching channels for country {code}: {e}")
            import traceback; traceback.print_exc()
            return []

    async def get_channels_by_category(self, category: str):
        """Fetches channels for a specific category."""
        cat = category.lower()
        cache_key = f"cat_{cat}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"{self.base_url}/categories/{cat}.json"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            channels = response.json()
            result = []
            for c in channels:
                formatted = self._format_channel(c)
                if formatted:
                    result.append(formatted)
            self.cache[cache_key] = result
            return result
        except Exception as e:
            print(f"[TVService] Error fetching channels for category {cat}: {e}")
            return []

    def _extract_youtube_id(self, url: str):
        """
        Extracts the video ID or channel ID from a YouTube embed URL.
        Examples:
          https://www.youtube-nocookie.com/embed/byG7EGw9NPs  -> byG7EGw9NPs
          https://www.youtube.com/embed/live_stream?channel=UCxxxxxx -> UCxxxxxx (channel)
        Returns (id, id_type) where id_type is 'video' or 'channel'
        """
        # Check for live_stream?channel=UC... format
        channel_match = re.search(r'[?&]channel=([A-Za-z0-9_-]+)', url)
        if channel_match:
            return channel_match.group(1), 'channel'

        # Standard embed format: /embed/VIDEO_ID
        video_match = re.search(r'/embed/([A-Za-z0-9_-]{11})', url)
        if video_match:
            return video_match.group(1), 'video'

        return None, None

    def _format_channel(self, c: dict):
        name = c.get('name', 'Unknown Channel')

        sources = c.get('sources') or {}
        iptv_urls = [u for u in (sources.get('streams') or c.get('stream_urls') or []) if u and u.strip()]
        youtube_urls = [u for u in (sources.get('youtube') or c.get('youtube_urls') or []) if u and u.strip()]

        logo_raw = c.get('logo', '')
        poster_url = f"/api/image-proxy?url={logo_raw}" if (logo_raw and logo_raw.startswith('http')) else logo_raw

        # Priority 1: Direct IPTV (HLS)
        if iptv_urls:
            return {
                "id": c.get('nanoid', name.replace(' ', '_').lower()),
                "title": name,
                "poster_url": poster_url,
                "url": iptv_urls[0],
                "stream_type": "hls",
                "source": "tv",
                "type": "channel"
            }
        
        # Priority 2: YouTube Live (Local HLS resolution via yt-dlp)
        if youtube_urls:
            yt_url = youtube_urls[0]
            yt_id, id_type = self._extract_youtube_id(yt_url)
            if yt_id:
                return {
                    "id": c.get('nanoid', name.replace(' ', '_').lower()),
                    "title": name,
                    "poster_url": poster_url,
                    "yt_id": yt_id,
                    "stream_type": "youtube_hls",
                    "source": "tv",
                    "type": "channel"
                }
            
            # Fallback: YouTube Embed
            return {
                "id": c.get('nanoid', name.replace(' ', '_').lower()),
                "title": name,
                "poster_url": poster_url,
                "url": yt_url,
                "stream_type": "embed",
                "source": "tv",
                "type": "channel"
            }
        
        return None

    async def parse_m3u_playlist(self, url: str):
        """Fetches and parses an M3U playlist URL with memory caching for instant loads."""
        cache_key = f"m3u_{url}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            resp = await self.client.get(url, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text

            lines = text.splitlines()
            channels = []
            current = None
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#EXTINF:'):
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line, re.IGNORECASE)
                    raw_logo = logo_match.group(1) if logo_match else ''
                    logo_url = f"/api/image-proxy?url={raw_logo}" if (raw_logo and raw_logo.startswith('http')) else raw_logo
                    comma_idx = line.rfind(',')
                    title = line[comma_idx + 1:].strip() if comma_idx != -1 else 'Channel'
                    current = {"title": title, "poster_url": logo_url, "url": ""}
                elif not line.startswith('#') and current:
                    current["url"] = line
                    current["id"] = f"m3u_{len(channels)}_{idx}"
                    current["stream_type"] = "hls" if ".m3u8" in line else ("embed" if ("youtube" in line or "youtu.be" in line) else "hls")
                    current["source"] = "tv"
                    current["type"] = "channel"
                    channels.append(current)
                    current = None

            self.cache[cache_key] = channels
            return channels
        except Exception as e:
            print(f"[TVService] Error parsing M3U playlist {url}: {e}")
            return []

    async def close(self):
        await self.client.aclose()
