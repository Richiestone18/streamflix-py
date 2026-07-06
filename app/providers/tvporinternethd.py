"""
TvporinternetHD IPTV provider (Spanish live TV).
Ported from streamflix-reborn/streamflix TvporinternetHDProvider.
URL: https://www.tvporinternet2.com
"""
import re
import httpx
from typing import Optional
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, MediaDetails


class TvporinternetHDProvider(BaseProvider):
    name = "TvporinternetHD"
    base_url = "https://www.tvporinternet2.com"
    language = "es"

    _FORBIDDEN = ["paypal", "donar", "pago", "qr", "cafecito", "pay.png", "donate"]

    def __init__(self):
        self.http = None
        self._cache = None
        self._cache_time = 0

    async def _get(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"Referer": self.base_url + "/"})
            resp.raise_for_status()
            return resp.text

    def _is_forbidden(self, url: str) -> bool:
        lower = url.lower()
        return any(f in lower for f in self._FORBIDDEN)

    def _is_valid_channel(self, link: str, title: str) -> bool:
        clean = link.strip().rstrip("/")
        base = self.base_url.rstrip("/")
        return (link and title
                and (link.startswith(self.base_url) or not link.startswith("http"))
                and clean != base
                and "linktre.online" not in link
                and "paypal.com" not in link
                and "/category/" not in link
                and "/tag/" not in link
                and "Telegram" not in title
                and "Soporte" not in title)

    async def _parse_channels(self, html: str) -> list:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for a in soup.select("a"):
            link = a.get("abs:href") or a.get("href", "")
            img = a.select_one("img")
            if not img:
                continue
            raw_img = img.get("data-src") or img.get("data-lazy-src") or img.get("abs:src") or img.get("src", "")
            title = a.get("title") or img.get("alt") or a.get_text(strip=True)
            if self._is_forbidden(raw_img):
                continue
            if not self._is_valid_channel(link, title):
                continue
            final_url = link if link.startswith("http") else f"{self.base_url}/{link.lstrip('/')}"
            final_img = raw_img if raw_img.startswith("http") else f"{self.base_url}/{raw_img.lstrip('/')}"
            results.append(TvShow(id=final_url, title=title.strip(), poster=final_img, banner=final_img))
        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)
        return unique

    async def _get_channels(self) -> list:
        import time
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < 7200:
            return self._cache
        try:
            html = await self._get(self.base_url)
            self._cache = await self._parse_channels(html)
            self._cache_time = now
            return self._cache
        except Exception:
            return self._cache or []

    async def get_home(self) -> list[Category]:
        try:
            tv = await self.get_tv_shows()
            if tv:
                return [Category("Canales en Vivo", tv)]
            return []
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        channels = await self._get_channels()
        start = (page - 1) * 50
        return channels[start:start+50]

    async def search(self, query: str, page: int = 1) -> list:
        channels = await self._get_channels()
        if not query:
            return [
                {"id": "Todos", "name": "Todos los Canales", "type": "genre"},
                {"id": "Deportes", "name": "Deportes", "type": "genre"},
                {"id": "Noticias", "name": "Noticias", "type": "genre"},
                {"id": "Cine", "name": "Cine y Series", "type": "genre"},
            ]
        q = query.lower()
        return [ch for ch in channels if q in ch.title.lower()]

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        channels = await self._get_channels()
        filtered = []
        if genre_id == "Todos":
            filtered = channels
        elif genre_id == "Deportes":
            kw = ["sport", "espn", "fox", "tyc", "direct"]
            filtered = [c for c in channels if any(k in c.title.lower() for k in kw)]
        elif genre_id == "Noticias":
            kw = ["news", "noticia", "cnn", "24h"]
            filtered = [c for c in channels if any(k in c.title.lower() for k in kw)]
        elif genre_id == "Cine":
            kw = ["hbo", "max", "cine", "warner", "star", "tnt", "film", "movie"]
            filtered = [c for c in channels if any(k in c.title.lower() for k in kw)]
        start = (page - 1) * 50
        return filtered[start:start+50]

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        return MediaDetails(
            id=item_id, title="Canal en Vivo", type="movie",
            poster=None, overview="Canal de TV por Internet en vivo.",
        )

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            html = await self._get(movie_id)
            soup = BeautifulSoup(html, "lxml")
            servers = []
            for link in soup.select("a"):
                text = link.get_text(strip=True)
                href = link.get("abs:href") or link.get("href", "")
                if href and ("Opción" in text or "Servidor" in text or "FHD" in text):
                    url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
                    servers.append(Server(id=url, name=text))
            if not servers and soup.select("iframe"):
                servers.append(Server(id=movie_id, name="Reproductor Automático"))
            seen = set()
            unique = []
            for s in servers:
                if s.id not in seen:
                    seen.add(s.id)
                    unique.append(s)
            return unique
        except Exception:
            return []
