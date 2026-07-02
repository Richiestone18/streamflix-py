"""
CableVisionHD provider — live TV channels (sports, series, movies, news).
Site: https://www.cablevisionhd.com
77+ live channels with iframe-based streaming.
"""
from bs4 import BeautifulSoup
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, MediaDetails
import httpx


class CableVisionHDProvider(BaseProvider):
    name = "CableVisionHD"
    base_url = "https://www.cablevisionhd.com"
    language = "es"

    def __init__(self):
        self.http = None  # Use httpx directly, no cloudscraper needed

    async def _get(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }, follow_redirects=True)
            resp.raise_for_status()
            return resp.text

    def _parse_channels(self, soup: BeautifulSoup) -> list:
        """Parse all channel cards from the page."""
        channels = []
        seen = set()
        for a in soup.select("a.channel-card, a[href*='-en-vivo.php']"):
            href = a.get("href", "")
            if href in seen or not href:
                continue
            seen.add(href)
            # Normalize URL
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = self.base_url + "/" + href.lstrip("/")

            img = a.select_one("img")
            name = ""
            if img:
                name = img.get("alt", "").strip()
            if not name:
                p = a.select_one("p")
                name = p.get_text(strip=True) if p else a.get_text(strip=True)
            name = name.replace("EN VIVO", "").strip()

            poster = img.get("src", "") if img else ""
            if poster and not poster.startswith("http"):
                poster = self.base_url + "/" + poster.lstrip("/")
            elif poster and poster.startswith("//"):
                poster = "https:" + poster

            if name and "-en-vivo.php" in href:
                channels.append({
                    "name": name,
                    "url": href,
                    "poster": poster,
                })
        return channels

    async def _get_all_channels(self) -> list:
        html = await self._get(self.base_url + "/")
        soup = BeautifulSoup(html, "lxml")
        return self._parse_channels(soup)

    async def get_movies(self, page: int = 1) -> list[Movie]:
        # All channels shown as movies (live TV)
        channels = await self._get_all_channels()
        start = (page - 1) * 24
        end = start + 24
        return [
            Movie(id=ch["url"], title=ch["name"], poster=ch["poster"])
            for ch in channels[start:end]
        ]

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        # Same channels available as TV shows
        channels = await self._get_all_channels()
        start = (page - 1) * 24
        end = start + 24
        return [
            TvShow(id=ch["url"], title=ch["name"], poster=ch["poster"])
            for ch in channels[start:end]
        ]

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return []  # No genres/categories
        channels = await self._get_all_channels()
        q_lower = query.lower()
        results = [ch for ch in channels if q_lower in ch["name"].lower()]
        start = (page - 1) * 24
        end = start + 24
        return [
            Movie(id=ch["url"], title=ch["name"], poster=ch["poster"])
            for ch in results[start:end]
        ]

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        return []

    async def get_servers(self, movie_id: str) -> list[Server]:
        """Fetch the channel page and extract the stream iframe URL."""
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Find the iframe that points to /stream/
        for iframe in soup.select("iframe[src*='/stream/']"):
            src = iframe.get("src", "")
            if src.startswith("/"):
                src = self.base_url + src
            elif src.startswith("//"):
                src = "https:" + src
            if src:
                servers.append(Server(id=src, name="En Vivo"))

        # Fallback: any iframe with allowfullscreen
        if not servers:
            for iframe in soup.select("iframe[allowfullscreen]"):
                src = iframe.get("src", "")
                if src and src.startswith("http"):
                    servers.append(Server(id=src, name="En Vivo"))

        return servers

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")

        # Extract title from og:title
        details = MediaDetails(
            id=item_id,
            title="",
            type="movie",
        )

        og_title = soup.select_one('meta[property="og:title"]')
        if og_title:
            details.title = og_title.get("content", "").strip()

        if not details.title:
            # Try h1 or title tag
            h1 = soup.select_one("h1, h2, .title")
            if h1:
                details.title = h1.get_text(strip=True)

        # Clean title
        if details.title:
            import re
            details.title = re.sub(r'\s*\|\s*.*$', '', details.title)
            details.title = re.sub(r'\s*EN VIVO\s*', '', details.title, flags=re.I).strip()

        # Poster from og:image
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            details.poster = og_img.get("content", "").strip()

        # Overview
        og_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
        if og_desc:
            details.overview = og_desc.get("content", "").strip()

        return details
