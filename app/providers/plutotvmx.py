"""
PlutoTV MX IPTV provider (Spanish live TV - Mexico).
Ported from streamflix-reborn/streamflix PlutoTvMxProvider.
Loads M3U playlist from GitHub.
"""
import base64
import re
import httpx
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, MediaDetails


class PlutoTvMxProvider(BaseProvider):
    name = "PlutoTV MX"
    base_url = "https://raw.githubusercontent.com"
    language = "es"

    _PLAYLIST = "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_mx.m3u"

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
        for line in text.split("\n"):
            t = line.strip()
            if t.startswith("#EXTINF"):
                m = re.search(r",(.+)$", t)
                name = m.group(1).strip() if m else ""
                m = re.search(r'tvg-logo="([^"]+)"', t)
                logo = m.group(1) if m else ""
                m = re.search(r'group-title="([^"]+)"', t)
                group = m.group(1) if m else "General"
            elif t.startswith("http"):
                if name:
                    channels.append({
                        "name": name, "url": t, "logo": logo or "",
                        "group": group or "General",
                    })
                    name = logo = group = ""
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
        raw = f"{ch['url']}|{ch['name']}|{ch['logo']}"
        return base64.b64encode(raw.encode()).decode()

    def _decode_id(self, idv: str) -> tuple:
        try:
            decoded = base64.b64decode(idv).decode()
            parts = decoded.split("|")
            return parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else ""
        except Exception:
            return idv, "Canal", ""

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        channels = await self._get_channels()
        start = (page - 1) * 50
        return [
            TvShow(id=self._create_id(ch), title=ch["name"], poster=ch["logo"])
            for ch in channels[start:start+50]
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
        return [
            TvShow(id=self._create_id(ch), title=ch["name"], poster=ch["logo"])
            for ch in channels if q in ch["name"].lower()
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
            overview=f"Canal en vivo: {name}",
        )

    async def get_servers(self, movie_id: str) -> list[Server]:
        url, name, _ = self._decode_id(movie_id)
        return [Server(id=url, name="PlutoTV Stream")]
