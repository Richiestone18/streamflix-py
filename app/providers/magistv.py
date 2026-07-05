"""
MAGISTV / CineCity IPTV provider (Spanish live TV).
Ported from streamflix-reborn/streamflix CineCityProvider.
Loads M3U playlist from GitHub.
"""
import base64
import re
import httpx
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, MediaDetails


class MagistvProvider(BaseProvider):
    name = "MAGISTV"
    base_url = "https://raw.githubusercontent.com"
    language = "es"

    # Base64-encoded playlist URL
    _OBFUSCATED = "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0NJTkVDSVRZMjAyMy9jaW5lY2l0eS9jaW5lY2l0eS5uZXQvcHJpbmNpcGFsLm0zdQ=="
    _PLAYLIST = base64.b64decode(_OBFUSCATED).decode()

    def __init__(self):
        self.http = None
        self._cache = None
        self._cache_time = 0

    async def _get(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_m3u(self, text: str) -> list:
        channels = []
        name = logo = group = ""
        ua = referrer = None
        for line in text.split("\n"):
            t = line.strip()
            if t.startswith("#EXTINF"):
                m = re.search(r",(.+)$", t)
                name = m.group(1).strip() if m else ""
                m = re.search(r'tvg-logo="([^"]+)"', t)
                logo = m.group(1) if m else ""
                m = re.search(r'group-title="([^"]+)"', t)
                group = m.group(1) if m else ""
                m = re.search(r'http-user-agent="([^"]+)"', t)
                ua = m.group(1) if m else None
                m = re.search(r'http-referrer="([^"]+)"', t)
                referrer = m.group(1) if m else None
            elif t.startswith("#EXTVLCOPT:"):
                if "http-user-agent=" in t:
                    ua = t.split("http-user-agent=")[1].strip()
                if "http-referrer=" in t:
                    referrer = t.split("http-referrer=")[1].strip()
            elif t.startswith("http"):
                if name:
                    channels.append({
                        "name": name, "url": t, "logo": logo or "",
                        "group": group or "General", "ua": ua, "referrer": referrer,
                    })
                    name = logo = group = ""
                    ua = referrer = None
        return channels

    async def _get_channels(self) -> list:
        import time
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < 1800:
            return self._cache
        try:
            text = await self._get(self._PLAYLIST)
            self._cache = self._parse_m3u(text)
            self._cache_time = now
            return self._cache
        except Exception:
            return self._cache or []

    def _create_id(self, ch: dict) -> str:
        raw = f"{ch['url']}|{ch['name']}|{ch['logo']}|{ch.get('ua','')}|{ch.get('referrer','')}"
        return base64.b64encode(raw.encode()).decode()

    def _decode_id(self, idv: str) -> tuple:
        try:
            decoded = base64.b64decode(idv).decode()
            parts = decoded.split("|")
            url = parts[0] if len(parts) > 0 else ""
            name = parts[1] if len(parts) > 1 else ""
            logo = parts[2] if len(parts) > 2 else ""
            ua = parts[3] if len(parts) > 3 else ""
            ref = parts[4] if len(parts) > 4 else ""
            # Convert "None" string to empty
            ua = "" if ua == "None" else ua
            ref = "" if ref == "None" else ref
            return url, name, logo, ua, ref
        except Exception:
            return idv, "Canal", "", "", ""

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        channels = await self._get_channels()
        start = (page - 1) * 50
        page_channels = channels[start:start+50]
        return [
            TvShow(id=self._create_id(ch), title=ch["name"], poster=ch["logo"])
            for ch in page_channels
        ]

    async def search(self, query: str, page: int = 1) -> list:
        channels = await self._get_channels()
        if not query:
            groups = set()
            for ch in channels:
                if ch["group"]:
                    groups.add(ch["group"])
            return [{"id": g, "name": g, "type": "genre"} for g in sorted(groups)]
        q = query.lower()
        results = [ch for ch in channels if q in ch["name"].lower() or q in ch["group"].lower()]
        return [
            TvShow(id=self._create_id(ch), title=ch["name"], poster=ch["logo"])
            for ch in results[:80]
        ]

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        channels = await self._get_channels()
        filtered = [ch for ch in channels if genre_id.lower() in ch["group"].lower()]
        start = (page - 1) * 40
        return [
            TvShow(id=self._create_id(ch), title=ch["name"], poster=ch["logo"])
            for ch in filtered[start:start+40]
        ]

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        url, name, logo = self._decode_id(item_id)
        return MediaDetails(
            id=item_id, title=name, type="movie",
            poster=logo if logo else None,
            overview=f"Transmisión en vivo: {name}\nFuente: MAGISTV",
        )

    async def get_servers(self, movie_id: str) -> list[Server]:
        url, name, _, ua, ref = self._decode_id(movie_id)
        # Encode ua/ref into the server id so the frontend can pass them to the proxy
        server_id = url
        if ua or ref:
            # Store headers in server id as url|ua|ref
            import base64 as b64
            server_id = b64.b64encode(f"{url}|{ua}|{ref}".encode()).decode()
        return [Server(id=server_id, name="MAGISTV Stream")]
