import httpx
import re

class TVService:
    def __init__(self):
        self.base_url = "https://raw.githubusercontent.com/famelack/famelack-data/c28d90693a3cf7466f1be73a290e209076b5b23f/channels/raw"
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
        """
        Normalizes a Famelack channel object to our standard item format.
        Schema: nanoid, name, iptv_urls (list), youtube_urls (list), language, country, isGeoBlocked

        For YouTube channels:
          - Uses ythls.armelin.one/channel/VIDEO_ID.m3u8 to convert to HLS (bypasses Error 153)
          - This is the same approach used by TV Garden and similar apps
        For IPTV channels:
          - Uses the direct M3U8 URL with HLS.js
        """
        name = c.get('name', 'Unknown Channel')

        # Filter out empty/blank URLs from both lists
        iptv_urls = [u for u in (c.get('iptv_urls') or []) if u and u.strip()]
        youtube_urls = [u for u in (c.get('youtube_urls') or []) if u and u.strip()]

        if iptv_urls:
            # Direct HLS stream — play with HLS.js
            stream_url = iptv_urls[0]
            stream_type = 'hls'
        elif youtube_urls:
            yt_url = youtube_urls[0]
            yt_id, id_type = self._extract_youtube_id(yt_url)

            if yt_id:
                # Use ythls.armelin.one proxy — converts YouTube live to HLS m3u8
                # This bypasses YouTube embed restrictions (Error 150/153)
                # Same approach used by TV Garden / gengas-garden
                stream_url = f"https://ythls.armelin.one/channel/{yt_id}.m3u8"
                stream_type = 'hls'
            else:
                # Fallback to embed (may show Error 153 for some channels)
                stream_url = yt_url
                stream_type = 'embed'
        else:
            # No valid stream URL — skip this channel entirely
            return None

        return {
            "id": c.get('nanoid', name.replace(' ', '_').lower()),
            "title": name,
            "poster_url": c.get('logo', ''),
            "url": stream_url,
            "all_urls": iptv_urls,
            "language": c.get('language', ''),
            "country": c.get('country', ''),
            "is_geo_blocked": c.get('isGeoBlocked', False),
            "stream_type": stream_type,
            "source": "tv",
            "type": "channel"
        }

    async def close(self):
        await self.client.aclose()
