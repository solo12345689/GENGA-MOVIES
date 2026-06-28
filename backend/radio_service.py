import httpx
import asyncio

class RadioService:
    def __init__(self):
        self.base_url = "https://raw.githubusercontent.com/famelack/famelack-data/main/radio/raw"
        self.client = httpx.AsyncClient(timeout=20.0)
        self.cache = {}

    async def get_countries(self):
        url = f"{self.base_url}/countries_metadata.json"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                countries = []
                for code, info in data.items():
                    if info and info.get('hasChannels'):
                        countries.append({
                            "id": code.lower(),
                            "name": info.get('country', code),
                            "title": info.get('country', code),
                            "type": "country",
                            "source": "radio"
                        })
                return sorted(countries, key=lambda x: x['name'])
        except Exception as e:
            print(f"Radio get_countries error: {e}")
        return []

    async def get_channels_by_country(self, country_code):
        url = f"{self.base_url}/countries/{country_code.lower()}.json"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return [self._format_channel(c) for c in data if self._format_channel(c)]
        except Exception as e:
            print(f"Radio get_channels_by_country error: {e}")
        return []

    def _format_channel(self, c: dict):
        name = c.get('name', 'Unknown Station')
        # Audio streams are in 'sources.streams' or 'stream_urls'
        sources = c.get('sources') or {}
        stream_urls = [u for u in (sources.get('streams') or c.get('stream_urls') or []) if u and u.strip()]

        if not stream_urls:
            return None

        return {
            "id": c.get('nanoid', name.replace(' ', '_').lower()),
            "title": name,
            "poster_url": c.get('logo', ''),
            "url": stream_urls[0],
            "stream_type": "hls", # Radio streams are also usually HLS/AAC
            "source": "radio",
            "type": "channel"
        }

    async def close(self):
        await self.client.aclose()
